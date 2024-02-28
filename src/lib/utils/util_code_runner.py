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

def _ensure_proper_appendages( code, always_appended ):
    
    # du.print_banner( "_ensure_proper_appendages", prepend_nl=True )
    # print( "always_appended", always_appended )
    len_always_appended = -len( always_appended )
    # print( f"len_always_appended [{len_always_appended}]" )
    
    # Check if the last N elements of 'code' match 'always_appended'
    if code[ len_always_appended: ] != always_appended:
        
        # print( "code[ len( always_appended ): ] != always_appended" )
        # print( "code", code[ len_always_appended: ] )
        
        # Identify any elements in 'always_appended' that are already in 'code' but not in the correct position
        to_remove = set( code[ len_always_appended: ] ) & set( always_appended )
        # print( "to_remove", to_remove )
        
        # Create a new list excluding the elements found above, to ensure they are not duplicated
        cleaned_code = [ line for line in code if line not in to_remove ]
        
        # Append 'always_appended' to the end of the list
        cleaned_code.extend( always_appended )
        
        return cleaned_code
    
    else:
        
        return code

def _append_post_function_code( code, code_return_type, example_code, path_to_df=None, debug=False, verbose=False ):
    
    """
    Appends the method's invocation example code to the given code list and the prints the returned solution value based on the code return type (dataframe or plain print).
    
    When added, example and print code should look ~like this:
    <pre><code>
    code[ -2 ] = "solution = get_time()"
    code[ -1 ] = "print( solution )"
    </code></pre>
    -- or --
    <pre><code>
    code[ -4 ] = "df = pd.read_csv( du.get_project_root() + '/src/conf/long-term-memory/events.csv' )"
    code[ -3 ] = "df = dup.cast_to_datetime( df, 'start_date' )
    code[ -2 ] = "solution = get_events_this_week( df )"
    code[ -1 ] = "print( solution.to_xml( index=False )"
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
    # code_return_type if occasionally 'pandas.core.frame.DataFrame', so we need to extract the last part of the string
    code_return_type = code_return_type.lower().split( "." )[ -1 ]
    
    always_appended = []
    
    # Conditionally apply the first two
    if path_to_df is not None:
        # 1st
        always_appended.append( f"df = pd.read_csv( du.get_project_root() + '{path_to_df}' )" )
        # 2nd
        always_appended.append( "df = dup.cast_to_datetime( df, debug=debug )" )
        
    # 3rd: Always append the example code
    always_appended.append( example_code )
    
    # 4th: Conditionally append the properly formatted print statement
    if debug and verbose: print( "return_type [{}]".format( code_return_type ) )
    if code_return_type == "dataframe":
        always_appended.append( "print( solution.to_xml( index=False ) )" )
    else:
        always_appended.append( "print( solution )" )
        
    code = _ensure_proper_appendages( code, always_appended )
    
    # Remove redundant imports, if present
    code = _remove_all_but_the_1st_of_repeated_lines( code, "import pandas as pd" )
    code = _remove_all_but_the_1st_of_repeated_lines( code, "import datetime" )
    code = _remove_all_but_the_1st_of_repeated_lines( code, "import pytz" )
    code = _remove_all_but_the_1st_of_repeated_lines( code, "import lib.utils.util as du" )
    code = _remove_all_but_the_1st_of_repeated_lines( code, "import lib.utils.util_pandas as dup" )
    #  Remove redundant debug settings, if present
    code = _remove_all_but_the_1st_of_repeated_lines( code, "debug = True" )
    code = _remove_all_but_the_1st_of_repeated_lines( code, "debug = False" )
    
    # Remove any repeated example code
    code = _remove_all_but_the_1st_of_repeated_lines( code, example_code )
    
    return code

def _remove_all_but_the_1st_of_repeated_lines( the_list, search_string ):
    
    # From: https://chat.openai.com/c/db28026c-444d-4a4b-b24b-bbb88fa52521
    match_indices = [ ]
    
    # Iterate through the list to find matches
    for i, item in enumerate( the_list ):
        item_trimmed = item.strip()
        if item_trimmed.startswith( search_string ):
            match_indices.append( i )
    
    # Remove the first occurrence from the match indices to keep it
    if match_indices: match_indices.pop( 0 )
    
    # Sort the match indices in descending order to remove items starting from the end
    for index in sorted( match_indices, reverse=True ):
        the_list.pop( index )
    
    return the_list

def _get_imports( path_to_df ):
    
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
        ]
    return code_preamble


def _remove_consecutive_empty_strings( strings ):
    
    # Initialize an empty list to store the result
    result = [ ]
    
    # Iterate through the list with index
    for i in range( len( strings ) ):
        
        # Check if the current string is zero-length
        if strings[ i ] == "":
            # If it's the first element or the previous element is not a zero-length string, add it to the result
            if i == 0 or strings[ i - 1 ] != "":
                result.append( strings[ i ] )
        else:
            # If the current string is not zero-length, add it to the result
            result.append( strings[ i ] )
            
    return result

def assemble_and_run_solution( solution_code, example_code, path_to_df=None, solution_code_returns="string", debug=False, verbose=False, inject_bugs=False ):
    
    if debug and verbose:
        du.print_banner( "Solution code BEFORE:", prepend_nl=True)
        du.print_list( solution_code)
    
    imports       = _get_imports( path_to_df )
    solution_code = imports + solution_code
    solution_code = _append_post_function_code( solution_code, solution_code_returns, example_code, path_to_df=path_to_df, debug=debug )
    solution_code = _remove_consecutive_empty_strings( solution_code )
    
    if debug and verbose:
        du.print_banner( "Solution code AFTER:", prepend_nl=True)
        du.print_list( solution_code )
    
    if inject_bugs:
        
        from lib.agents.bug_injector import BugInjector
        
        du.print_banner( "Injecting bugs...", prepend_nl=True, expletive=True, chunk="buggy 🦂 bug injector 💉 " )
        bug_injector  = BugInjector( solution_code, debug=debug, verbose=verbose )
        response_dict = bug_injector.run_prompt()
        code          = response_dict[ "code" ]
        
    code_path = du.get_project_root() + "/io/code.py"
    du.write_lines_to_file( code_path, solution_code )
    
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
    
    if debug and verbose:
        du.print_banner( "assemble_and_run_solution() output:", prepend_nl=True )
        print( results_dict[ "output" ] )
    
    # Return to original working directory
    os.chdir( original_wd )
    
    return results_dict

def test_assemble_and_run_solution( debug=False, verbose=False):

    solution_code = [
        "def check_birthdays(df):",
        "    today = pd.Timestamp('today')",
        "    week_from_today = today + pd.DateOffset(weeks=1)",
        "    birthdays = df[(df.event_type == 'birthday') & (df.start_date <= week_from_today) & (df.end_date >= today)]",
        "    return birthdays",
        "solution = check_birthdays( df )"
    ]
    example_code = "solution = check_birthdays( df )"
    results = assemble_and_run_solution( solution_code, example_code, solution_code_returns="dataframe", path_to_df="/src/conf/long-term-memory/events.csv", debug=debug, verbose=verbose )
    
    # solution_code = [
    #     "import datetime",
    #     "import pytz",
    #     "import pandas as pd",
    #     "import lib.utils.util as du",
    #     "import lib.utils.util_pandas as dup",
    #     "debug = False",
    #     "",
    #     "def get_events_for_this_week( df ):",
    #     "    import pandas as pd",
    #     "    import datetime",
    #     "    import pandas as pd",
    #     "    import datetime",
    #     "    today = datetime.date.today()",
    #     "    start_of_week = today - pd.DateOffset(days=today.weekday())",
    #     "    end_of_week = start_of_week + pd.DateOffset(days=7)",
    #     "    solution = df[(df['event_type'] == 'concert') & (df['start_date'].between(start_of_week, end_of_week))]",
    #     "    return solution",
    #     "",
    #     "",
    #     "df = pd.read_csv( du.get_project_root() + '/src/conf/long-term-memory/events.csv' )",
    #     "df = dup.cast_to_datetime( df, debug=debug )",
    # ]
    # example_code = "solution = get_events_for_this_week( df )"
    # results = assemble_and_run_solution( solution_code, example_code, solution_code_returns="pandas.core.frame.DataFrame", path_to_df="/src/conf/long-term-memory/events.csv", debug=debug, verbose=verbose )
    
    # solution_code = [
    #     "import datetime",
    #     "import pytz",
    #     "import datetime",
    #     "import pytz",
    #     "def get_time():",
    #     "    import datetime",
    #     "    now = datetime.datetime.now()",
    #     "    tz_name = 'America/New_York'",
    #     "    tz = pytz.timezone( tz_name )",
    #     "    tz_date = now.astimezone( tz )",
    #     "    return tz_date.strftime( '%I:%M %p %Z' )"
    # ]
    # example_code = "solution = get_time()"
    # results = assemble_and_run_solution( solution_code, example_code, solution_code_returns="string", debug=debug, verbose=verbose, inject_bugs=False )

    # du.print_banner( f"results[ 'return_code' ] = [{results[ 'return_code' ]}]..." )
    # for line in results[ "output" ].split( "\n" ): print( line )
        
if __name__ == "__main__":
    test_assemble_and_run_solution( debug=True, verbose=True )
    # pass