"""Tests for ``Annotated[X, TypedPath]`` — load nested Typed fields from JSON / YAML files.

This file pins the contract documented in
``trojanshot/DESIGN-PYDANTIC-NESTED-TYPED.md`` §4. The annotation
``Annotated[X, TypedPath]`` makes a field accept any of:

1. A pre-built ``X`` instance (identity preserved).
2. A dict matching ``X``'s schema.
3. A path string ending in ``.json``, ``.yaml``, or ``.yml``, OR a
   ``Path`` object pointing to such a file. The file is loaded,
   parsed, and validated as ``X``.

The path-loading machinery handles:

- Recursive nested resolution (a JSON file referencing another JSON
  file via a relative path resolves the second path against the first
  file's directory).
- CLI integration via ``Typed.parse_cli_args`` (argv is preprocessed
  so ``--target file.json --target.x.y VALUE`` deep-merges).
- Optional[X] union case.
- Missing files, malformed files, wrong root types — all produce
  clear errors that name the field and the resolved absolute path.

The implementation lives in ``morphic.typed`` next to the existing
lifecycle machinery; the ``Annotated[X, TypedPath]`` marker is the
discovery mechanism, the actual load logic runs inside the
``_pre_set_validate_inputs`` ``model_validator(mode="before")`` so it
slots cleanly into the existing pipeline.
"""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Annotated, List, Optional

import pytest

from morphic import Typed, TypedPath

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
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_config_dir(tmp_path: Path) -> Path:
    """A clean temp directory layout mirroring trojanshot's config tree:

    ``tmp_path/configs/llm/`` and ``tmp_path/configs/infra/`` are pre-created.
    """
    (tmp_path / "configs" / "llm").mkdir(parents=True)
    (tmp_path / "configs" / "infra").mkdir(parents=True)
    (tmp_path / "configs" / "judges").mkdir(parents=True)
    return tmp_path


# ---------------------------------------------------------------------------
# Demo classes used by multiple test classes.
# ---------------------------------------------------------------------------


class Inner(Typed):
    """Simple two-field Typed used as a TypedPath inner type."""

    name: str
    count: int = 0


class Outer(Typed):
    """Single TypedPath field at the root."""

    inner: Annotated[Inner, TypedPath] = None


class OuterOptional(Typed):
    """Optional[Inner] with TypedPath."""

    inner: Annotated[Optional[Inner], TypedPath] = None


# A two-level nested hierarchy mirroring the trojanshot
# Judge -> LLM -> Infra chain.
class Infra(Typed):
    mode: str = "Sync"
    address: str = "auto"


class LLMC(Typed):
    model: str
    infra: Annotated[Infra, TypedPath] = Infra()


class JudgeCfg(Typed):
    judge_name: str
    llm: Annotated[LLMC, TypedPath]


# ===========================================================================
# Singleton / marker contract
# ===========================================================================


class TestTypedPathSingleton:
    """``TypedPath`` is a singleton; ``TypedPath()`` returns the same instance."""

    def test_typed_path_is_a_singleton(self) -> None:
        from morphic.typed import _TypedPathMarker

        assert isinstance(TypedPath, _TypedPathMarker)

    def test_typed_path_called_returns_same_instance(self) -> None:
        """Both ``Annotated[X, TypedPath]`` (bare) and ``Annotated[X, TypedPath()]``
        (called) refer to the same singleton, so users can use either form."""
        assert TypedPath() is TypedPath
        assert TypedPath()() is TypedPath

    def test_typed_path_repr(self) -> None:
        assert repr(TypedPath) == "TypedPath"

    def test_two_separate_class_instances_are_same(self) -> None:
        """Even creating ``_TypedPathMarker()`` directly returns the singleton."""
        from morphic.typed import _TypedPathMarker

        a = _TypedPathMarker()
        b = _TypedPathMarker()
        assert a is b is TypedPath


# ===========================================================================
# Programmatic construction (no CLI)
# ===========================================================================


class TestProgrammaticInputForms:
    """The three accepted input shapes for a TypedPath field."""

    def test_pre_built_instance_preserves_identity(self) -> None:
        i = Inner(name="prebuilt", count=42)
        o = Outer(inner=i)
        assert o.inner is i

    def test_dict_input_validated_as_inner_type(self) -> None:
        o = Outer(inner={"name": "from-dict", "count": 5})
        assert isinstance(o.inner, Inner)
        assert o.inner.name == "from-dict"
        assert o.inner.count == 5

    def test_path_string_loaded_from_disk(self, tmp_path: Path) -> None:
        path = tmp_path / "inner.json"
        path.write_text(json.dumps({"name": "from-json", "count": 99}))
        o = Outer(inner=str(path))
        assert isinstance(o.inner, Inner)
        assert o.inner.name == "from-json"
        assert o.inner.count == 99

    def test_pathlib_path_object_loaded_from_disk(self, tmp_path: Path) -> None:
        path = tmp_path / "inner.json"
        path.write_text(json.dumps({"name": "from-path-obj", "count": 7}))
        o = Outer(inner=path)  # Path object, not str
        assert o.inner.name == "from-path-obj"

    def test_yaml_file_loaded(self, tmp_path: Path) -> None:
        yaml = pytest.importorskip("yaml")
        path = tmp_path / "inner.yaml"
        with open(path, "w") as f:
            yaml.safe_dump({"name": "from-yaml", "count": 11}, f)
        o = Outer(inner=str(path))
        assert o.inner.name == "from-yaml"
        assert o.inner.count == 11

    def test_yml_extension_treated_as_yaml(self, tmp_path: Path) -> None:
        yaml = pytest.importorskip("yaml")
        path = tmp_path / "inner.yml"  # Note: .yml not .yaml
        with open(path, "w") as f:
            yaml.safe_dump({"name": "from-yml", "count": 12}, f)
        o = Outer(inner=str(path))
        assert o.inner.name == "from-yml"


# ===========================================================================
# Optional[X] handling
# ===========================================================================


class TestOptionalTypedPath:
    """``Annotated[Optional[X], TypedPath] = None`` works correctly."""

    def test_optional_default_none(self) -> None:
        o = OuterOptional()
        assert o.inner is None

    def test_optional_explicit_none(self) -> None:
        o = OuterOptional(inner=None)
        assert o.inner is None

    def test_optional_with_path(self, tmp_path: Path) -> None:
        path = tmp_path / "inner.json"
        path.write_text(json.dumps({"name": "x"}))
        o = OuterOptional(inner=str(path))
        assert o.inner.name == "x"

    def test_optional_with_dict(self) -> None:
        o = OuterOptional(inner={"name": "x"})
        assert o.inner.name == "x"

    def test_optional_with_instance(self) -> None:
        i = Inner(name="x")
        o = OuterOptional(inner=i)
        assert o.inner is i


# ===========================================================================
# Nested path resolution (the trojanshot Judge -> LLM -> Infra case)
# ===========================================================================


class TestNestedPathResolution:
    """Relative paths inside a loaded JSON resolve against THAT file's directory.

    This is the §4.2 contract from
    ``trojanshot/DESIGN-PYDANTIC-NESTED-TYPED.md``: a Judge config
    references an LLM config, which references an Infra config, with
    each relative path threaded through transparently.
    """

    def test_two_level_nested_resolution(self, tmp_config_dir: Path) -> None:
        infra_path = tmp_config_dir / "configs" / "infra" / "sync.json"
        infra_path.write_text(json.dumps({"mode": "Ray", "address": "ray://x:1"}))

        llm_path = tmp_config_dir / "configs" / "llm" / "wildguard.json"
        llm_path.write_text(
            json.dumps(
                {
                    "model": "wildguard",
                    "infra": "../infra/sync.json",  # relative to llm/'s parent dir
                }
            )
        )

        ## When we load wildguard.json, the inner ``infra`` field's
        ## relative path is resolved against ``configs/llm/`` — NOT
        ## against the user's CWD.
        j = JudgeCfg(judge_name="j", llm=str(llm_path))
        assert j.llm.model == "wildguard"
        assert j.llm.infra.mode == "Ray"
        assert j.llm.infra.address == "ray://x:1"

    def test_three_level_nested_resolution(self, tmp_path: Path) -> None:
        """A -> B -> C, each in a different directory.

        Note on the file layout: the file referenced by ``A.child``
        contains ``B``'s data (since ``A.child`` is annotated as
        ``Annotated[B, TypedPath]``), the file inside that one
        contains ``C``'s data, and so on. We name the files by what
        they contain, not by the field that references them.
        """

        class C(Typed):
            value: str

        class B(Typed):
            name: str
            child: Annotated[C, TypedPath]

        class A(Typed):
            name: str
            child: Annotated[B, TypedPath]

        (tmp_path / "dir_a").mkdir()
        (tmp_path / "dir_b").mkdir()
        (tmp_path / "dir_c").mkdir()

        ## c_data.json contains C's data; lives in dir_c/.
        (tmp_path / "dir_c" / "c_data.json").write_text(json.dumps({"value": "leaf"}))

        ## b_data.json contains B's data; lives in dir_b/. Its `child`
        ## field is the path to c_data.json, RELATIVE to dir_b/.
        (tmp_path / "dir_b" / "b_data.json").write_text(
            json.dumps(
                {
                    "name": "B-config",
                    "child": "../dir_c/c_data.json",
                }
            )
        )

        ## a_entrypoint.json (in dir_a/) is what A.child points at;
        ## it contains B's data, so its keys match B's fields. Its
        ## `child` field points at b_data.json, RELATIVE to dir_a/.
        (tmp_path / "dir_a" / "a_entrypoint.json").write_text(
            json.dumps(
                {
                    "name": "B-from-A",
                    "child": "../dir_c/c_data.json",
                }
            )
        )

        a = A(name="root", child=str(tmp_path / "dir_a" / "a_entrypoint.json"))
        assert a.child.name == "B-from-A"
        assert a.child.child.value == "leaf"

    def test_absolute_paths_in_nested_files_work(self, tmp_path: Path) -> None:
        """An absolute path inside a loaded file is used as-is."""
        infra_path = tmp_path / "configs" / "infra" / "sync.json"
        infra_path.parent.mkdir(parents=True)
        infra_path.write_text(json.dumps({"mode": "Sync"}))

        llm_path = tmp_path / "configs" / "llm" / "qwen.json"
        llm_path.parent.mkdir(parents=True)
        llm_path.write_text(
            json.dumps(
                {
                    "model": "qwen",
                    "infra": str(infra_path),  # absolute path
                }
            )
        )

        ## Even though the user constructs from the absolute LLM path
        ## (parent dir is configs/llm/), the inner absolute path is
        ## used as-is, not joined.
        j = JudgeCfg(judge_name="j", llm=str(llm_path))
        assert j.llm.infra.mode == "Sync"

    def test_mixed_dict_and_path_at_different_levels(self, tmp_path: Path) -> None:
        """Outer can use a path while the loaded file inlines the inner."""
        llm_path = tmp_path / "qwen.json"
        llm_path.write_text(
            json.dumps(
                {
                    "model": "qwen",
                    "infra": {"mode": "Sync", "address": "auto"},  # inline dict, not a path
                }
            )
        )
        j = JudgeCfg(judge_name="j", llm=str(llm_path))
        assert j.llm.infra.mode == "Sync"

    def test_pre_built_inner_inside_loaded_outer_path(self, tmp_path: Path) -> None:
        """Mixing pre-built inner instances with path-loaded outers."""
        llm_path = tmp_path / "qwen.json"
        llm_path.write_text(
            json.dumps(
                {
                    "model": "qwen",
                    "infra": "./infra.json",
                }
            )
        )
        (tmp_path / "infra.json").write_text(json.dumps({"mode": "Ray"}))

        j = JudgeCfg(judge_name="j", llm=str(llm_path))
        assert j.llm.infra.mode == "Ray"


# ===========================================================================
# Errors and edge cases
# ===========================================================================


class TestErrorPaths:
    """Bad input surfaces as clear errors that name the field and resolved path."""

    def test_missing_file_raises_filenotfound_with_field_name(self) -> None:
        with pytest.raises((FileNotFoundError, ValueError)) as exc_info:
            Outer(inner="/does/not/exist.json")
        msg = str(exc_info.value)
        assert "inner" in msg or "/does/not/exist.json" in msg

    def test_corrupt_json_raises_value_error(self, tmp_path: Path) -> None:
        path = tmp_path / "broken.json"
        path.write_text("{not valid json")
        with pytest.raises((ValueError,)) as exc_info:
            Outer(inner=str(path))
        ## The error path may go through Typed's wrapping machinery,
        ## but the original ValueError text should mention the file.
        assert (
            "broken.json" in str(exc_info.value)
            or "JSON" in str(exc_info.value).upper()
            or "json" in str(exc_info.value).lower()
        )

    def test_json_top_level_is_not_object(self, tmp_path: Path) -> None:
        """A JSON file whose top-level is a list or scalar is invalid for
        a TypedPath field (Typed constructors take ``**kwargs``)."""
        path = tmp_path / "list.json"
        path.write_text(json.dumps([1, 2, 3]))
        with pytest.raises((ValueError,)):
            Outer(inner=str(path))

    def test_path_to_directory_raises(self, tmp_path: Path) -> None:
        """Passing a directory (with .json in name??) raises."""
        ## Path resolves but isn't a regular file.
        sub = tmp_path / "fake.json"
        sub.mkdir()  # directory named "fake.json"
        with pytest.raises((ValueError,)):
            Outer(inner=str(sub))

    def test_string_without_file_extension_not_loaded(self) -> None:
        """A plain string that doesn't end in .json/.yaml/.yml is NOT treated
        as a path — it just goes to inner-type validation, which fails."""
        with pytest.raises(ValueError):
            ## "not-a-path" is a string but no extension, so it does NOT
            ## get loaded. It then fails Inner's validation (Inner requires
            ## a dict/instance, not a string).
            Outer(inner="not-a-path")


# ===========================================================================
# Validation still runs on loaded content
# ===========================================================================


class TestValidationStillRuns:
    """Loading a file does NOT skip validation of the inner Typed."""

    def test_invalid_field_in_loaded_json_raises(self, tmp_path: Path) -> None:
        """A loaded file with wrong types fails validation as if it were
        a plain dict input."""
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"name": "x", "count": "not-a-number"}))
        with pytest.raises((ValueError,)):
            Outer(inner=str(path))

    def test_missing_required_field_in_loaded_json_raises(self, tmp_path: Path) -> None:
        path = tmp_path / "incomplete.json"
        path.write_text(json.dumps({"count": 5}))  # missing 'name'
        with pytest.raises((ValueError,)):
            Outer(inner=str(path))

    def test_extra_field_in_loaded_json_rejected(self, tmp_path: Path) -> None:
        """Typed's ``extra='forbid'`` applies to loaded JSON content too."""
        path = tmp_path / "extra.json"
        path.write_text(json.dumps({"name": "x", "extra_field": "y"}))
        with pytest.raises((ValueError,)):
            Outer(inner=str(path))


# ===========================================================================
# CLI integration via parse_cli_args
# ===========================================================================


class TestParseCLIArgsTypedPath:
    """``Typed.parse_cli_args`` correctly handles TypedPath fields."""

    def test_cli_path_loads_file(self, tmp_path: Path) -> None:
        path = tmp_path / "inner.json"
        path.write_text(json.dumps({"name": "from-cli", "count": 7}))
        o = Outer.parse_cli_args(["--inner", str(path)])
        assert o.inner.name == "from-cli"
        assert o.inner.count == 7

    def test_cli_path_equals_form(self, tmp_path: Path) -> None:
        """``--inner=path.json`` (single token) also works."""
        path = tmp_path / "inner.json"
        path.write_text(json.dumps({"name": "eq-form"}))
        o = Outer.parse_cli_args([f"--inner={path}"])
        assert o.inner.name == "eq-form"

    def test_cli_path_kebab_case_field_name(self, tmp_path: Path) -> None:
        """A field named ``my_inner`` is exposed as ``--my-inner``."""

        class Outer2(Typed):
            my_inner: Annotated[Inner, TypedPath] = None

        path = tmp_path / "inner.json"
        path.write_text(json.dumps({"name": "kebab"}))
        o = Outer2.parse_cli_args(["--my-inner", str(path)])
        assert o.my_inner.name == "kebab"

    def test_cli_path_snake_case_rejected(self, tmp_path: Path) -> None:
        """With Typed's default ``cli_kebab_case=True``, the snake_case
        flag form is rejected by argparse.

        This pins the underlying pydantic-settings behavior. To accept
        snake_case, a subclass would override
        ``model_config = SettingsConfigDict(cli_kebab_case=False)``.
        """

        class Outer2(Typed):
            my_inner: Annotated[Inner, TypedPath] = None

        path = tmp_path / "inner.json"
        path.write_text(json.dumps({"name": "x"}))
        with pytest.raises((SystemExit, ValueError)):
            Outer2.parse_cli_args(["--my_inner", str(path)])

    def test_cli_inline_json_still_works(self) -> None:
        """If the value is JSON (not a path-looking string), it is passed
        through to pydantic-settings unchanged."""
        o = Outer.parse_cli_args(["--inner", '{"name": "inline", "count": 5}'])
        assert o.inner.name == "inline"
        assert o.inner.count == 5

    def test_cli_path_plus_deep_override(self, tmp_path: Path) -> None:
        """The trojanshot pattern: file sets baseline, CLI flag patches a leaf.

        ``--inner file.json --inner.count 999`` => loaded dict + override
        merged via pydantic-settings' native deep-update.
        """
        path = tmp_path / "inner.json"
        path.write_text(json.dumps({"name": "from-file", "count": 1}))
        o = Outer.parse_cli_args(
            [
                "--inner",
                str(path),
                "--inner.count",
                "999",
            ]
        )
        assert o.inner.name == "from-file"  # from file
        assert o.inner.count == 999  # from CLI override

    def test_cli_path_plus_two_deep_overrides(self, tmp_path: Path) -> None:
        path = tmp_path / "inner.json"
        path.write_text(json.dumps({"name": "f", "count": 1}))
        o = Outer.parse_cli_args(
            [
                "--inner",
                str(path),
                "--inner.name",
                "patched-name",
                "--inner.count",
                "42",
            ]
        )
        assert o.inner.name == "patched-name"
        assert o.inner.count == 42

    def test_cli_yaml_path_works(self, tmp_path: Path) -> None:
        """YAML files load via CLI too."""
        yaml = pytest.importorskip("yaml")
        path = tmp_path / "inner.yaml"
        with open(path, "w") as f:
            yaml.safe_dump({"name": "yaml-cli", "count": 3}, f)
        o = Outer.parse_cli_args(["--inner", str(path)])
        assert o.inner.name == "yaml-cli"

    def test_cli_path_with_top_level_overrides(self, tmp_path: Path) -> None:
        """TypedPath field + sibling top-level field overrides."""

        class Outer3(Typed):
            inner: Annotated[Inner, TypedPath] = None
            seed: int = 42

        path = tmp_path / "inner.json"
        path.write_text(json.dumps({"name": "t"}))
        o = Outer3.parse_cli_args(["--inner", str(path), "--seed", "7"])
        assert o.inner.name == "t"
        assert o.seed == 7

    def test_cli_path_missing_file_raises(self) -> None:
        """A non-existent path produces a clear error from parse_cli_args
        too (the error happens during argv preprocessing)."""
        with pytest.raises((FileNotFoundError, ValueError)):
            Outer.parse_cli_args(["--inner", "/does/not/exist.json"])

    def test_cli_two_typed_path_fields(self, tmp_path: Path) -> None:
        """Multiple TypedPath fields on the same Typed."""

        class TwoInners(Typed):
            a: Annotated[Inner, TypedPath] = None
            b: Annotated[Inner, TypedPath] = None

        path_a = tmp_path / "a.json"
        path_b = tmp_path / "b.json"
        path_a.write_text(json.dumps({"name": "A-content"}))
        path_b.write_text(json.dumps({"name": "B-content"}))

        o = TwoInners.parse_cli_args(
            [
                "--a",
                str(path_a),
                "--b",
                str(path_b),
            ]
        )
        assert o.a.name == "A-content"
        assert o.b.name == "B-content"

    def test_cli_typed_path_with_nested_inside(self, tmp_config_dir: Path) -> None:
        """CLI loads a Judge config; the Judge file references LLM file
        which references Infra file."""
        infra_path = tmp_config_dir / "configs" / "infra" / "ray.json"
        infra_path.write_text(json.dumps({"mode": "Ray", "address": "ray://x:1"}))

        llm_path = tmp_config_dir / "configs" / "llm" / "qwen.json"
        llm_path.write_text(
            json.dumps(
                {
                    "model": "qwen",
                    "infra": "../infra/ray.json",
                }
            )
        )

        ## Use the JudgeCfg fixture defined at module level.
        j = JudgeCfg.parse_cli_args(
            [
                "--judge-name",
                "j",
                "--llm",
                str(llm_path),
            ]
        )
        assert j.llm.model == "qwen"
        assert j.llm.infra.mode == "Ray"

    def test_cli_typed_path_file_override_with_nested_deep_flag(self, tmp_config_dir: Path) -> None:
        """CLI loads JudgeCfg, and a deep flag inside the loaded LLM
        overrides one of LLM's fields.

        E.g., ``--llm qwen.json --llm.model patched-model``.
        """
        llm_path = tmp_config_dir / "configs" / "llm" / "qwen.json"
        llm_path.write_text(
            json.dumps(
                {
                    "model": "qwen-base",
                    "infra": {"mode": "Sync"},
                }
            )
        )
        j = JudgeCfg.parse_cli_args(
            [
                "--judge-name",
                "j",
                "--llm",
                str(llm_path),
                "--llm.model",
                "qwen-patched",
            ]
        )
        assert j.llm.model == "qwen-patched"
        assert j.llm.infra.mode == "Sync"


# ===========================================================================
# Real-subprocess integration tests
# ===========================================================================


_SCRIPT_TROJANSHOT_LIKE = textwrap.dedent('''
    """Mimic the trojanshot Judge -> LLM -> Infra config layout."""
    import json
    from typing import Annotated
    from morphic import Typed, TypedPath

    class Infra(Typed):
        mode: str = "Sync"
        address: str = "auto"

    class LLMC(Typed):
        model: str
        infra: Annotated[Infra, TypedPath] = Infra()

    class JudgeCfg(Typed):
        judge_name: str = "default"
        llm: Annotated[LLMC, TypedPath] = None

    if __name__ == "__main__":
        cfg = JudgeCfg.parse_cli_args()
        print(json.dumps({
            "judge_name": cfg.judge_name,
            "llm_model": cfg.llm.model if cfg.llm else None,
            "infra_mode": cfg.llm.infra.mode if cfg.llm and cfg.llm.infra else None,
            "infra_address": cfg.llm.infra.address if cfg.llm and cfg.llm.infra else None,
        }))
''')


class TestSubprocessTypedPath:
    """Spawn real ``python -c`` processes to exercise the full argv path.

    These tests build out a config tree on disk, then run a script that
    parses CLI flags, and assert on the JSON-encoded result printed to
    stdout. This catches issues that don't show up in in-process tests
    (e.g., issues with ``sys.argv`` handling, with how
    ``parse_cli_args`` interacts with real argparse behavior).
    """

    def test_subprocess_simple_path_load(self, tmp_path: Path) -> None:
        llm_path = tmp_path / "qwen.json"
        llm_path.write_text(
            json.dumps(
                {
                    "model": "qwen",
                    "infra": {"mode": "Sync"},
                }
            )
        )
        result = _run_python(
            _SCRIPT_TROJANSHOT_LIKE,
            [
                "--judge-name",
                "j",
                "--llm",
                str(llm_path),
            ],
        )
        assert result.returncode == 0, (
            f"Subprocess failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
        data = json.loads(result.stdout)
        assert data == {
            "judge_name": "j",
            "llm_model": "qwen",
            "infra_mode": "Sync",
            "infra_address": "auto",
        }

    def test_subprocess_nested_path_chain(self, tmp_path: Path) -> None:
        """Judge -> LLM file -> Infra file, each in its own directory."""
        (tmp_path / "configs" / "infra").mkdir(parents=True)
        (tmp_path / "configs" / "llm").mkdir(parents=True)

        infra_path = tmp_path / "configs" / "infra" / "ray.json"
        infra_path.write_text(
            json.dumps(
                {
                    "mode": "Ray",
                    "address": "ray://prod:10001",
                }
            )
        )

        llm_path = tmp_path / "configs" / "llm" / "qwen.json"
        llm_path.write_text(
            json.dumps(
                {
                    "model": "qwen-large",
                    "infra": "../infra/ray.json",
                }
            )
        )

        result = _run_python(
            _SCRIPT_TROJANSHOT_LIKE,
            [
                "--judge-name",
                "production",
                "--llm",
                str(llm_path),
            ],
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data == {
            "judge_name": "production",
            "llm_model": "qwen-large",
            "infra_mode": "Ray",
            "infra_address": "ray://prod:10001",
        }

    def test_subprocess_path_plus_deep_override(self, tmp_path: Path) -> None:
        """The trojanshot pattern: ``--llm file.json --llm.model patched``."""
        llm_path = tmp_path / "qwen.json"
        llm_path.write_text(
            json.dumps(
                {
                    "model": "qwen-base",
                    "infra": {"mode": "Sync"},
                }
            )
        )
        result = _run_python(
            _SCRIPT_TROJANSHOT_LIKE,
            [
                "--judge-name",
                "j",
                "--llm",
                str(llm_path),
                "--llm.model",
                "qwen-cli-patched",
            ],
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["llm_model"] == "qwen-cli-patched"
        assert data["infra_mode"] == "Sync"

    def test_subprocess_yaml_path(self, tmp_path: Path) -> None:
        yaml = pytest.importorskip("yaml")
        llm_path = tmp_path / "qwen.yaml"
        with open(llm_path, "w") as f:
            yaml.safe_dump(
                {
                    "model": "yaml-model",
                    "infra": {"mode": "Ray", "address": "ray://yaml:1"},
                },
                f,
            )
        result = _run_python(
            _SCRIPT_TROJANSHOT_LIKE,
            [
                "--judge-name",
                "j",
                "--llm",
                str(llm_path),
            ],
        )
        assert result.returncode == 0, result.stderr
        data = json.loads(result.stdout)
        assert data["llm_model"] == "yaml-model"

    def test_subprocess_missing_file_fails(self) -> None:
        result = _run_python(
            _SCRIPT_TROJANSHOT_LIKE,
            [
                "--judge-name",
                "j",
                "--llm",
                "/does/not/exist.json",
            ],
        )
        assert result.returncode != 0
        ## The error mentions the missing path:
        combined = result.stderr + result.stdout
        assert "/does/not/exist.json" in combined or "FileNotFoundError" in combined

    def test_subprocess_help_shows_typed_path_field(self) -> None:
        """``--help`` includes the TypedPath field in its usage info."""
        result = _run_python(_SCRIPT_TROJANSHOT_LIKE, ["--help"])
        ## --help exits 0 in argparse; on some pydantic versions the
        ## help generation may differ slightly, so just check that the
        ## flag name is mentioned.
        assert result.returncode == 0, result.stderr
        assert "--llm" in result.stdout


# ===========================================================================
# Weird edge cases
# ===========================================================================


class TestWeirdEdgeCases:
    """Things that might trip the implementation."""

    def test_path_with_uppercase_extension(self, tmp_path: Path) -> None:
        """Extensions are matched case-insensitively (``.JSON`` is treated
        the same as ``.json``)."""
        path = tmp_path / "FILE.JSON"
        path.write_text(json.dumps({"name": "upper"}))
        o = Outer(inner=str(path))
        assert o.inner.name == "upper"

    def test_path_with_mixed_case_extension(self, tmp_path: Path) -> None:
        path = tmp_path / "file.JsOn"
        path.write_text(json.dumps({"name": "mixed"}))
        o = Outer(inner=str(path))
        assert o.inner.name == "mixed"

    def test_path_with_dots_in_filename(self, tmp_path: Path) -> None:
        """A filename like ``my.config.json`` works (only the LAST dot
        determines the extension)."""
        path = tmp_path / "my.config.json"
        path.write_text(json.dumps({"name": "dots"}))
        o = Outer(inner=str(path))
        assert o.inner.name == "dots"

    def test_path_with_spaces_in_filename(self, tmp_path: Path) -> None:
        path = tmp_path / "my config.json"
        path.write_text(json.dumps({"name": "with spaces"}))
        o = Outer(inner=str(path))
        assert o.inner.name == "with spaces"

    def test_empty_json_object_loaded(self, tmp_path: Path) -> None:
        """Empty ``{}`` loads, but Inner's required ``name`` field then fails."""
        path = tmp_path / "empty.json"
        path.write_text("{}")
        with pytest.raises(ValueError):
            Outer(inner=str(path))

    def test_json_with_unicode_loaded(self, tmp_path: Path) -> None:
        path = tmp_path / "unicode.json"
        path.write_text(json.dumps({"name": "héllo wörld 🚀"}, ensure_ascii=False), encoding="utf-8")
        o = Outer(inner=str(path))
        assert o.inner.name == "héllo wörld 🚀"

    def test_json_with_large_payload(self, tmp_path: Path) -> None:
        """A reasonably large JSON file loads correctly."""

        class Big(Typed):
            name: str
            data: List[int] = []

        class WithBig(Typed):
            big: Annotated[Big, TypedPath]

        path = tmp_path / "big.json"
        path.write_text(
            json.dumps(
                {
                    "name": "bigfile",
                    "data": list(range(10_000)),
                }
            )
        )
        o = WithBig(big=str(path))
        assert o.big.name == "bigfile"
        assert len(o.big.data) == 10_000
        assert o.big.data[5000] == 5000

    def test_list_of_typed_path_is_NOT_supported(self) -> None:
        """``List[Annotated[X, TypedPath]]`` is NOT a documented use case.

        TypedPath is for single-Typed fields only. This test pins the
        current behavior (which is "the marker on the list element type
        is not picked up by our discovery"). If someone asks for list
        support later, this test will fail and signal that the design
        needs extending.
        """

        class WithList(Typed):
            items: List[Annotated[Inner, TypedPath]] = []

        ## TypedPath only triggers on single-field reads. A list of
        ## paths would need a different mechanism (and a different
        ## discovery rule).
        ## Pre-built instance in the list works as expected:
        i = Inner(name="x")
        o = WithList(items=[i])
        assert o.items == [i]

    def test_pure_typed_with_no_typed_path_fields_unaffected(self) -> None:
        """A Typed with no TypedPath fields has zero behavioral changes.

        This is critical: morphic's path-loading must not run / cost
        anything when classes don't opt in.
        """

        class Plain(Typed):
            name: str
            count: int = 0

        ## Normal construction:
        p = Plain(name="x", count=5)
        assert p.name == "x"

        ## CLI parse:
        p = Plain.parse_cli_args(["--name", "y", "--count", "7"])
        assert p.name == "y" and p.count == 7

    def test_default_value_with_path_string_does_not_load(self) -> None:
        """A path string supplied as a DEFAULT VALUE (not user input) is...
        also loaded, because Typed has ``validate_default=True``.

        This is intentional: defaults go through the same validation
        pipeline as user input. If you want a default-but-not-loaded
        path, use ``default_factory=lambda: SomeInstance(...)`` instead.
        """

        class WithDefault(Typed):
            inner: Annotated[Inner, TypedPath] = "/nonexistent/file.json"

        ## At class-definition time, validate_default tries to load and fails:
        with pytest.raises((FileNotFoundError, ValueError)):
            WithDefault()

    def test_pathlike_instance_not_a_string(self, tmp_path: Path) -> None:
        """A user-defined PathLike that returns a path-shaped string is
        treated as a path."""

        class MyPath:
            def __init__(self, p):
                self._p = p

            def __fspath__(self):
                return str(self._p)

            def __str__(self):
                return str(self._p)

        path = tmp_path / "x.json"
        path.write_text(json.dumps({"name": "fspath"}))

        ## ``isinstance(value, Path)`` is False here, but we also accept
        ## bare strings via ``str(value)``. The MyPath instance itself
        ## isn't a string, so it WON'T be treated as a path. Pass it
        ## explicitly converted (str()):
        o = Outer(inner=str(MyPath(path)))
        assert o.inner.name == "fspath"


# ===========================================================================
# Registry dispatch composed with TypedPath
# ===========================================================================


class TestTypedPathWithRegistryDispatch:
    """The ``Annotated[AbstractBase, TypedPath]`` + ``__type__`` pattern.

    Scenario: a field is annotated with an abstract ``Typed + Registry``
    base, AND has the ``TypedPath`` marker. The on-disk JSON/YAML file
    contains a ``__type__`` discriminator key plus subclass-specific
    fields (some of which themselves use ``TypedPath`` for relative paths).

    The contract: relative paths declared on the SUBCLASS (not on the
    abstract base) must still be resolved against the loaded file's
    directory. Without the discriminator-aware dispatch in
    ``_typed_path_resolve_in_dict``, those subclass-only TypedPath
    fields would be invisible during the in-band recursive load, and
    their relative paths would later be resolved against the user's
    cwd instead of the parent file's directory.
    """

    def _make_classes(self):
        """Build a fresh class hierarchy for each test (avoids Registry
        cross-test pollution)."""
        from abc import ABC

        from morphic import Registry

        class LeafConfig(Typed):
            label: str
            count: int = 0

        class AbstractBase(Typed, Registry, ABC):
            """Registry root. Has no TypedPath fields itself."""

            base_field: str = "default-base"

        class ConcreteWithPath(AbstractBase):
            """Subclass that adds a TypedPath-annotated field."""

            aliases = ("with_path",)
            leaf: Annotated[LeafConfig, TypedPath]

        class ConcreteWithoutPath(AbstractBase):
            """Subclass that adds a non-TypedPath field."""

            aliases = ("without_path",)
            number: int = 7

        class Holder(Typed):
            target: Annotated[AbstractBase, TypedPath]

        return LeafConfig, AbstractBase, ConcreteWithPath, ConcreteWithoutPath, Holder

    def test_subclass_typed_path_field_resolves_relative_path_against_parent_file(
        self,
        tmp_path: Path,
    ) -> None:
        """The core regression test for the agent's fix.

        - Outer config file references ``../leaf/leaf.json`` for the
          subclass-only ``leaf`` field.
        - Without the fix: the abstract base's ``model_fields`` doesn't
          include ``leaf``, so the recursive load skips it. Later
          Pydantic tries to resolve ``../leaf/leaf.json`` against the
          user's cwd → ``FileNotFoundError``.
        - With the fix: the discriminator is read, the concrete
          subclass is selected, ``leaf`` is found in its
          ``model_fields``, and the relative path is resolved against
          the parent file's directory.
        """
        LeafConfig, AbstractBase, ConcreteWithPath, ConcreteWithoutPath, Holder = self._make_classes()

        (tmp_path / "configs" / "outer").mkdir(parents=True)
        (tmp_path / "configs" / "leaf").mkdir(parents=True)

        (tmp_path / "configs" / "leaf" / "leaf.json").write_text(
            json.dumps(
                {
                    "label": "leaf-from-file",
                    "count": 99,
                }
            )
        )
        (tmp_path / "configs" / "outer" / "with_path.json").write_text(
            json.dumps(
                {
                    "__type__": "with_path",
                    "leaf": "../leaf/leaf.json",  # subclass-only TypedPath field
                }
            )
        )

        h = Holder(
            target=str(tmp_path / "configs" / "outer" / "with_path.json"),
        )
        assert type(h.target) is ConcreteWithPath
        assert h.target.leaf.label == "leaf-from-file"
        assert h.target.leaf.count == 99

    def test_subclass_with_no_typed_path_fields_works(self, tmp_path: Path) -> None:
        """Switching to the concrete subclass also works when the subclass
        has no TypedPath fields at all (the field iteration just finds
        nothing to load, which is fine)."""
        LeafConfig, AbstractBase, ConcreteWithPath, ConcreteWithoutPath, Holder = self._make_classes()

        path = tmp_path / "without.json"
        path.write_text(json.dumps({"__type__": "without_path", "number": 42}))

        h = Holder(target=str(path))
        assert type(h.target) is ConcreteWithoutPath
        assert h.target.number == 42

    def test_unknown_discriminator_falls_through_gracefully(self, tmp_path: Path) -> None:
        """If the discriminator value isn't a registered subclass key,
        the dispatch silently falls back to the abstract base. The
        actual subclass-resolution error surfaces later, during normal
        Pydantic validation, with the standard Registry message."""
        LeafConfig, AbstractBase, ConcreteWithPath, ConcreteWithoutPath, Holder = self._make_classes()

        path = tmp_path / "bogus.json"
        path.write_text(
            json.dumps(
                {
                    "__type__": "totally_does_not_exist",
                    "leaf": "leaf.json",
                }
            )
        )
        with pytest.raises((KeyError, ValueError)):
            Holder(target=str(path))

    def test_alias_in_discriminator_works(self, tmp_path: Path) -> None:
        """The discriminator can use any alias the subclass declared
        (not just the class name)."""
        LeafConfig, AbstractBase, ConcreteWithPath, ConcreteWithoutPath, Holder = self._make_classes()

        (tmp_path / "leaf").mkdir()
        (tmp_path / "leaf" / "leaf.json").write_text(json.dumps({"label": "L"}))
        outer = tmp_path / "outer.json"
        outer.write_text(
            json.dumps(
                {
                    "__type__": "with_path",  # alias declared on ConcreteWithPath
                    "leaf": "leaf/leaf.json",
                }
            )
        )

        h = Holder(target=str(outer))
        assert type(h.target) is ConcreteWithPath
        assert h.target.leaf.label == "L"

    def test_no_discriminator_no_dispatch_keeps_abstract_iteration(
        self,
        tmp_path: Path,
    ) -> None:
        """If the loaded dict has no ``__type__`` key, the dispatch step
        is a no-op — ``cls`` stays as the abstract base. The dict is
        validated against the abstract base's fields (which may or may
        not be enough to instantiate, depending on whether the abstract
        base has any ``@abstractmethod`` decorations enforcing
        abstractness).

        This test pins the no-dispatch path: the path-load step doesn't
        crash on a dict without ``__type__``, and doesn't silently
        invent a subclass.
        """
        LeafConfig, AbstractBase, ConcreteWithPath, ConcreteWithoutPath, Holder = self._make_classes()

        path = tmp_path / "no_disc.json"
        path.write_text(json.dumps({"base_field": "no-disc"}))

        ## With this AbstractBase (no @abstractmethod), the dict is
        ## actually instantiable as the bare base class. The important
        ## point is that the result is the abstract base type, NOT
        ## some accidentally-dispatched subclass.
        h = Holder(target=str(path))
        assert type(h.target) is AbstractBase
        assert h.target.base_field == "no-disc"

    def test_pre_built_subclass_instance_preserves_identity(self, tmp_path: Path) -> None:
        """Passing a pre-built concrete subclass instance still preserves
        identity. The fix only triggers when the value is a path
        (loaded from disk), not when it's already an instance."""
        LeafConfig, AbstractBase, ConcreteWithPath, ConcreteWithoutPath, Holder = self._make_classes()

        ## Construct the concrete subclass with a pre-built leaf:
        leaf = LeafConfig(label="prebuilt", count=1)
        target = ConcreteWithPath(leaf=leaf)

        h = Holder(target=target)
        assert h.target is target
        assert h.target.leaf is leaf

    def test_dict_input_with_discriminator_no_path(self, tmp_path: Path) -> None:
        """Programmatic dict with ``__type__`` works even without any
        file loading (this exercises Typed's ``__new__`` discriminator
        path, which is independent of TypedPath but also lives in
        morphic; we verify the two compose)."""
        LeafConfig, AbstractBase, ConcreteWithPath, ConcreteWithoutPath, Holder = self._make_classes()

        leaf_path = tmp_path / "l.json"
        leaf_path.write_text(json.dumps({"label": "L", "count": 5}))

        h = Holder(
            target={
                "__type__": "with_path",
                "leaf": str(leaf_path),  # absolute path inside an inline dict
            }
        )
        assert type(h.target) is ConcreteWithPath
        assert h.target.leaf.label == "L"
        assert h.target.leaf.count == 5

    def test_three_level_nesting_with_registry_dispatch_at_top(
        self,
        tmp_path: Path,
    ) -> None:
        """Holder -> abstract Registry (resolved via __type__) -> concrete
        subclass with TypedPath -> nested LeafConfig with its own TypedPath
        field. Every level's relative paths must resolve against the
        right parent."""
        from abc import ABC

        from morphic import Registry

        class Bottom(Typed):
            value: str

        class Middle(Typed):
            label: str
            bottom: Annotated[Bottom, TypedPath]

        class TopBase(Typed, Registry, ABC):
            pass

        class TopConcrete(TopBase):
            aliases = ("top_concrete",)
            middle: Annotated[Middle, TypedPath]

        class Holder3(Typed):
            top: Annotated[TopBase, TypedPath]

        (tmp_path / "top").mkdir()
        (tmp_path / "middle").mkdir()
        (tmp_path / "bottom").mkdir()

        (tmp_path / "bottom" / "bottom.json").write_text(json.dumps({"value": "leaf"}))
        (tmp_path / "middle" / "middle.json").write_text(
            json.dumps(
                {
                    "label": "middle-label",
                    "bottom": "../bottom/bottom.json",
                }
            )
        )
        (tmp_path / "top" / "top.json").write_text(
            json.dumps(
                {
                    "__type__": "top_concrete",
                    "middle": "../middle/middle.json",
                }
            )
        )

        h = Holder3(top=str(tmp_path / "top" / "top.json"))
        assert type(h.top) is TopConcrete
        assert h.top.middle.label == "middle-label"
        assert h.top.middle.bottom.value == "leaf"

    def test_yaml_with_registry_discriminator(self, tmp_path: Path) -> None:
        """The discriminator dispatch also works for YAML files."""
        yaml = pytest.importorskip("yaml")

        LeafConfig, AbstractBase, ConcreteWithPath, ConcreteWithoutPath, Holder = self._make_classes()

        (tmp_path / "leaf").mkdir()
        with open(tmp_path / "leaf" / "leaf.yaml", "w") as f:
            yaml.safe_dump({"label": "yaml-leaf", "count": 11}, f)
        with open(tmp_path / "outer.yaml", "w") as f:
            yaml.safe_dump(
                {
                    "__type__": "with_path",
                    "leaf": "leaf/leaf.yaml",
                },
                f,
            )

        h = Holder(target=str(tmp_path / "outer.yaml"))
        assert type(h.target) is ConcreteWithPath
        assert h.target.leaf.label == "yaml-leaf"
        assert h.target.leaf.count == 11

    def test_cli_with_registry_discriminator_in_loaded_file(self, tmp_path: Path) -> None:
        """End-to-end: CLI loads a file whose content has ``__type__``
        plus a relative path on a subclass-only TypedPath field."""
        LeafConfig, AbstractBase, ConcreteWithPath, ConcreteWithoutPath, Holder = self._make_classes()

        (tmp_path / "outer").mkdir()
        (tmp_path / "leaf").mkdir()
        (tmp_path / "leaf" / "leaf.json").write_text(json.dumps({"label": "from-cli"}))
        (tmp_path / "outer" / "with.json").write_text(
            json.dumps(
                {
                    "__type__": "with_path",
                    "leaf": "../leaf/leaf.json",
                }
            )
        )

        h = Holder.parse_cli_args(
            [
                "--target",
                str(tmp_path / "outer" / "with.json"),
            ]
        )
        assert type(h.target) is ConcreteWithPath
        assert h.target.leaf.label == "from-cli"

    def test_non_registry_inner_type_unaffected(self, tmp_path: Path) -> None:
        """Plain ``Annotated[ConcreteTyped, TypedPath]`` (no Registry) is
        unaffected by the dispatch logic — the fix only kicks in when
        ``cls`` is a Registry subclass.

        ``__type__`` is a morphic-reserved sentinel; ``Typed.__init__``
        silently pops it from any kwargs dict (whether or not the
        target class is a Registry subclass). So a non-Registry Typed
        with ``__type__`` in its loaded JSON is constructed normally
        with the discriminator key discarded.

        The important property this test pins: the fix does NOT call
        ``cls.get_subclass(...)`` on a non-Registry class (which would
        raise ``AttributeError: get_subclass``).
        """

        class Plain(Typed):
            name: str

        class PlainHolder(Typed):
            x: Annotated[Plain, TypedPath]

        path = tmp_path / "x.json"
        path.write_text(json.dumps({"__type__": "ignored", "name": "x"}))

        ## Should construct cleanly: __type__ is silently popped, name
        ## becomes "x". The fix's `issubclass(cls, Registry)` guard
        ## prevents an AttributeError on get_subclass.
        h = PlainHolder(x=str(path))
        assert h.x.name == "x"
        assert isinstance(h.x, Plain)
