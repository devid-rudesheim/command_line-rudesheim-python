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
    print( "dry run" )
elif mode == "apply":
    run_apply()
elif mode == "delete":
    run_delete()
else:
    raise ValueError( "unknown mode" )
```

### After (object selection + behavior dispatch)

```python
import rudesheim.command_line as cl

class DryRun( cl.Option ):
    # FREE: user-defined behavior
    @classmethod
    def execute( this ):
        print( "dry run" )

class Apply( cl.Option ):
    # FREE: user-defined behavior
    @classmethod
    def execute( this ):
        run_apply()

class Delete( cl.Option ):
    # FREE: user-defined behavior
    @classmethod
    def execute( this ):
        run_delete()

class Mode( cl.SelectableCategory ):
    # REQUIRED (practical): declare selectable options in this category
    @classmethod
    def selectables_defines( this ):
        return \
        [
            DryRun.tie( ( "d", "dry-run" ), "execute without changes" ),
            Apply.tie( ( "a", "apply" ), "apply changes" ),
            Delete.tie( ( "x", "delete" ), "delete resource" ),
        ]

    # REQUIRED (practical): declare fallback when no option is given
    @classmethod
    def default( this ):
        return DryRun

# FREE: caller sends behavior message to selected object
cl.Parser( [ Mode ] ).resolve( [ "--apply" ] ).categories[ Mode ].execute()
```

No `if/elif` by option value is needed in the caller.
The selected object can be called once or many times.

## Real Workflow Example (Repeated Option-Specific Calls)

The selected option is usually kept in a variable and used throughout shared flow:

```python
import rudesheim.command_line as cl

class DryRun( cl.Option ):
    @classmethod
    def before_batch( this, items ):
        print( f"[dry-run] check {len( items )} items" )

    @classmethod
    def process_item( this, item ):
        print( f"[dry-run] skip {item}" )

    @classmethod
    def after_batch( this ):
        print( "[dry-run] done" )

class Apply( cl.Option ):
    @classmethod
    def before_batch( this, items ):
        open_transaction()

    @classmethod
    def process_item( this, item ):
        apply_item( item )

    @classmethod
    def after_batch( this ):
        commit_transaction()

class Mode( cl.SelectableCategory ):
    @classmethod
    def selectables_defines( this ):
        return \
        [
            DryRun.tie( ( "d", "dry-run" ), "do not mutate" ),
            Apply.tie( ( "a", "apply" ), "apply changes" ),
        ]

    @classmethod
    def default( this ):
        return DryRun

class Quiet( cl.Option ):
    @classmethod
    def on_start( this, items ):
        pass

    @classmethod
    def on_item( this, item ):
        pass

    @classmethod
    def on_finish( this ):
        pass

class Verbose( cl.Option ):
    @classmethod
    def on_start( this, items ):
        print( f"[verbose] start {len( items )} items" )

    @classmethod
    def on_item( this, item ):
        print( f"[verbose] item {item}" )

    @classmethod
    def on_finish( this ):
        print( "[verbose] finish" )

class ReportStyle( cl.SelectableCategory ):
    @classmethod
    def selectables_defines( this ):
        return \
        [
            Quiet.tie( ( "q", "quiet" ), "minimal output" ),
            Verbose.tie( ( "V", "verbose" ), "verbose output" ),
        ]

    @classmethod
    def default( this ):
        return Quiet

run_parameters = cl.Parser( [ Mode, ReportStyle ] ).resolve( [ "--apply", "--verbose", "A", "B" ] )
categories = run_parameters.categories
mode = categories[ Mode ]
report = categories[ ReportStyle ]

# shared flow (common processing)
items = run_parameters.arguments
report.on_start( items )        # second category behavior
mode.before_batch( items )      # option-specific behavior
for item in items:               # common loop
    report.on_item( item )      # second category behavior
    mode.process_item( item )   # option-specific behavior
mode.after_batch()              # option-specific behavior
report.on_finish()              # second category behavior
```

In this style, common workflow stays in one place, and option-specific branching is absorbed by methods on selected option.

## Value Option Example (`-d 3` / `--depth=3`)

When an option receives a value, implement `value_amount()` and `with_value(strings)`.

```python
import rudesheim.command_line as cl

class Depth( cl.Option ):
    def __init__( this, text ):
        this.text = text

    # REQUIRED for value option
    @classmethod
    def value_amount( this ):
        return 1

    # REQUIRED for value option
    @classmethod
    def with_value( this, strings ):
        return this( strings )

    # FREE: domain behavior
    def as_int( this ):
        return int( this.text )

class DepthCategory( cl.SelectableCategory ):
    @classmethod
    def selectables_defines( this ):
        return [ Depth.tie( ( "d", "depth" ), "depth value" ) ]

    @classmethod
    def default( this ):
        return Depth( "1" )

run_parameters = cl.Parser( [ DepthCategory ] ).resolve( [ "--depth=3", "target" ] )
depth = run_parameters.categories[ DepthCategory ].as_int()  # 3
remaining = run_parameters.arguments  # ["target"]
```

## Quick Start

A flat command with no subcommands at all (like `pwd -L`) is driven with `resolve()` plus one
manual `run_with(...)` call — there is no verb to recurse into, so `parse()` (below) does not apply here.

```python
import rudesheim.command_line as cl

class Disabled( cl.Option ):
    # FREE: user-defined behavior
    @classmethod
    def example( this ):
        print( "Disable" )

class Enabled( cl.Option ):
    # FREE: user-defined behavior
    @classmethod
    def example( this ):
        print( "Enable" )

class Example( cl.SelectableCategory ):
    # REQUIRED (practical)
    @classmethod
    def selectables_defines( this ):
        return [ Enabled.tie( ( "e", "example" ), "for example" ) ]

    # REQUIRED (practical)
    @classmethod
    def default( this ):
        return Disabled

class Main( cl.Option ):
    # FREE: give the entry-point option a run_with of its own
    @classmethod
    def run_with( this, run_parameters ):
        run_parameters.categories[ Example ].example()

class Running( cl.SelectableCategory ):
    @classmethod
    def selectables_defines( this ):
        return []

    @classmethod
    def default( this ):
        return Main

categories_templates = [ Running, Example ]
run_parameters = cl.Parser( categories_templates ).resolve( [ "--example" ] )
run_parameters.categories[ Running ].run_with( run_parameters )
```

## Subcommands / Command Tree

When your CLI has verbs (`myapp compose up`, `git worktree add`, ...), use `Command` instead of
`Option`. A `Command`'s `parser_define()` declares the grammar one level down, and `Parser.parse()`
walks the whole tree by itself — no manual recursive `parse()` calls needed.

```python
import sys
import rudesheim.command_line as cl

class Up( cl.Command ):
    @classmethod
    def run_with( this, run_parameters ):
        print( f"up {list( run_parameters.arguments )}" )

class Down( cl.Command ):
    @classmethod
    def run_with( this, run_parameters ):
        print( f"down {list( run_parameters.arguments )}" )

class ComposeSubcommand( cl.SelectableCategory ):
    @classmethod
    def selectables_defines( this ):
        return [ Up.tie( ( "up", ), "start containers" ), Down.tie( ( "down", ), "stop containers" ) ]

    @classmethod
    def default( this ):
        # No subcommand typed here -> defer to Compose's own run_with(),
        # not Up's. See "Terminal" below.
        return cl.Terminal

class Compose( cl.Command ):
    # REQUIRED to have subcommands: declare the grammar one level down
    @classmethod
    def parser_define( this ):
        return cl.Parser( [ ComposeSubcommand ] )

    # FREE: only needed if "compose" with no subcommand should do something
    # of its own, instead of raising RunWithNotImplemented
    @classmethod
    def run_with( this, run_parameters ):
        print( "usage: compose [up|down]" )

class RootSubcommand( cl.SelectableCategory ):
    @classmethod
    def selectables_defines( this ):
        return [ Compose.tie( ( "compose", ), "manage compose stacks" ) ]

    @classmethod
    def default( this ):
        # No token typed at all -> a real Command, not Terminal. There is no
        # enclosing Command here for Terminal to defer to.
        return Compose

cl.Parser( [ RootSubcommand ] ).parse( sys.argv[1:] )
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
- `[Provides]` `value_completions(prefix)`: default returns `()` - only meaningful when
  `value_amount()` > 0; see "Tab Completion" below
- `[Provides]` `run_with(run_parameters)`: default raises `RunWithNotImplemented`, carrying the
  offending selectable on `.selectable`
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
  returns the first declared selectable. `DefaultDoesNotExist` carries the offending category on
  `.category`.
- `[Required]` implement `selectables_defines()`: selectable definitions in this category
- `[Free]` override `default()` explicitly instead of relying on "first declared wins" (recommended)

### `RequiredCategory` (optional)

A `SelectableCategory` subclass for a category that must be chosen explicitly on the command line -
`default()` raises `SelectableIsOmitted(this)` instead of falling back to `DefaultDoesNotExist` or the
first declared selectable:

```python
class Mode( cl.RequiredCategory ):
    @classmethod
    def selectables_defines( this ):
        return [ Apply.tie( ( "a", "apply" ), "apply changes" ) ]
```

`SelectableIsOmitted` carries the offending category on `.category`, so a caller catching it across
several `RequiredCategory` subclasses can tell which one was missing without parsing a message string.
The check runs inside `default()` itself - the same extension point every category already has - so it
fires identically for `Option`- and `Command`-based categories, and whether the category is driven via
`resolve()` (manual dispatch) or `parse()` (automatic `run_with()`).

### Exception Hierarchy

All exceptions this library raises are `BasicException` subclasses, composed along two independent
axes:

- **Phase** (every exception is exactly one of these three, no exceptions left unclassified):
  - `DeclarationException`: `Parser.__init__` raises these against the static `categories_templates`
    declarations themselves, before any command-line input is looked at - `KeyIsDuplicated`,
    `CategoryIsMixed`. An authoring bug, meant to be caught once during development.
  - `ParseException`: `Parser.resolve()`/`parse()` raises these while processing actual command-line
    input - `SelectableIsOmitted`, `DefaultDoesNotExist`, `OptionIsInConflict`,
    `UndefinedOptionSpecified`, `OptionValueIsMissing`, `OptionIsMalformed`. Bad end-user input to
    report and recover from.
  - `DispatchException`: fires from `run_with()` itself, after parsing has already succeeded -
    `RunWithNotImplemented`.
- **Shape** (which attributes it carries, independent of phase; internal only - not aliased into
  `rudesheim.command_line`): `private.CategoryException` carries a single offending `SelectableCategory`
  on `.category`; `private.KeyedException` carries a single offending external key spelling on `.key`
  (no leading `-`/`--`). Neither implies a phase by itself - e.g. `CategoryIsMixed` and
  `SelectableIsOmitted` both get `.category` from the same internal mixin but sit in different phases.
  `KeyIsDuplicated` and `OptionIsInConflict` carry more than one piece of data each and implement
  `__init__` directly instead. These mixins only exist to share `__init__` bodies between the concrete
  exceptions above - they aren't exposed for catching, since doing so (e.g. "catch anything with a
  `.category`") would mix a `DeclarationException` authoring bug with a `ParseException` end-user
  input error in one `except` clause.

Catch by phase (`ParseException`, `DeclarationException`, `DispatchException`) to decide how to react;
catch by the concrete exception type to read `.category`/`.key`/etc.

### Default Error Handling

Every `BasicException` provides two more hooks, meant to be composed into your own top-level error
handling instead of a hand-rolled isinstance/message chain:

- `describe()` (instance method): a human-readable one-line explanation built from this exception's
  own identifying attributes (e.g. `"unrecognized option: -x"`, `"category Mode requires an explicit
  selection"`). Default (`BasicException.describe()`) falls back to `str(this)`; every exception this
  library raises overrides it with a more specific message.
- `exit_code()` (classmethod): a [sysexits.h](https://man.freebsd.org/cgi/man.cgi?query=sysexits)-style
  process exit code for this exception's phase - `64` (`EX_USAGE`) for `ParseException`, `70`
  (`EX_SOFTWARE`) for `DeclarationException`/`DispatchException`, `1` for a bare `BasicException`.

Both are resolved polymorphically by the exception's own class - there is no separate handler object
to look up "what kind of exception is this" against, in keeping with this library's preference for
behavior living on the object itself. Typical use at your program's entry point:

```python
try:
    parser.parse_from_default()
except cl.BasicException as exception:
    print( exception.describe(), file = sys.stderr )
    sys.exit( exception.exit_code() )
```

### `Parser`

- `[Provides]` `Parser(categories_templates)`: validates the declarations immediately and raises
  `KeyIsDuplicated` if two selectables anywhere in `categories_templates` (same category or two
  different ones) tie the same external key, or `CategoryIsMixed` if one category's
  `selectables_defines()` ties selectables of more than one kind (e.g. an `Option` and a `Command`
  together) - keep `Option`s and `Command`s in separate categories, as every worked example above
  does. Both checks are scoped to this one level; a nested `Command`'s own `parser_define()` is
  validated independently once it is constructed, so reusing a key one level down is fine.
  `KeyIsDuplicated` carries the duplicated key spelling (`.key`) and both colliding categories
  (`.first_category`, `.second_category`); `CategoryIsMixed` carries the offending category
  (`.category`).
- `[Provides]` `resolve(arguments, user_datas=None) -> RunParameters`: parse without running
  anything; the returned `RunParameters` holds `categories`/`arguments`/`user_datas`. Raises
  `UndefinedOptionSpecified` for an unrecognized flag, `OptionIsInConflict` when two Options from
  the same category are both given, `OptionValueIsMissing` when a value-taking option is given
  with no value (e.g. `-d` at the end of argv with nothing after it), and `OptionIsMalformed` for
  any other malformed input getopt rejects (e.g. a no-value option given a value it doesn't
  accept, like `--help=x`, or an ambiguous long-option prefix). `UndefinedOptionSpecified`,
  `OptionValueIsMissing`, and `OptionIsMalformed` all carry the bare offending key spelling on
  `.key` (no leading `-`/`--`); `OptionIsInConflict` carries the offending category (`.category`),
  the selectable already chosen (`.previous`), and the one that lost (`.attempted`).
- `[Provides]` `parse(arguments, user_datas=None)`: resolve, then call `run_with(run_parameters)`
  exactly once on the deepest matched `Command`, and return its result
- `[Provides]` `parse_from_default(user_datas=None)`: same as `parse(sys.argv[1:], user_datas)`
- `[Provides]` `complete(arguments, user_datas=None) -> list[str]`: tab-completion candidates for
  the last element of `arguments`; never raises on incomplete/malformed input. See "Tab Completion"
  below - this alone does not make Tab-key completion work in a shell, it only computes candidates.
- `[Required]` pass a list of category classes to `Parser(...)`

### `OptionForPrint` / `BasicHelp` / `BasicVersion` (optional)

- `[Provides]` `OptionForPrint.run_with(run_parameters)`: prints `print_string()`
- `[Free]` override `overview()`, `usage()`, `explanation()` for help text (`BasicHelp`)
- `[Free]` override `product_name()`, `numbers()` for version text (`BasicVersion`)

## Tab Completion

`Parser.complete(arguments, user_datas=None)` computes candidate strings for the *last* element of
`arguments` (an empty string `""` if the user just typed a space and is starting a fresh word) -
flag/subcommand keys at whatever level of the command tree the earlier elements reach, or
`value_completions(prefix)` of a value-taking `Option`/`Command` whose flag was the immediately
preceding token. This is a **library-level interface only** - it takes a Python list and returns a Python
list. It has nothing to do with a shell yet.

```python
parser = cl.Parser( root_categories_templates )
parser.complete( [] )                                 # -> ["-v", "--verbose", "-q", "--quiet", "-h", "--help", "service", "config"]
parser.complete( [ "service", "" ] )                  # -> ["-d", "--detach", "-f", "--foreground", "-h", "--help", "start", "stop"]
parser.complete( [ "service", "st" ] )                # -> ["start", "stop"]
```

There are two separate, unrelated things below - do not mix them up:

1. **Testing `complete()` itself from a terminal**, with no shell involved at all. `examples/deploy.py`
   exposes a `--complete` mode for exactly this - it is a manual, explicit flag you type yourself to
   call `Parser.complete()` and print its result, purely to sanity-check the library's answer:

   ```zsh
   ./examples/deploy.py --complete                    # -> -v / --verbose / -q / --quiet / -h / --help / service / config
   ./examples/deploy.py --complete service ""          # -> -d / --detach / -f / --foreground / -h / --help / start / stop
   ./examples/deploy.py --complete service st          # -> start / stop
   ```

   Nothing here reacts to the Tab key. This is you, calling the backend directly.

2. **Actual Tab-key completion in a shell** is a *different, additional* piece of setup: a shell-side
   completion function that the shell calls automatically when you press Tab, and which then calls
   step 1's `--complete` mode *for you* and feeds the result back to the shell. An end user typing
   `--complete` by hand is never part of normal use - only the completion function does that, behind
   the scenes. Try it hands-on without touching your own shell config:

   ```zsh
   ./examples/deploy-completion-shell.zsh
   ```

   This drops you into a fresh interactive zsh with the wiring already done (it points `ZDOTDIR` at a
   throwaway directory holding a generated `.zshrc`, so your real `~/.zshrc` is untouched and the setup
   disappears again once you exit that shell with `exit`/Ctrl-D). Inside it, just type
   `./deploy.py <Tab>` / `./deploy.py service <Tab>` / etc.

   Its comments spell out two prerequisites that trip people up when wiring this into your own shell
   instead:
   - zsh's completion system doesn't exist until `autoload -Uz compinit && compinit` has run *in
     that shell*, and this state is per-session, not persistent - a brand new terminal tab has none
     of it until compinit runs there too, even if you already did it once elsewhere. Skipping this
     makes `compdef` either error outright or silently no-op, with Tab falling back to plain
     filename completion and no error at all - `print -r -- ${_comps[deploy.py]}` after registering
     should print `_deploy_py`; if it prints nothing, registration did not actually take effect in
     that shell.
   - `compdef` binds to the literal command word you type, so it only fires for `./deploy.py <Tab>`
     / `deploy.py <Tab>`, never for `python3 deploy.py <Tab>` (there the typed command word is
     `python3`, not `deploy.py`). `deploy.py` already ships executable (`#!/usr/bin/env python3` +
     the executable bit) so this works without typing `python3` in front.

   To make this permanent in your *own* shell (rather than the disposable one the script above gives
   you), copy the `autoload -Uz compinit && compinit`, `_deploy_py()` function body, and
   `compdef _deploy_py deploy.py` lines out of `examples/deploy-completion-shell.zsh` into `~/.zshrc`.

`value_completions()` is a plain classmethod override, same as `with_value()` - only override it on a
value-taking `Option`/`Command` where suggesting values makes sense.

## Help / Version

`BasicHelp` and `BasicVersion` are optional utilities.
The core feature is object-oriented option selection by `Parser`.

`examples/run.py` is a runnable, flat (Command-less) CLI wiring both of them in together with an
ordinary value-less `Example`/`Enabled`/`Disabled` option category - the "Quick Start" shape above,
plus `-v`/`--version` and `-h`/`--help`:

```bash
python3 examples/run.py --version   # -> Example, version 2.1.0
python3 examples/run.py --help      # -> generated options: listing
python3 examples/run.py --example   # -> Enable
python3 examples/run.py             # -> Disable (Example category's default())
```

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
