import json

import lib.utils.util                  as du

from lib.agents.agent_base             import AgentBase
from lib.memory.input_and_output_table import InputAndOutputTable


class FunctionMapperSearch( AgentBase ):
    
    def __init__( self, question="", last_question_asked="", routing_command="agent router go to function mapping", debug=False, verbose=False, auto_debug=False, inject_bugs=False ):
        
        super().__init__( question=question, last_question_asked=last_question_asked, routing_command=routing_command, push_counter=-1, debug=debug, verbose=verbose, auto_debug=auto_debug, inject_bugs=inject_bugs )
        
        self.debug                  = debug
        self.verbose                = verbose
        self.io_tbl                 = InputAndOutputTable( debug=self.debug, verbose=self.verbose )
        self.question               = question
        self.last_question_asked    = last_question_asked
        self.prompt                 = self._get_prompt()
        self.xml_response_tag_names = [ "question", "thoughts", "can-use-available-functions", "function_name", "arguments", "example", "returns" ]
        
    def _get_prompt( self ):
        
        date_yesterday      = du.get_current_date( offset=-1 )
        date_today          = du.get_current_date()
        date_tomorrow       = du.get_current_date( offset=1 )
        date_after_tomorrow = du.get_current_date( offset=2 )
        
        tools_path            = self.config_mgr.get( "agent_function_mapping_tools_path_wo_root" )
        du.print_banner( "Using a static message list for now. This should be dynamically generated from the tools_path!", expletive=True, chunk="WARNING! " )
        function_names        = [ "search_and_summarize_the_web_for_any_topic", "get_and_summarize_weather_forecast", "query_memory_table_for_knn_topics", "query_memory_table_by_date_for_knn_topics" ]
        
        function_descriptions = du.get_file_as_string( du.get_project_root() + tools_path )
        function_descriptions = function_descriptions.format( date_today=date_today, date_tomorrow=date_tomorrow, date_after_tomorrow=date_after_tomorrow )
        
        return self.prompt_template.format( query=self.last_question_asked, function_descriptions=function_descriptions, function_names=function_names, date_yesterday=date_yesterday, date_today=date_today, date_tomorrow=date_tomorrow, date_after_tomorrow=date_after_tomorrow )
    
    def restore_from_serialized_state( file_path ):
        
        raise NotImplementedError( "FunctionMapperSearch.restore_from_serialized_state() not implemented" )
        
if __name__ == "__main__":
    
    # question = "What's Spring like in Washington DC?"
    # question = "What's the temperature in Washington DC?"
    questions = [
        # "Did we talk about sports on Monday, April 1, 2024?", "Today is Friday, April 12, 2024. Did we talk about your new job yesterday?",
        "What's the weather forecast for today?", "What's the weather forecast for tomorrow?", "What's the weather forecast for next week?",
        # "Do you remember if we talked about the weather yesterday?", "Did we talk about the weather last week?", "Do you remember the last time we talked about the weather?"
    ]
    
    for question in questions:#[ 0:1]:
        mapper = FunctionMapperSearch( question=question, last_question_asked=question, debug=True, verbose=True )
        prompt_response_dict = mapper.run_prompt()
        # print( json.dumps( prompt_response_dict, indent=4, sort_keys=True ) )