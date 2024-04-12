import os
import json

import lib.utils.util as du

from lib.agents.agent_base        import AgentBase
from lib.tools.search_gib         import GibSearch
from lib.memory.solution_snapshot import SolutionSnapshot as ss


class WeatherAgent( AgentBase ):
    def __init__( self, prepend_date_and_time=True, question="", last_question_asked="", push_counter=-1, routing_command="agent router go to weather", debug=False, verbose=False, auto_debug=False, inject_bugs=False ):
        
        # Prepend a date and time to force the cache to update on an hourly basis
        self.reformulated_last_question_asked = f"It's {du.get_current_time( format='%I:00 %p' )} on {du.get_current_date( return_prose=True )}. {last_question_asked}"
        
        super().__init__( df_path_key=None, question=question, last_question_asked=last_question_asked, routing_command=routing_command, push_counter=push_counter, debug=debug, verbose=verbose, auto_debug=auto_debug, inject_bugs=inject_bugs )
        
        self.prompt                   = None
        self.xml_response_tag_names   = []
    
        # self.serialize_prompt_to_json = self.config_mgr.get( "agent_weather_serialize_prompt_to_json", default=False, return_type="boolean" )
        # self.serialize_code_to_json   = self.config_mgr.get( "agent_weather_serialize_code_to_json",   default=False, return_type="boolean" )
    
    def restore_from_serialized_state( self, file_path ):
        
        raise NotImplementedError( "WeatherAgent.restore_from_serialized_state() not implemented" )
    
    def run_code( self, auto_debug=None, inject_bugs=None ):
        
        try:
            search   = GibSearch( query=self.reformulated_last_question_asked, debug=self.debug, verbose=self.verbose)
            search.search_and_summarize_the_web()
            response = search.get_results( scope="summary" )
            
            self.code_response_dict = {
                "output": response.replace( "\n\n", " " ).replace( "\n", " " ),
                "return_code": 0
            }
            self.answer = response
            
        except Exception as e:
            
            self.code_response_dict = {
                "output"     : e,
                "return_code": -1
            }
            self.error = e
        
        return self.code_response_dict
    
    def run_prompt( self, auto_debug=None, inject_bugs=None ):
        
        raise NotImplementedError( "WeatherAgent.run_prompt() not implemented" )
    
    def is_code_runnable( self ):
        
        return True
    
    def is_prompt_executable( self ):
        
        return False
    
    def do_all( self ):
        
        # No prompt to run just yet!
        # self.run_prompt()
        self.run_code()
        self.format_output()
        
        return self.answer_conversational
    
if __name__ == "__main__":
    
    # question      = "What's the temperature in Washington DC?"
    question      = "Is it raining in Washington DC?"
    # question      = "What's Spring like in Puerto Rico?"
    print( question )
    
    weather_agent = WeatherAgent( question=ss.remove_non_alphabetics( question ), last_question_asked=question, routing_command="agent router go to weather", debug=True, verbose=True, auto_debug=True )
    weather       = weather_agent.do_all()
    
    print( weather )
    
    
    