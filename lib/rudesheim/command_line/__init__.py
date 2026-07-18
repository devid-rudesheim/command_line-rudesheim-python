"""rudesheim.command_line: an object-selecting CLI argument parser.

Instead of returning primitive values ("mode" == "apply"), this library resolves
each declared category of a command line to the *class* (or instance) the user
selected, then lets that object carry its own behavior via ``run_with(...)``.

Two independent selectable kinds exist:

- ``Option``: chosen by a flag (``-x`` / ``--xxx``), one per ``SelectableCategory``.
- ``Command``: chosen by a bare positional token (``build``, ``compose``), and can
  declare a nested grammar of its own subcommands via ``parser_define()``.

See README.md for full worked examples ("Quick Start" for flat Option-only CLIs,
"Subcommands / Command Tree" for Command-based ones); the docstrings below focus
on argument shapes and gotchas, not tutorials.
"""

import sys
import getopt as go
import functools as ft
import rudesheim.command_line.private as private

BasicException = private.BasicException
UndefinedOptionSpecified = private.UndefinedOptionSpecified
OptionIsInConflict = private.OptionIsInConflict

class DefaultDoesNotExist( BasicException ):
	"""Raised by the base SelectableCategory.default() when selectables_defines()
	is empty and the subclass did not override default() with its own fallback."""
	pass

class RunWithNotImplemented( BasicException ):
	"""Raised by the base Selectable.run_with() when a Command/Option that ended
	up selected as the terminal never overrode run_with(). Deliberately loud
	instead of a silent no-op, since Parser.parse() always calls run_with()
	exactly once on whatever it resolves to."""
	pass

class DefineOfOption( private.DefineOfSelectable ):
	"""Same as private.DefineOfSelectable, plus an `option()` alias for
	`.selectable()`.

	Use this (instead of `.tie()`) when you need to tie an *instance* into a
	category rather than the bare class - e.g. when a selectable such as
	BasicHelp needs constructor arguments before it can be selected:

		cl.DefineOfOption( Help( categories_templates ), ( 'h', 'help' ), "show help" )
	"""

	def option( this ):
		return this.selectable()

class Selectable( private.ItemForHelp ):
	"""Common base of Option and Command. You do not subclass this directly -
	subclass Option or Command instead. Its methods here are the protocol both
	rely on, and both categories of selectable inherit its default `run_with`.
	"""

	@classmethod
	def value_amount( this ):
		"""How many CLI values this selectable consumes when chosen. 0
		(default) means a bare flag/token; override to return 1 for anything
		that also reads a following value (`-d 3`, `--depth=3`)."""
		return 0

	@classmethod
	def with_value( this, strings ):
		"""Called only when value_amount() > 0, with the single value string
		getopt captured (despite the plural-looking parameter name, this is
		one `str`, not a list). Must return whatever object should end up
		selected - typically construct an instance to carry the value:

			class Depth( cl.Option ):
				def __init__( this, text ):
					this.text = text

				@classmethod
				def value_amount( this ):
					return 1

				@classmethod
				def with_value( this, strings ):
					return this( strings )

		Default returns the class itself unchanged, which is only correct
		when value_amount() is 0."""
		return this

	@classmethod
	def parse_identifier( this ):
		"""Which private-layer class (rudesheim.command_line.private.*) drives
		this kind of selectable. Not just for Parser.resolve()'s own
		dispatch: external_key_for(key, selectable), key_spec(key,
		selectable), and decided_for(category, state, selectable) all live
		on the returned class, not on Selectable itself, and are always
		called as `selectable.parse_identifier().the_method( ..., selectable )`
		- see private/__init__.py for what each of those three actually does.
		Option and Command already override this correctly; you should not
		need to touch it unless you are inventing an entirely new selectable
		kind (in which case you likely need a new private.* class too)."""
		return private.Selectable

	@classmethod
	def tie( this, keys, description ):
		"""Declare this selectable inside a SelectableCategory's
		selectables_defines():

			@classmethod
			def selectables_defines( this ):
				return [ Depth.tie( ( "d", "depth" ), "set the depth" ) ]

		Caveat: `keys` is NOT a (short, long) pair - it is a flat collection of
		independent key strings, and each one is classified as short ("-x") or
		long ("--xxx") purely by its own length (1 character vs. more). Tie as
		many short/long aliases as you like: `("d",)`, `("d", "depth")`,
		`("depth", "verbose-depth")`, etc.
		"""
		return private.DefineOfSelectable( this, keys, description )

	@classmethod
	def basic_tie( this, keys ):
		"""Same as tie(), using this.description() as the description text
		instead of passing one explicitly."""
		return this.tie( keys, this.description() )

	@classmethod
	def run_with( this, run_parameters ):
		"""Called when this selectable is the one actually executed - either
		automatically (Parser.parse(), for the deepest matched Command) or
		manually (you call it yourself, for a flat Option-only category - see
		README "Quick Start"). Receives a single RunParameters instance; see
		its docstring below for `.user_datas` / `.categories` / `.arguments`.

		Default raises RunWithNotImplemented - override to give this
		selectable actual behavior.
		"""
		raise RunWithNotImplemented()

class Option( Selectable ):
	"""A selectable chosen by a flag (`-x` / `--xxx`). Exactly one Option per
	SelectableCategory ends up selected per parse - giving two flags from the
	same category raises OptionIsInConflict. See README "Before / After" and
	"Value Option Example" for full worked examples.
	"""

	@classmethod
	def parse_identifier( this ):
		return private.Option

class Command( Selectable ):
	"""A selectable chosen by a bare positional token (`build`, `compose`,
	`up`), optionally declaring a nested grammar of its own subcommands. See
	README "Subcommands / Command Tree" for a full worked example.

	Caveats:
	- Only Commands ever become the terminal that Parser.parse() calls
	  run_with() on - Options never do, regardless of category.
	- If this Command has subcommands (parser_define() returns a non-empty
	  Parser) but the user gives no matching token, run_with() still needs to
	  be implemented on *this* Command for that case to do something other
	  than raise RunWithNotImplemented - see the "Subcommands / Command Tree"
	  notes on fallback behavior in README.md.
	"""

	@classmethod
	def parse_identifier( this ):
		return private.Command

	@classmethod
	def parser_define( this ):
		"""Declares this Command's own subcommand grammar as a fresh Parser.
		Default: `Parser([])` - a leaf with no subcommands at all. Override to
		return `Parser([SomeSubcommandCategory])` to add subcommands one level
		down; see README "Subcommands / Command Tree"."""
		return Parser( [] )

class Terminal( Selectable ):
	"""A selectable whose only purpose is to be a category's default() when
	you want "nothing more was typed here" to defer to the enclosing Command's
	own run_with(), instead of recursing further. Carries no behavior of its
	own - parse_identifier() routes it to private.Selectable's no-op
	decided_for(), so nothing gets added to `.terminals` when it is decided,
	and the enclosing Command's own decided_for() falls back to itself.

	Only meaningful for a Command-type category nested inside some other
	Command's parser_define() - there is no enclosing Command to fall back to
	for a Parser's own top-level categories, so do not use Terminal there
	(give that category's default() a real, executable Command instead)."""
	pass

class SelectableCategory( private.ItemForHelp ):
	"""Declares one mutually-exclusive slot in the parsed command line - e.g.
	"which mode", "which subcommand", "verbose or quiet". You never
	instantiate this - it is used as a bare class throughout, and the class
	itself becomes a key in RunParameters.categories.
	"""

	@classmethod
	def selectables_defines( this ):
		"""Return the list of DefineOfSelectable entries this category offers,
		usually built with tie()/basic_tie():

			@classmethod
			def selectables_defines( this ):
				return [ Apply.tie( ( "a", "apply" ), "apply changes" ) ]

		Default: none. A category with no entries at all is still usable (it
		always resolves to default()) - a bare Selectable's key_spec() (see
		private/__init__.py) contributes nothing to getopt, so it can never be
		matched from CLI input, only ever reached through default().
		"""
		return ()

	@classmethod
	def default( this ):
		"""Fallback selected when nothing from selectables_defines() was given
		on the command line. Default implementation: raises
		DefaultDoesNotExist if selectables_defines() is empty, otherwise
		returns the *first* declared selectable - relying on that ordering is
		fragile, so overriding this explicitly is recommended practice, not
		just an option.
		"""
		selectables = this.selectables_defines()
		if 0 == len( selectables ):
			raise DefaultDoesNotExist()

		return selectables[0].selectable()

class RunParameters:
	"""Everything a `run_with(run_parameters)` implementation gets, bundled
	into one object.

		@classmethod
		def run_with( this, run_parameters ):
			mode = run_parameters.categories[ Mode ]
			print( f"mode={mode}, extra args={run_parameters.arguments}" )

	Fields:
	- user_datas: whatever you passed as Parser.resolve()/parse()'s second
	  argument (or `[]` if you passed nothing). Not touched by the library at
	  all - use it to thread your own cross-cutting state (a logger, an
	  accumulator, a dry-run flag) down to every run_with() call.
	- categories: `{SelectableCategory subclass -> selected Option/Command}`,
	  merged from the root of the tree down to wherever parsing stopped.
	  Categories declared above a Command stay visible all the way down;
	  categories declared only inside a nested parser_define() only appear
	  once you have descended past that point.
	- arguments: the remaining positional arguments at that point (a list of
	  `str`).
	"""

	def __init__( this, user_datas, categories, arguments ):
		this.user_datas = user_datas
		this.categories = categories
		this.arguments = arguments

class ParseState:
	"""Internal accumulator threaded through Parser.resolve()'s recursion.
	Returned to you by resolve() (as `state`, with `state.run_parameters`
	being what you actually want) - you don't normally construct this
	yourself.

	- run_parameters: a RunParameters (see above); its `.categories` dict is
	  mutated in place as parsing proceeds.
	- opts: raw (flag, value) pairs straight out of getopt, consumed only by
	  Option.parse_with in private/__init__.py. Not meaningful to user code.
	- terminals: `[]`, or a single-element list holding the Command selected
	  as the deepest match so far - see Parser.parse()'s docstring for how
	  this gets resolved.
	"""

	def __init__( this, run_parameters, opts, terminals ):
		this.run_parameters = run_parameters
		this.opts = opts
		this.terminals = terminals

	@classmethod
	def following( this, parse_state, arguments, terminals ):
		"""Internal: build the next ParseState in the chain, carrying
		parse_state's user_datas/categories/opts forward unchanged while
		replacing arguments/terminals. Used by private/__init__.py's
		parse_with implementations - see that module if you are extending
		the parsing machinery itself, not just using it."""
		return ParseState \
		(
			RunParameters( parse_state.run_parameters.user_datas, parse_state.run_parameters.categories, arguments ),
			parse_state.opts,
			terminals
		)

class Parser:
	"""Parses one level of a command line against a list of SelectableCategory
	classes. See README "Two Ways To Drive It" for resolve() vs. parse().

		cl.Parser( [ Mode, ReportStyle ] )
	"""

	def resolve( this, arguments, user_datas = None ):
		"""Parse `arguments` (a list of `str`, no program name) and return a
		ParseState - never runs anything, always safe to call.

			state = cl.Parser( [ Mode ] ).resolve( [ "--apply", "target" ] )
			state.run_parameters.categories[ Mode ].execute()   # you drive it

		Recurses into a Command's own parser_define() automatically when a
		subcommand token matches, merging that Command's categories into the
		returned state (see RunParameters.categories).

		Caveats:
		- Raises UndefinedOptionSpecified for an unrecognized flag, and
		  OptionIsInConflict when two Options from the same category are both
		  given.
		- A GetoptError that is not an "unrecognized option" error (e.g. a
		  value-taking option given with no value) is currently swallowed:
		  this method returns `None` instead of raising or returning a
		  ParseState. This is a known, not-yet-fixed quirk - check for `None`
		  if it matters to you.
		"""
		user_datas = [] if user_datas is None else user_datas
		selectables = {}
		keys_specs = ( [], [] )

		# build lookup table and list for mapping
		for category in this.categories_templates_:
			for define in category.selectables_defines():
				for key in define.keys():
					selectable = define.selectable()
					identifier = selectable.parse_identifier()

					selectables.setdefault( identifier, {} )[ identifier.external_key_for( key, selectable ) ] = ( category, selectable )

					for spec, result in zip( keys_specs, identifier.key_spec( key, selectable ) ):
						spec.extend( result )

		try:
			getopt_result = go.getopt( arguments, "".join( keys_specs[0] ), keys_specs[1] )
			if 0 == len( selectables ):
				return ParseState( RunParameters( user_datas, {}, getopt_result[1] ), [], [] )

			state = ft.reduce \
			(
				lambda state, each: each.parse_with \
				(
					this.categories_templates_,
					selectables[ each.parse_identifier() ],
					state
				),
				sorted( [ key for key in selectables ], key = lambda each: each.parse_order() ),
				ParseState( RunParameters( user_datas, {}, getopt_result[1] ), getopt_result[0], [] )
			)

			for category in this.categories_templates_:

				if category in state.run_parameters.categories:
					continue

				default_value = category.default()
				state.run_parameters.categories[ category ] = default_value
				state = default_value.parse_identifier().decided_for( category, state, default_value )

			return state

		except go.GetoptError as exception:

			if 0 < str( exception ).find( "not recognize" ):
				raise UndefinedOptionSpecified() from exception

	def parse( this, arguments, user_datas = None ):
		"""Like resolve(), then calls `run_with(run_parameters)` exactly once
		and returns its result - see README "Subcommands / Command Tree" for
		the full mechanics of which Command ends up called.

		Caveat: needs at least one Command category somewhere in the tree. If
		nothing ever matches a Command (a flat Option-only Parser, or a
		Command tree where even the root token doesn't match), there is no
		terminal to call and this raises `IndexError`. Use resolve() instead
		for flat, Command-less CLIs (see README "Quick Start").
		"""
		state = this.resolve( arguments, user_datas )
		return state.terminals[0].run_with( state.run_parameters )

	def parse_from_default( this, user_datas = None ):
		"""Same as `parse(sys.argv[1:], user_datas)` - the usual top-level
		entry point for a real script."""
		return this.parse( sys.argv[1:], user_datas )

	def __init__( this, categories_templates ):
		"""categories_templates: a list of SelectableCategory *classes* (not
		instances), e.g. `Parser( [ Mode, ReportStyle ] )`."""
		this.categories_templates_ = categories_templates

class OptionForPrint( Option ):
	"""An Option whose run_with() just prints print_string(). Base for
	BasicVersion/BasicHelp below; you can also subclass it directly for your
	own "print something and stop" options.
	"""

	@classmethod
	def print_string( this ):
		return ""

	@classmethod
	def run_with( this, run_parameters ):
		print( this.print_string() )

class BasicVersion( OptionForPrint ):
	"""Ready-made "--version" option. Override product_name()/numbers() for
	your own application:

		class Version( cl.BasicVersion ):
			@classmethod
			def product_name( this ):
				return "myapp"

			@classmethod
			def numbers( this ):
				return ( 2, 1, 0 )   # -> "myapp, version 2.1.0"
	"""

	@classmethod
	def description( this ):
		return "Print version information and exit"

	@classmethod
	def product_name( this ):
		return ""

	@classmethod
	def numbers( this ):
		return ( 1, 0 )

	@classmethod
	def print_string( this ):
		product_name = ""

		if 0 < len( this.product_name() ):
			product_name = this.product_name() + ", "

		return product_name + "version " + ".".join( [ str( i ) for i in this.numbers() ] )


class BasicHelp( OptionForPrint ):
	"""Ready-made "--help" option that lists every category/selectable passed
	to its constructor.

	Caveat: unlike most Selectables (used as bare classes), BasicHelp needs an
	*instance*, constructed with the same categories_templates list you pass
	to Parser(...), and tied in with DefineOfOption instead of tie():

		class Help( cl.BasicHelp ):
			@classmethod
			def usage( this ):
				return [ "myapp [options]" ]

		categories_templates = [ Running, Mode ]

		class Running( cl.SelectableCategory ):
			@classmethod
			def selectables_defines( this ):
				return [ cl.DefineOfOption( Help( categories_templates ), ( 'h', 'help' ), "show help" ) ]

	Override overview()/usage()/explanation() to add free-text lines before
	the generated per-category option listing.
	"""

	@classmethod
	def description( this ):
		return "Print Help (this message) and exit"

	@classmethod
	def overview( this ):
		return []

	@classmethod
	def usage( this ):
		return []

	@classmethod
	def explanation( this ):
		return []

	def print_string( this ):
		# Builds: overview()/usage()/explanation() lines, then every
		# category's declared selectables with their keys, column-aligned
		# and grouped into sections keyed by each selectable's
		# parse_identifier() itself (private.Option, private.Command, ...)
		# - the identifier is the key, its display_name()/display_order()
		# are only called when rendering, so no separate lookup table ties
		# identifiers to section titles/ordering. See private.Selectable's
		# can_display()/display_name()/display_order() for the hook
		# Option/Command plug into, so this stays generic over identifier
		# kinds instead of naming them directly. See
		# tests/test_command_line.py's HelpTests for exact output
		# formatting - easier read from an example than restated here.
		max_length = 0

		sections = {}

		for category in this.categories_templates:
			category_entries = {}

			for define in category.selectables_defines():
				selectable = define.selectable()
				identifier = selectable.parse_identifier()

				if not identifier.can_display():
					continue

				keys = ",".join( [ identifier.external_key_for( key, selectable ) for key in define.keys() ] )
				max_length = max( max_length, len( keys ) )

				category_entries.setdefault( identifier, [] ).append( ( define.description(), keys ) )

			for identifier, entries in category_entries.items():
				sections.setdefault( identifier, [] ).append( ( category.description(), entries ) )

		lines = []
		for i in this.overview():
			lines.append( "overview: {0}\n".format( i ) )

		for i in this.usage():
			lines.append( "usage: {0}\n".format( i ) )

		for i in this.explanation():
			lines.append( "{0}\n".format( i ) )

		max_length += 1

		printed_section = False
		for identifier in sorted( sections, key = lambda identifier: identifier.display_order() ):
			lines_elements = sections[ identifier ]

			if printed_section:
				lines.append( "" )

			lines.append( "{0}:".format( identifier.display_name() ) )
			printed_section = True

			for category in lines_elements:
				if 0 < len( category[1] ):
					lines.append( "\t{0}:" .format( category[0] ) )

				for define in category[1]:
					lines.append( ( "\t\t{0:" + str( max_length ) +"}{1}" ).format( define[1] , define[0] ) )

		return "\n".join( lines )

	def run_with( this, run_parameters ):
		print( this.print_string() )

	def __init__( this, categories_templates ):
		this.categories_templates = categories_templates
