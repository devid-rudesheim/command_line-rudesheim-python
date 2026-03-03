# Rudesheim Command Line Toolkit

`rudesheim.command_line` is a lightweight CLI argument parser for Python.
Its primary goal is not "parse string options into values" but
"select objects that own behavior".

## Install

Install from this repository root:

```bash
pip install .
```

For development:

```bash
pip install -e .
```

After publishing to PyPI:

```bash
pip install command-line-rudesheim-python
```

## Why This Library Exists

Many CLI libraries return primitive values (`str`, `bool`, etc.), then your app writes branching logic:

- `if args.mode == "...": ...`
- `elif args.mode == "...": ...`
- callback routing tables spread across files

As features grow, this area becomes hard to maintain.

This library solves that by selecting `Option` objects (or classes) directly.
After parsing, you get a map like:

- `Category -> selected Option`

If each `Option` has its own behavior method, caller-side branching is no longer needed.
Branching is absorbed into object behavior (polymorphism).

## What Gets Cleaner

1. Command execution code stops depending on option strings.
2. Adding a new option usually means adding one class, not editing large `if/elif` blocks.
3. Default behavior is explicit per category via `default()`.
4. Conflict rules (one option per category) are enforced by parser design.

## Argument Examples (Input Shape)

Examples of command-line inputs this library can parse:

```bash
# no-value option
myapp --apply

# short key
myapp -a

# value option (short form)
myapp -d 3

# value option (long form)
myapp --depth=3

# option + remaining args
myapp --apply target_a target_b
```

## Before / After

### Before (value-based branching)

```python
mode = args.mode

if mode == "dry-run":
    print("dry run")
elif mode == "apply":
    run_apply()
elif mode == "delete":
    run_delete()
else:
    raise ValueError("unknown mode")
```

### After (object selection + behavior dispatch)

```python
import rudesheim.command_line as cl

class DryRun(cl.Option):
    # FREE: user-defined behavior
    @classmethod
    def execute(cls):
        print("dry run")

class Apply(cl.Option):
    # FREE: user-defined behavior
    @classmethod
    def execute(cls):
        run_apply()

class Delete(cl.Option):
    # FREE: user-defined behavior
    @classmethod
    def execute(cls):
        run_delete()

class Mode(cl.OptionCategory):
    # REQUIRED (practical): declare selectable options in this category
    @classmethod
    def options_defines(cls):
        return [
            DryRun.tie(("d", "dry-run"), "execute without changes"),
            Apply.tie(("a", "apply"), "apply changes"),
            Delete.tie(("x", "delete"), "delete resource"),
        ]

    # REQUIRED (practical): declare fallback when no option is given
    @classmethod
    def default(cls):
        return DryRun

categories, arguments = cl.Parser([Mode]).parse(["--apply"])
# FREE: caller sends behavior message to selected object
categories[Mode].execute()
```

No `if/elif` by option value is needed in the caller.
The selected object can be called once or many times.

## Real Workflow Example (Repeated Option-Specific Calls)

The selected option is usually kept in a variable and used throughout shared flow:

```python
import rudesheim.command_line as cl

class DryRun(cl.Option):
    @classmethod
    def before_batch(cls, items):
        print(f"[dry-run] check {len(items)} items")

    @classmethod
    def process_item(cls, item):
        print(f"[dry-run] skip {item}")

    @classmethod
    def after_batch(cls):
        print("[dry-run] done")

class Apply(cl.Option):
    @classmethod
    def before_batch(cls, items):
        open_transaction()

    @classmethod
    def process_item(cls, item):
        apply_item(item)

    @classmethod
    def after_batch(cls):
        commit_transaction()

class Mode(cl.OptionCategory):
    @classmethod
    def options_defines(cls):
        return [
            DryRun.tie(("d", "dry-run"), "do not mutate"),
            Apply.tie(("a", "apply"), "apply changes"),
        ]

    @classmethod
    def default(cls):
        return DryRun

class Quiet(cl.Option):
    @classmethod
    def on_start(cls, items):
        pass

    @classmethod
    def on_item(cls, item):
        pass

    @classmethod
    def on_finish(cls):
        pass

class Verbose(cl.Option):
    @classmethod
    def on_start(cls, items):
        print(f"[verbose] start {len(items)} items")

    @classmethod
    def on_item(cls, item):
        print(f"[verbose] item {item}")

    @classmethod
    def on_finish(cls):
        print("[verbose] finish")

class ReportStyle(cl.OptionCategory):
    @classmethod
    def options_defines(cls):
        return [
            Quiet.tie(("q", "quiet"), "minimal output"),
            Verbose.tie(("V", "verbose"), "verbose output"),
        ]

    @classmethod
    def default(cls):
        return Quiet

categories, arguments = cl.Parser([Mode, ReportStyle]).parse(["--apply", "--verbose", "A", "B"])
mode = categories[Mode]
report = categories[ReportStyle]

# shared flow (common processing)
items = arguments
report.on_start(items)        # second category behavior
mode.before_batch(items)      # option-specific behavior
for item in items:            # common loop
    report.on_item(item)      # second category behavior
    mode.process_item(item)   # option-specific behavior
mode.after_batch()            # option-specific behavior
report.on_finish()            # second category behavior
```

In this style, common workflow stays in one place, and option-specific branching is absorbed by methods on selected option.

## Value Option Example (`-d 3` / `--depth=3`)

When an option receives a value, implement `value_amount()` and `with_value(strings)`.

```python
import rudesheim.command_line as cl

class Depth(cl.Option):
    def __init__(self, text):
        self.text = text

    # REQUIRED for value option
    @classmethod
    def value_amount(cls):
        return 1

    # REQUIRED for value option
    @classmethod
    def with_value(cls, strings):
        return cls(strings)

    # FREE: domain behavior
    def as_int(self):
        return int(self.text)

class DepthCategory(cl.OptionCategory):
    @classmethod
    def options_defines(cls):
        return [Depth.tie(("d", "depth"), "depth value")]

    @classmethod
    def default(cls):
        return Depth("1")

categories, arguments = cl.Parser([DepthCategory]).parse(["--depth=3", "target"])
depth = categories[DepthCategory].as_int()  # 3
remaining = arguments  # ["target"]
```

## Quick Start

```python
import rudesheim.command_line as cl

class Disabled(cl.Option):
    # FREE: user-defined behavior
    @classmethod
    def example(cls):
        print("Disable")

class Enabled(cl.Option):
    # FREE: user-defined behavior
    @classmethod
    def example(cls):
        print("Enable")

class Example(cl.OptionCategory):
    # REQUIRED (practical)
    @classmethod
    def options_defines(cls):
        return [Enabled.tie(("e", "example"), "for example")]

    # REQUIRED (practical)
    @classmethod
    def default(cls):
        return Disabled

class Main(cl.OptionForRun):
    # REQUIRED only when you use OptionForRun pattern
    @classmethod
    def run_with(cls, categories, arguments):
        categories[Example].example()

class Running(cl.OptionCategory):
    @classmethod
    def options_defines(cls):
        return []

    @classmethod
    def default(cls):
        return Main

categories_templates = [Running, Example]
categories, arguments = cl.Parser(categories_templates).parse(["--example"])
categories[Running].run_with(categories, arguments)
```

## Required vs Free (Contract)

### `Option`

- `[Provides]` `tie(keys, description)`: create option definition
- `[Provides]` `basic_tie(keys)`: use class name as description
- `[Provides]` `value_amount()`: default `0`
- `[Provides]` `with_value(strings)`: default returns class itself
- `[Required]` nothing for no-value flags
- `[Required]` implement `value_amount()` and `with_value(strings)` only when the option takes a value
- `[Free]` add behavior methods such as `execute()`, `example()`, `apply()`

### `OptionCategory`

- `[Provides]` category key type used in parse result map
- `[Provides]` conflict enforcement: one selected option per category
- `[Required]` implement `options_defines()`: selectable definitions in this category
- `[Required]` implement `default()`: fallback option when none is given
- `[Free]` add helper methods for category-level policy

### `Parser`

- `[Provides]` `parse(arguments) -> (categories, remaining_args)`
- `[Provides]` `parse_from_default()`: parse from `sys.argv[1:]`
- `[Required]` pass a list of category classes to `Parser(...)`

### `OptionForRun` (optional pattern)

- `[Provides]` convention class for executable entry option
- `[Required]` implement `run_with(categories, arguments)` if you use this pattern

### `BasicHelp` / `BasicVersion` (optional)

- `[Provides]` prebuilt behavior for help/version output
- `[Free]` override `overview()`, `usage()`, `explanation()` for help text
- `[Free]` override `product_name()`, `numbers()` for version text

## Help / Version

`BasicHelp` and `BasicVersion` are optional utilities.
The core feature is object-oriented option selection by `Parser`.

## Run Tests

```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

Compatibility runner:

```bash
python3 test/run.py
```

## Smoke Check After `pip install .`

```bash
python3 examples/smoke_install_check.py
```

Expected output:

```text
mode=apply args=['target']
```
