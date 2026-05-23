# Typed CLI & Settings

Every `Typed` class in morphic is also a [`pydantic_settings.BaseSettings`](https://docs.pydantic.dev/latest/concepts/pydantic_settings/), so you can build CLI tools and twelve-factor configuration loaders directly on top of any data model — no separate "Settings" class, no wrapper around argparse, no hand-rolled JSON-merging logic.

This guide covers everything about the CLI / environment / dotenv / secret-file flow on `Typed`: how it works, what to put in your `script.py`, the four common usage patterns (with full working examples), edge cases and gotchas, the priority rules between sources, the source-isolation defaults, and the lifecycle invariants that guarantee `post_initialize` runs exactly once per instance even with nested CLI overrides.

If you have not read [Typed](typed.md) yet, start there for the basics of validation, immutability, lifecycle hooks, and `PrivateAttr`. This guide assumes you already know how to write a `Typed` model.

## Why every Typed is a BaseSettings

`pydantic_settings.BaseSettings` is just a `pydantic.BaseModel` with extra `__init__` machinery that loads field values from external sources (CLI argv, environment variables, dotenv files, secret-file directories) before handing the merged dict to standard Pydantic validation. When you construct a `Typed` instance with plain Python kwargs, the BaseSettings machinery is a no-op — your kwargs flow straight through to validation. When you opt in by passing `_cli_parse_args=...` (or `_env_file=...`), the corresponding source kicks in.

This means a single `Typed` model is both your data schema AND your CLI / config-loading entrypoint. You don't write `class App(Typed): ...` and then `class AppCLI(BaseSettings): ...`. There is one class that does both.

```python
from morphic import Typed

class App(Typed):
    name: str = "default"
    seed: int = 42

# In-process construction with kwargs (BaseSettings is a no-op):
app = App(name="alice", seed=7)

# CLI construction reads sys.argv[1:]:
app = App(_cli_parse_args=True)
# or with explicit argv:
app = App(_cli_parse_args=["--name", "alice", "--seed", "7"])
```

## Quick reference: what works on the CLI

| Form | Example | Notes |
|---|---|---|
| Top-level scalar | `--seed 99` | Strings, ints, floats, AutoEnums all coerce automatically |
| Top-level scalar (equals form) | `--seed=99` | Equivalent to space-separated form |
| Implicit boolean true | `--enabled` | Sets a `bool` field to `True` |
| Implicit boolean false | `--no-enabled` | Sets a `bool` field to `False` |
| Field with underscore (kebab) | `--log-level debug` | Underscores in field names become hyphens on the CLI |
| Inline JSON for nested model | `--infra '{"mode":"ray"}'` | Replaces the entire nested model |
| Inline JSON for list | `--tags '["a","b"]'` | List values get coerced element-wise |
| Inline JSON for dict | `--mapping '{"a":1}'` | Dict values get coerced |
| Deep override on a leaf | `--infra.ray-init.address X` | Patches one leaf, leaves siblings untouched |
| Inline JSON + deep override | `--infra '{...}' --infra.x.y X` | JSON sets baseline, deep override patches on top |
| Repeated flag | `--name a --name b` | Last one wins |

## Quick reference: what does NOT work by default

| Pattern | Why it doesn't work |
|---|---|
| Reading env vars (e.g. `$USER` for a `user:` field) | Disabled by default; opt in via `settings_customise_sources` |
| `--config path/to/cfg.json` | No native flag; build a small argparse wrapper (see [Pattern: JSON-File Config](#pattern-json-file-config-with-cli-overrides)) |
| `--enabled true` | Boolean fields use implicit `--flag` / `--no-flag` (configurable) |
| `--log_level debug` (snake form) | Kebab-case is the CLI form by default (configurable) |
| Inline JSON for the WHOLE root model | No native flag; the JSON would be passed to a single root-typed field, not the whole tree |

The "why does this not work" answers all have escape hatches; see the corresponding sections below.

## The four usage patterns

These are the four patterns we recommend, ordered from simplest to most powerful. Pick the one that fits your need; you can always migrate from a simpler pattern to a more complex one later.

### Pattern: Pure native CLI

The simplest pattern. One line of script.py, every Typed field is a CLI flag.

**`script.py`:**
```python
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

if __name__ == "__main__":
    app = App(_cli_parse_args=True)
    print(f"Running with seed={app.seed}, mode={app.infra.mode}")
```

**Invocations that all work:**
```bash
# Top-level scalar:
python script.py --seed 99

# Inline JSON for a single nested model:
python script.py --infra '{"mode":"ray","ray_init":{"address":"ray://x:1"}}'

# Deep override on a leaf:
python script.py --infra.ray-init.address ray://1.2.3.4:10001

# Inline JSON sets baseline, deep override patches one leaf:
python script.py \
    --infra '{"mode":"ray","ray_init":{"address":"ray://orig:1"}}' \
    --infra.ray-init.address ray://override:1

# All deep flags, no JSON anywhere:
python script.py \
    --infra.mode ray \
    --infra.ray-init.address ray://x:1 \
    --infra.ray-init.num-cpus 32 \
    --seed 7

# See auto-generated --help text:
python script.py --help
```

**When to use:** quick scripts, internal tools, anything where every parameter has a sensible default and runtime overrides come from argv.

**When NOT to use:** if you need a config file as the source of truth (use [JSON-File Config](#pattern-json-file-config-with-cli-overrides)), or if you need env vars (use [Environment Variables](#pattern-environment-variables-and-dotenv-files)).

### Pattern: JSON-File config with CLI overrides

The trojanshot use case: a JSON config file is the source of truth, with CLI flags layering deep overrides on top.

Pydantic-settings does not have a native `--config path/to/cfg.json` flag, so we add a tiny argparse wrapper (10 lines of boilerplate) that pops `--config` and `--config-json` before pydantic-settings sees argv, and folds the loaded JSON into the `_cli_parse_args` list.

**`script.py`:**
```python
import argparse
import json
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

def parse_app() -> App:
    """Load App from --config path.json and/or --config-json '{...}', plus
    any --field.deep.path VALUE overrides on top.
    """
    wrapper = argparse.ArgumentParser(add_help=False)
    wrapper.add_argument("--config", type=str, default=None,
                        help="Path to JSON config file (root of App)")
    wrapper.add_argument("--config-json", type=str, default=None,
                        help="Inline JSON for root of App")
    known, remaining = wrapper.parse_known_args()

    baseline = {}
    if known.config is not None:
        with open(known.config) as f:
            baseline = json.load(f)
    elif known.config_json is not None:
        baseline = json.loads(known.config_json)

    # Convert baseline dict into argv form. Each top-level key becomes a
    # `--<key> <json-value>` pair, then any remaining `--field.deep.path
    # VALUE` flags are appended (and win, because pydantic-settings'
    # deep_update is later-takes-precedence).
    baseline_argv = []
    for key, value in baseline.items():
        baseline_argv.append(f"--{key.replace('_', '-')}")
        baseline_argv.append(json.dumps(value) if not isinstance(value, str) else value)

    return App(_cli_parse_args=baseline_argv + remaining)

if __name__ == "__main__":
    app = parse_app()
    print(app)
```

**Invocations:**
```bash
# Just a config file:
python script.py --config configs/prod.json

# Just inline root JSON:
python script.py --config-json '{"seed":7,"infra":{"mode":"ray"}}'

# Config file + a top-level scalar override:
python script.py --config configs/prod.json --seed 999

# Config file + a DEEP override (the trojanshot use case):
python script.py \
    --config configs/prod.json \
    --infra.ray-init.address ray://override:10001

# Config file + multiple overrides at different depths:
python script.py \
    --config configs/prod.json \
    --infra.mode ray \
    --infra.ray-init.address ray://x:1 \
    --infra.ray-init.num-cpus 32 \
    --seed 42
```

**Where `configs/prod.json` looks like:**
```json
{
    "infra": {
        "mode": "ray",
        "ray_init": {
            "address": "ray://default:10001",
            "num_cpus": 4
        }
    },
    "seed": 100
}
```

**Priority order:** model defaults < JSON file < CLI overrides. The CLI flags layer on top because we put `baseline_argv` first and `remaining` last in `_cli_parse_args=baseline_argv + remaining`, and pydantic-settings' `deep_update` makes later argv beat earlier argv on the same path.

**Verified end-to-end:** `tests/test_typed_basesettings.py::TestRealCLIScriptWithJSONConfig` (10 tests).

### Pattern: Environment variables and dotenv files

The 12-factor app pattern: settings come from env vars (and optionally a `.env` file), with CLI flags overriding env values when both are present.

By default, `Typed` does **NOT** read environment variables. This is a critical safety default — without it, a field named `user` would silently pick up `$USER` from the shell, fields named `path`, `home`, `shell` would clash with their identically-named env vars, and a confusing `SettingsError` about "JSON-decoding 'adivekar'" would result.

To opt in on a specific subclass, override `settings_customise_sources`:

**`script.py`:**
```python
from morphic import Typed
from pydantic_settings import SettingsConfigDict

class App(Typed):
    model_config = SettingsConfigDict(
        env_prefix="MYAPP_",            # only env vars starting with MYAPP_
        env_nested_delimiter="__",      # MYAPP_INFRA__MODE → infra.mode
        env_file=".env",                # also load from .env in CWD
    )

    seed: int = 42
    name: str = "default"
    api_key: str = ""

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings,
    ):
        # Re-enable env vars (and dotenv) — Typed disables them by default.
        # Order = priority order. CLI > init > env > dotenv > secrets > defaults
        # (CLI is added on top of whatever this returns when _cli_parse_args is set).
        return init_settings, env_settings, dotenv_settings, file_secret_settings

if __name__ == "__main__":
    app = App(_cli_parse_args=True)
    print(app)
```

**Invocations:**
```bash
# Pure env vars:
MYAPP_SEED=99 MYAPP_NAME=production python script.py

# .env file (a file named .env in CWD):
echo 'MYAPP_API_KEY=secret-xyz' > .env
python script.py

# Env + CLI override (CLI wins):
MYAPP_SEED=99 python script.py --name override
# → seed=99 from env, name="override" from CLI

# Nested env vars (with env_nested_delimiter="__"):
MYAPP_INFRA__MODE=ray python script.py
# → infra.mode = "ray" (if App has an infra: Infra field)
```

**Important:** the `env_prefix` is essential. Without a prefix, `MYAPP_SEED=99` becomes just `SEED=99`, which can collide with shell or system env vars (and fields like `home`, `path`, `user` would pick up their shell-var siblings). Always set a prefix in the config dict.

### Pattern: Registry dispatch with per-class CLI

When you have a [Registry](registry.md) hierarchy and want to choose the concrete subclass at runtime, then build it from CLI flags.

**`script.py`:**
```python
import sys
from abc import ABC
from morphic import Registry, Typed

class Backend(Typed, Registry, ABC):
    name: str

class HttpBackend(Backend):
    aliases = ("http",)
    url: str = "http://localhost"
    timeout: int = 30

class GrpcBackend(Backend):
    aliases = ("grpc",)
    target: str = "localhost:50051"
    use_tls: bool = True

if __name__ == "__main__":
    # Resolve concrete class from first positional arg:
    backend_kind = sys.argv[1]
    remaining = sys.argv[2:]

    backend_cls = Backend.get_subclass(backend_kind)   # class lookup, no construction yet
    backend = backend_cls(_cli_parse_args=remaining)   # construct via CLI on the concrete class
    print(f"Built {type(backend).__name__}: {backend}")
```

**Invocations:**
```bash
python script.py http --name primary --url http://api.example.com --timeout 60
python script.py grpc --name primary --target prod.example.com:50051 --no-use-tls
```

**Why `Backend.get_subclass(...)` not `Backend.of(...)`:** `Backend.of("http", **kwargs)` returns an *instance* of HttpBackend, but you don't have the kwargs yet — they come from argv. `Backend.get_subclass("http")` returns the *class* (no instance), and you then call its `__init__` with `_cli_parse_args=remaining`. See the [Registry guide](registry.md) for more on the difference.

**Verified end-to-end:** `tests/test_typed_basesettings.py::TestTypedRegistryBaseSettings` (5 tests).


## CLI flag syntax rules

These rules apply to all four patterns above:

### 1. Field names are kebab-cased on the CLI

A field like `num_cpus: int` is exposed as `--num-cpus` on the command line:

```python
class App(Typed):
    log_level: str = "info"

# CLI: --log-level debug   ✓ works
# CLI: --log_level debug   ✗ rejected (with the default cli_kebab_case=True)
```

If you need snake-case CLI flags (or both forms), override `cli_kebab_case`:

```python
from pydantic_settings import SettingsConfigDict

class App(Typed):
    model_config = SettingsConfigDict(cli_kebab_case=False)

    log_level: str = "info"

# CLI: --log_level debug   ✓ works
# CLI: --log-level debug   ✗ rejected (kebab disabled)
```

### 2. Booleans use implicit flag pairs by default

A field like `enabled: bool = False` exposes `--enabled` (sets True) and `--no-enabled` (sets False). The explicit-value form (`--enabled true`) is rejected by default:

```python
class App(Typed):
    enabled: bool = False
    verbose: bool = True

# CLI: --enabled                  ✓ enabled=True
# CLI: --no-enabled               ✓ enabled=False
# CLI: --no-verbose               ✓ verbose=False
# CLI: --enabled true             ✗ rejected
```

If you prefer the `--enabled true|false` form, override `cli_implicit_flags`:

```python
class App(Typed):
    model_config = SettingsConfigDict(cli_implicit_flags=False)

    enabled: bool = False

# CLI: --enabled true             ✓ enabled=True
# CLI: --enabled false            ✓ enabled=False
# CLI: --enabled                  ✗ rejected (no value)
```

### 3. Equals-form and space-form are equivalent

Both `--flag value` and `--flag=value` work. The equals form is useful when the value contains spaces or characters the shell would otherwise interpret:

```bash
python script.py --note "hello world"        # space-form, requires shell quoting
python script.py --note="hello world"        # equals-form, requires shell quoting
python script.py --tags '["a","b"]'          # JSON via space-form
python script.py --tags='["a","b"]'          # JSON via equals-form
```

### 4. Nested fields use dot notation with kebab-case at every level

`infra.ray_init.address` becomes `--infra.ray-init.address` on the CLI:

```python
class RayInit(Typed):
    address: str = "auto"

class Infra(Typed):
    ray_init: RayInit = RayInit()

class App(Typed):
    infra: Infra = Infra()

# CLI: --infra.ray-init.address ray://x:1
```

The dots are part of the flag name (argparse handles them). Each segment between dots is independently kebab-cased.

### 5. Inline JSON for nested fields replaces the entire model

`--infra '{"mode":"ray"}'` REPLACES the default `Infra` model with `Infra(mode="ray")`. Every field of `Infra` not in the JSON falls back to its model-default:

```python
class Infra(Typed):
    mode: str = "thread"
    ray_init: RayInit = RayInit(address="auto", num_cpus=4)

# CLI: --infra '{"mode":"ray"}'
# Result: Infra(mode="ray", ray_init=RayInit(address="auto", num_cpus=4))
#         (ray_init falls back to its own default because the JSON didn't mention it)
```

### 6. Deep overrides win when combined with inline JSON

When you use both `--infra '{...}'` and `--infra.ray-init.address X`, the inline JSON sets the baseline and the deep flag patches one leaf:

```bash
# Inline JSON sets ray_init.address to "ray://orig:1" and num_cpus to 8.
# Deep override patches ray_init.address to "ray://override:1".
# num_cpus stays 8 (not overridden).
python script.py \
    --infra '{"mode":"ray","ray_init":{"address":"ray://orig:1","num_cpus":8}}' \
    --infra.ray-init.address ray://override:1
```

This works because pydantic-settings emits nested dicts from each CLI flag and merges them via `deep_update` (later wins on the same leaf, siblings preserved).

### 7. Repeated flags: last wins

```bash
python script.py --name first --name last
# → name="last"
```

### 8. Lists and dicts via inline JSON

```python
class App(Typed):
    tags: List[str] = []
    ports: List[int] = []
    settings: Dict[str, str] = {}

# CLI: --tags '["a","b","c"]'                    → ["a", "b", "c"]
# CLI: --ports '["80","443","8080"]'             → [80, 443, 8080]  (strings coerced)
# CLI: --settings '{"key1":"v1","key2":"v2"}'    → {"key1": "v1", "key2": "v2"}
```

Strings inside the JSON are coerced to the element type during validation, so `["80","443"]` becomes `[80, 443]` for a `List[int]` field.

## Source priority order

When multiple sources provide the same field, priority order determines who wins. The default Typed configuration uses CLI > init > env > dotenv > secrets > model defaults, but env / dotenv / secrets are disabled out of the box and have to be explicitly enabled.

The exact order is determined by the tuple returned from `settings_customise_sources`. Sources earlier in the tuple win:

```python
@classmethod
def settings_customise_sources(
    cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings,
):
    # Order = priority. Earlier wins.
    return init_settings, env_settings, dotenv_settings, file_secret_settings
    # CLI source (when _cli_parse_args is set) is added BEFORE this tuple,
    # so it wins over all of the above.
```

`init_settings` represents the kwargs you passed to the constructor (`App(seed=42, ...)`). The CLI source is added by pydantic-settings *on top* of whatever this method returns when `_cli_parse_args` is set, so CLI is always the highest priority when active.

The default Typed implementation returns `(init_settings,)` only — env / dotenv / secrets disabled. Override this on a specific subclass to opt in.

## Source isolation: why env vars are disabled by default

The single most important safety default in `Typed`'s BaseSettings integration is that environment variables are NOT read by default.

### What goes wrong without source isolation

`pydantic_settings.BaseSettings` defaults to reading every env variable as a candidate source. With `case_sensitive=False` (the default), an env var named `USER` matches a field named `user`. For the trojanshot example earlier, this would mean:

```python
class SimpleTyped(Typed):
    name: str
    age: int = 25

class NestedTyped(Typed):
    user: SimpleTyped   # field name "user"

# WITHOUT source isolation:
m = NestedTyped(user={"name": "alice"})
# → SettingsError: error parsing value for field "user" from source "EnvSettingsSource"
#   (because $USER='adivekar' was matched against the user field, then JSON-decoded as 'adivekar')
```

Every Typed model with a field named `user`, `path`, `home`, `shell`, `lang`, etc. would silently try to interpret the matching shell env variable as that field's value, almost always crashing with a confusing error.

### How Typed prevents this

`Typed` overrides `settings_customise_sources` to return only `init_settings`, disabling env / dotenv / secret-file sources by default. The field `user` does NOT pick up `$USER`:

```python
import os
os.environ["USER"] = "test_user"

class NestedTyped(Typed):
    user: SimpleTyped

m = NestedTyped(user={"name": "alice"})
# ✓ works; user.name == "alice", $USER ignored
```

### Opt-in pattern for env vars

When you DO want env vars on a specific subclass, override `settings_customise_sources` and ALWAYS set `env_prefix`:

```python
class AppSettings(Typed):
    model_config = SettingsConfigDict(
        env_prefix="MYAPP_",  # ← essential; never leave this empty
    )

    name: str = "default"

    @classmethod
    def settings_customise_sources(
        cls, settings_cls, init_settings, env_settings, dotenv_settings, file_secret_settings,
    ):
        return init_settings, env_settings, dotenv_settings, file_secret_settings
```

Now `MYAPP_NAME=production` is loaded into `name`, but bare `$NAME` or `$USER` are not.

### CLI parsing is independent of env loading

CLI parsing is enabled by passing `_cli_parse_args=...` to the constructor, regardless of what `settings_customise_sources` returns. You can have CLI on every Typed (the default) without ever opting into env vars.

## Identity preservation across CLI / nested-Typed boundaries

A non-obvious property of `Typed` that matters in practice: when you pass a pre-built `Typed` instance as a field of an outer `Typed`, the inner instance is REUSED, not cloned. Mutable state held in `PrivateAttr`s is preserved.

```python
from morphic import Typed
from pydantic import PrivateAttr

class HeavyResource(Typed):
    hf_model_id: str
    _spawned: bool = PrivateAttr(default=False)

    def post_initialize(self) -> None:
        # Simulate spawning a worker / loading a model.
        object.__setattr__(self, "_spawned", True)

class Container(Typed):
    target: HeavyResource

# `post_initialize` runs once when HeavyResource is built:
hr = HeavyResource(hf_model_id="qwen-3-4b")
assert hr._spawned is True

# Passing it to Container does NOT clone, does NOT re-spawn:
c = Container(target=hr)
assert c.target is hr             # same Python object
assert c.target._spawned is True  # PrivateAttr preserved
```

This is governed by the `revalidate_instances="never"` setting in `Typed.model_config`. Without it, Pydantic would re-validate the inner instance during outer construction and could clone it, defeating any mutable state held in `PrivateAttr`s.

### What this means for CLI flows

When you pre-build instances and pass them programmatically, identity is preserved:

```python
heavy = HeavyResource(hf_model_id="qwen-3-4b")
container = Container(target=heavy)
assert container.target is heavy   # ✓
```

When the input comes from CLI argv (or any dict-shaped source), a NEW instance is constructed (because there is no pre-built instance to reuse — the CLI source produces a dict, which has to be validated into a new `HeavyResource`):

```python
container = Container(_cli_parse_args=["--target", '{"hf_model_id":"qwen"}'])
# container.target is a brand-new HeavyResource constructed from the dict.
# post_initialize runs once on this new instance.
```

Both flows produce the same final `Container`, but the question of whether `post_initialize` runs once vs. spawns a new resource matters when `post_initialize` is expensive.

## The double-fire bug and how Typed handles it

This is the most subtle and most important property to understand if your `post_initialize` does expensive work (spawning workers, loading models, opening cloud connections).

### What the bug is

Pydantic 2 has a known issue ([#12876](https://github.com/pydantic/pydantic/issues/12876)): `model_validator(mode="after")` re-fires on a nested model instance during the outer container's validation, even when `revalidate_instances="never"` preserves identity.

In plain English: when you have `Container(target=heavy_resource)`, Pydantic runs every `mode="after"` validator on `heavy_resource` AGAIN as part of validating `Container`. The instance's identity is preserved (same `id()`), but the validator fires twice on the same instance.

`morphic.Typed`'s lifecycle hooks (`post_initialize`, `post_validate`) are invoked from a `@model_validator(mode="after")`, so without intervention, `post_initialize` would fire twice for every nested Typed.

### How Typed handles it

`Typed` adds a per-instance `_typed_post_initialized: bool` `PrivateAttr` marker. The model_validator checks this marker and short-circuits the second fire:

```python
class Typed(BaseSettings, ABC):
    _typed_post_initialized: bool = PrivateAttr(default=False)

    @model_validator(mode="after")
    def _post_set_validate_inputs(self) -> T:
        if self._typed_post_initialized:
            return self                            # ← Re-fire? Skip silently.
        self.post_set_validate_inputs()            # User hooks: post_initialize, post_validate
        object.__setattr__(self, "_typed_post_initialized", True)
        return self
```

The marker:

- Defaults to `False` on every newly constructed instance.
- Flips to `True` immediately after the first time `post_initialize` / `post_validate` complete.
- Travels with the instance — when identity is preserved (the Typed default), the marker survives every outer construction the instance participates in.
- Resets on each new instance from `model_validate(model_dump())` or any other path that produces a brand-new instance.

### What this means for users

`post_initialize` runs **exactly once per instance**, regardless of how deeply that instance is nested in outer Typed/BaseSettings models, regardless of how many times Pydantic re-fires the underlying after-validator, regardless of which CLI override path is used.

You do NOT need per-class idempotency guards in `post_initialize` to handle the framework's re-fire behavior:

```python
# ❌ NOT NEEDED any more — the framework marker handles this.
class HeavyResource(Typed):
    _spawned: bool = PrivateAttr(default=False)

    def post_initialize(self) -> None:
        if self._spawned:                        # ← framework already short-circuits
            return
        object.__setattr__(self, "_spawned", True)
        spawn_expensive_worker()
```

```python
# ✓ This is enough — post_initialize is guaranteed to run exactly once.
class HeavyResource(Typed):
    def post_initialize(self) -> None:
        spawn_expensive_worker()
```

You may still want a per-class guard for OTHER reasons (e.g., if `post_initialize` is invoked manually elsewhere, or if you support `Model.model_validate(model.model_dump())` round-trips on heavy resources, since round-trips DO produce a new instance with a fresh marker, so they DO re-spawn). But the framework re-fire is no longer your problem.

### Verifying it works (the regression suite)

The double-fire neutralization is exhaustively tested in `tests/test_typed_cli_native_edge_cases.py::TestPostInitializeCalledExactlyOnce` (11 tests). Each test isolates a different construction path and asserts that a class-level `Counter` of `post_initialize` calls is exactly 1 per instance:

| Test scenario | What it verifies |
|---|---|
| Root construction from dict | Three nested Typeds → 3 instances → 3 `post_initialize` calls total |
| Pre-built leaf → mid → root chain | Each instance fires once when constructed; outer wrapping does NOT re-fire |
| Mixed pre-built and dict | Pre-built leaf preserved through dict-based outer construction |
| CLI parse with dict path | `_cli_parse_args` does not double-fire |
| CLI parse with deep override | Multiple-flag CLI does not double-fire |
| `model_validate(model.model_dump())` round-trip | Creates NEW instances; each gets its own one-time fire |
| Sibling instances of the same class | Independent markers, each fires once |
| Same instance in two fields | Shared instance fires only ONCE total |
| `List[Inner]` with mixed dict + pre-built | Each list element fires exactly once |
| `Dict[str, Inner]` with mixed dict + pre-built | Each dict value fires exactly once |
| Heavy-resource pattern, NO per-class guard | A guard that raises on second fire never raises |

Run the suite:

```bash
cd /Users/adivekar/workplace/morphic
python -m pytest tests/test_typed_cli_native_edge_cases.py::TestPostInitializeCalledExactlyOnce -v
```

## Error handling

### Validation errors propagate clearly

Pydantic validation errors from CLI input are wrapped in morphic's enhanced error message format, with field paths and offending values:

```python
class App(Typed):
    seed: int = 42

App(_cli_parse_args=["--seed", "not-a-number"])
# pydantic.ValidationError or SystemExit with:
#   error: argument --seed: invalid int value: 'not-a-number'
```

### Required fields without a value

A field with no default and no CLI value triggers a validation error at construction time:

```python
class App(Typed):
    mandatory: str   # no default

App(_cli_parse_args=[])
# ValidationError: 1 validation error for App
#   mandatory
#     Field required [type=missing, ...]
```

To make required-ness explicit at the CLI layer, set `cli_enforce_required=True` in `model_config`. This makes pydantic-settings error out via argparse (with the standard `error: the following arguments are required` message) before validation runs.

### Unknown flags

Unknown flags are rejected with an argparse error:

```bash
python script.py --does-not-exist value
# usage: script.py [-h] [--seed int] ...
# script.py: error: unrecognized arguments: --does-not-exist value
```

To ignore unknown flags instead, set `cli_ignore_unknown_args=True` in `model_config`.

### Missing values after a flag

```bash
python script.py --seed
# error: argument --seed: expected one argument
```

### File / JSON errors in the JSON-File pattern

In the [JSON-File config pattern](#pattern-json-file-config-with-cli-overrides), file errors surface as standard exceptions:

- Missing file → `FileNotFoundError` from `open(known.config)`.
- Corrupt JSON → `json.JSONDecodeError`.
- Type errors in the JSON content → `pydantic.ValidationError` (caught and wrapped in morphic's enhanced format).

Tests `test_config_file_invalid_path_fails`, `test_config_file_invalid_json_fails`, and `test_config_file_validation_error_propagates` in `test_typed_basesettings.py` verify each of these.

## Auto-generated `--help`

Every Typed model that uses `_cli_parse_args` gets an auto-generated help text from pydantic-settings:

```python
class App(Typed):
    """A demo app."""

    name: str = "default"
    """User-friendly application name."""

    seed: int = 42
    """Seed for the random number generator."""

if __name__ == "__main__":
    App(_cli_parse_args=True)
```

```bash
$ python script.py --help
usage: script.py [-h] [--name str] [--seed int]

options:
  -h, --help    show this help message and exit
  --name str    User-friendly application name. (default: default)
  --seed int    Seed for the random number generator. (default: 42)
```

Use `cli_use_class_docs_for_groups=True` in `model_config` to use a Typed's class docstring as the help-group description.

For boolean fields with `cli_implicit_flags=True` (the Typed default), the help text shows both forms:

```
  --enabled, --no-enabled  (default: False)
```

For nested Typed fields, every leaf is exposed individually:

```
  --infra str
  --infra.mode str
  --infra.ray-init.address str
  --infra.ray-init.num-cpus int
```

## Configuration reference

The Typed defaults relevant to the CLI / settings flow:

| Setting | Typed default | Effect |
|---|---|---|
| `cli_kebab_case` | `True` | Field names are exposed as kebab-case (`--num-cpus` not `--num_cpus`) |
| `cli_implicit_flags` | `True` | Boolean fields generate `--flag` / `--no-flag` pairs (no explicit `true` / `false`) |
| `cli_parse_args` | unset (None) | Argv NOT auto-read on every Typed construction; opt in via `_cli_parse_args=True` |
| `cli_enforce_required` | `False` | Missing required fields surface as Pydantic ValidationError, not argparse error |
| `cli_ignore_unknown_args` | `False` | Unknown CLI flags raise argparse error |
| `revalidate_instances` | `"never"` | Pre-built Typed instances passed as field values are reused, not cloned |
| `nested_model_default_partial_update` | unset | Per-field defaults preserved when CLI passes inline JSON; setting True breaks identity preservation |
| `extra` | `"forbid"` | Extra fields not in the model raise ValidationError |
| `frozen` | `True` | Instances are immutable after construction (PrivateAttrs are still mutable) |
| `validate_default` | `True` | Default values are validated when the class is defined |
| `arbitrary_types_allowed` | `True` | Custom types without Pydantic validators are allowed |

To override any of these on a specific subclass:

```python
from pydantic_settings import SettingsConfigDict

class App(Typed):
    model_config = SettingsConfigDict(
        # Override Typed defaults:
        cli_kebab_case=False,
        cli_implicit_flags=False,
        cli_enforce_required=True,
        # Add settings-specific config:
        env_prefix="MYAPP_",
        env_nested_delimiter="__",
        env_file=".env",
    )
    ...
```

## Troubleshooting

### "error parsing value for field X from source EnvSettingsSource"

Cause: env-var loading was enabled (via a `settings_customise_sources` override), and an env var with a colliding name is being interpreted as a complex field value, then JSON-decoded.

Fixes:

1. Always set an `env_prefix` on the model_config when enabling env vars.
2. Or remove the `env_settings` from the tuple returned by `settings_customise_sources` if you don't need env vars on this subclass.
3. Or rename the field to avoid the collision.

### "unrecognized arguments: --my-flag"

Cause: either the flag name is wrong (snake vs kebab mismatch — see [CLI flag syntax rule 1](#1-field-names-are-kebab-cased-on-the-cli)), or the field doesn't exist on the model.

Fixes:

1. Use kebab-case for fields with underscores (`--num-cpus`, not `--num_cpus`).
2. Run `python script.py --help` to see the auto-generated list of valid flags.
3. If you really want both forms, set `cli_kebab_case=False`.

### My `post_initialize` is firing twice / spawning two workers

Cause: this should NOT happen with `morphic.Typed`. The framework marker (`_typed_post_initialized`) prevents the #12876 re-fire automatically.

Investigate:

1. Are you running the latest morphic with `Typed(BaseSettings)`? Check `Typed.__mro__` should contain `BaseSettings`.
2. Are you constructing your heavy resource via `model_validate(model.model_dump())`? That DOES create a new instance with a fresh marker — round-trips legitimately re-spawn.
3. Are you holding TWO different instances of the same class? Each gets its own marker.
4. Are you sure it's `post_initialize` running twice and not your code calling it twice manually?

Run the regression suite to confirm the framework guarantee holds in your environment:

```bash
python -m pytest tests/test_typed_cli_native_edge_cases.py::TestPostInitializeCalledExactlyOnce -v
```

### My pre-built instance is being cloned (identity not preserved)

Cause: probably an explicit `revalidate_instances="always"` somewhere, or `nested_model_default_partial_update=True` on the outer model.

Fixes:

1. Don't override `revalidate_instances` away from `"never"`.
2. Don't enable `nested_model_default_partial_update=True` (it dumps init kwargs to dict via TypeAdapter, destroying identity). Deep CLI overrides work without it.

### CLI flags don't work for a nested model field

Cause: the nested field has no default value (just a type annotation). Pydantic-settings only generates sub-flags when the field has a model-instance default to merge into.

Fix: provide a default model instance:

```python
# ❌ No --infra.* sub-flags generated:
class App(Typed):
    infra: Infra   # no default

# ✓ Sub-flags generated:
class App(Typed):
    infra: Infra = Infra()
```

If the inner model has any required fields without defaults, you can't use `Infra()` as the default. In that case, either:

1. Pass `--infra '{"required":"value"}'` as inline JSON for the entire nested model.
2. Make the inner field defaults so `Infra()` works.
3. Use a `Union[str, Infra]` annotation with a path string default and write a path-loader (the trojanshot pattern, but consider switching to the [JSON-File config pattern](#pattern-json-file-config-with-cli-overrides) instead).

### "Extra inputs are not permitted" when passing inline JSON

Cause: passing the full root JSON to a single nested-field flag (e.g. `--infra '{"infra":{...},"seed":42}'`). The whole-root JSON has its OWN `infra` key, which doesn't match `Infra`'s field schema.

Fix: either

1. Split into per-field flags: `--infra '{...}' --seed 42`.
2. Use the [JSON-File config pattern](#pattern-json-file-config-with-cli-overrides) which loads root-level JSON properly.

## See also

- [Typed user guide](typed.md) — the foundational guide for `Typed`, validation, lifecycle hooks, frozen models, `PrivateAttr`.
- [Registry user guide](registry.md) — for hierarchical class factories, used in [Pattern: Registry dispatch with per-class CLI](#pattern-registry-dispatch-with-per-class-cli).
- [Typed + Registry integration](typed-registry-integration.md) — how `Typed.of()` and `Registry.of()` compose.
- [pydantic-settings documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/) — the underlying CLI / env / dotenv source machinery.
- Pydantic [issue #12876](https://github.com/pydantic/pydantic/issues/12876) — the after-validator re-fire bug that morphic neutralizes via the `_typed_post_initialized` marker.

## Test coverage

The CLI / settings flow on Typed is covered by two test files in the morphic repo:

- `tests/test_typed_basesettings.py` — 38 tests covering basic invariants, identity preservation, source isolation, in-process CLI parsing, real-subprocess CLI integration, JSON-file config integration, and Typed + Registry + BaseSettings integration.
- `tests/test_typed_cli_native_edge_cases.py` — 48 tests covering the #12876 double-fire regression suite (11), CLI type coercion (12), CLI argument-form edge cases (16), `PrivateAttr` survival (4), and multi-instance / shared-instance scenarios (5).

Run the full set:

```bash
cd /Users/adivekar/workplace/morphic
python -m pytest tests/test_typed_basesettings.py tests/test_typed_cli_native_edge_cases.py -v
```
