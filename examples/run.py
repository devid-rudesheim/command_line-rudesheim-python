#!/opt/homebrew/bin/python3

import rudesheim.command_line as cl

class Null( cl.Option ):
	@classmethod
	def example( this ):
		print( "Disable" )

class Disabled( Null ):
	pass

class Enabled( Null ):
	@classmethod
	def example( this ):
		print( "Enable" )

class Example( cl.OptionCategory ):

	@classmethod
	def options_defines( this ):
		global categories_templates

		return [ Enabled.tie( ( 'e', 'example' ), "for example" ) ]
	
	@classmethod
	def default( this ):
		return Disabled

class Main( cl.OptionForRun ):

	@classmethod
	def run_with( this, categories, arguments ):
		categories[ Example ].example()

class Version( cl.BasicVersion ):

	@classmethod
	def product_name( this ):
		return "Example"

	@classmethod
	def numbers( this ):
		return ( 2, 1, 0 )

class Help( cl.BasicHelp ):

	@classmethod
	def usage( this ):
		return [ Version.product_name() ]

	def __init__( this, categories_templates ):
		super( Help, this ).__init__( categories_templates )


categories_templates = []
class Running( cl.OptionCategory ):

	@classmethod
	def options_defines( this ):
		global categories_templates

		return [ Version.tie( ( 'v', 'version' ), "Print version" ), cl.DefineOfOption( Help( categories_templates ), ( 'h', 'help' ), "Print help" ) ]
	
	@classmethod
	def default( this ):
		return Main

categories_templates = [ Running, Example ]
result = cl.Parser( categories_templates ).parse_from_default()

categories = result[0]
categories[ Running ].run_with( categories, result[1] )
