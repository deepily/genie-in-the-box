import os
from collections import Counter
from subprocess import PIPE, run

debug = os.getenv( "GIB_CODE_EXEC_DEBUG", "False" ) == "True"

# import sys
# if debug:
#     sys.path.sort()
#     for path in sys.path: print( path )

import lib.utils.util as du

@staticmethod
def initialize_code_response_dict():
    
    # defaults to unsuccessful run state
    return {
        "return_code": -1,
             "output": "No code run yet"
    }

def _append_example_and_print_code( code, code_return_type, example_code, debug=False, verbose=False ):
    
    """
    Appends the method's invocation example code to the given code list and the prints the returned solution value based on the code return type (dataframe or plain print).
    
    When added, example and print code would look like this:
    <pre><code>
    code[ -2 ] = "solution = get_time()"
    code[ -1 ] = "print( solution )"
    </code></pre>

    Parameters:
        code (list): A list of code lines.
        code_return_type (str): The return type of the code.
        example_code (str): The example code to be appended.
        debug (bool, optional): Whether to print debug information. Defaults to False.
        verbose (bool, optional): Whether to print verbose information. Defaults to False.

    Returns:
        list: The updated code list with the example code appended.
    """
    plain_print     = "print( solution )"
    formatted_print = "print( solution.to_xml( index=False ) )"
    # formatted_print = "print( solution.to_json( orient='records', lines=True ) )"
    
    if code[ -2 ] != example_code and code[ -1 ] not in [ plain_print, formatted_print ]:
        
        code.append( example_code )
    
        # code_return_type if occasionally 'pandas.core.frame.DataFrame'
        return_type = code_return_type.lower().split( "." )[ -1 ]
        if debug and verbose: print( "return_type [{}]".format( return_type ) )
        
        if return_type == "dataframe":
            code.append( formatted_print )
        else:
            code.append( plain_print )
    
    # Remove duplicate imports if present
    # code = remove_last_occurrence( code, "import pandas as pd" )
    # code = remove_last_occurrence( code, "import datetime" )
    
    duplicates_report, clean_code = _remove_duplicate_lines( code )
    
    if len( duplicates_report ) > 0:
        du.print_banner( "Code Runner: Duplicate lines removed:", prepend_nl=False, end="\n" )
        for line, count in duplicates_report.items():
            print( f"Count: [{count:02d}] Line [{line}]" )
        print()
    
    return clean_code


def _remove_duplicate_lines( code_lines ):
    
    # Count the occurrences of each line
    line_count = Counter( code_lines )
    
    # Report the duplicate lines and their frequencies
    duplicates_report = { line: count for line, count in line_count.items() if count > 1 }
    
    # Remove duplicate lines, keeping only the first occurrence
    unique_lines = [ ]
    seen_lines   = set()
    
    for line in code_lines:
        if line not in seen_lines:
            unique_lines.append( line )
            seen_lines.add( line )
    
    return duplicates_report, unique_lines


# Apply the method to the sample code
# duplicates_report, unique_code_lines = remove_duplicate_lines( code_lines )

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
# def remove_last_occurrence( the_list, the_string ):
#
#     # ¡OJO! This has issues with white space that precedes any target strings. Not worth worrying about right now
#     # Example: "    import datetime" will not be removed if the List contains "import datetime", and vice versa
#     if the_list.count( the_string ) > 1:
#
#         the_list.reverse()
#         the_list.remove( the_string )
#         the_list.reverse()
#
#     return the_list

def assemble_and_run_solution( solution_code, example_code, path_to_df=None, solution_code_returns="string", debug=True, verbose=False, inject_bugs=False ):
    
    # if there's no dataframe to open or prep, then skip it
    if path_to_df is None:
        code_preamble = [
            "import datetime",
            "import pytz",
        ]
    else:
        # Otherwise, do a bit of prep for pandas & cleanup
        code_preamble = [
            "import datetime",
            "import pytz",
            "import pandas as pd",
            "import lib.utils.util as du",
            "import lib.utils.util_pandas as dup",
            "",
            "debug = {}".format( debug ),
            "",
            # "if debug: print( sys.path )",
            "df = pd.read_csv( du.get_project_root() + '{path}' )".format( path=path_to_df ),
            "df = dup.cast_to_datetime( df, debug=debug )"
        ]
        # Remove duplicate imports if present
        # code_preamble = remove_last_occurrence( code_preamble, "import pandas as pd" )
        # code_preamble = remove_last_occurrence( code_preamble, "import datetime as dt" )
    
    if debug and verbose:
        du.print_banner( "Solution code BEFORE:", prepend_nl=True)
        du.print_list( solution_code)
    
    solution_code = _append_example_and_print_code( solution_code, solution_code_returns, example_code, debug=debug )
    
    if debug and verbose:
        du.print_banner( "Solution code AFTER:", prepend_nl=True)
        du.print_list( solution_code)
    
    code = code_preamble + solution_code + [ "" ]
    
    if inject_bugs:
        
        from lib.agents.bug_injector import BugInjector
        
        du.print_banner( "Injecting bugs...", prepend_nl=True, expletive=True, chunk="buggy 🦂 bug injector 💉 " )
        bug_injector  = BugInjector( code, debug=debug, verbose=verbose )
        response_dict = bug_injector.run_prompt()
        code          = response_dict[ "code" ]
        
    code_path = du.get_project_root() + "/io/code.py"
    du.write_lines_to_file( code_path, code )
    
    # Stash current working directory, so we can return to it after code has finished executing
    original_wd = os.getcwd()
    os.chdir( du.get_project_root() + "/io" )
    
    if debug: print( "Code runner executing [{}]... ".format( code_path ), end="" )
    
    # ¡OJO! Hardcoded value of python run time... Make this runtime configurable
    results = run( [ "python3", code_path ], stdout=PIPE, stderr=PIPE, universal_newlines=True )
    
    if debug: print( f"results.returncode = [{results.returncode}]...", end="" )
    
    if results.returncode != 0:
        if debug: print()
        output = f"ERROR executing code: \n\n{results.stderr.strip()}"
        if debug: print( output )
    else:
        if debug: print( "Done!" )
        output = results.stdout.strip()
        if output == "":
            output = "No results returned"
    
    results_dict = initialize_code_response_dict()
    results_dict[ "return_code" ] = results.returncode
    results_dict[ "output"      ] = output
    
    if debug:
        du.print_banner( "Code runner output:", prepend_nl=True )
        print( results_dict[ "output" ] )
    
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
        "import datetime",
        "import pytz",
        "def get_time():",
        "def get_time():",
        "    import datetime",
        "    now = datetime.datetime.now()",
        "    tz_name = 'America/New_York'",
        "    tz = pytz.timezone( tz_name )",
        "    tz_date = now.astimezone( tz )",
        "    return tz_date.strftime( '%I:%M %p %Z' )"
    ]
    example_code = "solution = get_time()"
    results = assemble_and_run_solution( solution_code, example_code, solution_code_returns="string", debug=False, verbose=False, inject_bugs=False )

    for line in results[ "output" ].split( "\n" ): print( line )
        
if __name__ == "__main__":
    test_assemble_and_run_solution()
    # pass