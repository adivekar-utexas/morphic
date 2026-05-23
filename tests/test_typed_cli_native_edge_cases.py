"""Edge-case tests for the native pydantic-settings CLI flow on Typed models.

This file complements ``test_typed_basesettings.py``, which establishes the
basic invariants. Here we exhaustively probe the ``App(_cli_parse_args=...)``
construction path against:

A. **Construction-count invariants** — the centerpiece. Verify that
   ``post_initialize`` fires *exactly once per instance* across every
   construction path (dict input, pre-built, mixed, CLI parse, ``model_validate``
   round-trips, lists, dicts, shared instances). This is the regression suite
   for the Pydantic ``model_validator(mode="after")`` re-fire bug
   (https://github.com/pydantic/pydantic/issues/12876), which morphic neutralizes
   via the per-instance ``_typed_post_initialized`` PrivateAttr marker on Typed.

B. **Type coercion edge cases** — strings to ints / floats / bools / Optionals /
   Lists / Dicts / Enums via the CLI source.

C. **Argument-form edge cases** — ``--flag value`` vs ``--flag=value``, kebab
   vs snake, missing values, unknown flags, repeated flags.

D. **Frozen-instance state survival** — ``PrivateAttr`` mutations on an inner
   Typed are not lost when the inner is held as a field of an outer Typed.

E. **Multi-instance scenarios** — same Typed instance used in two slots of an
   outer model, lists/dicts of mixed dict + pre-built instances, etc.

The construction-count tests use ``collections.Counter`` keyed on ``id(self)``
to record every entry into ``post_initialize`` (including no-ops). A double-fire
shows up as ``count > 1`` for some instance id. All assertions check both
per-class totals AND per-instance counts.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from collections import Counter
from typing import Dict, List, Optional, Tuple

import pytest
from pydantic import Field, PrivateAttr, ValidationError

from morphic import AutoEnum, Registry, Typed, auto


# ---------------------------------------------------------------------------
# Subprocess helper (same pattern as test_typed_basesettings.py).
# ---------------------------------------------------------------------------


def _run_python(code: str, argv: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", code, *argv],
        capture_output=True,
        text=True,
        timeout=30,
    )


# ===========================================================================
# Construction-count invariants (the #12876 double-fire regression suite)
# ===========================================================================


class TestPostInitializeCalledExactlyOnce:
    """Exhaustively prove that post_initialize fires EXACTLY ONCE per instance.

    Each test isolates a different construction path. The counter records
    every entry into post_initialize (NOT just non-no-op ones), so a
    double-fire would show up as count=2 instead of count=1.
    """

    def _make_classes(self):
        """Fresh classes per test so the call counter is isolated."""
        # Counter[int] keyed by id(self) — survives across tests via the
        # closure but is re-created per call to _make_classes().
        per_instance_counts: "Counter[int]" = Counter()
        per_class_counts: "Counter[str]" = Counter()

        class Leaf(Typed):
            value: str

            def post_initialize(self) -> None:
                per_instance_counts[id(self)] += 1
                per_class_counts[type(self).__name__] += 1

        class Mid(Typed):
            leaf: Leaf
            mid_field: str = "default"

            def post_initialize(self) -> None:
                per_instance_counts[id(self)] += 1
                per_class_counts[type(self).__name__] += 1

        class Root(Typed):
            mid: Mid
            root_field: int = 0

            def post_initialize(self) -> None:
                per_instance_counts[id(self)] += 1
                per_class_counts[type(self).__name__] += 1

        return Leaf, Mid, Root, per_instance_counts, per_class_counts

    def test_root_construction_from_dict_input(self) -> None:
        """``Root(mid={...})`` builds 3 instances; each post_initialize fires
        exactly once."""
        Leaf, Mid, Root, per_instance, per_class = self._make_classes()

        r = Root(mid={"leaf": {"value": "x"}})

        assert per_class["Leaf"] == 1, f"Leaf fired {per_class['Leaf']}× — expected 1"
        assert per_class["Mid"] == 1, f"Mid fired {per_class['Mid']}× — expected 1"
        assert per_class["Root"] == 1, f"Root fired {per_class['Root']}× — expected 1"
        # And every per-instance count is exactly 1:
        for inst_id, count in per_instance.items():
            assert count == 1, f"Instance {inst_id} fired {count}× — expected 1"

    def test_nested_pre_built_construction(self) -> None:
        """Pre-build leaf → mid → root; each instance fires exactly once total."""
        Leaf, Mid, Root, per_instance, per_class = self._make_classes()

        leaf = Leaf(value="x")
        assert per_instance[id(leaf)] == 1
        mid = Mid(leaf=leaf)
        assert per_instance[id(leaf)] == 1, (
            f"leaf re-fired during Mid construction: count={per_instance[id(leaf)]}"
        )
        assert per_instance[id(mid)] == 1
        root = Root(mid=mid)
        assert per_instance[id(leaf)] == 1, (
            f"leaf re-fired during Root construction: count={per_instance[id(leaf)]}"
        )
        assert per_instance[id(mid)] == 1, (
            f"mid re-fired during Root construction: count={per_instance[id(mid)]}"
        )
        assert per_instance[id(root)] == 1

    def test_mixed_pre_built_and_dict_construction(self) -> None:
        """Pre-build leaf, but pass mid/root as dicts."""
        Leaf, Mid, Root, per_instance, per_class = self._make_classes()

        leaf = Leaf(value="x")
        assert per_instance[id(leaf)] == 1

        # mid is a dict that contains the pre-built leaf:
        root = Root(mid={"leaf": leaf})

        # leaf still fired only once (the marker survived the dict-coerce path):
        assert per_instance[id(leaf)] == 1, f"leaf double-fired in dict path: counts={dict(per_instance)}"

    def test_cli_parse_dict_path_no_double_fire(self) -> None:
        """``Root(_cli_parse_args=...)`` route doesn't double-fire either."""
        Leaf, Mid, Root, per_instance, per_class = self._make_classes()

        r = Root(
            _cli_parse_args=[
                "--mid",
                '{"leaf":{"value":"x"}}',
            ]
        )

        assert per_class["Leaf"] == 1
        assert per_class["Mid"] == 1
        assert per_class["Root"] == 1

    def test_cli_parse_deep_override_no_double_fire(self) -> None:
        """Deep override route also fires post_initialize exactly once per instance."""
        Leaf, Mid, Root, per_instance, per_class = self._make_classes()

        r = Root(
            _cli_parse_args=[
                "--mid",
                '{"leaf":{"value":"x"}}',
                "--mid.leaf.value",
                "patched",
            ]
        )

        assert per_class["Leaf"] == 1
        assert per_class["Mid"] == 1
        assert per_class["Root"] == 1
        assert r.mid.leaf.value == "patched"

    def test_model_validate_dump_creates_new_marker(self) -> None:
        """``model_validate(model.model_dump())`` creates a new instance with a
        fresh marker — post_initialize correctly runs once on the NEW instance.
        """
        Leaf, Mid, Root, per_instance, per_class = self._make_classes()

        r1 = Root(mid={"leaf": {"value": "x"}})
        # Root and its descendants each fired once for r1:
        assert per_class["Leaf"] == 1
        assert per_class["Mid"] == 1
        assert per_class["Root"] == 1

        # Round-trip: this MUST create new instances and fire post_initialize
        # exactly once for each new instance.
        r2 = Root.model_validate(r1.model_dump())
        assert r2 is not r1
        assert r2.mid is not r1.mid
        assert r2.mid.leaf is not r1.mid.leaf

        # Now total per-class counts should be 2 (one for r1, one for r2):
        assert per_class["Leaf"] == 2
        assert per_class["Mid"] == 2
        assert per_class["Root"] == 2

    def test_each_instance_gets_independent_marker(self) -> None:
        """Two siblings of the same type each fire post_initialize exactly once."""
        per_instance: "Counter[int]" = Counter()

        class Leaf(Typed):
            value: str

            def post_initialize(self) -> None:
                per_instance[id(self)] += 1

        class Container(Typed):
            a: Leaf
            b: Leaf

        a = Leaf(value="a")
        b = Leaf(value="b")
        c = Container(a=a, b=b)

        assert per_instance[id(a)] == 1
        assert per_instance[id(b)] == 1
        assert c.a is a and c.b is b

    def test_same_instance_used_in_two_fields_fires_only_once(self) -> None:
        """Same Typed used twice in an outer model: post_initialize fires once
        on the shared instance regardless of how many slots reference it.
        """
        per_instance: "Counter[int]" = Counter()

        class Leaf(Typed):
            value: str

            def post_initialize(self) -> None:
                per_instance[id(self)] += 1

        class Container(Typed):
            a: Leaf
            b: Leaf

        shared = Leaf(value="shared")
        # Use the SAME instance for both a and b:
        c = Container(a=shared, b=shared)

        assert per_instance[id(shared)] == 1, (
            f"Shared instance fired {per_instance[id(shared)]}× — expected 1. "
            f"This means the validator re-firing on different field paths is "
            f"not being absorbed by the marker."
        )
        assert c.a is shared and c.b is shared

    def test_list_of_typed_each_fires_once(self) -> None:
        """A ``List[Inner]`` field: each list element fires post_initialize once."""
        per_instance: "Counter[int]" = Counter()

        class Inner(Typed):
            value: str

            def post_initialize(self) -> None:
                per_instance[id(self)] += 1

        class Outer(Typed):
            items: List[Inner]

        # Mix dicts and pre-built instances in the same list:
        pre_built = Inner(value="pre")
        o = Outer(
            items=[
                {"value": "from-dict-1"},
                pre_built,
                {"value": "from-dict-2"},
            ]
        )

        assert len(o.items) == 3
        assert per_instance[id(pre_built)] == 1, (
            f"pre_built in list re-fired: count={per_instance[id(pre_built)]}"
        )
        # Each constructed-from-dict instance fired exactly once:
        for item in o.items:
            assert per_instance[id(item)] == 1

    def test_dict_of_typed_each_fires_once(self) -> None:
        """A ``Dict[str, Inner]`` field: each value fires post_initialize once."""
        per_instance: "Counter[int]" = Counter()

        class Inner(Typed):
            value: str

            def post_initialize(self) -> None:
                per_instance[id(self)] += 1

        class Outer(Typed):
            mapping: Dict[str, Inner]

        pre_built = Inner(value="pre")
        o = Outer(
            mapping={
                "alpha": {"value": "a"},
                "beta": pre_built,
                "gamma": {"value": "g"},
            }
        )

        assert per_instance[id(pre_built)] == 1
        for inner in o.mapping.values():
            assert per_instance[id(inner)] == 1

    def test_heavy_resource_pattern_no_per_class_guard_needed(self) -> None:
        """The trojanshot pattern: per-class guard is now redundant, the
        framework marker handles everything.

        We use a guard that raises if the second fire happens, proving the
        framework guarantees no second fire reaches the user code.
        """
        spawn_log: List[str] = []

        class HeavyService(Typed):
            model_id: str
            _initialized: bool = PrivateAttr(default=False)

            def post_initialize(self) -> None:
                # If the framework marker is broken, this will fire twice.
                if self._initialized:
                    pytest.fail(
                        "Framework marker BROKEN — post_initialize fired twice "
                        "on the same instance, despite the framework's "
                        "_typed_post_initialized check. The per-class guard "
                        "would have to take over."
                    )
                spawn_log.append(self.model_id)
                object.__setattr__(self, "_initialized", True)

        class Container(Typed):
            service: HeavyService

        # Path A: pre-built service.
        s = HeavyService(model_id="qwen-3-4b")
        assert spawn_log == ["qwen-3-4b"]
        c = Container(service=s)
        assert spawn_log == ["qwen-3-4b"]  # No second spawn on outer construction.
        assert c.service is s

        # Path B: dict input.
        spawn_log.clear()
        c2 = Container(service={"model_id": "qwen-other"})
        assert spawn_log == ["qwen-other"]  # Exactly one spawn.

        # Path C: CLI parse.
        spawn_log.clear()
        c3 = Container(
            _cli_parse_args=[
                "--service",
                '{"model_id":"cli-model"}',
            ]
        )
        assert spawn_log == ["cli-model"]  # Exactly one spawn.


# ===========================================================================
# Type coercion via the CLI source
# ===========================================================================


class TestCLITypeCoercion:
    """Pydantic-settings' CLI source coerces strings to native types."""

    def test_int_coercion(self) -> None:
        class App(Typed):
            count: int = 0

        app = App(_cli_parse_args=["--count", "42"])
        assert app.count == 42 and isinstance(app.count, int)

    def test_negative_int(self) -> None:
        class App(Typed):
            offset: int = 0

        app = App(_cli_parse_args=["--offset", "-7"])
        assert app.offset == -7

    def test_float_coercion(self) -> None:
        class App(Typed):
            rate: float = 0.0

        app = App(_cli_parse_args=["--rate", "3.14"])
        assert app.rate == 3.14 and isinstance(app.rate, float)

    def test_scientific_notation_float(self) -> None:
        class App(Typed):
            small: float = 0.0

        app = App(_cli_parse_args=["--small", "1e-9"])
        assert app.small == 1e-9

    def test_optional_int_explicit_value(self) -> None:
        class App(Typed):
            limit: Optional[int] = None

        app = App(_cli_parse_args=["--limit", "100"])
        assert app.limit == 100

    def test_optional_int_default_unset(self) -> None:
        class App(Typed):
            limit: Optional[int] = None

        app = App(_cli_parse_args=[])
        assert app.limit is None

    def test_list_of_strings_inline_json(self) -> None:
        class App(Typed):
            tags: List[str] = []

        app = App(_cli_parse_args=["--tags", '["a","b","c"]'])
        assert app.tags == ["a", "b", "c"]

    def test_list_of_ints_with_coercion(self) -> None:
        """Strings inside a JSON list get coerced to ints."""

        class App(Typed):
            ports: List[int] = []

        app = App(_cli_parse_args=["--ports", '["80","443","8080"]'])
        assert app.ports == [80, 443, 8080]

    def test_dict_field_inline_json(self) -> None:
        class App(Typed):
            settings: Dict[str, str] = {}

        app = App(_cli_parse_args=["--settings", '{"key1":"v1","key2":"v2"}'])
        assert app.settings == {"key1": "v1", "key2": "v2"}

    def test_dict_with_mixed_value_types(self) -> None:
        class App(Typed):
            mapping: Dict[str, int] = {}

        app = App(_cli_parse_args=["--mapping", '{"a":1,"b":2}'])
        assert app.mapping == {"a": 1, "b": 2}

    def test_autoenum_string_coercion(self) -> None:
        class Color(AutoEnum):
            RED = auto()
            GREEN = auto()
            BLUE = auto()

        class App(Typed):
            color: Color = Color.RED

        app = App(_cli_parse_args=["--color", "GREEN"])
        assert app.color is Color.GREEN

    def test_autoenum_fuzzy_match_via_cli(self) -> None:
        """AutoEnum's fuzzy matching applies to CLI string inputs."""

        class Mode(AutoEnum):
            FAST_MODE = auto()
            SLOW_MODE = auto()

        class App(Typed):
            mode: Mode = Mode.FAST_MODE

        # AutoEnum normalizes case and punctuation:
        app = App(_cli_parse_args=["--mode", "slow_mode"])
        assert app.mode is Mode.SLOW_MODE


# ===========================================================================
# Argument form edge cases
# ===========================================================================


class TestCLIArgumentForms:
    """Different ways to write the same flag on the command line."""

    def test_space_separated_form(self) -> None:
        class App(Typed):
            name: str = "default"

        app = App(_cli_parse_args=["--name", "alice"])
        assert app.name == "alice"

    def test_equals_separated_form(self) -> None:
        class App(Typed):
            name: str = "default"

        app = App(_cli_parse_args=["--name=alice"])
        assert app.name == "alice"

    def test_kebab_case_for_underscore_field(self) -> None:
        class App(Typed):
            log_level: str = "info"

        app = App(_cli_parse_args=["--log-level", "debug"])
        assert app.log_level == "debug"

    def test_snake_case_rejected_when_kebab_case_enabled(self) -> None:
        """With ``cli_kebab_case=True`` (Typed default), snake-case form is rejected.

        This pins the behavior: the Typed default chooses one canonical
        spelling for CLI flags. Users who want snake-case must override
        ``model_config = SettingsConfigDict(cli_kebab_case=False)``.
        """

        class App(Typed):
            log_level: str = "info"

        with pytest.raises((SystemExit, ValueError, ValidationError)):
            App(_cli_parse_args=["--log_level", "debug"])

    def test_implicit_bool_flag_true(self) -> None:
        class App(Typed):
            enabled: bool = False

        app = App(_cli_parse_args=["--enabled"])
        assert app.enabled is True

    def test_implicit_bool_flag_false(self) -> None:
        class App(Typed):
            enabled: bool = True

        app = App(_cli_parse_args=["--no-enabled"])
        assert app.enabled is False

    def test_explicit_bool_value_rejected_with_implicit_flags(self) -> None:
        """With ``cli_implicit_flags=True`` (Typed default), explicit
        ``--flag value`` form for booleans is rejected — the bool field
        ONLY exposes the ``--flag`` / ``--no-flag`` pair.

        This pins the behavior. Users who want ``--enabled true`` style
        must override ``model_config = SettingsConfigDict(cli_implicit_flags=False)``.
        """

        class App(Typed):
            enabled: bool = False

        with pytest.raises((SystemExit, ValueError, ValidationError)):
            App(_cli_parse_args=["--enabled", "true"])

    def test_repeated_flag_last_wins(self) -> None:
        class App(Typed):
            name: str = "default"

        app = App(_cli_parse_args=["--name", "first", "--name", "last"])
        assert app.name == "last"

    def test_unknown_flag_raises(self) -> None:
        class App(Typed):
            name: str = "default"

        with pytest.raises((SystemExit, ValueError, ValidationError)):
            App(_cli_parse_args=["--unknown-flag", "value"])

    def test_missing_value_after_flag_raises(self) -> None:
        class App(Typed):
            name: str = "default"
            count: int = 0

        with pytest.raises((SystemExit, ValueError, ValidationError)):
            App(_cli_parse_args=["--name"])

    def test_required_field_missing_raises(self) -> None:
        """A field with no default and no CLI value triggers a validation error."""

        class App(Typed):
            mandatory: str  # no default

        with pytest.raises((ValueError, ValidationError)):
            App(_cli_parse_args=[])

    def test_required_field_provided_works(self) -> None:
        class App(Typed):
            mandatory: str

        app = App(_cli_parse_args=["--mandatory", "hello"])
        assert app.mandatory == "hello"

    def test_invalid_int_value_raises(self) -> None:
        class App(Typed):
            count: int = 0

        with pytest.raises((ValueError, ValidationError, SystemExit)):
            App(_cli_parse_args=["--count", "not-a-number"])

    def test_value_with_special_chars_via_equals(self) -> None:
        """Values containing spaces / special chars round-trip via the
        ``--flag=value`` form (as long as the shell quotes them)."""

        class App(Typed):
            note: str = ""

        app = App(_cli_parse_args=["--note=hello world; echo BAD"])
        assert app.note == "hello world; echo BAD"

    def test_empty_string_value(self) -> None:
        class App(Typed):
            label: str = "default"

        app = App(_cli_parse_args=["--label", ""])
        assert app.label == ""

    def test_zero_int_value(self) -> None:
        class App(Typed):
            count: int = 5

        app = App(_cli_parse_args=["--count", "0"])
        assert app.count == 0


# ===========================================================================
# Frozen-instance state survival across the validator re-fire
# ===========================================================================


class TestPrivateAttrSurvival:
    """``PrivateAttr`` mutations on an inner Typed are NOT lost when the
    inner is held as a field of an outer Typed — the marker neutralizes
    Pydantic's after-validator re-fire, so user state is preserved.
    """

    def test_private_attr_dict_mutations_preserved(self) -> None:
        """A dict PrivateAttr populated in post_initialize survives outer construction."""

        class Inner(Typed):
            name: str
            _state: dict = PrivateAttr(default_factory=dict)

            def post_initialize(self) -> None:
                self._state["initialized"] = True

        class Outer(Typed):
            inner: Inner

        i = Inner(name="x")
        # User mutates state AFTER post_initialize, BEFORE wrapping in outer:
        i._state["user_added"] = "value"
        assert i._state == {"initialized": True, "user_added": "value"}

        o = Outer(inner=i)
        # If the validator re-fire had cleared state or re-run post_initialize,
        # we'd see _state["user_added"] vanish or _state reset to {"initialized": True}:
        assert o.inner is i
        assert o.inner._state == {"initialized": True, "user_added": "value"}

    def test_private_attr_counter_not_incremented(self) -> None:
        """A counter incremented in post_initialize is NOT incremented twice."""

        class Inner(Typed):
            name: str
            _calls: int = PrivateAttr(default=0)

            def post_initialize(self) -> None:
                object.__setattr__(self, "_calls", self._calls + 1)

        class Outer(Typed):
            inner: Inner

        i = Inner(name="x")
        assert i._calls == 1
        Outer(inner=i)
        assert i._calls == 1, f"post_initialize re-ran on outer construction: _calls={i._calls}"

    def test_private_attr_object_identity_preserved(self) -> None:
        """An object stored in PrivateAttr keeps the SAME id() through outer construction."""
        sentinel_obj = object()

        class Inner(Typed):
            name: str
            _resource: Optional[object] = PrivateAttr(default=None)

            def post_initialize(self) -> None:
                if self._resource is None:
                    object.__setattr__(self, "_resource", sentinel_obj)

        class Outer(Typed):
            inner: Inner

        i = Inner(name="x")
        assert i._resource is sentinel_obj
        original_id = id(i._resource)

        o = Outer(inner=i)
        assert o.inner._resource is sentinel_obj
        assert id(o.inner._resource) == original_id

    def test_deeply_nested_private_attr_preserved(self) -> None:
        """PrivateAttr survives THREE levels of nesting."""

        class Leaf(Typed):
            name: str
            _state: List[str] = PrivateAttr(default_factory=list)

            def post_initialize(self) -> None:
                self._state.append("post_init")

        class Mid(Typed):
            leaf: Leaf

        class Root(Typed):
            mid: Mid

        leaf = Leaf(name="x")
        leaf._state.append("user_added")
        assert leaf._state == ["post_init", "user_added"]

        root = Root(mid=Mid(leaf=leaf))
        assert root.mid.leaf is leaf
        assert root.mid.leaf._state == ["post_init", "user_added"]


# ===========================================================================
# Multi-instance scenarios
# ===========================================================================


class TestMultiInstanceIdempotency:
    """Multiple instances + multiple containers + various reuse patterns."""

    def test_two_distinct_instances_in_same_outer(self) -> None:
        per_instance: "Counter[int]" = Counter()

        class Inner(Typed):
            value: str

            def post_initialize(self) -> None:
                per_instance[id(self)] += 1

        class Outer(Typed):
            a: Inner
            b: Inner

        a = Inner(value="a")
        b = Inner(value="b")
        Outer(a=a, b=b)

        assert per_instance[id(a)] == 1
        assert per_instance[id(b)] == 1
        assert id(a) != id(b)

    def test_same_instance_in_two_outers(self) -> None:
        """The same instance reused across TWO different outers fires once total."""
        per_instance: "Counter[int]" = Counter()

        class Inner(Typed):
            value: str

            def post_initialize(self) -> None:
                per_instance[id(self)] += 1

        class OuterA(Typed):
            inner: Inner

        class OuterB(Typed):
            inner: Inner

        shared = Inner(value="shared")
        assert per_instance[id(shared)] == 1

        a = OuterA(inner=shared)
        b = OuterB(inner=shared)

        assert per_instance[id(shared)] == 1, (
            f"Shared instance fired multiple times across outers: count={per_instance[id(shared)]}"
        )
        assert a.inner is shared
        assert b.inner is shared

    def test_list_with_duplicate_references(self) -> None:
        """A list containing the same instance twice fires post_initialize once."""
        per_instance: "Counter[int]" = Counter()

        class Inner(Typed):
            value: str

            def post_initialize(self) -> None:
                per_instance[id(self)] += 1

        class Outer(Typed):
            items: List[Inner]

        shared = Inner(value="shared")
        assert per_instance[id(shared)] == 1

        Outer(items=[shared, shared, shared])
        assert per_instance[id(shared)] == 1, (
            f"Repeated reference in list re-fired: count={per_instance[id(shared)]}"
        )

    def test_shared_inner_across_dict_values(self) -> None:
        per_instance: "Counter[int]" = Counter()

        class Inner(Typed):
            value: str

            def post_initialize(self) -> None:
                per_instance[id(self)] += 1

        class Outer(Typed):
            mapping: Dict[str, Inner]

        shared = Inner(value="x")
        Outer(mapping={"a": shared, "b": shared, "c": shared})

        assert per_instance[id(shared)] == 1

    def test_distinct_inners_in_dict_each_fire_once(self) -> None:
        per_instance: "Counter[int]" = Counter()

        class Inner(Typed):
            value: str

            def post_initialize(self) -> None:
                per_instance[id(self)] += 1

        class Outer(Typed):
            mapping: Dict[str, Inner]

        a = Inner(value="a")
        b = Inner(value="b")
        Outer(mapping={"x": a, "y": b})

        assert per_instance[id(a)] == 1
        assert per_instance[id(b)] == 1
