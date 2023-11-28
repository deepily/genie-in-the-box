import os
debug = os.getenv( "GIB_CODE_EXEC_DEBUG", "True" ) == "True"

# if debug: print( f"pwd [{os.getcwd()}]" )

import sys
if debug:
    sys.path.sort()
    for path in sys.path: print( path )

# try:
#     import util as du
# except ImportError:
#     print( "Failed to import 'util', trying 'lib.util'..." )
import lib.utils.util as du

from subprocess import PIPE, run

def append_example_and_print_code( code, code_return_type, example_code, debug=False ):
    
    # Everybody runs the example code
    code.append( example_code )
    
    # code_return_type occasionally 'pandas.core.frame.DataFrame'
    return_type = code_return_type.lower().split( "." )[ -1 ]
    if debug: print( "return_type [{}]".format( return_type ) )
    
    if return_type == "dataframe":
        code.append( "print( solution.to_json( orient='records', lines=True ) )" )
    else:
        code.append( "print( solution )" )
        
    return code


# TODO: This may be overkill/superfluous
# def swap_return_value_assignment( code ):
#
#     penultimate_line = code[ -2 ]
#     last_line        = code[ -1 ]
#
#     # grab whatever comes after the return reserved word
#     returned_var_name = last_line.split( "return" )[ 1 ].strip()
#
#     # swap in the proper assignment name: 'solution = '
#     code[ -2 ] = penultimate_line.replace( returned_var_name + " = ", "solution = " )
#
#     # swap in the proper return statement: 'return solution'
#     code[ -1 ] = last_line.replace( "return " + returned_var_name, "return solution" )
#
#     return code


# TODO: This should generalize to include more than two instances of a string?
def remove_last_occurrence( the_list, the_string ):

    if the_list.count( the_string ) > 1:

        the_list.reverse()
        the_list.remove( the_string )
        the_list.reverse()

    return the_list

def assemble_and_run_solution( solution_code, example_code, path=None, solution_code_returns="string", debug=debug ):
    
    # if there's no dataframe to open or prep, then skip it
    if path is None:
        code_preamble = [ ]
    else:
        # Otherwise, do a bit of prep for pandas & cleanup
        code_preamble = [
            "import pandas as pd",
            "import lib.utils.util as du",
            "import lib.utils.util_pandas as dup",
            "",
            "debug = {}".format( debug ),
            "",
            # "if debug: print( sys.path )",
            "df = pd.read_csv( du.get_project_root() + '{path}' )".format( path=path ),
            "df = dup.cast_to_datetime( df, debug=debug )"
        ]
        # Remove duplicate imports if present
        code_preamble = remove_last_occurrence( code_preamble, "import pandas as pd" )
    
    # if debug: print( "last command, before [{}]:".format( solution_code[ -1 ] ) )
    solution_code = append_example_and_print_code( solution_code, solution_code_returns, example_code, debug=debug )
    # if debug: print( "last command,  after [{}]:".format( solution_code[ -1 ] ), end="\n\n" )
    
    code = code_preamble + solution_code + [ "" ]
    
    if debug: du.print_list( code )
    
    code_path = du.get_project_root() + "/io/code.py"
    du.write_lines_to_file( code_path, code )
    
    # Stash current working directory, so we can return to it after code has finished executing
    original_wd = os.getcwd()
    os.chdir( du.get_project_root() + "/io" )
    
    if debug: print( "Executing {}... ".format( code_path ), end="" )
    
    results = run( [ "python3", code_path ], stdout=PIPE, stderr=PIPE, universal_newlines=True )
    
    if results.returncode != 0:
        if debug: print()
        output = "ERROR executing code: \n\n{}".format( results.stderr.strip() )
        if debug: print( output )
    else:
        if debug: print( "Done!" )
        output = results.stdout.strip()
        if output == "":
            output = "No results returned"
    
    results_dict = {
        "return_code": results.returncode,
             "output": output
    }
    
    # Return to original working directory
    os.chdir( original_wd )
    
    return results_dict

def test_assemble_and_run_solution():

    # solution_code = [
    #     "def check_birthdays(df):",
    #     "    today = pd.Timestamp('today')",
    #     "    week_from_today = today + pd.DateOffset(weeks=1)",
    #     "    birthdays = df[(df.event_type == 'birthday') & (df.start_date <= week_from_today) & (df.end_date >= today)]",
    #     "    return birthdays"
    # ]
    # example_code = "solution = check_birthdays( df )"
    # results = assemble_and_run_solution( solution_code, example_code, solution_code_returns="dataframe", path="/src/conf/long-term-memory/events.csv", debug=debug )
    
    solution_code = [
        "import datetime",
        "import pytz",
        "def get_time():",
        "    now = datetime.datetime.now()",
        "    tz_name = 'America/New_York'",
        "    tz = pytz.timezone( tz_name )",
        "    tz_date = now.astimezone( tz )",
        "    return tz_date.strftime( '%I:%M %p %Z' )"
    ]
    example_code = "solution = get_time()"
    results = assemble_and_run_solution( solution_code, example_code, solution_code_returns="string", debug=debug )

    for line in results[ "output" ].split( "\n" ): print( line )
        
if __name__ == "__main__":
    test_assemble_and_run_solution()
    # pass