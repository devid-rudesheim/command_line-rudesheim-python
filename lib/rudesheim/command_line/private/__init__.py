"""Internal machinery behind rudesheim.command_line - parse-time dispatch plus
help-text scaffolding not meant for library users to reference directly.

You should not need to import this module directly - Parser/Option/Command in
the public `rudesheim.command_line` package already talk to it through
`parse_identifier()`, and ItemForHelp/DefineOfSelectable are reached only
through the public classes that inherit or subclass them.

Caveat, read this if anything below looks confusingly familiar: the
Selectable/Option/Command classes in *this* module are NOT the same classes as
the public `rudesheim.command_line.Selectable/Option/Command`. They are
internal identifiers/behavior for one step of `Parser.resolve()`'s reduce,
looked up via the public classes' `parse_identifier()`. The two class
families are deliberately unrelated by inheritance - linked only through that
identifier lookup, so this module never has to import the public one (which
would create a circular import, since the public module imports this one).
"""

class BasicException( Exception ):
	pass

class UndefinedOptionSpecified( BasicException ):
	pass

class OptionIsInConflict( BasicException ):
	pass

class OptionValueIsMissing( BasicException ):
	pass

class OptionIsMalformed( BasicException ):
	"""Catch-all for a GetoptError that is neither "not recognized" (an
	undefined flag) nor "requires argument" (a missing value) - e.g. a
	no-value option given a value it doesn't accept (`--help=x`), or an
	ambiguous long-option prefix matching more than one declared option."""
	pass

class ParseState:
	"""Internal accumulator threaded through Parser._resolve()'s recursion.
	Returned by the public module's Parser._resolve() (never by the public
	resolve(), which unwraps this down to just `.run_parameters`) - you don't
	normally construct this yourself.

	- run_parameters: a command_line.RunParameters; its `.categories` dict is
	  mutated in place as parsing proceeds.
	- opts: raw (flag, value) pairs straight out of getopt, consumed only by
	  Option.parse_with below. Not meaningful to user code.
	- terminals: `[]`, or a single-element list holding the Command selected
	  as the deepest match so far - see command_line.Parser.parse()'s
	  docstring for how this gets resolved.
	"""

	def __init__( this, run_parameters, opts, terminals ):
		this.run_parameters = run_parameters
		this.opts = opts
		this.terminals = terminals

	@classmethod
	def following( this, parse_state, arguments, terminals ):
		"""Internal: build the next ParseState in the chain, carrying
		parse_state's user_datas/categories/opts forward unchanged while
		replacing arguments/terminals. Used by parse_with implementations
		below. Delegates to RunParameters.following() rather than
		constructing one directly, so this module never has to import the
		public one (see module docstring above)."""
		return ParseState \
		(
			parse_state.run_parameters.following( arguments ),
			parse_state.opts,
			terminals
		)

class ShortKeyDecorator:
	"""Formats a key for the short-option form: external spelling "-x", spec
	suffix ":" when the option also takes a value."""

	@classmethod
	def select( this, container ):
		return container[0]

	@classmethod
	def convert_for_external( this, key ):
		return "-" + key

	@classmethod
	def convert_for_spec( this, key ):
		return key + ":"

class LongKeyDecorator:
	"""Formats a key for the long-option form: external spelling "--xxx", spec
	suffix "=" when the option also takes a value."""

	@classmethod
	def select( this, container ):
		return container[1]

	@classmethod
	def convert_for_external( this, key ):
		return "--" + key

	@classmethod
	def convert_for_spec( this, key ):
		return key + "="

def key_decorator_for( key ):
	"""Picks ShortKeyDecorator for a 1-character key, LongKeyDecorator
	otherwise. This length check is the entire short-vs-long rule referenced
	throughout the public Selectable.tie()'s docstring."""
	return [ ShortKeyDecorator, LongKeyDecorator ][ 1 != len( key ) ]

class Selectable:
	"""Internal base for this module's Option/Command - see this module's
	docstring for how these relate to the public classes of the same name.
	"""

	@classmethod
	def value_amount( this ):
		return 0

	@classmethod
	def with_value( this, strings ):
		return this

	@classmethod
	def parse_identifier( this ):
		return Selectable

	@classmethod
	def external_key_for( this, key, selectable ):
		"""Converts one key from tie() into its CLI-facing spelling (e.g.
		"d" -> "-d", "depth" -> "--depth"). Command overrides this to return
		the key unchanged, since subcommands are typed bare, without dashes.
		`selectable` (the actual command_line.Option/Command subclass, e.g.
		Depth) is unused at this level - it only matters to Option.key_spec
		below, which needs selectable.value_amount()."""
		return key_decorator_for( key ).convert_for_external( key )

	@classmethod
	def key_spec( this, key, selectable ):
		"""This key's getopt short/long spec contribution. The base
		implementation contributes nothing at all - a bare
		command_line.Selectable (neither Option nor Command) can therefore
		never be matched from CLI input, only ever reached through a
		category's default()."""
		return ( [], [] )

	@classmethod
	def decided_for( this, category, state, selectable ):
		"""Called once, right after `selectable` becomes
		`state.run_parameters.categories[category]` - whether that happened
		because it was explicitly typed (Command.parse_with) or because it
		was category.default() (command_line.Parser.resolve()'s fill loop).
		Both call sites treat the two origins identically, which is what
		lets default() behave like a real, resolvable candidate instead of a
		value that only sits in `categories` inertly.

		Base: no-op passthrough - correct for Option and for
		command_line.Terminal (neither ever contributes to `.terminals`,
		since neither is ever something Parser.parse() should call
		run_with() on by itself). Command overrides this to recurse into
		`selectable.parser_define()` - see there."""
		return state

	@classmethod
	def parse_with( this, categories_templates, selectables_by_key, state ):
		"""One reduce step of Parser._resolve(): consume whatever this
		identifier is responsible for out of `state` (a ParseState), return
		the resulting ParseState to hand to the next step.
		`selectables_by_key` is `{external key -> (category, selectable)}`,
		scoped to this identifier only. Base: no-op passthrough - see
		Option.parse_with / Command.parse_with below for the real logic, and
		`command_line.Parser._resolve()` for how this gets driven.
		"""
		return state

	@classmethod
	def parse_order( this ):
		"""Lower runs first within one Parser.resolve() reduce. Options (0)
		run before Commands (1), so a subcommand token is only looked at
		after every flag on that level has already been consumed."""
		return 999

	@classmethod
	def can_display( this ):
		"""Whether entries of this kind should appear at all in
		command_line.BasicHelp's generated listing. Base: True - lets
		BasicHelp stay generic over identifier kinds instead of naming
		Option/Command directly."""
		return True

	@classmethod
	def display_name( this ):
		"""Label for the section command_line.BasicHelp prints entries of
		this kind under - BasicHelp adds its own trailing ":" when
		rendering, same as it does for category.description(). Base:
		"options" - covers Option and any bare Selectable tied directly;
		Command overrides this to "commands"."""
		return "options"

	@classmethod
	def display_order( this ):
		"""Sort key for this kind's section among others in
		command_line.BasicHelp's output - lower sorts first. Base: 0 -
		Command overrides this to 1 so commands: sorts after options:."""
		return 0

class Option( Selectable ):
	"""Consumes every getopt-recognized flag out of `state.opts` into
	`state.run_parameters.categories`, raising OptionIsInConflict if a
	category already got a value this round. See the public
	`command_line.Option`/`SelectableCategory` for the user-facing side of
	this."""

	@classmethod
	def key_spec( this, key, selectable ):
		if 1 == len( key ):
			return ( [ [ key, key_decorator_for( key ).convert_for_spec( key ) ][ 0 < selectable.value_amount() ] ], [] )

		return ( [], [ [ key, key_decorator_for( key ).convert_for_spec( key ) ][ 0 < selectable.value_amount() ] ] )

	@classmethod
	def parse_identifier( this ):
		return Option

	@classmethod
	def parse_order( this ):
		return 0

	@classmethod
	def parse_with( this, categories_templates, selectables_by_key, state ):
		for key_value in state.opts:
			category, selectable = selectables_by_key[ key_value[0] ]
			if category in state.run_parameters.categories:
				raise OptionIsInConflict()

			if 0 < selectable.value_amount():
				selectable = selectable.with_value( key_value[1] )

			state.run_parameters.categories[ category ] = selectable

		return state

class Command( Selectable ):
	"""Consumes at most one positional token from
	`state.run_parameters.arguments` (if it matches a declared subcommand),
	assigns the matched selectable into `state.run_parameters.categories`,
	then hands off to `decided_for(...)` below for what happens next -
	recursing into the selectable's own `parser_define()` and settling
	`.terminals`. This is also called directly by
	`command_line.Parser._resolve()`'s default-fill loop (via
	`default_value.parse_identifier().decided_for(...)`), so a
	category.default() value recurses exactly the same way an explicitly
	typed one does.
	"""

	@classmethod
	def parse_identifier( this ):
		return Command

	@classmethod
	def parse_order( this ):
		return 1

	@classmethod
	def display_name( this ):
		return "commands"

	@classmethod
	def display_order( this ):
		return 1

	@classmethod
	def external_key_for( this, key, selectable ):
		return key

	@classmethod
	def decided_for( this, category, state, selectable ):
		"""Recurse into `selectable.parser_define()`, merging whatever it
		resolves back into state.run_parameters.categories. If that nested
		resolve() produced its own terminal (something deeper matched, or
		defaulted to something that itself recursed), that terminal wins;
		otherwise `selectable` falls back to being the terminal itself - see
		command_line's README "Subcommands / Command Tree" for the worked
		example."""
		next_state = selectable.parser_define()._resolve( state.run_parameters.arguments, state.run_parameters.user_datas )
		state.run_parameters.categories.update( next_state.run_parameters.categories )
		return next_state.following( state, next_state.run_parameters.arguments, [ ( next_state.terminals + [ selectable ] )[0] ] )

	@classmethod
	def parse_with( this, categories_templates, selectables_by_key, state ):
		if 0 == len( state.run_parameters.arguments ):
			return state

		key = state.run_parameters.arguments[0]

		if key not in selectables_by_key:
			return state

		category, selectable = selectables_by_key[ key ]
		state.run_parameters.categories[ category ] = selectable

		return selectable.parse_identifier().decided_for( category, state.following( state, state.run_parameters.arguments[1:], state.terminals ), selectable )

class ItemForHelp:
	"""Mixin providing a describable label for help/error text. Moved here
	from the public module since library users never reference this mixin
	by name - they only ever see it through inherited description()
	overrides on Selectable/SelectableCategory."""

	@classmethod
	def description( this ):
		"""Default label: the class's own name (`this` is the class here, most
		callers invoke this as `SomeClass.description()`). Override to give a
		human-readable description instead - used in BasicHelp's generated
		output."""
		return this.__name__

class DefineOfSelectable( ItemForHelp ):
	"""The result of the public Selectable.tie(keys, description): pairs one
	selectable (a class, or an instance for pre-configured selectables) with
	the CLI keys that select it and a human-readable description.

	Library users normally never construct or name this directly - call
	`SomeSelectable.tie(...)` instead. The public `DefineOfOption` subclasses
	this to add the `option()` alias; that subclass is the one users actually
	instantiate (for the BasicHelp pattern), so it stays in the public
	module.
	"""

	def __init__( this, selectable, keys, description ):
		this.selectable_ = selectable
		this.keys_ = keys
		this.description_ = description

	def selectable( this ):
		"""The tied class (or instance, for a pre-configured selectable such
		as `Help(categories_templates)`)."""
		return this.selectable_

	def keys( this ):
		"""The keys tuple passed to tie(), e.g. ("d", "depth"). Each entry is
		an independent key string, not a (short, long) pair - see the public
		Selectable.tie()'s docstring for how short vs. long is decided."""
		return this.keys_

	def description( this ):
		return this.description_
