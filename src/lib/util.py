import json
import os
import time
import regex as re

debug = False

def init( d ):
    
    global debug
    debug = d

def get_name_value_pairs( arg_list, debug=False ):
    
    """
    Parses a list of strings -- name=value -- into dictionary format { "name":"value" }

    NOTE: Only the 1st element, the name of the class called is exempt from parsing

    :raises: ValueError if any but the 1st element is not of the format: 'name=value'

    :param arg_list: Space delimited input from CLI

    :return: dictionary of name=value pairs
    """
    
    # Quick sanity check. Do we have anything to iterate?
    if debug: print( "Length of arg_list [{}]".format( len( arg_list ) ) )
    if len( arg_list ) <= 1: return { }
    
    name_value_pairs = { }
    
    for i, arg in enumerate( arg_list ):
        
        if debug: print( "[{0}]th arg = [{1}]... ".format( i, arg_list[ i ] ), end="" )
        
        if "=" in arg:
            pair = arg.split( "=" )
            name_value_pairs[ pair[ 0 ] ] = pair[ 1 ]
            if debug: print( "done!" )
        else:
            if debug: print( "SKIPPING, name=value format not found" )
    
    if debug: print()
    if debug: print( "Name value dictionary pairs:", end="\n\n" )
    
    # get max width for right justification
    max_len = max( [ len( key ) for key in name_value_pairs.keys() ] ) + 1
    
    # iterate keys and print values w/ this format:
    #       [foo] = [bar]
    # [flibberty] = [jibbet]
    names = list( name_value_pairs.keys() )
    names.sort()
    
    for name in names:
        if debug: print( "{0}] = [{1}]".format( ("[" + name).rjust( max_len, " " ), name_value_pairs[ name ] ) )
    if debug: print()
    
    return name_value_pairs


# Load a plain text file as a list of lines.
def get_file_as_list( path, lower_case=False, clean=False ):
    with open( path, "r" ) as file:
        lines = file.readlines()
    
    if lower_case:
        lines = [ line.lower() for line in lines ]
        
    if clean:
        lines = [ line.strip() for line in lines ]
    
    return lines


def get_file_as_string( path ):
    with open( path, "r" ) as file:
        return file.read()


def get_file_as_json( path ):
    with open( path, "r" ) as file:
        return json.load( file )


def get_file_as_dictionary( path, lower_case=False, omit_comments=True, debug=False ):
    # ¡OJO! The pipe symbol is a reserved character used to delimit white space. See the keywords "space" or "| at |" below.
    
    lines = get_file_as_list( path, lower_case=lower_case )
    
    lines_as_dict = { }
    
    # Delete the first and last type symbols if they're there
    pipe_regex = re.compile( "^\||\|$" )
    
    for line in lines:
        
        # Skip comments: if a line starts with # or // then skip it
        if omit_comments and (line.startswith( "#" ) or line.startswith( "//" )):
            continue
        
        pair = line.strip().split( " = " )
        if len( pair ) > 1:
            if debug: print( "[{}] = [{}]".format( pair[ 0 ], pair[ 1 ] ) )
            # Only pull pipes after the key and values have been stripped.
            p0 = pipe_regex.sub( "", pair[ 0 ].strip() )
            p1 = pipe_regex.sub( "", pair[ 1 ].strip() )
            lines_as_dict[ p0 ] = p1
        else:
            if debug: print( "ERROR: [{}]".format( pair[ 0 ] ) )
    
    return lines_as_dict

def print_banner( msg, expletive=False, chunk="¡@#!-$?%^_¿", end="\n\n", prepend_nl=False, flex=False ):

    """
    Prints message to console w/ 'header'/horizontal lines as brackets

    :param expletive: Do you want a fancy error string, like in the cartoons?

    :param chunk: Allows caller to use their own expletives string

    :param end: String representation of multiple or no newline characters, just like in print( "foo", end="\n\n" )

    :param msg: What do you want to print to the console?

    :param prepend_nl: Insert a NL char before printing the banner

    :param flex: Adapt bar line length to the length of message? Defaults to False

    :return: None, prints to console
    """
    if prepend_nl: print()

    max_len = 120
    if expletive:

        bar_str = ""
        while len( bar_str ) < max_len:
            bar_str += chunk

    elif flex:

        # Get max length of string, Splitting onCharacters
        bar_len = max( [ len( line ) for line in msg.split( "\n" ) ] + [ max_len ] ) + 2
        print( bar_len )
        bar_str = ""
        while len( bar_str ) < bar_len:
            bar_str += "-"

    else:

        bar_str = ""
        while len( bar_str ) < max_len:
            bar_str += "-"
        # bar_str = "----------------------------------------------------------------------------------------------------"

    print( bar_str )
    if expletive:
        print( chunk )
        print( chunk, msg )
        print( chunk )
    else:
        print( "-", msg )
    print( bar_str, end=end )
    
def get_project_root_path():
    
    """
    Returns the path to the root of the project.
    
    If we're running in a docker container, we need to set the project root to the docker container's root. Otherwise,
    we can just use the working directory specified in the environment variable.
    :return:
    """
    
    if debug:
        print( "GENIE_IN_THE_BOX_ROOT [{}]".format( os.getenv( "GENIE_IN_THE_BOX_ROOT" ) ) )
        print( "          os.getcwd() [{}]".format( os.getcwd() ) )
        
    if "GENIE_IN_THE_BOX_ROOT" in os.environ:
        return os.environ[ "GENIE_IN_THE_BOX_ROOT" ]
    else:
        return "/var/genie-in-the-box"

if __name__ == "__main__":
    
    # raw = "r-i-c-o dot f-e-l-i-p dot j-o-n-e-s at gmail.com"
    # dashes_regex = re.compile( "[a-z]-+", re.IGNORECASE )
    # # x = dashes_regex.sub( "[a-z]", raw )
    # x = dashes_regex.match( raw )
    # print( x )
    raw_txt = [ "multimodel text email", "MulTi mOdel text email", "MulTi-mOdel text email", "MulTi-mOdal text email" ]
    
    multimodal_regex = re.compile( "multi([ -]){0,1}mod[ae]l", re.IGNORECASE )
    for i in range( 0, len( raw_txt ) ):
        txt = raw_txt[ i ]
        x = multimodal_regex.sub( "multimodal", txt, 1 )
        print( x )
    
    # regex = re.compile( r"(\w+)(\s+)(\w+)" )
    
    #
    regex_str = "^\||\|$"
    regex_pattern = re.compile( regex_str )
    print( regex_pattern.sub( "", "|1|2|" ) )
    print( "|1|2|".replace( regex_str, "" ) )
    
    xlation_dict = get_file_as_dictionary( "conf/translation-dictionary.map", debug=True )
    print( "xlation_dict[ 'pipe' ] = [{}]".format( xlation_dict[ "pipe" ] ) )
    print( "xlation_dict[ 'space' ] = [{}]".format( xlation_dict[ "space" ] ) )
    print( "xlation_dict[ ' dot com' ] = [{}]".format( xlation_dict[ " dot com" ] ) )
    print( "xlation_dict[ 'comma ' ] = [{}]".format( xlation_dict[ "comma " ] ) )