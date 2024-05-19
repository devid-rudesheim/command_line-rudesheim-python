#!/opt/homebrew/bin/python3

import rudesheim.command_line as cl
import unittest as ut

class Option_0( cl.Option ):
	pass

class Option_1( cl.Option ):
	pass

class Option_2( cl.Option ):
	pass

class Option_3( cl.Option ):

	def values( this ):
		return this.strings

	def __init__( this, strings ):
		this.strings = strings

	@classmethod
	def value_amount( this ):
		return 1

	@classmethod
	def with_values( this, strings ):
		return this( strings )

class Mode_0( cl.Mode ):

	@classmethod
	def options_defines( this ):
		return [ Option_1.tie( ( 'v', 'version' ), "Print version" ), Option_2.tie( ( 'h', 'help' ), "Print help" ) ]
	
	@classmethod
	def default( this ):
		return Option_0

class Mode_1( cl.Mode ):

	@classmethod
	def options_defines( this ):
		return [ Option_3.tie( ( 'd', 'depth' ), "depth" ) ]
	
	@classmethod
	def default( this ):
		return Option_0

class ParserTests( ut.TestCase ):

	def test_0( this ):
		parser = cl.Parser( [] )

		result = parser.parse( [] )

		this.assertEqual( 2, len( result ) )
		this.assertEqual( 0, len( result[0] ) )
		this.assertEqual( 0, len( result[1] ) )

	def test_1( this ):
		parser = cl.Parser( [] )

		arguments = [ 'one', 'two' ]
		result = parser.parse( arguments )

		this.assertEqual( 0, len( result[0] ) )
		this.assertEqual( 2, len( result[1] ) )

		this.assertEqual( arguments, result[1] )

	def test_2( this ):
		parser = cl.Parser( [] )

		with this.assertRaises( cl.UndefinedOptionSpecified ):
			parser.parse( [ "-h" ] )


	def test_3( this ):
		parser = cl.Parser( [ Mode_0 ] )

		with this.assertRaises( cl.OptionIsInConflict ):
			parser.parse( [ "-v", "-v" ] )

	def test_4( this ):
		parser = cl.Parser( [ Mode_0 ] )

		arguments = [ 'one' ]
		result = parser.parse( arguments )

		this.assertEqual( 1, len( result[0] ) )
		this.assertEqual( 1, len( result[1] ) )

		this.assertEqual( arguments, result[1] )

	def test_5( this ):
		parser = cl.Parser( [ Mode_0 ] )

		result = parser.parse( [] )

		this.assertEqual( 1, len( result[0] ) )
		this.assertEqual( 0, len( result[1] ) )

		this.assertEqual( { Mode_0 : Option_0 }, result[0] )

	def test_6( this ):
		parser = cl.Parser( [ Mode_0 ] )

		result = parser.parse( [ "-v" ] )

		this.assertEqual( 1, len( result[0] ) )
		this.assertEqual( 0, len( result[1] ) )

		this.assertEqual( { Mode_0 : Option_1 }, result[0] )

	def test_7( this ):
		parser = cl.Parser( [ Mode_0 ] )

		result = parser.parse( [ "--version" ] )

		this.assertEqual( 1, len( result[0] ) )
		this.assertEqual( 0, len( result[1] ) )

		this.assertEqual( { Mode_0 : Option_1 }, result[0] )

	def test_8( this ):
		parser = cl.Parser( [ Mode_0 ] )
		argument = "value"

		result = parser.parse( [ "--version", argument ] )

		this.assertEqual( 1, len( result[0] ) )
		this.assertEqual( 1, len( result[1] ) )

		this.assertEqual( { Mode_0 : Option_1 }, result[0] )
		this.assertEqual( argument, result[1][0] )

	def test_9( this ):
		parser = cl.Parser( [ Mode_0 ] )

		result = parser.parse( [ "-h" ] )

		this.assertEqual( { Mode_0 : Option_2 }, result[0] )

	def test_10( this ):
		parser = cl.Parser( [ Mode_1 ] )

		argument = "value"
		result = parser.parse( [ "-d", argument ] )

		this.assertEqual( [ argument ], result[0][Mode_1].values() )

	def test_11( this ):
		parser = cl.Parser( [ Mode_0, Mode_1 ] )

		argument = "value"
		result = parser.parse( [ "--help", "--depth", argument ] )

		this.assertEqual( Option_2, result[0][Mode_0] )
		this.assertEqual( [ argument ], result[0][Mode_1].values() )

	def test_12( this ):
		parser = cl.Parser( [ Mode_1, Mode_0 ] )

		argument = "value"
		result = parser.parse( [ "--help", "--depth", argument ] )

		this.assertEqual( Option_2, result[0][Mode_0] )
		this.assertEqual( [ argument ], result[0][Mode_1].values() )

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

class Help_0( cl.BasicHelp ):

	@classmethod
	def usage( this ):
		return [ "example" ]

	def __init__( this, modes_templates ):
		super( Help_0, this ).__init__( modes_templates )


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
					"usage: example",
					"options:",
					"	Mode_0:",
					"		-v,--version Print version",
					"		-h,--help    Print help",
					"	Mode_1:",
					"		-d,--depth   depth"
				)
			),
			Help_0( [ Mode_0, Mode_1 ] ).print_string()
		)

ut.main()
