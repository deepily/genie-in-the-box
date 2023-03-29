import json
import os

def get_name_value_pairs( arg_list ):

    """
    Parses a list of strings -- name=value -- into dictionary format { "name":"value" }

    NOTE: Only the 1st element, the name of the class called is exempt from parsing

    :raises: ValueError if any but the 1st element is not of the format: 'name=value'

    :param arg_list: Space delimited input from CLI

    :return: dictionary of name=value pairs
    """

    # Quick sanity check. Do we have anything to iterate?
    print( "Length of arg_list [{}]".format( len( arg_list ) ) )
    if len( arg_list ) <= 1: return { }
    
    name_value_pairs = { }

    for i, arg in enumerate( arg_list ):

        print( "[{0}]th arg = [{1}]... ".format( i, arg_list[ i ] ), end="" )

        if "=" in arg:
            pair = arg.split( "=" )
            name_value_pairs[ pair[ 0 ] ] = pair[ 1 ]
            print( "done!" )
        else:
            print( "SKIPPING, name=value format not found" )

    print()
    print( "Name value dictionary pairs:", end="\n\n" )

    # get max width for right justification
    max_len = max( [ len( key ) for key in name_value_pairs.keys() ] ) + 1

    # iterate keys and print values w/ this format:
    #       [foo] = [bar]
    # [flibberty] = [jibbet]
    names = list( name_value_pairs.keys() )
    names.sort()

    for name in names:
        print( "{0}] = [{1}]".format( ("[" + name).rjust( max_len, " " ), name_value_pairs[ name ] ) )
    print()

    return name_value_pairs

# Load a plain text file as a list of lines.
def get_file_as_list( path, lower_case=False ):
    
    with open( path, "r" ) as file:
        lines = file.readlines()
        
    if lower_case:
        lines = [ line.lower() for line in lines ]
        
    return lines

def get_file_as_string( path ):

    with open( path, "r" ) as file:
        return file.read()
    
def get_file_as_json( path ):
    
    with open( path, "r" ) as file:
        return json.load( file )
   
def get_file_as_dictionary( path, lower_case=False, debug=False ):
    
    lines = get_file_as_list( path, lower_case=lower_case )

    lines.sort()

    lines_as_dict = { }
    # lines_as_dict[ "space" ] = " "

    for lines in lines:

        pair = lines.strip().split( " = " )
        if len( pair ) > 1:
            if debug: print( "[{}] = [{}]".format( pair[ 0 ], pair[ 1 ].strip() ) )
            lines_as_dict[ pair[ 0 ] ] = pair[ 1 ].strip()
        else:
            if debug: print( "ERROR: [{}]".format( pair[ 0 ] ) )
    
    return lines_as_dict

# lines_dict = get_lines_as_dictionary( "conf/translation-dictionary.txt" )
# print( lines_dict )
#
# lines = get_file_as_list( "conf/translation-dictionary.txt" )
# lines.sort()
#
# punctuation_dict = { }
# punctuation_dict[ "space" ] = " "
#
# for lines in lines:
#
#     pair = lines.strip().split( " = " )
#     if len( pair ) > 1:
#         print( "[{}] = [{}]".format( pair[ 0 ], pair[ 1 ].strip() ) )
#         punctuation_dict[ pair[ 0 ] ] = pair[ 1 ].strip()
#     else:
#         print( "ERROR: [{}]".format( pair[ 0 ] ) )
#
# print()
# print( punctuation_dict, end="\n\n" )
#
# print( punctuation_dict.keys() )
# def get_titles( modes_dict ):
#
#     titles = [ ]
#     for key in modes_dict.keys():
#         titles.append( modes_dict[ key ][ "title" ] )
#
#     return titles
#
# def get_titles_to_methods_dict( modes_dict ):
#
#     title_to_methods_dict = { }
#     for key in modes_dict.keys():
#         title_to_methods_dict[ modes_dict[ key ][ "title" ] ] = modes_dict[ key ][ "method_name" ]
#
#     return title_to_methods_dict
#
# print( os.getcwd() )
# modes_dict = get_file_as_json( "conf/modes.json" )
#
# modes_list = list( modes_dict.keys() )
#
# print( modes_list )
# print( type( modes_list ) )
#
# print( modes_list.index( "transcribe_and_clean_python" ) )
# print( modes_list.index( "g00" ) )

# print( modes_dict.keys() )
# print( modes_dict.values() )
#
# print( get_titles( modes_dict ) )
# print( get_titles_to_methods_dict( modes_dict ) )

# Create a method that reads in a JSON file containing chatgpt prompts and populates the dictionary with it.

prompts = get_file_as_dictionary( "conf/prompts.txt" )
for key in prompts.keys():
    print( "[{}] = [{}]".format( key, prompts[ key ] ) )
