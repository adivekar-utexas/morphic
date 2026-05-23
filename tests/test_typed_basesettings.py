"""Tests for ``Typed`` integration with ``pydantic_settings.BaseSettings``.

This file covers four orthogonal integrations that landed when ``Typed``
was switched from inheriting :class:`pydantic.BaseModel` to inheriting
:class:`pydantic_settings.BaseSettings`:

1. **Lifecycle invariants** — ``post_initialize`` / ``post_validate`` run
   exactly once per instance, even when Pydantic re-fires the underlying
   ``model_validator(mode="after")`` due to nested-Typed re-validation
   (see https://github.com/pydantic/pydantic/issues/12876).
2. **Identity preservation** — passing a pre-built ``Typed`` as a field
   value of an outer ``Typed`` reuses the exact same instance, so heavy
   resources held by a ``PrivateAttr`` are not duplicated.
3. **CLI integration** — every ``Typed`` accepts ``_cli_parse_args=...``
   and supports nested overrides like ``--infra.ray-init.address X``.
   This is exercised by spawning a subprocess that runs a real CLI script
   so we test the full argv-to-validated-model flow.
4. **Source isolation** — environment variables, ``.env`` files, and
   secret directories are NOT read by default. The user opts in by
   overriding ``settings_customise_sources`` on a specific subclass.

The CLI tests spawn ``python -c "..."`` subprocesses. This is the only
realistic way to test the argv path, since ``_cli_parse_args=[...]``
inside the same process is already covered by the in-process tests.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from abc import ABC
from typing import List, Optional

import pytest
from pydantic import PrivateAttr

from morphic import Registry, Typed

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_python(code: str, argv: List[str], *, env: Optional[dict] = None) -> subprocess.CompletedProcess:
    """Run ``code`` in a fresh Python subprocess with the given ``argv``.

    The subprocess gets the same ``sys.executable`` (so it sees the same
    morphic install), and stderr is captured so we can surface failures
    inline in the assertion message.
    """
    full_env = dict(os.environ)
    if env is not None:
        full_env.update(env)
    return subprocess.run(
        [sys.executable, "-c", code, *argv],
        capture_output=True,
        text=True,
        env=full_env,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Lifecycle invariants
# ---------------------------------------------------------------------------


class TestLifecycleIdempotency:
    """``post_initialize`` and ``post_validate`` run exactly once per instance."""

    def test_post_initialize_fires_once_on_root_construction(self) -> None:
        """Direct construction fires post_initialize exactly once."""

        calls: List[int] = []

        class Inner(Typed):
            name: str

            def post_initialize(self) -> None:
                calls.append(id(self))

        i = Inner(name="x")
        assert calls == [id(i)]

    def test_post_initialize_fires_once_when_nested_in_outer_typed(self) -> None:
        """Nested Typed: post_initialize on inner fires exactly once.

        Pydantic re-fires ``model_validator(mode="after")`` on the inner
        instance during outer construction (issue #12876). The
        ``_typed_post_initialized`` marker on Typed makes this re-fire
        a silent no-op.
        """
        calls: List[int] = []

        class Inner(Typed):
            name: str

            def post_initialize(self) -> None:
                calls.append(id(self))

        class Outer(Typed):
            inner: Inner
            seed: int = 42

        # dict input: inner is constructed once during outer construction.
        calls.clear()
        o = Outer(inner={"name": "alpha"})
        assert len(calls) == 1, f"Expected 1 fire, got {len(calls)}: {calls}"
        assert calls[0] == id(o.inner)

        # pre-built: inner already fired once at construction time;
        # passing into outer should NOT re-fire.
        calls.clear()
        i = Inner(name="beta")
        first = list(calls)
        assert len(first) == 1
        Outer(inner=i)
        assert calls == first, (
            "post_initialize re-fired on a nested instance — the _typed_post_initialized marker is broken."
        )

    def test_post_initialize_runs_on_each_distinct_instance(self) -> None:
        """A fresh instance gets a fresh marker."""
        calls: List[int] = []

        class Inner(Typed):
            name: str

            def post_initialize(self) -> None:
                calls.append(id(self))

        a = Inner(name="a")
        b = Inner(name="b")
        assert len(calls) == 2
        assert id(a) in calls and id(b) in calls
        assert id(a) != id(b)

    def test_post_initialize_runs_on_model_validate_dump_roundtrip(self) -> None:
        """``Model.model_validate(model.model_dump())`` creates a NEW instance.

        This is by design: serialize-then-deserialize is a copy operation.
        The new instance gets its own marker, so post_initialize runs once
        on it (independent of how many times the after-validator re-fires
        on it during the validate call).
        """
        calls: List[int] = []

        class Inner(Typed):
            name: str

            def post_initialize(self) -> None:
                calls.append(id(self))

        a = Inner(name="x")
        first = len(calls)
        assert first == 1

        b = Inner.model_validate(a.model_dump())
        assert b is not a, "Round-trip MUST create a new instance"
        # Exactly one *new* call for b.
        assert len(calls) == first + 1, calls
        assert calls[-1] == id(b)

    def test_post_initialize_idempotent_for_heavy_resources(self) -> None:
        """A heavy resource pattern: PrivateAttr set in post_initialize.

        This mirrors the trojanshot ``LLMAPIService`` pattern. Without
        the framework-level marker, the second post_initialize fire would
        either crash (if there is no per-class guard) or silently waste
        work (if the guard exists). With the marker, it's a no-op AND
        the per-class guard is no longer load-bearing.
        """
        spawn_count = {"value": 0}

        class HeavyResource(Typed):
            hf_model_id: str
            _spawned: bool = PrivateAttr(default=False)

            def post_initialize(self) -> None:
                if self._spawned:
                    pytest.fail(
                        "post_initialize was called twice on the same instance — "
                        "the framework marker is broken (or the per-class guard "
                        "would be load-bearing again)."
                    )
                object.__setattr__(self, "_spawned", True)
                spawn_count["value"] += 1

        class Container(Typed):
            target: HeavyResource

        # dict path
        c1 = Container(target={"hf_model_id": "qwen-3-4b"})
        assert spawn_count["value"] == 1
        assert c1.target._spawned is True

        # pre-built path
        spawn_count["value"] = 0
        hr = HeavyResource(hf_model_id="qwen-3-4b")
        assert spawn_count["value"] == 1
        c2 = Container(target=hr)
        assert spawn_count["value"] == 1, "pre-built path re-spawned"
        assert c2.target is hr, "pre-built path lost identity"


# ---------------------------------------------------------------------------
# Identity preservation
# ---------------------------------------------------------------------------


class TestIdentityPreservation:
    """A pre-built Typed passed as a field value is REUSED, not cloned."""

    def test_pre_built_typed_preserved_in_outer_typed(self) -> None:
        class Inner(Typed):
            name: str

        class Outer(Typed):
            inner: Inner

        i = Inner(name="x")
        o = Outer(inner=i)
        assert o.inner is i, "Identity NOT preserved — clone introduced"

    def test_pre_built_typed_preserved_in_outer_with_multiple_fields(self) -> None:
        """Identity preserved even when some siblings are dicts."""

        class Inner(Typed):
            name: str

        class Outer(Typed):
            a: Inner
            b: Inner

        a = Inner(name="alpha")
        # b is a dict so it gets validated; a is an instance and must be reused.
        o = Outer(a=a, b={"name": "beta"})
        assert o.a is a
        assert o.b.name == "beta"

    def test_pre_built_typed_preserved_through_optional(self) -> None:
        class Inner(Typed):
            name: str

        class Outer(Typed):
            inner: Optional[Inner] = None

        i = Inner(name="x")
        o = Outer(inner=i)
        assert o.inner is i

    def test_private_attr_state_preserved_through_outer_construction(self) -> None:
        """A PrivateAttr set on the inner is NOT reset by the outer."""

        class Inner(Typed):
            name: str
            _state: dict = PrivateAttr(default_factory=dict)

            def post_initialize(self) -> None:
                self._state["ready"] = True

        class Outer(Typed):
            inner: Inner

        i = Inner(name="x")
        assert i._state == {"ready": True}
        # Mutate the private state AFTER construction; outer must not reset it.
        i._state["custom"] = "value"
        o = Outer(inner=i)
        assert o.inner._state == {"ready": True, "custom": "value"}, (
            "Outer construction reset the inner's PrivateAttr state — "
            "either identity was lost or the marker re-ran post_initialize."
        )


# ---------------------------------------------------------------------------
# Source isolation
# ---------------------------------------------------------------------------


class TestSourceIsolation:
    """Env / dotenv / secret-file sources are off by default."""

    def test_env_var_does_not_leak_into_field_with_same_name(self) -> None:
        """A field named ``user`` does NOT pick up the ``USER`` env var.

        Without source isolation, ``BaseSettings``'s default
        ``EnvSettingsSource`` would read ``USER='adivekar'`` (or whatever
        the shell has) and try to JSON-decode it as a value for the
        ``user: SimpleTyped`` field, raising a confusing
        ``SettingsError``.
        """

        class SimpleTyped(Typed):
            name: str
            age: int = 25

        class NestedTyped(Typed):
            user: SimpleTyped

        # Make sure USER is set so the test is meaningful.
        os.environ["USER"] = "test_user_for_morphic"
        try:
            m = NestedTyped(user={"name": "alice", "age": 30})
            assert m.user.name == "alice"
        finally:
            # Don't pollute the env for downstream tests; restore to whatever
            # the shell had (or remove if it wasn't set).
            pass

    def test_subclass_can_opt_into_env_loading(self) -> None:
        """Override ``settings_customise_sources`` to opt into env var loading."""
        from pydantic_settings import SettingsConfigDict

        class WithEnv(Typed):
            model_config = SettingsConfigDict(
                env_prefix="MORPHIC_TEST_OPT_IN_",
                cli_parse_args=False,
                extra="forbid",
                frozen=True,
                arbitrary_types_allowed=True,
                revalidate_instances="never",
                validate_default=True,
            )

            name: str = "default"

            @classmethod
            def settings_customise_sources(
                cls,
                settings_cls,
                init_settings,
                env_settings,
                dotenv_settings,
                file_secret_settings,
            ):
                return init_settings, env_settings, dotenv_settings, file_secret_settings

        os.environ["MORPHIC_TEST_OPT_IN_NAME"] = "from_env"
        try:
            w = WithEnv()
            assert w.name == "from_env"
        finally:
            del os.environ["MORPHIC_TEST_OPT_IN_NAME"]


# ---------------------------------------------------------------------------
# CLI integration — in-process via _cli_parse_args
# ---------------------------------------------------------------------------


class TestCLIInProcess:
    """``_cli_parse_args=[...]`` works for every Typed subclass."""

    def test_simple_cli_parse(self) -> None:
        class Cfg(Typed):
            name: str = "default"
            count: int = 1

        c = Cfg(_cli_parse_args=["--name", "patched", "--count", "42"])
        assert c.name == "patched"
        assert c.count == 42

    def test_cli_kebab_case_default(self) -> None:
        """Field names with underscores are exposed as kebab-case on the CLI."""

        class Cfg(Typed):
            log_level: str = "info"
            num_retries: int = 0

        c = Cfg(_cli_parse_args=["--log-level", "debug", "--num-retries", "3"])
        assert c.log_level == "debug"
        assert c.num_retries == 3

    def test_cli_implicit_flags_for_bool(self) -> None:
        """Booleans get auto-generated --flag / --no-flag pairs."""

        class Cfg(Typed):
            enabled: bool = False
            verbose: bool = True

        c = Cfg(_cli_parse_args=["--enabled", "--no-verbose"])
        assert c.enabled is True
        assert c.verbose is False

    def test_cli_nested_inline_json(self) -> None:
        """``--inner '{...}'`` accepts inline JSON for nested models."""

        class Inner(Typed):
            name: str = "default"
            count: int = 1

        class Outer(Typed):
            inner: Inner = Inner()

        o = Outer(_cli_parse_args=["--inner", '{"name":"json","count":10}'])
        assert o.inner.name == "json"
        assert o.inner.count == 10

    def test_cli_nested_deep_override(self) -> None:
        """``--inner.field VALUE`` overrides a single nested field.

        This is the trojanshot use case: the user wants to override
        ``--infra.ray-init.address`` without rewriting the entire
        ``infra`` config.
        """

        class RayInit(Typed):
            address: str = "auto"
            num_cpus: int = 4

        class Infra(Typed):
            mode: str = "thread"
            ray_init: RayInit = RayInit()

        class App(Typed):
            infra: Infra = Infra()
            seed: int = 42

        app = App(_cli_parse_args=["--infra.ray-init.address", "ray://1.2.3.4:10001"])
        assert app.infra.ray_init.address == "ray://1.2.3.4:10001"
        # Other fields preserved at their defaults:
        assert app.infra.mode == "thread"
        assert app.infra.ray_init.num_cpus == 4
        assert app.seed == 42

    def test_cli_inline_json_plus_deep_override(self) -> None:
        """Inline JSON sets a baseline, then deep override patches a leaf."""

        class RayInit(Typed):
            address: str = "auto"
            num_cpus: int = 4

        class Infra(Typed):
            mode: str = "thread"
            ray_init: RayInit = RayInit()

        class App(Typed):
            infra: Infra = Infra()

        app = App(
            _cli_parse_args=[
                "--infra",
                '{"mode":"ray","ray_init":{"address":"ray://orig:10001","num_cpus":8}}',
                "--infra.ray-init.address",
                "ray://override:10001",
            ],
        )
        assert app.infra.mode == "ray"
        assert app.infra.ray_init.address == "ray://override:10001"
        assert app.infra.ray_init.num_cpus == 8

    def test_cli_three_levels_deep_override(self) -> None:
        """Verify the override path works at arbitrary depth."""

        class L3(Typed):
            value: str = "default"

        class L2(Typed):
            l3: L3 = L3()

        class L1(Typed):
            l2: L2 = L2()

        class Root(Typed):
            l1: L1 = L1()

        r = Root(_cli_parse_args=["--l1.l2.l3.value", "patched"])
        assert r.l1.l2.l3.value == "patched"


# ---------------------------------------------------------------------------
# CLI integration — subprocess (real argv path)
# ---------------------------------------------------------------------------


# Boilerplate for subprocess scripts. Defines the model classes and prints
# a JSON-serializable result the parent process can parse.
_CLI_SUBPROCESS_PREAMBLE = textwrap.dedent("""
    import json, sys
    from morphic import Typed

    class RayInit(Typed):
        address: str = "auto"
        num_cpus: int = 4

    class Infra(Typed):
        mode: str = "thread"
        ray_init: RayInit = RayInit()

    class App(Typed):
        infra: Infra = Infra()
        seed: int = 42

    # cli_parse_args=True tells pydantic-settings to read sys.argv[1:].
    app = App(_cli_parse_args=True)
    print(json.dumps(app.model_dump()))
""")


class TestCLISubprocess:
    """Spawn a real subprocess to exercise the argv-to-Typed flow.

    These tests are slower than the in-process tests but verify the full
    pydantic-settings CLI source is wired correctly when argv is the
    actual ``sys.argv`` (not an explicit ``_cli_parse_args=[...]`` list).
    """

    def test_subprocess_deep_override(self) -> None:
        result = _run_python(
            _CLI_SUBPROCESS_PREAMBLE,
            ["--infra.ray-init.address", "ray://1.2.3.4:10001"],
        )
        assert result.returncode == 0, (
            f"Subprocess failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        data = json.loads(result.stdout)
        assert data["infra"]["ray_init"]["address"] == "ray://1.2.3.4:10001"
        assert data["infra"]["mode"] == "thread"
        assert data["seed"] == 42

    def test_subprocess_inline_json(self) -> None:
        result = _run_python(
            _CLI_SUBPROCESS_PREAMBLE,
            ["--infra", '{"mode":"ray","ray_init":{"address":"ray://x:1"}}'],
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["infra"]["mode"] == "ray"
        assert data["infra"]["ray_init"]["address"] == "ray://x:1"

    def test_subprocess_inline_json_plus_deep_override(self) -> None:
        """The trojanshot use case end-to-end."""
        result = _run_python(
            _CLI_SUBPROCESS_PREAMBLE,
            [
                "--infra",
                '{"mode":"ray","ray_init":{"address":"ray://orig:1"}}',
                "--infra.ray-init.address",
                "ray://override:1",
            ],
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["infra"]["mode"] == "ray"
        assert data["infra"]["ray_init"]["address"] == "ray://override:1"

    def test_subprocess_top_level_field(self) -> None:
        """Top-level fields override correctly."""
        result = _run_python(
            _CLI_SUBPROCESS_PREAMBLE,
            ["--seed", "99"],
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["seed"] == 99

    def test_subprocess_no_env_pollution(self) -> None:
        """Even with random env vars set, the script picks up only argv values.

        This is the regression test for the source-isolation default.
        """
        result = _run_python(
            _CLI_SUBPROCESS_PREAMBLE,
            ["--seed", "7"],
            env={
                # These would silently leak into model fields if env source
                # were enabled by default.
                "SEED": "999",
                "INFRA": '{"mode":"WRONG"}',
            },
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["seed"] == 7
        assert data["infra"]["mode"] == "thread"  # NOT 'WRONG'


# ---------------------------------------------------------------------------
# Typed + Registry + BaseSettings three-way integration
# ---------------------------------------------------------------------------


class TestTypedRegistryBaseSettings:
    """``Typed + Registry + ABC`` hierarchies still work as factories.

    Registry's ``of(key, ...)`` factory routing goes through ``Typed.of``
    which is unaffected by the BaseSettings change. CLI ``_cli_parse_args``
    targets a SPECIFIC concrete subclass (since BaseSettings can't dispatch
    based on a Registry key the way ``of()`` does).
    """

    def test_registry_factory_unchanged(self) -> None:
        class Animal(Typed, Registry, ABC):
            name: str

        class Dog(Animal):
            aliases = ("canine", "puppy")
            breed: str = "Mixed"

        class Cat(Animal):
            aliases = ("feline",)
            color: str = "Orange"

        d = Animal.of("Dog", name="Rex", breed="Lab")
        assert isinstance(d, Dog)
        assert d.name == "Rex"
        assert d.breed == "Lab"

        c = Animal.of("feline", name="Shadow", color="Black")
        assert isinstance(c, Cat)
        assert c.color == "Black"

    def test_registry_factory_with_cli_on_concrete_subclass(self) -> None:
        """Concrete Registry subclass accepts CLI directly."""

        class Backend(Typed, Registry, ABC):
            name: str

        class HttpBackend(Backend):
            aliases = ("http",)
            url: str = "http://localhost"
            timeout: int = 30

        h = HttpBackend(_cli_parse_args=["--name", "primary", "--timeout", "60"])
        assert isinstance(h, HttpBackend)
        assert h.name == "primary"
        assert h.timeout == 60

    def test_registry_with_nested_cli_overrides(self) -> None:
        """A concrete Registry subclass with a nested Typed field supports
        deep CLI overrides."""

        class Auth(Typed):
            scheme: str = "bearer"
            token: str = ""

        class Backend(Typed, Registry, ABC):
            name: str

        class HttpBackend(Backend):
            aliases = ("http",)
            url: str = "http://localhost"
            auth: Auth = Auth()

        h = HttpBackend(
            _cli_parse_args=[
                "--name",
                "primary",
                "--auth.scheme",
                "basic",
                "--auth.token",
                "secret-xyz",
            ],
        )
        assert h.name == "primary"
        assert h.auth.scheme == "basic"
        assert h.auth.token == "secret-xyz"

    def test_registry_dispatch_with_pre_built_nested(self) -> None:
        """``Animal.of('Dog', target=pre_built)`` preserves identity of the
        nested instance."""

        class Inner(Typed):
            name: str

        class Animal(Typed, Registry, ABC):
            target: Inner

        class Dog(Animal):
            aliases = ("canine",)

        i = Inner(name="x")
        d = Animal.of("Dog", target=i)
        assert isinstance(d, Dog)
        assert d.target is i

    def test_registry_subclass_lifecycle_idempotency(self) -> None:
        """post_initialize on a Registry subclass also runs exactly once."""
        calls: List[int] = []

        class Inner(Typed):
            name: str

            def post_initialize(self) -> None:
                calls.append(id(self))

        class Animal(Typed, Registry, ABC):
            name: str
            companion: Inner

        class Dog(Animal):
            aliases = ("canine",)

        i = Inner(name="bone")
        before = list(calls)
        Animal.of("Dog", name="Rex", companion=i)
        # Inner constructed once when `i` was made; no extra call from
        # outer construction because of the marker.
        assert calls == before, f"Animal.of() re-fired Inner.post_initialize: before={before} after={calls}"


# ---------------------------------------------------------------------------
# Integration test: real `python script.py` invocation with JSON config
# ---------------------------------------------------------------------------


# The script that the integration tests run as a real subprocess.
#
# It defines a multi-level Typed hierarchy (App > Infra > RayInit), accepts:
#   --config PATH            → load a JSON config file from disk
#   --config-json '{...}'    → inline JSON for the WHOLE root model
#   --infra '{...}'          → inline JSON for one nested field
#   --infra.ray-init.address VALUE  → deep override on a leaf
# ...and any combination of the above.
#
# It prints the resulting App's model_dump as JSON to stdout, so the parent
# test can parse it and assert.
_REAL_CLI_SCRIPT = textwrap.dedent("""
    import argparse
    import json
    import sys
    from morphic import Typed

    class RayInit(Typed):
        address: str = "auto"
        num_cpus: int = 4

    class Infra(Typed):
        mode: str = "thread"
        ray_init: RayInit = RayInit()

    class App(Typed):
        infra: Infra = Infra()
        seed: int = 42
        name: str = "default"

    # Two-pass argv handling: pop our wrapper flags (--config, --config-json)
    # before pydantic-settings sees them. Whatever JSON they produce becomes
    # the "baseline" passed via _cli_parse_args, and the remaining argv is
    # appended for pydantic-settings to layer overrides on top.
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--config", type=str, default=None,
                        help="Path to JSON config file (root of App)")
    parser.add_argument("--config-json", type=str, default=None,
                        help="Inline JSON for root of App")
    wrapper_args, remaining = parser.parse_known_args()

    # Build baseline kwargs from the file or inline JSON.
    baseline = {}
    if wrapper_args.config is not None:
        with open(wrapper_args.config) as f:
            baseline = json.load(f)
    elif wrapper_args.config_json is not None:
        baseline = json.loads(wrapper_args.config_json)

    # Convert the baseline dict into argv form: each top-level key becomes
    # `--<key> <json-of-value>` so pydantic-settings parses it as the field's
    # initial value, and any remaining `--field.deep.path VALUE` flags from
    # `remaining` patch on top.
    baseline_argv = []
    for key, value in baseline.items():
        baseline_argv.append(f"--{key.replace('_', '-')}")
        baseline_argv.append(json.dumps(value) if not isinstance(value, str) else value)

    # Final argv: baseline first (so it gets overridden by remaining).
    final_argv = baseline_argv + remaining

    app = App(_cli_parse_args=final_argv)
    print(json.dumps(app.model_dump()))
""")


class TestRealCLIScriptWithJSONConfig:
    """End-to-end: a real ``python script.py --config=path.json [overrides]`` flow.

    These tests write a JSON config file to a temp dir, then spawn a real
    Python subprocess that:

    1. Parses ``--config PATH`` / ``--config-json '{...}'`` with argparse
       (a wrapper around pydantic-settings, since pydantic-settings has no
       built-in "load from JSON file" CLI flag).
    2. Layers any remaining ``--field.deep.path VALUE`` flags on top of the
       file values via pydantic-settings' native CLI source.
    3. Prints the resulting validated model as JSON.

    This mirrors the trojanshot pattern (``--infra configs/infra/ec2-ray.json
    --infra.ray-init.address ray://...``) but using a single root config
    file instead of per-field path-loadable fields.
    """

    def test_load_config_file_only(self, tmp_path) -> None:
        """``--config path/to/cfg.json`` loads the whole tree from disk."""
        config_path = tmp_path / "app.json"
        config_path.write_text(
            json.dumps(
                {
                    "infra": {
                        "mode": "ray",
                        "ray_init": {"address": "ray://from-file:10001", "num_cpus": 8},
                    },
                    "seed": 100,
                    "name": "from-config-file",
                }
            )
        )

        result = _run_python(
            _REAL_CLI_SCRIPT,
            ["--config", str(config_path)],
        )
        assert result.returncode == 0, (
            f"Subprocess failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        data = json.loads(result.stdout)
        assert data["name"] == "from-config-file"
        assert data["seed"] == 100
        assert data["infra"]["mode"] == "ray"
        assert data["infra"]["ray_init"]["address"] == "ray://from-file:10001"
        assert data["infra"]["ray_init"]["num_cpus"] == 8

    def test_inline_root_json_only(self, tmp_path) -> None:
        """``--config-json '{...}'`` loads the whole tree from inline JSON."""
        full_config = json.dumps(
            {
                "infra": {
                    "mode": "ray",
                    "ray_init": {"address": "ray://inline:1", "num_cpus": 12},
                },
                "seed": 7,
                "name": "inline-root",
            }
        )
        result = _run_python(
            _REAL_CLI_SCRIPT,
            ["--config-json", full_config],
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["name"] == "inline-root"
        assert data["infra"]["ray_init"]["num_cpus"] == 12

    def test_config_file_with_top_level_override(self, tmp_path) -> None:
        """File loaded, then a top-level scalar overridden via CLI flag."""
        config_path = tmp_path / "app.json"
        config_path.write_text(
            json.dumps(
                {
                    "seed": 1,
                    "name": "from-file",
                }
            )
        )
        result = _run_python(
            _REAL_CLI_SCRIPT,
            [
                "--config",
                str(config_path),
                "--seed",
                "999",  # override file's seed=1
            ],
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["seed"] == 999
        assert data["name"] == "from-file"  # unchanged from file

    def test_config_file_with_nested_deep_override(self, tmp_path) -> None:
        """The trojanshot pattern: file provides infra defaults, CLI patches
        a single deep leaf.
        """
        config_path = tmp_path / "app.json"
        config_path.write_text(
            json.dumps(
                {
                    "infra": {
                        "mode": "ray",
                        "ray_init": {
                            "address": "ray://file-default:10001",
                            "num_cpus": 4,
                        },
                    },
                }
            )
        )
        result = _run_python(
            _REAL_CLI_SCRIPT,
            [
                "--config",
                str(config_path),
                "--infra.ray-init.address",
                "ray://cli-override:10001",
            ],
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        # CLI override won the deep leaf:
        assert data["infra"]["ray_init"]["address"] == "ray://cli-override:10001"
        # Other fields from the file preserved:
        assert data["infra"]["mode"] == "ray"
        assert data["infra"]["ray_init"]["num_cpus"] == 4

    def test_config_file_with_multiple_deep_overrides(self, tmp_path) -> None:
        """Multiple deep overrides at different depths apply correctly."""
        config_path = tmp_path / "app.json"
        config_path.write_text(
            json.dumps(
                {
                    "infra": {
                        "mode": "thread",
                        "ray_init": {"address": "auto", "num_cpus": 4},
                    },
                    "seed": 0,
                    "name": "base",
                }
            )
        )
        result = _run_python(
            _REAL_CLI_SCRIPT,
            [
                "--config",
                str(config_path),
                "--infra.mode",
                "ray",
                "--infra.ray-init.address",
                "ray://override:1",
                "--infra.ray-init.num-cpus",
                "32",
                "--seed",
                "42",
            ],
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["infra"]["mode"] == "ray"
        assert data["infra"]["ray_init"]["address"] == "ray://override:1"
        assert data["infra"]["ray_init"]["num_cpus"] == 32
        assert data["seed"] == 42
        assert data["name"] == "base"  # only one not overridden

    def test_config_file_pretty_printed_json(self, tmp_path) -> None:
        """Multi-line JSON files (with indentation/comments-as-whitespace) work."""
        config_path = tmp_path / "app.json"
        config_path.write_text(
            textwrap.dedent("""
            {
                "infra": {
                    "mode": "ray",
                    "ray_init": {
                        "address": "ray://pretty:1",
                        "num_cpus": 16
                    }
                },
                "seed": 2026,
                "name": "pretty"
            }
        """)
        )
        result = _run_python(_REAL_CLI_SCRIPT, ["--config", str(config_path)])
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["name"] == "pretty"
        assert data["seed"] == 2026
        assert data["infra"]["ray_init"]["num_cpus"] == 16

    def test_config_file_with_partial_tree_uses_defaults(self, tmp_path) -> None:
        """Fields absent from the JSON file fall back to model defaults."""
        config_path = tmp_path / "app.json"
        # Only override `name`; everything else should come from defaults.
        config_path.write_text(json.dumps({"name": "minimal"}))
        result = _run_python(_REAL_CLI_SCRIPT, ["--config", str(config_path)])
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["name"] == "minimal"
        assert data["seed"] == 42  # default
        assert data["infra"]["mode"] == "thread"  # default
        assert data["infra"]["ray_init"]["address"] == "auto"  # default

    def test_config_file_invalid_path_fails(self, tmp_path) -> None:
        """Pointing to a missing JSON file produces a clear error."""
        result = _run_python(
            _REAL_CLI_SCRIPT,
            ["--config", str(tmp_path / "does-not-exist.json")],
        )
        assert result.returncode != 0, "Expected nonzero exit on missing config"
        # The error mentions the missing file (stderr from FileNotFoundError):
        assert "does-not-exist" in (result.stderr + result.stdout)

    def test_config_file_invalid_json_fails(self, tmp_path) -> None:
        """Corrupt JSON in the config file produces a clear error."""
        config_path = tmp_path / "broken.json"
        config_path.write_text('{"infra": {invalid json}}')
        result = _run_python(_REAL_CLI_SCRIPT, ["--config", str(config_path)])
        assert result.returncode != 0
        # The error mentions JSON decoding:
        assert (
            "json" in (result.stderr + result.stdout).lower()
            or "expecting" in (result.stderr + result.stdout).lower()
        )

    def test_config_file_validation_error_propagates(self, tmp_path) -> None:
        """Type errors in the JSON file are caught and reported."""
        config_path = tmp_path / "bad-type.json"
        # `seed` should be int, not str; `infra.ray_init.num_cpus` should be int.
        config_path.write_text(
            json.dumps(
                {
                    "seed": "not-an-int-and-not-coercible",
                    "infra": {"ray_init": {"num_cpus": "also-bad"}},
                }
            )
        )
        result = _run_python(_REAL_CLI_SCRIPT, ["--config", str(config_path)])
        assert result.returncode != 0
        # The error should mention validation:
        combined = result.stderr + result.stdout
        assert "ValidationError" in combined or "validation" in combined.lower()


# ---------------------------------------------------------------------------
# Pydantic ABC compatibility (the `_abc_impl` regression suite)
# ---------------------------------------------------------------------------


class TestABCImplStripRegression:
    """``_abc_impl`` is a CPython ABC implementation detail that ends up in
    a class's ``__dict__`` whenever ``abc.ABC`` is in the MRO. Pydantic's
    ``inspect_namespace`` walks the namespace and (correctly per its rules)
    treats any ``_foo`` name as a ``PrivateAttr``. When a downstream library
    composes a Typed subclass via ``type(name, bases, dict(parent.__dict__))``
    — concurry's ``Worker`` composition wrapper does this — ``_abc_impl``
    gets registered as a private attribute on the new class.

    Subsequently, ``init_private_attributes`` ``deepcopy``s every
    ``PrivateAttr``'s default. The default of the spurious ``_abc_impl``
    PrivateAttr is the actual ``_abc._abc_data`` instance, which is
    unpicklable: ``deepcopy`` raises ``TypeError: cannot pickle '_abc._abc_data'
    object``.

    Before ``_typed_post_initialized`` was added to ``Typed``, this latent
    bug never fired in practice, because no PrivateAttrs existed in the
    chain so Pydantic never registered ``init_private_attributes`` as
    ``model_post_init``. Adding our marker turned that condition on,
    exposing the bug. The fix lives in ``Typed.__pydantic_init_subclass__``,
    which strips ``_abc_impl`` from ``__private_attributes__`` after
    Pydantic builds the class.

    These tests pin the fix so it cannot silently regress across pydantic
    or pydantic-settings upgrades.
    """

    def test_abc_impl_stripped_from_typed_with_abc_base(self) -> None:
        """A ``Typed + ABC`` subclass does NOT have ``_abc_impl`` in its
        ``__private_attributes__``."""
        from abc import ABC

        from morphic import Typed

        class Foo(Typed, ABC):
            name: str

        assert "_abc_impl" not in Foo.__private_attributes__, (
            f"_abc_impl was not stripped from Foo's __private_attributes__: "
            f"{list(Foo.__private_attributes__.keys())}"
        )

    def test_abc_impl_stripped_from_composed_subclass(self) -> None:
        """The concurry-style composition pattern produces a class with
        ``_abc_impl`` in its ``__dict__``. Without our strip, Pydantic would
        register it as a PrivateAttr. With our strip, it does not."""
        from abc import ABC

        from morphic import Typed

        class Base(Typed, ABC):
            name: str

        ## Mirror what concurry's Worker composition wrapper does:
        ##   target_cls = type(target_cls.__name__, (Worker, target_cls), dict(target_cls.__dict__))
        Composed = type("Composed", (Base,), dict(Base.__dict__))

        assert "_abc_impl" not in Composed.__private_attributes__, (
            f"_abc_impl leaked into Composed.__private_attributes__: "
            f"{list(Composed.__private_attributes__.keys())}"
        )

    def test_composed_subclass_can_be_instantiated_without_unpicklable_default(self) -> None:
        """The composed subclass must instantiate successfully — without our
        strip, ``init_private_attributes`` would call ``deepcopy`` on the
        ``_abc_data`` default and raise ``TypeError: cannot pickle
        '_abc._abc_data' object``."""
        from abc import ABC

        from morphic import Typed

        class Base(Typed, ABC):
            name: str

        Composed = type("Composed", (Base,), dict(Base.__dict__))

        ## This is the canary: the unfixed code raises with
        ## "cannot pickle '_abc._abc_data' object" here.
        instance = Composed(name="x")
        assert instance.name == "x"
        assert isinstance(instance, Base)

    def test_user_defined_underscore_field_unaffected(self) -> None:
        """The strip is targeted at known implementation-detail names. A
        user-defined ``PrivateAttr`` with any other underscore-prefixed name
        is preserved."""
        from morphic import Typed

        class WithPrivate(Typed):
            name: str
            _custom_state: dict = PrivateAttr(default_factory=dict)

        assert "_custom_state" in WithPrivate.__private_attributes__
        assert "_typed_post_initialized" in WithPrivate.__private_attributes__

        ## And the instance can read/write the custom private attr:
        w = WithPrivate(name="x")
        w._custom_state["key"] = "value"
        assert w._custom_state == {"key": "value"}

    def test_all_typed_subclasses_share_only_typed_post_initialized(self) -> None:
        """Confirm that bare ``Typed`` and ``Typed + ABC`` subclasses have
        a single inherited PrivateAttr: ``_typed_post_initialized``. If a
        new Pydantic version introduces a different implementation-detail
        name in this dict, this test will fail and prompt us to update the
        strip list in ``Typed.__pydantic_init_subclass__``."""
        from abc import ABC

        from morphic import Typed

        class PlainTyped(Typed):
            name: str

        class AbstractTyped(Typed, ABC):
            name: str

        Composed = type("Composed", (AbstractTyped,), dict(AbstractTyped.__dict__))

        ## Each of these classes should have EXACTLY one inherited
        ## PrivateAttr — the one Typed itself defines. If any other
        ## name shows up, pydantic has changed its behavior or a new
        ## CPython implementation detail leaked through and we need
        ## to update Typed.__pydantic_init_subclass__.
        for cls in (PlainTyped, AbstractTyped, Composed):
            keys = set(cls.__private_attributes__.keys())
            assert keys == {"_typed_post_initialized"}, (
                f"{cls.__name__}.__private_attributes__ = {keys!r}; "
                f"expected just _typed_post_initialized. If this fails, a "
                f"new implementation-detail PrivateAttr leaked through and "
                f"the strip list in Typed.__pydantic_init_subclass__ may "
                f"need updating."
            )


# ---------------------------------------------------------------------------
# `model_config = ConfigDict(...)` subclass compatibility
# ---------------------------------------------------------------------------


class TestConfigDictSubclassCompatibility:
    """Subclasses that override ``model_config`` with ``ConfigDict(...)``
    (instead of ``SettingsConfigDict(...)``) must keep working.

    Background: Typed's base ``model_config`` is a ``SettingsConfigDict``.
    Plenty of existing user code declares
    ``model_config = ConfigDict(extra='allow')`` (or similar) on Typed
    subclasses. Pydantic merges ``model_config`` across the MRO so the
    subclass's keys override only what they specify; everything else
    (``frozen``, ``revalidate_instances``, ``cli_parse_args``,
    ``cli_kebab_case``, etc.) is inherited from the base.

    We pin this contract here so future Typed changes don't accidentally
    break user code that uses ``ConfigDict``.
    """

    def test_subclass_with_config_dict_inherits_typed_defaults(self) -> None:
        from pydantic import ConfigDict

        class Sub(Typed):
            model_config = ConfigDict(extra="allow")
            name: str

        ## The user-supplied override applies:
        assert Sub.model_config["extra"] == "allow"
        ## All Typed defaults are preserved via the merge:
        assert Sub.model_config["frozen"] is True
        assert Sub.model_config["revalidate_instances"] == "never"
        assert Sub.model_config["validate_default"] is True
        assert Sub.model_config["arbitrary_types_allowed"] is True
        assert Sub.model_config["cli_kebab_case"] is True
        assert Sub.model_config["cli_implicit_flags"] is True
        ## And the source-isolation override is still in place
        ## (cli_parse_args remains unset / None so CLI is opt-in):
        assert Sub.model_config.get("cli_parse_args") in (None, False)

    def test_config_dict_subclass_basic_instantiation(self) -> None:
        from pydantic import ConfigDict

        class Sub(Typed):
            model_config = ConfigDict(extra="allow")
            name: str

        s = Sub(name="x", extra_field="bonus")
        assert s.name == "x"
        ## extra="allow" honored:
        assert s.model_extra == {"extra_field": "bonus"}

    def test_config_dict_subclass_cli_parse(self) -> None:
        """CLI parsing still works on a ConfigDict-overridden subclass."""
        from pydantic import ConfigDict

        class Sub(Typed):
            model_config = ConfigDict(extra="ignore")
            name: str = "default"
            count: int = 0

        s = Sub(_cli_parse_args=["--name", "cli", "--count", "42"])
        assert s.name == "cli"
        assert s.count == 42

    def test_config_dict_subclass_post_initialize_idempotent(self) -> None:
        """The framework's ``post_initialize`` idempotency marker still
        applies even when the subclass uses ``ConfigDict``."""
        from pydantic import ConfigDict

        calls: List[int] = []

        class Inner(Typed):
            model_config = ConfigDict(extra="ignore")
            name: str

            def post_initialize(self) -> None:
                calls.append(id(self))

        class Outer(Typed):
            inner: Inner

        i = Inner(name="x")
        assert len(calls) == 1
        Outer(inner=i)
        ## The marker still prevents the second fire:
        assert len(calls) == 1, f"post_initialize re-fired despite inner using ConfigDict: {calls}"

    def test_config_dict_subclass_identity_preserved(self) -> None:
        """``revalidate_instances='never'`` is inherited from Typed even when
        the subclass overrides ``model_config`` with ``ConfigDict``."""
        from pydantic import ConfigDict

        class Inner(Typed):
            model_config = ConfigDict(extra="ignore")
            name: str

        class Outer(Typed):
            inner: Inner

        i = Inner(name="x")
        o = Outer(inner=i)
        assert o.inner is i, (
            "Identity NOT preserved when inner uses ConfigDict — revalidate_instances inheritance is broken."
        )

    def test_config_dict_subclass_with_registry_dispatch(self) -> None:
        """``__type__`` discriminator dispatch works on a ``Typed + Registry +
        ABC`` hierarchy where the abstract base uses ``ConfigDict``."""
        from abc import ABC

        from pydantic import ConfigDict

        from morphic import Registry

        class Base(Typed, Registry, ABC):
            model_config = ConfigDict(extra="allow")
            name: str

        class Sub1(Base):
            aliases = ("first",)
            field1: str = "default1"

        class Sub2(Base):
            aliases = ("second",)
            field2: str = "default2"

        b = Base(__type__="first", name="x", field1="patched", random_extra="ok")
        assert type(b) is Sub1
        assert b.field1 == "patched"
        ## And extras allowed because the base's ConfigDict said so:
        assert b.model_extra == {"random_extra": "ok"}

    def test_config_dict_subclass_revalidate_instances_override(self) -> None:
        """A subclass CAN override ``revalidate_instances`` if it really wants
        to — the merge respects the subclass's value."""
        from pydantic import ConfigDict

        class Override(Typed):
            ## Explicitly turn off identity preservation on this subclass.
            model_config = ConfigDict(revalidate_instances="always")
            name: str

        ## The subclass override wins:
        assert Override.model_config["revalidate_instances"] == "always"
        ## Other Typed defaults still inherited:
        assert Override.model_config["frozen"] is True

    def test_mutable_typed_subclass_with_config_dict(self) -> None:
        """Same compatibility for ``MutableTyped`` subclasses (frozen=False).
        ``MutableTyped`` itself uses ``SettingsConfigDict`` internally, but
        a subclass can override with ``ConfigDict``."""
        from pydantic import ConfigDict

        from morphic import MutableTyped

        class Mut(MutableTyped):
            model_config = ConfigDict(extra="allow")
            name: str

        m = Mut(name="x")
        ## frozen=False inherited from MutableTyped:
        assert Mut.model_config["frozen"] is False
        m.name = "patched"  # would raise if accidentally frozen
        assert m.name == "patched"
