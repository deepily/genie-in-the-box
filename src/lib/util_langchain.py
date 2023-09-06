import lib.util as du

from subprocess import PIPE, run

def force_print_cmd( code ):
    
    if "print(" not in code[ -1 ]:
        code[ -1 ] = "print( {} )".format( code[ -1 ] )
        
    return code

def assemble_and_run_solution( solution_code, path=None, debug=False ):
    
    # if there's no dataframe to open then skip it
    if path is not None:
        code_preamble = [
            "import pandas as pd",
            "df = pd.read_csv( \"{path}\" )".format( path=path )
        ]
    else:
        code_preamble = [ ]
    
    if debug: print( "last command, before [{}]:".format( solution_code[ -1 ] ) )
    solution_code = force_print_cmd( solution_code )
    if debug: print( "last command,  after [{}]:".format( solution_code[ -1 ] ) )
    
    code = code_preamble + solution_code + [ "" ]
    
    code_path = du.get_project_root() + "/io/code.py"
    du.write_lines_to_file( code_path, code )
    
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
    # results = assemble_and_run_solution( solution_code, du.get_project_root() + "/src/conf/long-term-memory/events.csv" )
    
    solution_code = [
        "import datetime",
        "import pytz",
        "now = datetime.datetime.now()",
        "tz_name = 'America/New_York'",
        "tz = pytz.timezone( tz_name )",
        "tz_date = now.astimezone( tz )",
        "print( tz_date.strftime( '%I:%M %p %Z' ) )"
    ]
    results = assemble_and_run_solution( solution_code )
    
    if results[ "return_code" ] != 0:
        print( results[ "response" ] )
    else:
        response = results[ "response" ]
        for line in response.split( "\n" ): print( line )
        
if __name__ == "__main__":
    test_assemble_and_run_solution()