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

class ExampleMode( cl.Mode ):

	@classmethod
	def options_defines( this ):
		global modes_templates

		return [ Enabled.tie( ( 'e', 'example' ), "for example" ) ]
	
	@classmethod
	def default( this ):
		return Disabled

class Main( cl.OptionForRun ):

	@classmethod
	def run_with( this, modes, arguments ):
		modes[ ExampleMode ].example()

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

	def __init__( this, modes_templates ):
		super( Help, this ).__init__( modes_templates )


modes_templates = []
class RunningMode( cl.Mode ):

	@classmethod
	def options_defines( this ):
		global modes_templates

		return [ Version.tie( ( 'v', 'version' ), "Print version" ), cl.DefineOfOption( Help( modes_templates ), ( 'h', 'help' ), "Print help" ) ]
	
	@classmethod
	def default( this ):
		return Main

modes_templates = [ RunningMode, ExampleMode ]
result = cl.Parser( modes_templates ).parse_from_default()

modes = result[0]
modes[ RunningMode ].run_with( modes, result[1] )
