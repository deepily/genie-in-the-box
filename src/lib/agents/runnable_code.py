import lib.utils.util             as du
import lib.utils.util_code_runner as ucr

# from lib.agents.iterative_debugging_agent import IterativeDebuggingAgent

class RunnableCode:
    def __init__( self, debug=False, verbose=False ):
        
        self.debug                = debug
        self.verbose              = verbose
        
        self.prompt_response      = None
        self.prompt_response_dict = None
        
        self.code_response_dict   = None
        self.answer               = None
        self.error                = None

    def print_code( self ):
        
        du.print_banner( "Code", prepend_nl=True )
        du.print_list( self.prompt_response_dict[ "code" ] )
        
    def run_code( self, path_to_df=None, inject_bugs=False ):
        
        if self.debug: du.print_banner( f"RunnableCode.run_code( path_to_df={path_to_df}, debug={self.debug}, verbose={self.verbose} )", prepend_nl=True )
        
        self.code_response_dict = ucr.assemble_and_run_solution(
            self.prompt_response_dict[ "code" ],
            self.prompt_response_dict[ "example" ],
            path_to_df=path_to_df,
            solution_code_returns=self.prompt_response_dict.get( "returns", "string" ),
            debug=self.debug, inject_bugs=inject_bugs
        )
        if self.code_response_dict[ "return_code" ] != 0:
            self.error = self.code_response_dict[ "output" ]
            self.answer = None
        else:
            self.error = None
            self.answer = self.code_response_dict[ "output" ]
        
        if self.debug and self.verbose:
            du.print_banner("Code output", prepend_nl=True )
            for line in self.code_response_dict[ "output" ].split( "\n" ):
                print( line )
                
        return self.code_response_dict
    
    def ran_to_completion( self ):
        
        return self.code_response_dict is not None and self.code_response_dict[ "return_code" ] == 0
    
    def get_code_and_metadata( self ):
        
        return self.code_response_dict
    