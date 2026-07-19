#!/usr/bin/env python3

from pathlib import Path
import contextlib
import io
import sys
import unittest as ut

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "lib"))

import rudesheim.command_line as cl
import rudesheim.command_line.private as clp

class Option_0( cl.Option ):
	pass

class Option_1( cl.Option ):
	pass

class Option_2( cl.Option ):
	pass

class Option_3( cl.Option ):

	def value( this ):
		return this.strings

	def __init__( this, strings ):
		this.strings = strings

	@classmethod
	def value_amount( this ):
		return 1

	@classmethod
	def with_value( this, strings ):
		return this( strings )

class Category_0( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ Option_1.tie( ( 'v', 'version' ), "Print version" ), Option_2.tie( ( 'h', 'help' ), "Print help" ) ]
	
	@classmethod
	def default( this ):
		return Option_0

class Category_1( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ Option_3.tie( ( 'd', 'depth' ), "depth" ) ]
	
	@classmethod
	def default( this ):
		return Option_0

class Category_2( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return []
	
	@classmethod
	def default( this ):
		return Option_0

class ParserTests( ut.TestCase ):

	def test_0( this ):
		parser = cl.Parser( [] )

		result = parser.resolve([] )

		this.assertEqual( 0, len( result.categories ) )
		this.assertEqual( 0, len( result.arguments ) )

	def test_1( this ):
		parser = cl.Parser( [] )

		arguments = [ 'one', 'two' ]
		result = parser.resolve(arguments )

		this.assertEqual( 0, len( result.categories ) )
		this.assertEqual( 2, len( result.arguments ) )

		this.assertEqual( arguments, result.arguments )

	def test_2( this ):
		parser = cl.Parser( [] )

		with this.assertRaises( cl.UndefinedOptionSpecified ):
			parser.resolve([ "-h" ] )


	def test_3( this ):
		parser = cl.Parser( [ Category_0 ] )

		with this.assertRaises( cl.OptionIsInConflict ):
			parser.resolve([ "-v", "-v" ] )

	def test_4( this ):
		parser = cl.Parser( [ Category_0 ] )

		arguments = [ 'one' ]
		result = parser.resolve(arguments )

		this.assertEqual( 1, len( result.categories ) )
		this.assertEqual( 1, len( result.arguments ) )

		this.assertEqual( arguments, result.arguments )

	def test_5( this ):
		parser = cl.Parser( [ Category_0 ] )

		result = parser.resolve([] )

		this.assertEqual( 1, len( result.categories ) )
		this.assertEqual( 0, len( result.arguments ) )

		this.assertEqual( { Category_0 : Option_0 }, result.categories )

	def test_6( this ):
		parser = cl.Parser( [ Category_0 ] )

		result = parser.resolve([ "-v" ] )

		this.assertEqual( 1, len( result.categories ) )
		this.assertEqual( 0, len( result.arguments ) )

		this.assertEqual( { Category_0 : Option_1 }, result.categories )

	def test_7( this ):
		parser = cl.Parser( [ Category_0 ] )

		result = parser.resolve([ "--version" ] )

		this.assertEqual( 1, len( result.categories ) )
		this.assertEqual( 0, len( result.arguments ) )

		this.assertEqual( { Category_0 : Option_1 }, result.categories )

	def test_8( this ):
		parser = cl.Parser( [ Category_0 ] )
		argument = "value"

		result = parser.resolve([ "--version", argument ] )

		this.assertEqual( 1, len( result.categories ) )
		this.assertEqual( 1, len( result.arguments ) )

		this.assertEqual( { Category_0 : Option_1 }, result.categories )
		this.assertEqual( argument, result.arguments[0] )

	def test_9( this ):
		parser = cl.Parser( [ Category_0 ] )

		this.assertEqual( { Category_0 : Option_2 }, parser.resolve([ "-h" ] ).categories )

	def test_10( this ):
		parser = cl.Parser( [ Category_1 ] )

		argument = "value"

		this.assertEqual( argument, parser.resolve([ "-d", argument ] ).categories[Category_1].value() )

	def test_11( this ):
		parser = cl.Parser( [ Category_0, Category_1 ] )

		argument = "value"
		result = parser.resolve([ "--help", "--depth", argument ] )

		this.assertEqual( Option_2, result.categories[Category_0] )
		this.assertEqual( argument, result.categories[Category_1].value() )

	def test_12( this ):
		parser = cl.Parser( [ Category_1, Category_0 ] )

		argument = "value"
		result = parser.resolve([ "--help", "--depth", argument ] )

		this.assertEqual( Option_2, result.categories[Category_0] )
		this.assertEqual( argument, result.categories[Category_1].value() )

class Version_0( cl.BasicVersion ):

	@classmethod
	def product_name( this ):
		return "Example"

	@classmethod
	def numbers( this ):
		return ( 2, 1, 0 )

class VersionTests( ut.TestCase ):

	def product_name( this ):
		return "Print version information and exit"

	def test_0( this ):
		this.assertEqual( this.product_name(), Version_0.description() )
		this.assertEqual( this.product_name(), Version_0.basic_tie( [] ).description() )

	def test_1( this ):
		this.assertEqual( "Example, version 2.1.0", Version_0.print_string() )

	def test_2( this ):
		this.assertEqual( "version 1.0", cl.BasicVersion.print_string() )

class Help_1( cl.BasicHelp ):

	@classmethod
	def overview( this ):
		return [ "example overview" ]

	def __init__( this, categories_templates ):
		super().__init__( categories_templates )


class Help_2( cl.BasicHelp ):

	@classmethod
	def usage( this ):
		return [ "example usage" ]

	def __init__( this, categories_templates ):
		super().__init__( categories_templates )

class Help_3( cl.BasicHelp ):

	@classmethod
	def explanation( this ):
		return [ "example explanation" ]

	def __init__( this, categories_templates ):
		super().__init__( categories_templates )

class Help_0( Help_1, Help_2, Help_3 ):

	@classmethod
	def overview( this ):
		return [ "example overview" ]

	@classmethod
	def usage( this ):
		return [ "example usage" ]

	@classmethod
	def explanation( this ):
		return [ "example explanation" ]

	def __init__( this, categories_templates ):
		super().__init__( categories_templates )

# --- fixtures for the options:/commands: split (single level) ---

class HelpCommand_0( cl.Command ):
	pass

class HelpCommand_1( cl.Command ):
	pass

class Category_3( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ HelpCommand_0.tie( ( "start", ), "start the thing" ), HelpCommand_1.tie( ( "stop", ), "stop the thing" ) ]

	@classmethod
	def default( this ):
		return cl.Terminal

# --- fixtures for the options:/commands: split across two nested levels ---
# root: "container" (a Command) sits in commands:, alongside plain options:
# nested: Container.parser_define() declares its own options:/commands: one level down

class SubLs( cl.Command ):
	pass

class SubStart( cl.Command ):
	pass

class SubCommandCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ SubLs.tie( ( "ls", ), "list" ), SubStart.tie( ( "start", ), "start" ) ]

	@classmethod
	def default( this ):
		return cl.Terminal

class SubOptionCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ Option_2.tie( ( "h", "help" ), "Print help" ) ]

	@classmethod
	def default( this ):
		return Option_0

class Container( cl.Command ):

	@classmethod
	def parser_define( this ):
		return cl.Parser( [ SubOptionCategory, SubCommandCategory ] )

class RootCommandCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ Container.tie( ( "container", ), "manage containers" ) ]

	@classmethod
	def default( this ):
		return Container


class HelpTests( ut.TestCase ):

	def product_name( this ):
		return "Print Help (this message) and exit"

	def test_0( this ):
		this.assertEqual( this.product_name(), Help_0.description() )
		this.assertEqual( this.product_name(), Help_0.basic_tie( [] ).description() )

	def test_1( this ):
		this.assertEqual \
		(
		 	"\n".join \
			(
			 	(
					"overview: example overview",
					"",
					"usage: example usage",
					"",
					"example explanation",
					"",
					"options:",
					"	Category_0:",
					"		-v,--version Print version",
					"		-h,--help    Print help",
					"	Category_1:",
					"		-d,--depth   depth"
				)
			),
			Help_0( [ Category_0, Category_1 ] ).print_string()
		)

	def test_2( this ):
		this.assertEqual \
		(
		 	"\n".join \
			(
			 	(
					"options:",
					"	Category_0:",
					"		-v,--version Print version",
					"		-h,--help    Print help",
					"	Category_1:",
					"		-d,--depth   depth"
				)
			),
			cl.BasicHelp( [ Category_0, Category_1 ] ).print_string()
		)

	def test_3( this ):
		this.assertEqual \
		(
		 	"\n".join \
			(
			 	(
					"overview: example overview",
					"",
					"options:",
					"	Category_0:",
					"		-v,--version Print version",
					"		-h,--help    Print help",
				)
			),
			Help_1( [ Category_0 ] ).print_string()
		)

	def test_4( this ):
		this.assertEqual \
		(
		 	"\n".join \
			(
			 	(
					"usage: example usage",
					"",
					"options:",
					"	Category_1:",
					"		-d,--depth depth"
				)
			),
			Help_2( [ Category_1 ] ).print_string()
		)

	def test_5( this ):
		this.assertEqual \
		(
		 	"\n".join \
			(
			 	(
					"example explanation",
					"",
					"options:",
					"	Category_0:",
					"		-v,--version Print version",
					"		-h,--help    Print help",
					"	Category_1:",
					"		-d,--depth   depth"
				)
			),
			Help_3( [ Category_0, Category_1 ] ).print_string()
		)


	def test_6( this ):
		this.assertEqual \
		(
		 	"\n".join \
			(
			 	(
				)
			),
			cl.BasicHelp( [ Category_2 ] ).print_string()
		)

	def test_7( this ):
		this.assertEqual \
		(
		 	"\n".join \
			(
			 	(
					"options:",
					"	Category_1:",
					"		-d,--depth depth"
				)
			),
			cl.BasicHelp( [ Category_1, Category_2 ] ).print_string()
		)

	def test_options_and_commands_split_at_a_single_level( this ):
		this.assertEqual \
		(
		 	"\n".join \
			(
			 	(
					"options:",
					"	Category_0:",
					"		-v,--version Print version",
					"		-h,--help    Print help",
					"",
					"commands:",
					"	Category_3:",
					"		start        start the thing",
					"		stop         stop the thing"
				)
			),
			cl.BasicHelp( [ Category_0, Category_3 ] ).print_string()
		)

	def test_options_and_commands_split_across_two_nested_levels( this ):
		# Root level: Category_0 (Options) sits alongside RootCommandCategory
		# (a Command-type category whose only entry is the "container"
		# subcommand itself) - so "container" lands in commands:, not
		# options:.
		this.assertEqual \
		(
		 	"\n".join \
			(
			 	(
					"options:",
					"	Category_0:",
					"		-v,--version Print version",
					"		-h,--help    Print help",
					"",
					"commands:",
					"	RootCommandCategory:",
					"		container    manage containers"
				)
			),
			cl.BasicHelp( [ Category_0, RootCommandCategory ] ).print_string()
		)

		# One level down: Container.parser_define() declares its own,
		# independent options:/commands: split (SubOptionCategory's -h/--help
		# vs. SubCommandCategory's ls/start) - built from a completely
		# separate categories_templates list, same as a real "container
		# --help" would use.
		this.assertEqual \
		(
		 	"\n".join \
			(
			 	(
					"options:",
					"	SubOptionCategory:",
					"		-h,--help Print help",
					"",
					"commands:",
					"	SubCommandCategory:",
					"		ls        list",
					"		start     start"
				)
			),
			cl.BasicHelp( [ SubOptionCategory, SubCommandCategory ] ).print_string()
		)

class Verbose( cl.Option ):
	pass

class Silent( cl.Option ):
	pass

class GlobalCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ Verbose.tie( ( "v", "verbose" ), "verbose" ) ]

	@classmethod
	def default( this ):
		return Silent

class BuildDebug( cl.Option ):
	pass

class BuildRelease( cl.Option ):
	pass

class BuildModeCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ BuildRelease.tie( ( "r", "release" ), "release" ) ]

	@classmethod
	def default( this ):
		return BuildDebug

class InstallDepth( cl.Option ):

	def value( this ):
		return this.text

	def __init__( this, text ):
		this.text = text

	@classmethod
	def value_amount( this ):
		return 1

	@classmethod
	def with_value( this, strings ):
		return this( strings )

class InstallDepthCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ InstallDepth.tie( ( "d", "depth" ), "depth" ) ]

	@classmethod
	def default( this ):
		return InstallDepth( "1" )

class Main( cl.Command ):
	pass

class Build( cl.Command ):

	@classmethod
	def parser_define( this ):
		return cl.Parser( [ BuildModeCategory ] )

class Install( cl.Command ):

	@classmethod
	def parser_define( this ):
		return cl.Parser( [ InstallDepthCategory ] )

class RunningCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ Build.tie( ( "build", ), "build" ), Install.tie( ( "install", ), "install" ) ]

	@classmethod
	def default( this ):
		return Main

class CommandParserTests( ut.TestCase ):

	def test_0( this ):
		parser = cl.Parser( [ RunningCategory, GlobalCategory ] )
		result = parser.resolve([ "build", "--release", "target-a" ] )

		this.assertEqual( Build, result.categories[ RunningCategory ] )
		this.assertEqual( BuildRelease, result.categories[ BuildModeCategory ] )
		this.assertEqual( Silent, result.categories[ GlobalCategory ] )
		this.assertEqual( [ "target-a" ], result.arguments )

	def test_1( this ):
		parser = cl.Parser( [ RunningCategory, GlobalCategory ] )
		result = parser.resolve([ "--verbose", "install", "--depth", "3", "pkg-a" ] )

		this.assertEqual( Install, result.categories[ RunningCategory ] )
		this.assertEqual( "3", result.categories[ InstallDepthCategory ].value() )
		this.assertEqual( Verbose, result.categories[ GlobalCategory ] )
		this.assertEqual( [ "pkg-a" ], result.arguments )

	def test_2( this ):
		parser = cl.Parser( [ RunningCategory, GlobalCategory ] )
		result = parser.resolve([ "pkg-a" ] )

		this.assertEqual( Main, result.categories[ RunningCategory ] )
		this.assertEqual( Silent, result.categories[ GlobalCategory ] )
		this.assertEqual( [ "pkg-a" ], result.arguments )

class Detach( cl.Option ):
	pass

class Foreground( cl.Option ):
	pass

class DetachCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ Detach.tie( ( "d", "detach" ), "detach" ) ]

	@classmethod
	def default( this ):
		return Foreground

class Up( cl.Command ):

	@classmethod
	def parser_define( this ):
		return cl.Parser( [ DetachCategory ] )

	@classmethod
	def run_with( this, run_parameters ):
		run_parameters.user_datas.append( ( "up", run_parameters.categories[ DetachCategory ], list( run_parameters.arguments ) ) )
		return "up-ran"

class ComposeSubcommand( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ Up.tie( ( "up", ), "up" ) ]

	@classmethod
	def default( this ):
		return cl.Terminal

class Compose( cl.Command ):

	@classmethod
	def parser_define( this ):
		return cl.Parser( [ ComposeSubcommand ] )

	@classmethod
	def run_with( this, run_parameters ):
		run_parameters.user_datas.append( ( "compose", run_parameters.categories[ ComposeSubcommand ], list( run_parameters.arguments ) ) )
		return "compose-ran"

class Context( cl.Option ):

	def value( this ):
		return this.text

	def __init__( this, text ):
		this.text = text

	@classmethod
	def value_amount( this ):
		return 1

	@classmethod
	def with_value( this, strings ):
		return this( strings )

class ContextCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ Context.tie( ( "c", "context" ), "context" ) ]

	@classmethod
	def default( this ):
		return Context( "default" )

class RootSubcommand( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ Compose.tie( ( "compose", ), "compose" ) ]

	@classmethod
	def default( this ):
		return Compose

class TerminalDispatchTests( ut.TestCase ):

	def test_parse_reaches_deepest_matched_leaf_and_calls_its_run_with( this ):
		log = []
		parser = cl.Parser( [ ContextCategory, RootSubcommand ] )

		this.assertEqual( "up-ran", parser.parse( [ "--context", "prod", "compose", "up", "-d", "web", "db" ], log ) )
		this.assertEqual( 1, len( log ) )
		this.assertEqual( ( "up", Detach, [ "web", "db" ] ), log[0] )

	def test_global_category_survives_recursion_into_local_scope( this ):
		parser = cl.Parser( [ ContextCategory, RootSubcommand ] )

		state = parser.resolve([ "--context", "prod", "compose", "up" ] )

		this.assertEqual( "prod", state.categories[ ContextCategory ].value() )
		this.assertEqual( Compose, state.categories[ RootSubcommand ] )
		this.assertEqual( Up, state.categories[ ComposeSubcommand ] )

	def test_fallback_terminal_is_nearest_matched_ancestor( this ):
		log = []
		parser = cl.Parser( [ ContextCategory, RootSubcommand ] )

		this.assertEqual( "compose-ran", parser.parse( [ "--context", "prod", "compose" ], log ) )
		this.assertEqual( 1, len( log ) )
		# ComposeSubcommand.default() は cl.Terminal (潜らず親へ委譲する印) なので、
		# categories には Terminal が入り、Compose 自身の run_with が実行される。
		this.assertEqual( ( "compose", cl.Terminal, [] ), log[0] )

	def test_root_default_recurses_instead_of_index_error( this ):
		# RootSubcommand は何も型入力が無いと match しない。RootSubcommand.default()
		# は Compose (実在の Command) なので、以前は categories に記録されるだけで
		# terminals には反映されず IndexError になっていたが、default() で埋めた値にも
		# decided_for が通るようになったことで、ここでも同じ再帰が起き Compose.run_with
		# まで届く。
		log = []
		parser = cl.Parser( [ ContextCategory, RootSubcommand ] )

		this.assertEqual( "compose-ran", parser.parse( [], log ) )
		this.assertEqual( 1, len( log ) )
		this.assertEqual( ( "compose", cl.Terminal, [] ), log[0] )

class AlwaysCommand( cl.Command ):

	@classmethod
	def run_with( this, run_parameters ):
		return ( "always-ran", list( run_parameters.arguments ) )

class AlwaysCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return []

	@classmethod
	def default( this ):
		return AlwaysCommand

class DecidedForTests( ut.TestCase ):

	def test_terminal_decided_for_is_inert_no_op( this ):
		state = clp.ParseState( cl.RunParameters( [], {}, [] ), [], [] )

		this.assertIs( state, cl.Terminal.parse_identifier().decided_for( None, state, cl.Terminal ) )

	def test_category_with_no_declared_selectables_always_dispatches_to_its_default( this ):
		# selectables_defines() が [] だと明示的な match が原理上不可能なので、
		# default() を実在の Command に override すれば、何を型入力しても常に
		# そのCommandへ落ちる - Quick Start の Running/Main と同じ縮退形。
		this.assertEqual \
		(
			( "always-ran", [ "compose", "up", "web" ] ),
			cl.Parser( [ AlwaysCategory ] ).parse( [ "compose", "up", "web" ] )
		)

class Plain( cl.Selectable ):
	pass

class PlainCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ Plain.tie( ( 'p', ), "plain selectable" ) ]

	@classmethod
	def default( this ):
		return Plain

class NoOverrideDescription( cl.Option ):
	pass

class NeedsValueWithoutOverride( cl.Option ):

	def __init__( this, text ):
		this.text = text

	@classmethod
	def value_amount( this ):
		return 1

class EmptyCategoryWithBaseDefault( cl.SelectableCategory ):
	pass

class OptionOnlyCategoryWithBaseDefault( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ NoOverrideDescription.tie( ( 'n', ), "no override" ) ]

class SelectableProtocolTests( ut.TestCase ):

	def test_bare_selectable_is_reachable_only_via_default( this ):
		this.assertEqual( Plain, cl.Parser( [ PlainCategory ] ).resolve( [] ).categories[ PlainCategory ] )

	def test_bare_selectable_contributes_no_getopt_spec_so_cannot_be_typed( this ):
		with this.assertRaises( cl.UndefinedOptionSpecified ):
			cl.Parser( [ PlainCategory ] ).resolve( [ '-p' ] )

	def test_item_for_help_default_description_is_class_name( this ):
		this.assertEqual( 'NoOverrideDescription', NoOverrideDescription.description() )

	def test_with_value_default_returns_class_itself( this ):
		this.assertEqual( NeedsValueWithoutOverride, NeedsValueWithoutOverride.with_value( [ 'ignored' ] ) )

	def test_selectable_category_default_raises_when_no_selectables( this ):
		with this.assertRaises( cl.DefaultDoesNotExist ):
			EmptyCategoryWithBaseDefault.default()

	def test_selectable_category_default_returns_first_selectable_when_unoverridden( this ):
		this.assertEqual( NoOverrideDescription, OptionOnlyCategoryWithBaseDefault.default() )

	def test_define_of_option_option_is_alias_for_selectable( this ):
		define = cl.DefineOfOption( NoOverrideDescription, ( 'n', ), "no override" )
		this.assertEqual( define.selectable(), define.option() )

class SilentByDefault( cl.Option ):
	pass

class PureOptionCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return []

	@classmethod
	def default( this ):
		return SilentByDefault

class NoRunWithCommand( cl.Command ):
	pass

class NoRunWithCommandCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ NoRunWithCommand.tie( ( 'noop', ), "noop" ) ]

	@classmethod
	def default( this ):
		return NoRunWithCommand

class LoggingCommand( cl.Command ):

	@classmethod
	def run_with( this, run_parameters ):
		run_parameters.user_datas.append( 'ran' )
		return run_parameters.user_datas

class LoggingCommandCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ LoggingCommand.tie( ( 'log', ), "log" ) ]

	@classmethod
	def default( this ):
		return LoggingCommand

class RunWithDispatchTests( ut.TestCase ):

	def test_selectable_run_with_raises_when_unoverridden( this ):
		with this.assertRaises( cl.RunWithNotImplemented ):
			SilentByDefault.run_with( None )

	def test_parse_raises_run_with_not_implemented_for_unoverridden_command( this ):
		with this.assertRaises( cl.RunWithNotImplemented ):
			cl.Parser( [ NoRunWithCommandCategory ] ).parse( [ 'noop' ] )

	def test_parse_raises_index_error_when_no_command_category_at_all( this ):
		# terminals は Command.parse_with だけが埋める。Command系categoryが1つも
		# 無い（=Optionだけの）Parserで.parse()すると末端が確定せず、既知の未解決課題
		# としてIndexErrorになる。
		with this.assertRaises( IndexError ):
			cl.Parser( [ PureOptionCategory ] ).parse( [] )

	def test_option_for_print_run_with_prints_string( this ):
		buffer = io.StringIO()
		with contextlib.redirect_stdout( buffer ):
			Version_0.run_with( None )
		this.assertEqual( "Example, version 2.1.0\n", buffer.getvalue() )

	def test_basic_help_run_with_prints_string( this ):
		instance = Help_0( [ Category_0, Category_1 ] )
		buffer = io.StringIO()
		with contextlib.redirect_stdout( buffer ):
			instance.run_with( None )
		this.assertEqual( instance.print_string() + "\n", buffer.getvalue() )

	def test_user_datas_default_does_not_leak_across_separate_calls( this ):
		first = cl.Parser( [ LoggingCommandCategory ] ).parse( [ 'log' ] )
		second = cl.Parser( [ LoggingCommandCategory ] ).parse( [ 'log' ] )

		this.assertEqual( [ 'ran' ], first )
		this.assertEqual( [ 'ran' ], second )

	def test_parse_from_default_reads_sys_argv( this ):
		original_argv = sys.argv
		sys.argv = [ 'prog', 'log' ]
		try:
			result = cl.Parser( [ LoggingCommandCategory ] ).parse_from_default()
		finally:
			sys.argv = original_argv

		this.assertEqual( [ 'ran' ], result )

class ParserEdgeCaseTests( ut.TestCase ):

	def test_resolve_still_fills_defaults_when_every_category_defines_nothing( this ):
		# selectables_defines() が全カテゴリで [] でも、default() 埋めは省略され
		# ない（かつて getopt 由来の selectables が空だと丸ごと短絡し、default()
		# が一切埋まらないバグがあった）。
		result = cl.Parser( [ Category_2 ] ).resolve( [ 'leftover' ] )

		this.assertEqual( { Category_2 : Option_0 }, result.categories )
		this.assertEqual( [ 'leftover' ], result.arguments )

	def test_missing_required_value_raises_option_value_is_missing( this ):
		# "requires argument" な GetoptError（値必須オプションに値が無い）は
		# OptionValueIsMissing に変換される。
		with this.assertRaises( cl.OptionValueIsMissing ):
			cl.Parser( [ Category_1 ] ).resolve( [ '-d' ] )

	def test_unexpected_value_on_no_value_option_raises_option_is_malformed( this ):
		# "requires argument" にも "not recognize" にも該当しない GetoptError
		# （例: 値を取らない --help に --help=x として値を渡した場合）は
		# OptionValueIsMissing ではなく、汎用の OptionIsMalformed に変換される。
		with this.assertRaises( cl.OptionIsMalformed ):
			cl.Parser( [ Category_0 ] ).resolve( [ '--help=x' ] )

class DuplicateKeyOption_0( cl.Option ):
	pass

class DuplicateKeyOption_1( cl.Option ):
	pass

class DuplicateKeyCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ DuplicateKeyOption_0.tie( ( "a", ), "first" ), DuplicateKeyOption_1.tie( ( "a", ), "second" ) ]

class DuplicateKeyCategory_A( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ DuplicateKeyOption_0.tie( ( "a", ), "first" ) ]

class DuplicateKeyCategory_B( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ DuplicateKeyOption_1.tie( ( "a", ), "second" ) ]

class MixedKindCommand( cl.Command ):
	pass

class MixedCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ DuplicateKeyOption_0.tie( ( "apply", ), "apply" ), MixedKindCommand.tie( ( "deploy", ), "deploy" ) ]

class ParserValidationTests( ut.TestCase ):

	def test_duplicate_key_within_one_category_raises_key_is_duplicated( this ):
		# 同一category内で同じkeyを二重にtieすると、1回のgetopt呼び出しを共有する
		# 単一lookupテーブル (Parser._resolve() 内) が黙って後勝ち上書きされてしまう
		# ため、構築時に弾く。
		with this.assertRaises( cl.KeyIsDuplicated ):
			cl.Parser( [ DuplicateKeyCategory ] )

	def test_duplicate_key_across_two_categories_raises_key_is_duplicated( this ):
		# 別categoryどうしでも、同一Parserレベルでは1回のgetopt呼び出しを共有する
		# ため同じ危険がある - category内かcategory跨ぎかは区別しない。
		with this.assertRaises( cl.KeyIsDuplicated ):
			cl.Parser( [ DuplicateKeyCategory_A, DuplicateKeyCategory_B ] )

	def test_option_and_command_mixed_in_one_category_raises_category_is_mixed( this ):
		# Option.parse_with は同一categoryへの二重代入を OptionIsInConflict で
		# 検出するが、Command.parse_with には対称のチェックがない。1つの
		# category に Option と Command を混在させると、マッチした Command が
		# 黙って既に決まっていた Option を上書きしてしまう - それを構築時に防ぐ。
		with this.assertRaises( cl.CategoryIsMixed ):
			cl.Parser( [ MixedCategory ] )

	def test_reusing_a_key_at_a_nested_level_does_not_raise( this ):
		# "h"/"help" はroot (Category_0) と Container.parser_define() 配下
		# (SubOptionCategory) の両方で使われているが、getopt は最初の非オプション
		# 引数 (サブコマンドtoken) で止まり、ネストした Parser は独立に構築・
		# 検証されるため、階層をまたいだ衝突は起こり得ない。
		cl.Parser( [ Category_0, RootCommandCategory ] )
		Container.parser_define()

class RequiredOption_0( cl.Option ):
	pass

class RequiredOptionCategory( cl.RequiredCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ RequiredOption_0.tie( ( 'a', 'apply' ), "apply changes" ) ]

class RequiredCommand_0( cl.Command ):
	pass

class RequiredCommandCategory( cl.RequiredCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ RequiredCommand_0.tie( ( 'build', ), "build" ) ]

class RequiredCategoryTests( ut.TestCase ):

	def test_omitted_option_category_raises_selectable_is_omitted( this ):
		with this.assertRaises( cl.SelectableIsOmitted ):
			cl.Parser( [ RequiredOptionCategory ] ).resolve( [] )

	def test_omitted_command_category_raises_selectable_is_omitted( this ):
		# Option/Command どちらの種類のカテゴリでも、種類による分岐なしに
		# 同じ default() のタイミングで検出できることを確認する。
		with this.assertRaises( cl.SelectableIsOmitted ):
			cl.Parser( [ RequiredCommandCategory ] ).resolve( [] )

	def test_explicit_selection_does_not_raise( this ):
		run_parameters = cl.Parser( [ RequiredOptionCategory ] ).resolve( [ '-a' ] )
		this.assertEqual( RequiredOption_0, run_parameters.categories[ RequiredOptionCategory ] )

	def test_exception_carries_offending_category( this ):
		try:
			cl.Parser( [ RequiredOptionCategory ] ).resolve( [] )
			this.fail( "expected SelectableIsOmitted" )
		except cl.SelectableIsOmitted as exception:
			this.assertEqual( RequiredOptionCategory, exception.category )

class DepthChoice( cl.Option ):

	def value( this ):
		return this.text

	def __init__( this, text ):
		this.text = text

	@classmethod
	def value_amount( this ):
		return 1

	@classmethod
	def with_value( this, strings ):
		return this( strings )

	@classmethod
	def value_completions( this, prefix ):
		return ( "small", "medium", "large" )

class DepthChoiceCategory( cl.SelectableCategory ):

	@classmethod
	def selectables_defines( this ):
		return [ DepthChoice.tie( ( "d", "depth" ), "depth choice" ) ]

	@classmethod
	def default( this ):
		return DepthChoice( "small" )

class CompletionTests( ut.TestCase ):

	def test_empty_prefix_returns_every_top_level_candidate( this ):
		parser = cl.Parser( [ Category_0 ] )

		this.assertEqual( [ "-v", "--version", "-h", "--help" ], parser.complete( [] ) )

	def test_candidates_are_filtered_by_the_partial_word_being_completed( this ):
		parser = cl.Parser( [ Category_0 ] )

		this.assertEqual( [ "--version" ], parser.complete( [ "--v" ] ) )

	def test_unmatched_key_yields_no_candidates( this ):
		parser = cl.Parser( [ Category_0 ] )

		this.assertEqual( [], parser.complete( [ "--nope", "" ] ) )

	def test_command_token_descends_into_its_own_parser_define_for_completion( this ):
		parser = cl.Parser( [ RunningCategory, GlobalCategory ] )

		this.assertEqual( [ "-r", "--release" ], parser.complete( [ "build", "" ] ) )

	def test_unmatched_subcommand_token_yields_no_candidates( this ):
		parser = cl.Parser( [ RunningCategory, GlobalCategory ] )

		this.assertEqual( [], parser.complete( [ "frobnicate", "" ] ) )

	def test_value_taking_option_consumes_its_value_token_then_stays_at_the_same_level( this ):
		parser = cl.Parser( [ RunningCategory, GlobalCategory ] )

		this.assertEqual( [ "-d", "--depth" ], parser.complete( [ "install", "--depth", "3", "" ] ) )

	def test_default_value_completions_is_empty( this ):
		parser = cl.Parser( [ Category_1 ] )

		this.assertEqual( [], parser.complete( [ "--depth", "" ] ) )

	def test_value_completions_used_when_flag_is_the_last_completed_token( this ):
		parser = cl.Parser( [ DepthChoiceCategory ] )

		this.assertEqual( [ "medium" ], parser.complete( [ "--depth", "m" ] ) )

	def test_value_completions_with_empty_prefix_returns_every_choice( this ):
		parser = cl.Parser( [ DepthChoiceCategory ] )

		this.assertEqual( [ "small", "medium", "large" ], parser.complete( [ "--depth", "" ] ) )

if __name__ == "__main__":
	ut.main()
