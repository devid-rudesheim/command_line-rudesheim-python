# Rudesheim Command Line Toolkit

`rudesheim.command_line` is a lightweight CLI argument parser for Python.
Its primary goal is not "parse string options into values" but
"select objects that own behavior".

## Version 3.0 — Breaking Change Notice

This is version 3.0, and it is **not compatible with 2.0**. `Parser.resolve()` now returns a
`RunParameters` directly instead of an internal wrapper object. Code written as
`state.run_parameters.categories[...]` (or `.arguments`) must become `state.categories[...]`
(or `.arguments`) — `state` (whatever you called the return value of `resolve()`) *is* the
`RunParameters` now, not something holding one. The wrapper type this removes (`ParseState`) was
never documented as something you construct yourself, but was technically importable from the
public module; it no longer is — it now lives under `rudesheim.command_line.private`, which was
already documented as internal-only. `Parser.parse()` is unaffected.
Code written against 2.0 needs to be updated before it will run on 3.0.

## Version 2.0 — Breaking Change Notice

This is version 2.0, and it is **not compatible with 1.0**. `Parser.parse()` no longer returns a
`(categories, arguments)` tuple; it now walks a `Command` tree and calls `run_with(run_parameters)`
for you (see "Two Ways To Drive It" below). `run_with` takes a single `RunParameters` argument
instead of separate `categories`/`arguments` parameters, and `OptionForRun` has been removed.
Code written against 1.0 needs to be updated before it will run on 2.0.

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

This library solves that by selecting `Option`/`Command` objects (or classes) directly.
After parsing, you get a map like:

- `Category -> selected Option` (or `Category -> selected Command`)

If each selected object has its own behavior method, caller-side branching is no longer needed.
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

# subcommands (see "Subcommands / Command Tree" below)
myapp compose up -d web db
```

## Two Ways To Drive It

- **`Parser.resolve(arguments, user_datas=None)`** never executes anything - it just returns a
  `RunParameters` holding `categories`, `arguments`, and `user_datas` (raising
  `UndefinedOptionSpecified`, `OptionIsInConflict`, `OptionValueIsMissing`, or `OptionIsMalformed`
  for a malformed command line - see `Parser`'s reference entry below). You dispatch behavior
  yourself, typically with one line at the end (see "Quick Start" below).
- **`Parser.parse(arguments, user_datas=None)`** additionally walks a `Command` tree (declared via
  `parser_define()`) and calls `run_with(run_parameters)` exactly once on whichever `Command` ends up
  selected deepest, then returns its result (see "Subcommands / Command Tree" below).
  It only makes sense when at least one category in the tree is made of `Command`s.

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
    def execute(this):
        print("dry run")

class Apply(cl.Option):
    # FREE: user-defined behavior
    @classmethod
    def execute(this):
        run_apply()

class Delete(cl.Option):
    # FREE: user-defined behavior
    @classmethod
    def execute(this):
        run_delete()

class Mode(cl.SelectableCategory):
    # REQUIRED (practical): declare selectable options in this category
    @classmethod
    def selectables_defines(this):
        return [
            DryRun.tie(("d", "dry-run"), "execute without changes"),
            Apply.tie(("a", "apply"), "apply changes"),
            Delete.tie(("x", "delete"), "delete resource"),
        ]

    # REQUIRED (practical): declare fallback when no option is given
    @classmethod
    def default(this):
        return DryRun

# FREE: caller sends behavior message to selected object
cl.Parser([Mode]).resolve(["--apply"]).categories[Mode].execute()
```

No `if/elif` by option value is needed in the caller.
The selected object can be called once or many times.

## Real Workflow Example (Repeated Option-Specific Calls)

The selected option is usually kept in a variable and used throughout shared flow:

```python
import rudesheim.command_line as cl

class DryRun(cl.Option):
    @classmethod
    def before_batch(this, items):
        print(f"[dry-run] check {len(items)} items")

    @classmethod
    def process_item(this, item):
        print(f"[dry-run] skip {item}")

    @classmethod
    def after_batch(this):
        print("[dry-run] done")

class Apply(cl.Option):
    @classmethod
    def before_batch(this, items):
        open_transaction()

    @classmethod
    def process_item(this, item):
        apply_item(item)

    @classmethod
    def after_batch(this):
        commit_transaction()

class Mode(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return [
            DryRun.tie(("d", "dry-run"), "do not mutate"),
            Apply.tie(("a", "apply"), "apply changes"),
        ]

    @classmethod
    def default(this):
        return DryRun

class Quiet(cl.Option):
    @classmethod
    def on_start(this, items):
        pass

    @classmethod
    def on_item(this, item):
        pass

    @classmethod
    def on_finish(this):
        pass

class Verbose(cl.Option):
    @classmethod
    def on_start(this, items):
        print(f"[verbose] start {len(items)} items")

    @classmethod
    def on_item(this, item):
        print(f"[verbose] item {item}")

    @classmethod
    def on_finish(this):
        print("[verbose] finish")

class ReportStyle(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return [
            Quiet.tie(("q", "quiet"), "minimal output"),
            Verbose.tie(("V", "verbose"), "verbose output"),
        ]

    @classmethod
    def default(this):
        return Quiet

run_parameters = cl.Parser([Mode, ReportStyle]).resolve(["--apply", "--verbose", "A", "B"])
categories = run_parameters.categories
mode = categories[Mode]
report = categories[ReportStyle]

# shared flow (common processing)
items = run_parameters.arguments
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
    def __init__(this, text):
        this.text = text

    # REQUIRED for value option
    @classmethod
    def value_amount(this):
        return 1

    # REQUIRED for value option
    @classmethod
    def with_value(this, strings):
        return this(strings)

    # FREE: domain behavior
    def as_int(this):
        return int(this.text)

class DepthCategory(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return [Depth.tie(("d", "depth"), "depth value")]

    @classmethod
    def default(this):
        return Depth("1")

run_parameters = cl.Parser([DepthCategory]).resolve(["--depth=3", "target"])
depth = run_parameters.categories[DepthCategory].as_int()  # 3
remaining = run_parameters.arguments  # ["target"]
```

## Quick Start

A flat command with no subcommands at all (like `pwd -L`) is driven with `resolve()` plus one
manual `run_with(...)` call — there is no verb to recurse into, so `parse()` (below) does not apply here.

```python
import rudesheim.command_line as cl

class Disabled(cl.Option):
    # FREE: user-defined behavior
    @classmethod
    def example(this):
        print("Disable")

class Enabled(cl.Option):
    # FREE: user-defined behavior
    @classmethod
    def example(this):
        print("Enable")

class Example(cl.SelectableCategory):
    # REQUIRED (practical)
    @classmethod
    def selectables_defines(this):
        return [Enabled.tie(("e", "example"), "for example")]

    # REQUIRED (practical)
    @classmethod
    def default(this):
        return Disabled

class Main(cl.Option):
    # FREE: give the entry-point option a run_with of its own
    @classmethod
    def run_with(this, run_parameters):
        run_parameters.categories[Example].example()

class Running(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return []

    @classmethod
    def default(this):
        return Main

categories_templates = [Running, Example]
run_parameters = cl.Parser(categories_templates).resolve(["--example"])
run_parameters.categories[Running].run_with(run_parameters)
```

## Subcommands / Command Tree

When your CLI has verbs (`myapp compose up`, `git worktree add`, ...), use `Command` instead of
`Option`. A `Command`'s `parser_define()` declares the grammar one level down, and `Parser.parse()`
walks the whole tree by itself — no manual recursive `parse()` calls needed.

```python
import sys
import rudesheim.command_line as cl

class Up(cl.Command):
    @classmethod
    def run_with(this, run_parameters):
        print(f"up {list(run_parameters.arguments)}")

class Down(cl.Command):
    @classmethod
    def run_with(this, run_parameters):
        print(f"down {list(run_parameters.arguments)}")

class ComposeSubcommand(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return [Up.tie(("up",), "start containers"), Down.tie(("down",), "stop containers")]

    @classmethod
    def default(this):
        # No subcommand typed here -> defer to Compose's own run_with(),
        # not Up's. See "Terminal" below.
        return cl.Terminal

class Compose(cl.Command):
    # REQUIRED to have subcommands: declare the grammar one level down
    @classmethod
    def parser_define(this):
        return cl.Parser([ComposeSubcommand])

    # FREE: only needed if "compose" with no subcommand should do something
    # of its own, instead of raising RunWithNotImplemented
    @classmethod
    def run_with(this, run_parameters):
        print("usage: compose [up|down]")

class RootSubcommand(cl.SelectableCategory):
    @classmethod
    def selectables_defines(this):
        return [Compose.tie(("compose",), "manage compose stacks")]

    @classmethod
    def default(this):
        # No token typed at all -> a real Command, not Terminal. There is no
        # enclosing Command here for Terminal to defer to.
        return Compose

cl.Parser([RootSubcommand]).parse(sys.argv[1:])
```

```text
$ myapp compose up web db
up ['web', 'db']

$ myapp compose
usage: compose [up|down]

$ myapp
usage: compose [up|down]
```

Notes on how dispatch works:

- Every time a category's value is decided — whether by an explicit match or by `default()` — its
  `decided_for(category, state)` runs. `Command` overrides this to recurse into its own
  `parser_define()`, then falls back to being the terminal itself if that recursion didn't produce a
  deeper one; `Option` and `Terminal` are no-ops. `run_with(run_parameters)` is then called **exactly
  once**, on whichever `Command` this settles on.
- Giving a Command-type category's `default()` a real `Command` (`RootSubcommand` above, defaulting to
  `Compose`) makes bare invocation behave like typing that Command explicitly — the same idea as `git
  stash` defaulting to `git stash push`.
- Giving it `cl.Terminal` instead (`ComposeSubcommand` above) means "no subcommand typed here — defer
  to the *enclosing* Command's own `run_with()`" (bare `compose` runs `Compose.run_with()`, not
  `Up.run_with()`). `Terminal` only makes sense for a category nested inside some other Command's
  `parser_define()` — there is no enclosing Command for a `Parser`'s own top-level category to defer
  to, so give that one a real `Command` instead, as `RootSubcommand` does.
- Categories declared above a `Command` (e.g. a global `--context` option declared alongside
  `RootSubcommand`) stay visible in the resulting `RunParameters.categories` all the way down; categories declared
  only inside a nested `parser_define()` are only visible from that point down.
- Forgetting to override `run_with` on a `Command` that does end up selected raises
  `RunWithNotImplemented`, not a silent no-op.
- A single `Parser`'s category list should declare at most one Command-type category. `Option`-type
  categories can coexist freely (they just sit independently in `run_parameters.categories`), but two
  Command-type categories both needing `default()` at the same level have no defined precedence between
  them — whichever is processed later in the list silently overwrites the other's contribution to
  `.terminals`. This isn't enforced at runtime, just avoid it.

This exact example is also a runnable file:

```bash
python3 examples/compose.py compose up web db
python3 examples/compose.py compose
python3 examples/compose.py
```

## `RunParameters`

Both `resolve()` and `parse()` build a `RunParameters` object with three fields:

- `user_datas`: whatever you passed as the second argument to `resolve`/`parse`/`parse_from_default`
  (or `[]` if you passed nothing). Use it to thread caller-owned, cross-cutting state — logging,
  a dry-run flag, an accumulator — down to every `run_with(...)` call without a global variable.
- `categories`: `{Category -> selected Option/Command}`, merged from the root of the tree down to
  wherever parsing stopped.
- `arguments`: the remaining positional arguments at that point.

## Required vs Free (Contract)

### `Selectable` (common base of `Option` and `Command`)

- `[Provides]` `tie(keys, description)`: create a selectable definition
- `[Provides]` `basic_tie(keys)`: use class name as description
- `[Provides]` `value_amount()`: default `0`
- `[Provides]` `with_value(strings)`: default returns the class itself
- `[Provides]` `run_with(run_parameters)`: default raises `RunWithNotImplemented`
- `[Free]` override `run_with(run_parameters)` to make this selectable executable
- `[Provides]` `decided_for(category, state)`: internal - runs once, right when this selectable becomes
  a category's value (matched or defaulted). Default no-op; `Command` overrides it - you should not
  need to touch this directly, see "Subcommands / Command Tree" above

### `Option`

- `[Required]` nothing for no-value flags
- `[Required]` implement `value_amount()` and `with_value(strings)` only when the option takes a value
- `[Free]` add behavior methods such as `execute()`, `example()`, `apply()`
- `[Free]` override `run_with(run_parameters)` if this option is meant to be the entry point of a flat,
  subcommand-less category (see "Quick Start")

### `Command`

- `[Provides]` `parser_define()`: default returns an empty `Parser([])` (a leaf with no subcommands)
- `[Required]` override `parser_define()` to declare a category of further subcommands
- `[Required]` override `run_with(run_parameters)` on any `Command` that can end up being the deepest
  selected one — otherwise `Parser.parse()` raises `RunWithNotImplemented` when it gets there
- `[Provides]` `decided_for(category, state)`: recurses into `parser_define()`, falling back to this
  Command itself if that recursion settled on nothing deeper
- see "Subcommands / Command Tree" above

### `Terminal`

- A ready-to-use `Selectable` with nothing overridden. Its only purpose is to be a Command-type
  category's `default()` when "nothing typed here" should defer to the *enclosing* Command's own
  `run_with()` instead of recursing further - see "Subcommands / Command Tree" above. Meaningless
  anywhere else (as an explicit `tie()` target, or as a `Parser`'s own top-level category's `default()`
  - there is no enclosing Command there to defer to).

### `SelectableCategory`

- `[Provides]` category key type used in the parse result map
- `[Provides]` conflict enforcement: one selected option per category
- `[Provides]` `default()`: raises `DefaultDoesNotExist` if `selectables_defines()` is empty, otherwise
  returns the first declared selectable
- `[Required]` implement `selectables_defines()`: selectable definitions in this category
- `[Free]` override `default()` explicitly instead of relying on "first declared wins" (recommended)

### `Parser`

- `[Provides]` `resolve(arguments, user_datas=None) -> RunParameters`: parse without running
  anything; the returned `RunParameters` holds `categories`/`arguments`/`user_datas`. Raises
  `UndefinedOptionSpecified` for an unrecognized flag, `OptionIsInConflict` when two Options from
  the same category are both given, `OptionValueIsMissing` when a value-taking option is given
  with no value (e.g. `-d` at the end of argv with nothing after it), and `OptionIsMalformed` for
  any other malformed input getopt rejects (e.g. a no-value option given a value it doesn't
  accept, like `--help=x`, or an ambiguous long-option prefix).
- `[Provides]` `parse(arguments, user_datas=None)`: resolve, then call `run_with(run_parameters)`
  exactly once on the deepest matched `Command`, and return its result
- `[Provides]` `parse_from_default(user_datas=None)`: same as `parse(sys.argv[1:], user_datas)`
- `[Required]` pass a list of category classes to `Parser(...)`

### `OptionForPrint` / `BasicHelp` / `BasicVersion` (optional)

- `[Provides]` `OptionForPrint.run_with(run_parameters)`: prints `print_string()`
- `[Free]` override `overview()`, `usage()`, `explanation()` for help text (`BasicHelp`)
- `[Free]` override `product_name()`, `numbers()` for version text (`BasicVersion`)

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
