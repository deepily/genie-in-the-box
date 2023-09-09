import re
import os
debug = os.getenv( "GIB_CODE_EXEC_DEBUG", "True" ) == "True"

if debug: print( f"pwd [{os.getcwd()}]" )

import sys
if debug:
    sys.path.sort()
    for path in sys.path: print( path )

try:
    import util as du
except ImportError:
    print( "Failed to import 'util', trying 'lib.util'..." )
    import lib.util as du

from subprocess import PIPE, run

def force_print_cmd( code, solution_code_returns, debug=False ):
    
    # solution_code_returns is occassionally 'pandas.core.frame.DataFrame'
    return_type = solution_code_returns.lower().split( "." )[ -1 ]
    df = "dataframe"
    if debug: print( "return_type [{}]".format( return_type ) )
    
    if return_type == df and "solution" in code[ -1 ]:
        code.append( "print( solution.to_csv( index=False, sep=',', lineterminator='\\n', quoting=csv.QUOTE_NONNUMERIC ) )" )
    elif return_type == df and "solution" not in code[ -1 ]:
        print( f"ERROR: last command DOES NOT contain 'solution', found this instead [{code[ -1 ]}]:" )
        code.append( "# Where's the solution?!?" )
    elif "solution" in code[ -1 ] and "print(" not in code[ -1 ]:
        code.append( "print( solution )" )
    else:
        print( f"ERROR: return_type [{return_type}] and last command [{code[ -1 ]}] are incompatible!" )
        code.append( "# What's up with that LLM's return type?!?" )
        
    # if "print(" not in code[ -1 ]:
    #     code[ -1 ] = "print( {} )".format( code[ -1 ] )
    #
    # # Now add CSV output to the df(?!?) on the last line
    # match = re.search( r'print\(([^)]+)\)', code[ -1 ] )
    # if match:
    #     content = match.group( 1 )
    #     code[ -1 ] = f"print({content}.to_csv( index=False, sep=',', lineterminator='\\n', quoting=csv.QUOTE_NONNUMERIC ) )"
    # print( "last command, after adding CSV [{}]:".format( code[ -1 ] ) )
    
    return code

def assemble_and_run_solution( solution_code, path=None, solution_code_returns="string", debug=debug ):
    
    # if there's no dataframe to open then skip it
    if path is None:
        code_preamble = [ ]
    else:
        # Otherwise, do a bit of kludgey prep and clean up
        code_preamble = [
            "import csv",
            "import sys",
            "debug = {}".format( debug ),
            "if debug: print( sys.path )",
            "import pandas as pd",
            "df = pd.read_csv( \"{path}\" )".format( path=path ),
            # Clean up date columns that end with "_date"
            "try:",
            "    import util_pandas as up",
            "except ImportError:",
            "    import lib.util_pandas as up",
            "df = up.cast_to_datetime( df, debug={} )".format( debug )
        ]
    
    if debug: print( "last command, before [{}]:".format( solution_code[ -1 ] ) )
    solution_code = force_print_cmd( solution_code, solution_code_returns, debug=debug )
    if debug: print( "last command,  after [{}]:".format( solution_code[ -1 ] ) )
    
    code = code_preamble + solution_code + [ "" ]
    
    if debug:
        for line in code: print( line )
    
    code_path = du.get_project_root() + "/src/code.py"
    du.write_lines_to_file( code_path, code )
    
    os.chdir( du.get_project_root() + "/src" )
    # if debug: print( f"pwd [{os.getcwd()}]" )
    
    if debug: print( "Executing {}... ".format( code_path ), end="" )
    
    results = run( [ "python3", code_path ], stdout=PIPE, stderr=PIPE, universal_newlines=True )
    
    if results.returncode != 0:
        if debug: print()
        response = "ERROR:\n{}".format( results.stderr.strip() )
        if debug: print( response )
    else:
        if debug: print( "Done!" )
        response = results.stdout.strip()
    
    results_dict = {
        "return_code": results.returncode,
        "response"   : response
    }
    return results_dict

def test_assemble_and_run_solution():

    # solution_code = [
    #     "num_records = df.shape[0]",
    #     "num_records"
    # ]
    
    solution_code = [
        "import datetime",
        "import pytz",
        "now = datetime.datetime.now()",
        "tz_name = 'America/New_York'",
        "tz = pytz.timezone( tz_name )",
        "tz_date = now.astimezone( tz )",
        "print( tz_date.strftime( '%I:%M %p %Z' ) )"
    ]
    results = assemble_and_run_solution( solution_code, du.get_project_root() + "/src/conf/long-term-memory/events.csv", debug=debug )
    # results = assemble_and_run_solution( solution_code )
    
    if results[ "return_code" ] != 0:
        print( results[ "response" ] )
    else:
        response = results[ "response" ]
        for line in response.split( "\n" ): print( line )
        
if __name__ == "__main__":
    test_assemble_and_run_solution()