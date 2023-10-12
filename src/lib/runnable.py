import lib.util             as du
import lib.util_code_runner as ucr
class Runnable:
    def __init__( self, debug=False, verbose=False ):
        
        self.debug                = debug
        self.verbose              = verbose
        
        self.prompt_response      = None
        self.prompt_response_dict = None
        
        self.code_response_dict   = None
        self.error                = None

    def run_code(self):
        
        self.code_response_dict = ucr.assemble_and_run_solution(
            self.prompt_response_dict[ "code" ], path="/src/conf/long-term-memory/events.csv",
            solution_code_returns=self.prompt_response_dict.get( "returns", "string" ), debug=self.debug
        )
        if self.debug and self.verbose:
            du.print_banner("Code output", prepend_nl=True)
            for line in self.code_response_dict[ "output" ].split( "\n" ):
                print( line )

        return self.code_response_dict