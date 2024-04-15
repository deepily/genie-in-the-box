import os
import regex as re
import random
import sys
from datetime import datetime as dt
from datetime import timedelta as td
import pytz
import json
import traceback

debug = False

def init( d ):
    
    global debug
    debug = d
    
def add_to_path( path ):

    if path not in sys.path:
        sys.path.append( path )
        print( "Added [{}] to sys.path".format( path ) )
    else:
        print( "Path [{}] already in sys.path".format( path ) )


def get_current_datetime_raw( tz_name="US/Eastern", days_offset=0 ):

    # Get the current date plus or minus the specified days_offset
    now     = dt.now()
    delta   = td( days=days_offset )
    now     = now + delta
    tz      = pytz.timezone( tz_name )
    tz_date = now.astimezone( tz )
    
    return tz_date

def get_current_datetime( tz_name="US/Eastern" ):
    
    tz_date = get_current_datetime_raw( tz_name )
    
    return tz_date.strftime( '%Y-%m-%d @ %H:%M:%S %Z' )

def get_current_date( tz_name="US/Eastern", return_prose=False, offset=0 ):
    """
    Returns the current date in the specified time zone.

    Args:
        tz_name (str): The name of the time zone. Defaults to "US/Eastern".
        return_prose (bool): Whether to return the date in prose format. Defaults to False.
            If True, the date will be returned in the format: "Monday, January 01, 2021".

    Returns:
        str: The current date formatted as specified.
    """
    tz_date = get_current_datetime_raw( tz_name, days_offset=offset )
    
    if return_prose:
        return tz_date.strftime( "%A, %B %d, %Y" )
    else:
        return tz_date.strftime( "%Y-%m-%d" )

def get_current_time( tz_name="US/Eastern", include_timezone=True, format="%H:%M:%S" ):
    """
    A function that returns the current time in a specified time zone with optional timezone information.

    Parameters:
    - tz_name (str): The name of the timezone to get the current time in. Default is "US/Eastern".
    - include_timezone (bool): Whether to include the timezone information in the output. Default is True.
    - format (str): The format of the time string to return. Default is "%H:%M:%S".

    Returns:
    - str: The current time in the specified timezone with optional timezone information based on the format.
    """
    tz_date = get_current_datetime_raw( tz_name )
    
    if include_timezone:
        return tz_date.strftime( format + " %Z" )
    else:
        return tz_date.strftime( format )

def get_name_value_pairs( arg_list, debug=False, verbose=False ):
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
    
    # add a little whitespace
    if debug: print()
    
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
        if debug and verbose: print( "[{0}] = [{1}]".format( ("[ " + name).rjust( max_len, " " ), name_value_pairs[ name ] ) )
    if debug and verbose: print()
    
    return name_value_pairs


def get_file_as_source_code_with_line_numbers( path ):
    
    source_code = get_file_as_list( path, lower_case=False, clean=False, randomize=False )
    return get_source_code_with_line_numbers( source_code )
    
def get_source_code_with_line_numbers( source_code, join_str="" ):
    
    # iterate through the source code and prepend the line number to each line
    for i in range( len( source_code ) ):
        source_code[ i ] = f"{i + 1:03d} {source_code[ i ]}"
    
    # join the lines back together into a single string
    source_code = join_str.join( source_code )
    
    return source_code

# Load a plain text file as a list of lines.
def get_file_as_list( path, lower_case=False, clean=False, randomize=False, seed=42, strip_newlines=False ):
    
    with open( path, "r", encoding="utf-8" ) as file:
        lines = file.readlines()
    
    if lower_case:
        lines = [ line.lower() for line in lines ]
        
    if clean:
        lines = [ line.strip() for line in lines ]
        
    if strip_newlines:
        lines = [ line.strip( "\n" ) for line in lines ]
        
    if randomize:
        random.seed( seed )
        random.shuffle( lines )
    
    return lines


def get_file_as_string( path ):
    with open( path, "r" ) as file:
        return file.read()


def get_file_as_json( path ):
    with open( path, "r" ) as file:
        return json.load( file )


def get_file_as_dictionary( path, lower_case=False, omit_comments=True, debug=False, verbose=False ):
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
            if debug and verbose: print( "[{}] = [{}]".format( pair[ 0 ], pair[ 1 ] ) )
            # Only pull pipes after the key and values have been stripped.
            p0 = pipe_regex.sub( "", pair[ 0 ].strip() )
            p1 = pipe_regex.sub( "", pair[ 1 ].strip() )
            lines_as_dict[ p0 ] = p1
        else:
            if debug: print( "ERROR: [{}]".format( pair[ 0 ] ) )
    
    return lines_as_dict

def write_lines_to_file( path, lines, strip_blank_lines=False, world_read_write=False ):

    if strip_blank_lines:
        lines = [ line for line in lines if line.strip() != "" ]
    
    with open( path, "w" ) as outfile:
        outfile.write( "\n".join( lines ) )
        
    if world_read_write: os.chmod( path, 0o666 )
        
def write_string_to_file( path, string ):
    
    with open( path, "w" ) as outfile:
        outfile.write( string )

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
    
def get_project_root():
    
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

# do the same as do the same as get_project_root() but for the GENIE_IN_THE_BOX_TGI_SERVER
def get_tgi_server_url_for_this_context( default_url=None ):
    
    """
    Get the TGI server URL for one of two execution contexts: docker or local

    Args:
        default_url (str, optional): The default URL to return if the TGI server URL is not found in the environment variables. Defaults to None.

    Returns:
        str: The TGI server URL.

    Raises:
        ValueError: If the TGI server URL is not found in the environment variables and no default URL is provided.
    """
    
    if debug: print( "GENIE_IN_THE_BOX_TGI_SERVER [{}]".format( os.getenv( "GENIE_IN_THE_BOX_TGI_SERVER" ) ) )
    
    if "GENIE_IN_THE_BOX_TGI_SERVER" in os.environ:
        return os.environ[ "GENIE_IN_THE_BOX_TGI_SERVER" ]
    else:
        if default_url is None:
            raise ValueError( "GENIE_IN_THE_BOX_TGI_SERVER not found in environment variables and default_url NOT provided" )
        
        return default_url

# get api key
def get_api_key( key_name, project_root=get_project_root() ):
    
    path = project_root + f"/src/conf/keys/{key_name}"
    if debug: print( f"Fetching [{key_name}] from [{path}]..." )
    
    # test path to see if key exists
    if not os.path.exists( path ):
        print_banner( f"ERROR: Key [{key_name}] not found at [{path}]" )
        return None
    
    return get_file_as_string( path )

def generate_domain_names( count=10, remove_dots=False, debug=False ):
    
    adjectives        = [ "amazing", "beautiful", "exciting", "fantastic", "hilarious", "incredible", "jubilant", "magnificent", "remarkable", "spectacular", "wonderful" ]
    nouns             = [ "apple", "banana", "cherry", "dolphin", "elephant", "giraffe", "hamburger", "iceberg", "jellyfish", "kangaroo", "lemur", "mango", "november", "octopus", "penguin", "quartz", "rainbow", "strawberry", "tornado", "unicorn", "volcano", "walrus", "xylophone", "yogurt", "zebra" ]
    
    top_level_domains = [ ".com", ".org", ".gov", ".info", ".net", ".io" ]
    sub_domains       = [ "", "", "www.", "blog.", "login.", "mail.", "dev.", "beta.", "alpha.", "test.", "stage.", "prod." ]
    
    if remove_dots:
        top_level_domains = [ tld.replace( ".", "" ) for tld in top_level_domains ]
        sub_domains       = [ sub.replace( ".", "" ) for sub in sub_domains ]
    
    domain_names = [ ]
    for _ in range( count ):
        
        adj  = random.choice( adjectives )
        noun = random.choice( nouns )
        tld  = random.choice( top_level_domains )
        sub  = random.choice( sub_domains )
        
        domain_name = f"{sub}{adj}{noun}{tld}"
        domain_names.append( domain_name )
        
        if debug: print( domain_name )

    return domain_names

# def get_search_terms( requested_length ):
#
#     # Load search terms file
#     search_terms = get_file_as_list( get_project_root() + "/src/ephemera/prompts/data/search-terms.txt", lower_case=False, clean=True, randomize=True )
#
#     # If we don't have enough search terms, append copies of the search term list until we do
#     while requested_length > len( search_terms ):
#         search_terms += search_terms
#
#     # Truncate the search terms list to equal the requested len
#     search_terms = search_terms[ :requested_length ]
#
#     return search_terms

def is_jsonl( string ):
    
    try:
        # Split the string into lines
        lines = string.splitlines()

        # Iterate over each line and validate as JSON
        for line in lines:
            json.loads(line)

        return True
    
    except json.JSONDecodeError:
        return False

# A function that truncates a string if it exceeds a maximum length parameter. If it does add an ellipsis to the end.
def truncate_string( string, max_len=64 ):
    
    if len( string ) > max_len:
        string = string[ :max_len ] + "..."
        
    return string


def find_files_with_prefix_and_suffix( directory, prefix, suffix ):
    
    matching_files = [ ]
    for file_name in os.listdir( directory ):
        if file_name.startswith( prefix ) and file_name.endswith( suffix ):
            file_path = os.path.join( directory, file_name )
            matching_files.append( file_path )
            
    return matching_files

def get_files_as_strings( file_paths ):
    
    contents = [ ]
    
    for file_path in file_paths:
        
        contents.append( get_file_as_string( file_path ) )
        
    return contents

# Add a function that takes a list and print it to the consul one line of time
def print_list( list_to_print, end="\n" ):
    
    for item in list_to_print:
        print( item, end=end )
    
    
def print_stack_trace( exception, explanation="Unknown reason", caller="Unknown caller", prepend_nl=True ):
    
    msg = f"ERROR: {explanation} in {caller}"
    print_banner( msg, prepend_nl=prepend_nl, expletive=True )
    stack_trace = traceback.format_tb( exception.__traceback__ )
    for line in stack_trace: print( line )
    
def sanity_check_file_path( file_path, silent=False ):

    """
    Check to see if file exists

    :param file_path: path to be checked

    :param silent: Suppresses any output, defaults to false

    :return: None, throws assertion error if not
    """

    fail_msg = "That file doesn't exist: [{0}] Please correct path to file".format( file_path )
    assert os.path.isfile( file_path ), fail_msg

    if not silent: print( f"File exists! [{file_path}]" )
    
def get_name_value_pairs( arg_list, decode_spaces=True ):
    
    """
    Parses a list of strings -- name=value -- into dictionary format { "name":"value" }

    NOTE: Only the 1st element, the name of the class called, is exempt from parsing

    :raises: ValueError if any but the 1st element is not of the format: 'name=value'

    :param arg_list: Space delimited input from CLI
    
    :param decode_spaces: Decode spaces in value? Defaults to True

    :return: dictionary of name=value pairs
    """

    name_value_pairs = { }

    # Quick sanity check. Do we have anything to iterate?
    if len( arg_list ) <= 1:
        print( "No name=value pairs found in arg_list" )
        return { }
    
    for i, arg in enumerate( arg_list ):

        print( "[{0}]th arg = [{1}]... ".format( i, arg_list[ i ] ), end="" )

        if "=" in arg:
            
            pair  = arg.split( "=" )
            value = pair[ 1 ].replace( "+", " " ) if decode_spaces else pair[ 1 ]
            name_value_pairs[ pair[ 0 ] ] = value
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
        print( f"[{(name.rjust( max_len, ' ' ))}] = [{name_value_pairs[ name ]}]" )
    print()

    return name_value_pairs

if __name__ == "__main__":
    
    print( os.getcwd() )
    init_dict = get_name_value_pairs( sys.argv )
    
    # print( get_current_datetime() )
    # print( get_tgi_server_url_for_this_context())
    # print( get_api_key( "eleven11" ) )
    print( get_api_key( "openai" ) )
    # print( get_api_key( "openai", project_root="/Users/rruiz/Projects/projects-sshfs/genie-in-the-box" ) )
    
    print( get_current_date( return_prose=True ) )
    print( get_current_time( format="%H:00" ) )
    
    print( "yesterday:", get_current_datetime_raw( days_offset=-1 ) )
    print( "    today:", get_current_datetime_raw( days_offset=0 ) )
    print( " tomorrow:", get_current_datetime_raw( days_offset=1 ) )
    
    # line = get_file_as_source_code_with_line_numbers( get_project_root() + "/io/code.py" )
    # print( line )
    
    # generate_domain_names( 10, debug=True )
    
    # search_terms = get_file_as_list( get_project_root() + "/src/conf/search-terms.txt", lower_case=True, clean=True, randomize=True )
    # #
    # for search_term in search_terms: print( search_term )
    # search_terms = get_search_terms( 120 )
    # print( len( search_terms ) )
    
    # raw = "r-i-c-o dot f-e-l-i-p dot j-o-n-e-s at gmail.com"
    # dashes_regex = re.compile( "[a-z]-+", re.IGNORECASE )
    # # x = dashes_regex.sub( "[a-z]", raw )
    # x = dashes_regex.match( raw )
    # print( x )
    # raw_txt = [ "multimodel text email", "MulTi mOdel text email", "MulTi-mOdel text email", "MulTi-mOdal text email" ]
    #
    # multimodal_regex = re.compile( "multi([ -]){0,1}mod[ae]l", re.IGNORECASE )
    # for i in range( 0, len( raw_txt ) ):
    #     txt = raw_txt[ i ]
    #     x = multimodal_regex.sub( "multimodal", txt, 1 )
    #     print( x )
    
    # regex = re.compile( r"(\w+)(\s+)(\w+)" )
    #
    # #
    # regex_str = "^\||\|$"
    # regex_pattern = re.compile( regex_str )
    # print( regex_pattern.sub( "", "|1|2|" ) )
    # print( "|1|2|".replace( regex_str, "" ) )
    #
    # xlation_dict = get_file_as_dictionary( "conf/translation-dictionary.map", debug=True )
    # print( "xlation_dict[ 'pipe' ] = [{}]".format( xlation_dict[ "pipe" ] ) )
    # print( "xlation_dict[ 'space' ] = [{}]".format( xlation_dict[ "space" ] ) )
    # print( "xlation_dict[ ' dot com' ] = [{}]".format( xlation_dict[ " dot com" ] ) )
    # print( "xlation_dict[ 'comma ' ] = [{}]".format( xlation_dict[ "comma " ] ) )