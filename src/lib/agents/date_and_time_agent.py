import os
import json

import lib.utils.util as du

from lib.agents.agent_base        import AgentBase
class DateAndTimeAgent( AgentBase ):
    def __init__( self, question="", last_question_asked="", push_counter=-1, routing_command="agent router go to date and time", debug=False, verbose=False, auto_debug=False, inject_bugs=False ):
        
        super().__init__( df_path_key=None, question=question, last_question_asked=last_question_asked, routing_command=routing_command, push_counter=push_counter, debug=debug, verbose=verbose, auto_debug=auto_debug, inject_bugs=inject_bugs )
        
        self.prompt = self.prompt_template.format( question=self.question )
        self.xml_response_tag_names   = [ "thoughts", "brainstorm", "evaluation", "code", "example", "returns", "explanation" ]
    
        # self.serialize_prompt_to_json = self.config_mgr.get( "agent_todo_list_serialize_prompt_to_json", default=False, return_type="boolean" )
        # self.serialize_code_to_json   = self.config_mgr.get( "agent_todo_list_serialize_code_to_json",   default=False, return_type="boolean" )
    
    def restore_from_serialized_state( self, file_path ):
        
        raise NotImplementedError( "DateAndTimeAgent.restore_from_serialized_state() not implemented" )
    
    
if __name__ == "__main__":
    # question = "What time is it in San Francisco?"
    question = "What time is it in Washington DC?"
    date_agent = DateAndTimeAgent( question=question, routing_command="agent router go to date and time", debug=True, verbose=True, auto_debug=True )
    date_agent.run_prompt()
    date_agent.run_code()