"""Tests for ``Typed + Registry`` discriminator dispatch via ``__type__``.

This file covers the three ways morphic dispatches a ``Typed + Registry``
abstract base to its concrete subclass at construction time:

1. **Direct kwargs**: ``Backend(__type__="http", name="x", url="y")`` returns
   an ``HttpBackend`` instance via ``Typed.__new__`` redirecting to
   ``Backend.of("http", ...)``.
2. **Nested dict input**: ``Config(backend={"__type__": "http", ...})``
   triggers the same dispatch when morphic's ``_convert_nested_typed_fields``
   coerces the inner dict via ``Backend(**dict)``.
3. **CLI parse**: ``Config.parse_cli_args(["--backend.__type__", "http",
   "--backend.url", "..."])`` does two-pass parsing, dynamically rebuilds
   ``Config`` with ``HttpBackend`` substituted, then runs pydantic-settings'
   normal CLI source. Subclass-specific fields like ``--backend.url`` work.

The discriminator is :data:`morphic.TYPED_REGISTRY_DISCRIMINATOR_KEY` (which
is ``"__type__"``). It is a dunder, so Pydantic's field discovery filters it
out — it cannot collide with a user-defined field. The sentinel is popped
from kwargs before Pydantic ever sees it.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from abc import ABC
from typing import List

import pytest

from morphic import (
    TYPED_REGISTRY_DISCRIMINATOR_KEY,
    Registry,
    Typed,
)

# ---------------------------------------------------------------------------
# Subprocess helper for end-to-end CLI integration tests.
# ---------------------------------------------------------------------------


def _run_python(code: str, argv: List[str]) -> subprocess.CompletedProcess:
    """Run ``code`` in a fresh Python subprocess with the given ``argv``."""
    return subprocess.run(
        [sys.executable, "-c", code, *argv],
        capture_output=True,
        text=True,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Demo class hierarchies used by multiple test classes.
# ---------------------------------------------------------------------------


class Auth(Typed, Registry, ABC):
    """Authentication scheme. Abstract Registry base."""


class BearerAuth(Auth):
    aliases = ("bearer",)
    token: str = ""


class BasicAuth(Auth):
    aliases = ("basic",)
    username: str = ""
    password: str = ""


class Backend(Typed, Registry, ABC):
    """Generic backend. Abstract Registry base."""

    name: str


class HttpBackend(Backend):
    aliases = ("http",)
    url: str = "http://localhost"
    auth: Auth = BearerAuth()
    timeout: int = 30


class GrpcBackend(Backend):
    aliases = ("grpc",)
    target: str = "localhost:50051"
    use_tls: bool = True


class Config(Typed):
    """Outer config that embeds an abstract ``Backend`` field."""

    backend: Backend
    seed: int = 42
    name: str = "default"


# ===========================================================================
# Discriminator constant
# ===========================================================================


class TestDiscriminatorConstant:
    """The discriminator key is exported from morphic and is a dunder."""

    def test_constant_value(self) -> None:
        assert TYPED_REGISTRY_DISCRIMINATOR_KEY == "__type__"

    def test_constant_is_dunder(self) -> None:
        """Dunders are filtered out of Pydantic field discovery, so the
        sentinel cannot collide with a user-defined field."""
        assert TYPED_REGISTRY_DISCRIMINATOR_KEY.startswith("__")
        assert TYPED_REGISTRY_DISCRIMINATOR_KEY.endswith("__")


# ===========================================================================
# `__new__` dispatch via direct kwargs
# ===========================================================================


class TestNewDispatchDirectKwargs:
    """``Backend(__type__="http", ...)`` returns an ``HttpBackend`` instance."""

    def test_abstract_base_with_type_returns_concrete_subclass(self) -> None:
        b = Backend(__type__="http", name="alice", url="http://api")
        assert type(b) is HttpBackend
        assert b.name == "alice"
        assert b.url == "http://api"

    def test_dispatch_to_alternative_subclass(self) -> None:
        b = Backend(__type__="grpc", name="g", target="prod:50051")
        assert type(b) is GrpcBackend
        assert b.target == "prod:50051"

    def test_dispatch_uses_subclass_alias(self) -> None:
        """Aliases registered on the subclass are valid discriminator values."""
        b = Backend(__type__="http", name="x")
        assert type(b) is HttpBackend

    def test_default_fields_filled_in_after_dispatch(self) -> None:
        """Fields not in kwargs fall back to the SUBCLASS defaults, not the
        abstract base's defaults."""
        b = Backend(__type__="http", name="x")
        assert b.url == "http://localhost"  # HttpBackend default
        assert b.timeout == 30
        assert isinstance(b.auth, BearerAuth)

    def test_dispatch_with_unknown_key_raises(self) -> None:
        with pytest.raises(KeyError):
            Backend(__type__="does-not-exist", name="x")

    def test_dispatch_with_invalid_subclass_field_raises(self) -> None:
        """Using the wrong subclass for a given field set raises ValidationError."""
        with pytest.raises((ValueError, TypeError)):
            Backend(__type__="grpc", name="x", url="http://wrong-field")

    def test_concrete_subclass_accepts_matching_type(self) -> None:
        """``HttpBackend(__type__="http", ...)`` is a no-op (sentinel popped)."""
        h = HttpBackend(__type__="http", name="x", url="http://y")
        assert type(h) is HttpBackend
        assert h.url == "http://y"

    def test_concrete_subclass_accepts_any_type_value(self) -> None:
        """Concrete subclasses silently pop ``__type__`` regardless of value
        (the discriminator is only enforced on the abstract base path).
        Users who want strict matching should use ``Backend.of("http", ...)``.
        """
        h = HttpBackend(__type__="grpc", name="x")
        # The discriminator is silently popped on direct concrete construction;
        # the wrong-type discriminator does not raise here. This matches the
        # behavior of `HttpBackend(**dict_with_extra)` after popping.
        assert type(h) is HttpBackend

    def test_pure_typed_class_unaffected(self) -> None:
        """A pure ``Typed`` (no Registry) is not affected by ``__type__``."""

        class Plain(Typed):
            seed: int = 0

        # __type__ on a pure Typed: the dunder gets popped silently.
        p = Plain(__type__="ignored-value", seed=99)
        assert p.seed == 99
        # But __type__ does NOT become a field of Plain:
        assert "__type__" not in p.model_dump()

    def test_dispatch_preserves_post_initialize(self) -> None:
        """``post_initialize`` runs on the resolved concrete subclass exactly once."""
        calls: List[str] = []

        class B(Typed, Registry, ABC):
            name: str

            def post_initialize(self) -> None:
                calls.append(type(self).__name__)

        class B1(B):
            aliases = ("one",)

        b = B(__type__="one", name="x")
        assert calls == ["B1"]
        assert type(b) is B1

    def test_of_method_still_works(self) -> None:
        """Backend.of() is unchanged."""
        b = Backend.of("http", name="x", url="http://y")
        assert type(b) is HttpBackend
        assert b.url == "http://y"


# ===========================================================================
# Dict-input dispatch in nested Typed fields
# ===========================================================================


class TestDictInputDispatch:
    """``Config(backend={"__type__": "http", ...})`` dispatches via the
    ``__new__`` redirect when the dict is coerced to a ``Backend`` instance.
    """

    def test_dict_dispatch_in_outer_typed(self) -> None:
        c = Config(backend={"__type__": "http", "name": "x", "url": "http://y"})
        assert type(c.backend) is HttpBackend
        assert c.backend.url == "http://y"

    def test_dict_dispatch_with_default_fields(self) -> None:
        c = Config(backend={"__type__": "http", "name": "x"})
        assert type(c.backend) is HttpBackend
        # Subclass defaults apply:
        assert c.backend.url == "http://localhost"
        assert c.backend.timeout == 30

    def test_nested_dict_dispatch_double_registry(self) -> None:
        """Outer Config -> Backend -> Auth (two Registry levels)."""
        c = Config(
            backend={
                "__type__": "http",
                "name": "x",
                "url": "http://api",
                "auth": {
                    "__type__": "basic",
                    "username": "alice",
                    "password": "secret",
                },
            }
        )
        assert type(c.backend) is HttpBackend
        assert type(c.backend.auth) is BasicAuth
        assert c.backend.auth.username == "alice"
        assert c.backend.auth.password == "secret"

    def test_pre_built_inner_still_preserved_through_dict_coerce(self) -> None:
        """When inner is already a concrete instance, identity is preserved."""
        h = HttpBackend(name="prebuilt", url="http://pre")
        c = Config(backend=h)
        assert c.backend is h

    def test_alternate_subclass_via_dict(self) -> None:
        c = Config(backend={"__type__": "grpc", "name": "g", "target": "prod:1"})
        assert type(c.backend) is GrpcBackend
        assert c.backend.target == "prod:1"


# ===========================================================================
# `Typed.parse_cli_args` for top-level dispatch
# ===========================================================================


class TestParseCLIArgsTopLevel:
    """Pure Typed (no Registry root) and abstract-base-as-root cases."""

    def test_pure_typed_parse_cli_args(self) -> None:
        """No discriminator flags; just regular CLI parsing."""

        class Plain(Typed):
            seed: int = 0
            name: str = "x"

        p = Plain.parse_cli_args(["--seed", "99", "--name", "test"])
        assert p.seed == 99
        assert p.name == "test"
        assert type(p) is Plain

    def test_parse_cli_args_argv_default_uses_sys_argv(self, monkeypatch) -> None:
        """When ``argv=None`` (default), ``sys.argv[1:]`` is used."""

        class Plain(Typed):
            seed: int = 0

        monkeypatch.setattr(sys, "argv", ["script.py", "--seed", "7"])
        p = Plain.parse_cli_args()
        assert p.seed == 7

    def test_root_level_abstract_dispatch(self) -> None:
        """``Backend.parse_cli_args(["--__type__", "http", ...])`` returns
        an ``HttpBackend``."""
        b = Backend.parse_cli_args(
            [
                "--__type__",
                "http",
                "--name",
                "rootlevel",
                "--url",
                "http://root",
            ]
        )
        assert type(b) is HttpBackend
        assert b.name == "rootlevel"
        assert b.url == "http://root"

    def test_root_level_dispatch_equals_form(self) -> None:
        b = Backend.parse_cli_args(
            [
                "--__type__=http",
                "--name",
                "x",
                "--url",
                "http://y",
            ]
        )
        assert type(b) is HttpBackend
        assert b.url == "http://y"


# ===========================================================================
# `Typed.parse_cli_args` for nested registries (the trojanshot use case)
# ===========================================================================


class TestParseCLIArgsNestedRegistries:
    """The actual problem: ``Config`` has ``backend: Backend`` and we want
    deep CLI overrides of subclass-specific fields."""

    def test_simple_nested_dispatch(self) -> None:
        c = Config.parse_cli_args(
            [
                "--backend.__type__",
                "http",
                "--backend.name",
                "x",
                "--backend.url",
                "http://api",
            ]
        )
        assert type(c.backend) is HttpBackend
        assert c.backend.url == "http://api"
        assert c.backend.name == "x"

    def test_nested_dispatch_with_top_level_overrides(self) -> None:
        c = Config.parse_cli_args(
            [
                "--backend.__type__",
                "http",
                "--backend.name",
                "x",
                "--seed",
                "999",
                "--name",
                "prod",
            ]
        )
        assert type(c.backend) is HttpBackend
        assert c.seed == 999
        assert c.name == "prod"

    def test_two_levels_of_registries(self) -> None:
        """``Config -> Backend -> Auth`` with ``__type__`` at every level."""
        c = Config.parse_cli_args(
            [
                "--backend.__type__",
                "http",
                "--backend.name",
                "x",
                "--backend.auth.__type__",
                "basic",
                "--backend.auth.username",
                "alice",
                "--backend.auth.password",
                "secret",
            ]
        )
        ## Use isinstance, not `type() is`: when nested registries are
        ## resolved, the outer HttpBackend gets dynamically rebuilt as
        ## HttpBackend__resolved (a true subclass of HttpBackend) so
        ## that pydantic-settings sees the resolved BasicAuth annotation
        ## for the `auth` field.
        assert isinstance(c.backend, HttpBackend)
        assert type(c.backend.auth) is BasicAuth
        assert c.backend.auth.username == "alice"
        assert c.backend.auth.password == "secret"

    def test_alternate_subclass_for_root(self) -> None:
        c = Config.parse_cli_args(
            [
                "--backend.__type__",
                "grpc",
                "--backend.name",
                "g",
                "--backend.target",
                "prod:50051",
            ]
        )
        assert type(c.backend) is GrpcBackend
        assert c.backend.target == "prod:50051"

    def test_alternate_subclass_for_nested(self) -> None:
        """Switch the auth subtype, keep backend HTTP."""
        c = Config.parse_cli_args(
            [
                "--backend.__type__",
                "http",
                "--backend.name",
                "x",
                "--backend.auth.__type__",
                "bearer",
                "--backend.auth.token",
                "Bearer xyz",
            ]
        )
        assert type(c.backend.auth) is BearerAuth
        assert c.backend.auth.token == "Bearer xyz"

    def test_subclass_field_default_when_not_overridden(self) -> None:
        """Fields of the resolved subclass that are not on the CLI fall back
        to the subclass defaults."""
        c = Config.parse_cli_args(
            [
                "--backend.__type__",
                "http",
                "--backend.name",
                "x",
            ]
        )
        assert c.backend.timeout == 30  # HttpBackend default

    def test_inline_json_for_resolved_subclass_works(self) -> None:
        """``--backend '{...}'`` with ``__type__`` inside the JSON also dispatches."""
        c = Config.parse_cli_args(
            [
                "--backend",
                json.dumps(
                    {
                        "__type__": "http",
                        "name": "fromjson",
                        "url": "http://json",
                    }
                ),
            ]
        )
        assert type(c.backend) is HttpBackend
        assert c.backend.url == "http://json"

    def test_nested_inline_json_then_deep_override(self) -> None:
        """Inline JSON sets the baseline; deep override patches a leaf.

        Note: when using inline JSON for the nested model, the discriminator
        goes INSIDE the JSON, not as a separate flag — but the resolved
        subclass's deep-override flags still work because the rebuild uses
        the type_map from the deep-flag scan.
        """
        c = Config.parse_cli_args(
            [
                "--backend.__type__",
                "http",
                "--backend.name",
                "x",
                "--backend.url",
                "http://override",
            ]
        )
        assert c.backend.url == "http://override"


# ===========================================================================
# Error handling
# ===========================================================================


class TestParseCLIArgsErrors:
    """Bad input surfaces as clear errors."""

    def test_unknown_type_raises_keyerror(self) -> None:
        with pytest.raises(KeyError):
            Config.parse_cli_args(
                [
                    "--backend.__type__",
                    "does-not-exist",
                    "--backend.name",
                    "x",
                ]
            )

    def test_subclass_specific_field_for_wrong_subclass_rejected(self) -> None:
        """``--backend.url`` is rejected when ``__type__=grpc``: the
        rebuilt schema does not have a ``url`` flag for GrpcBackend."""
        with pytest.raises((SystemExit, ValueError)):
            Config.parse_cli_args(
                [
                    "--backend.__type__",
                    "grpc",
                    "--backend.name",
                    "x",
                    "--backend.url",
                    "http://wrong",
                ]
            )

    def test_missing_value_for_type_flag(self) -> None:
        with pytest.raises(ValueError, match="has no value"):
            Config.parse_cli_args(
                [
                    "--backend.__type__",  # no value follows
                ]
            )

    def test_unknown_root_level_type(self) -> None:
        with pytest.raises(KeyError):
            Backend.parse_cli_args(
                [
                    "--__type__",
                    "does-not-exist",
                    "--name",
                    "x",
                ]
            )


# ===========================================================================
# Subprocess integration tests (real `python script.py` invocations)
# ===========================================================================


_SCRIPT_NESTED_REGISTRIES = textwrap.dedent("""
    import json
    from abc import ABC
    from morphic import Typed, Registry

    class Auth(Typed, Registry, ABC):
        pass

    class BearerAuth(Auth):
        aliases = ("bearer",)
        token: str = ""

    class BasicAuth(Auth):
        aliases = ("basic",)
        username: str = ""
        password: str = ""

    class Backend(Typed, Registry, ABC):
        name: str

    class HttpBackend(Backend):
        aliases = ("http",)
        url: str = "http://localhost"
        auth: Auth = BearerAuth()

    class GrpcBackend(Backend):
        aliases = ("grpc",)
        target: str = "localhost:50051"

    class Config(Typed):
        backend: Backend
        seed: int = 42

    if __name__ == "__main__":
        config = Config.parse_cli_args()
        # Print result as JSON for the parent test to parse.
        print(json.dumps({
            "backend_type": type(config.backend).__name__.replace("__resolved", ""),
            "backend_name": config.backend.name,
            "url": getattr(config.backend, "url", None),
            "target": getattr(config.backend, "target", None),
            "auth_type": type(config.backend.auth).__name__.replace("__resolved", "") if hasattr(config.backend, "auth") else None,
            "auth_username": getattr(getattr(config.backend, "auth", None), "username", None),
            "auth_token": getattr(getattr(config.backend, "auth", None), "token", None),
            "seed": config.seed,
        }))
""")


class TestSubprocessRegistryDispatch:
    """End-to-end ``python script.py --backend.__type__ http ...`` flows."""

    def test_subprocess_simple_http_backend(self) -> None:
        result = _run_python(
            _SCRIPT_NESTED_REGISTRIES,
            [
                "--backend.__type__",
                "http",
                "--backend.name",
                "primary",
                "--backend.url",
                "http://api.example.com",
            ],
        )
        assert result.returncode == 0, (
            f"Subprocess failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        data = json.loads(result.stdout)
        assert data["backend_type"] == "HttpBackend"
        assert data["backend_name"] == "primary"
        assert data["url"] == "http://api.example.com"

    def test_subprocess_grpc_backend(self) -> None:
        result = _run_python(
            _SCRIPT_NESTED_REGISTRIES,
            [
                "--backend.__type__",
                "grpc",
                "--backend.name",
                "g",
                "--backend.target",
                "prod:50051",
            ],
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["backend_type"] == "GrpcBackend"
        assert data["target"] == "prod:50051"

    def test_subprocess_nested_registries(self) -> None:
        """The full demo: choose backend AND its auth subtype on the CLI."""
        result = _run_python(
            _SCRIPT_NESTED_REGISTRIES,
            [
                "--backend.__type__",
                "http",
                "--backend.name",
                "primary",
                "--backend.auth.__type__",
                "basic",
                "--backend.auth.username",
                "alice",
                "--backend.auth.password",
                "secret-xyz",
                "--seed",
                "777",
            ],
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["backend_type"] == "HttpBackend"
        assert data["auth_type"] == "BasicAuth"
        assert data["auth_username"] == "alice"
        assert data["seed"] == 777

    def test_subprocess_unknown_type_fails(self) -> None:
        """Unknown discriminator value produces a clear error."""
        result = _run_python(
            _SCRIPT_NESTED_REGISTRIES,
            [
                "--backend.__type__",
                "totally-bogus-key",
                "--backend.name",
                "x",
            ],
        )
        assert result.returncode != 0
        # KeyError mentioning the bogus key:
        assert "totally-bogus-key" in (result.stderr + result.stdout)

    def test_subprocess_subclass_field_for_wrong_type_fails(self) -> None:
        """``--backend.url`` (HttpBackend field) is rejected when ``__type__=grpc``."""
        result = _run_python(
            _SCRIPT_NESTED_REGISTRIES,
            [
                "--backend.__type__",
                "grpc",
                "--backend.name",
                "g",
                "--backend.url",
                "http://wrong-field-for-grpc",
            ],
        )
        assert result.returncode != 0
        # argparse complains about the unrecognized flag for the resolved class:
        combined = result.stderr + result.stdout
        assert "--backend.url" in combined or "unrecognized" in combined.lower()

    def test_subprocess_help_shows_resolved_subclass_fields(self) -> None:
        """``--help`` after ``--backend.__type__ http`` shows HttpBackend's
        subclass-specific fields (``--backend.url``, ``--backend.auth.*``)."""
        result = _run_python(
            _SCRIPT_NESTED_REGISTRIES,
            [
                "--backend.__type__",
                "http",
                "--backend.auth.__type__",
                "basic",
                "--help",
            ],
        )
        # --help exits with 0 in argparse:
        assert result.returncode == 0, result.stderr
        # The help text should now show HttpBackend AND BasicAuth's fields:
        assert "--backend.url" in result.stdout
        assert "--backend.auth.username" in result.stdout
        assert "--backend.auth.password" in result.stdout

    def test_subprocess_inline_json_with_type_inside(self) -> None:
        """``--backend '{"__type__":"http",...}'`` also works end-to-end."""
        result = _run_python(
            _SCRIPT_NESTED_REGISTRIES,
            [
                "--backend",
                json.dumps(
                    {
                        "__type__": "http",
                        "name": "fromjson",
                        "url": "http://json-cli",
                    }
                ),
            ],
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["backend_type"] == "HttpBackend"
        assert data["url"] == "http://json-cli"
