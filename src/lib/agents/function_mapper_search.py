from lib.agents.agent_base             import AgentBase
from lib.memory.input_and_output_table import InputAndOutputTable


class FunctionMapperSearch( AgentBase ):
    
    def __init__( self, question="", last_question_asked="", debug=False, verbose=False, auto_debug=False, inject_bugs=False):
        
        super().__init__( question=None, last_question_asked=None, routing_command=None, push_counter=-1, debug=debug, verbose=verbose, auto_debug=auto_debug, inject_bugs=inject_bugs )
        
        self.debug               = debug
        self.verbose             = verbose
        self.io_tbl              = InputAndOutputTable( debug=self.debug, verbose=self.verbose )
        self.question            = question
        self.last_question_asked = last_question_asked
        self.prompt              = self._get_prompt()
        
    def _get_prompt( self ):
        
        function_descriptions = self._get_df_metadata()
        
        return self.prompt_template.format( query=self.last_question_asked, function_descriptions=function_descriptions )
    
    def _get_metadata( self ):
        
        pass
        
        