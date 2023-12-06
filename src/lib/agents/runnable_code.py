import lib.utils.util as du
import lib.utils.util_code_runner as ucr
class RunnableCode:
    def __init__( self, debug=False, verbose=False ):
        
        self.debug                = debug
        self.verbose              = verbose
        
        # self.code                 = None
        
        self.prompt_response      = None
        self.prompt_response_dict = None
        
        self.code_response_dict   = None
        self.answer               = None
        # self.answer_conversational= None
        self.error                = None

    def print_code( self ):
        
        du.print_banner( "Code", prepend_nl=True )
        for line in self.prompt_response_dict[ "code" ]: print( line )
        
    def run_code( self ):
        
        self.code_response_dict = ucr.assemble_and_run_solution(
            self.prompt_response_dict[ "code" ],
            self.prompt_response_dict[ "example" ],
            path="/src/conf/long-term-memory/events.csv",
            solution_code_returns=self.prompt_response_dict.get( "returns", "" ),
            debug=self.debug
        )
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
    