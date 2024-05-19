import sys
import getopt as go

class BasicException( Exception ):
	pass

class UndefinedOptionSpecified( BasicException ):
	pass

class OptionIsInConflict( BasicException ):
	pass

class DefaultDoesNotExist( BasicException ):
	pass

class ItemForhelp:

	@classmethod
	def description( this ):
		return this.__name__

class DefineOfOption( ItemForhelp ):

	def option( this ):
		return this.option_

	def keys( this ):
		return this.keys_

	def description( this ):
		return this.description_

	def __init__( this, option, keys, description ):
		this.option_ = option
		this.keys_ = keys
		this.description_ = description

class Option( ItemForhelp ):

	@classmethod
	def value_amount( this ):
		return 0

	@classmethod
	def with_values( this, strings ):
		return this

	@classmethod
	def tie( this, keys, description ):
		return DefineOfOption( this, keys, description )

	@classmethod
	def basic_tie( this, keys ):
		return this.tie( keys, this.description() )


class Mode( ItemForhelp ):

	@classmethod
	def options_defines( this ):
		return ()
	
	@classmethod
	def default( this ):
		options = this.options_defines()
		if 0 == len( options ):
			raise DefaultDoesNotExist()

		return options.option()

class KeyDecorator:

	@classmethod
	def convert_string( this, key ):
		return [ "-", "--" ][ 1 != len( key ) ] + key

class ShortKeyDecorator:

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
	return [ ShortKeyDecorator, LongKeyDecorator ][ 1 != len( key ) ]

class Parser:

	def parse( this, arguments ):
		options = {}
		keys_specs = ( [], [] )

		# build lookup table and list for mapping
		for mode in this.modes_templates_:
			for define in mode.options_defines():
				for key in define.keys():
					option = define.option()
					amount = 0 < option.value_amount()

					decorator = key_decorator_for( key )

					key_value = ( mode, option )
					options[ decorator.convert_for_external( key ) ] = key_value

					decorator.select( keys_specs ).append( [ key, decorator.convert_for_spec( key ) ][amount] )

		try:
			result = go.getopt( arguments, "".join( keys_specs[0] ), keys_specs[1] )

			modes = {}
			# for inputs
			for key_value in result[0]:
				define = options[ key_value[0] ]

				mode = define[0]
				if mode in modes:
					raise OptionIsInConflict()

				option = define[1]
				if 0 < option.value_amount():
					option = option.with_values( [ key_value[1] ] )

				modes[ mode ] = option

			# for default value
			for mode in this.modes_templates_:

				if mode in modes:
					continue

				modes[ mode ] = mode.default()

			return ( modes, result[1] )

		except go.GetoptError as exception:

			if 0 < str( exception ).find( "not recognize" ):
				raise UndefinedOptionSpecified() from exception

	def parse_from_default( this ):
		return this.parse( sys.argv[1:] )

	def __init__( this, modes_templates ):
		this.modes_templates_ = modes_templates


class OptionForRun( Option ):

	@classmethod
	def run_with( this, modes, arguments ):
		pass

class OptionForPrint( OptionForRun ):

	@classmethod
	def print_string( this ):
		return ""

	@classmethod
	def run_with( this, modes, arguments ):
		print( this.print_string() )

class BasicVersion( OptionForPrint ):

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

	@classmethod
	def description( this ):
		return "Print Help (this message) and exit"

	@classmethod
	def usage( this ):
		return []

	def print_string( this ):
		max_length = 0
		
		lines_elements = []

		for mode in this.modes_templates:
			line_elements = []

			for define in mode.options_defines():
				keys = ",".join( [ key_decorator_for( key ).convert_for_external( key ) for key in define.keys() ] )

				max_length = max( max_length, len( keys ) )
				line_elements.append( ( define.description(), keys ) )

			lines_elements.append( ( mode.description(), line_elements ) )

		lines = []
		for i in this.usage():
			lines.append( "usage: " + i )


		max_length += 1

		lines.append( "options:" )
		for mode in lines_elements:
			lines.append( "\t{0}:" .format( mode[0] ) )

			for define in mode[1]:
				lines.append( ( "\t\t{0:" + str( max_length ) +"}{1}" ).format( define[1] , define[0] ) )

		return "\n".join( lines )

	def run_with( this, modes, arguments ):
		print( this.print_string() )

	def __init__( this, modes_templates ):
		this.modes_templates = modes_templates
