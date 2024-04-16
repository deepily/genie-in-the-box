import json

import lib.utils.util                  as du

from lib.utils.util_stopwatch          import Stopwatch
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
        self.xml_response_tag_names = [ "thoughts", "can-use-available-functions", "function_name", "kwargs", "example", "returns" ]
        
    def _get_prompt( self ):
        
        date_yesterday      = du.get_current_date( offset=-1 )
        date_today          = du.get_current_date()
        date_tomorrow       = du.get_current_date( offset=1 )
        # date_after_tomorrow = du.get_current_date( offset=2 )
        
        tools_path            = self.config_mgr.get( "agent_function_mapping_tools_path_wo_root" )
        du.print_banner( "Using a static function_names list for now. This should be dynamically generated from the tools_path!", expletive=True, chunk="WARNING! " )
        function_names        = [ "search_and_summarize_the_web_for_any_topic", "search_and_summarize_weather", "query_memory_table_for_knn_topics" ]
        
        function_descriptions = du.get_file_as_string( du.get_project_root() + tools_path )
        function_descriptions = function_descriptions.format( date_today=date_today, date_tomorrow=date_tomorrow )
        
        return self.prompt_template.format( query=self.last_question_asked, function_descriptions=function_descriptions, function_names=function_names, date_yesterday=date_yesterday, date_today=date_today, date_tomorrow=date_tomorrow )
    
    def restore_from_serialized_state( file_path ):
        
        raise NotImplementedError( "FunctionMapperSearch.restore_from_serialized_state() not implemented" )
        
if __name__ == "__main__":
    
    # question = "What's Spring like in Washington DC?"
    # question = "What's the temperature in Washington DC?"
    questions = [
        "What does the term 'drama queen' mean?", "How do you say good morning in Spanish?", "What's the capital of France?", "What's the population of New York City?", "What's the population of Los Angeles?",
        "Who won the big game yesterday?", "How is DC United doing this season", "Who won Yesterdays presidential debate?", "What does my choice of words say about me?", "What song is number one on the Billboard top 40 chart?",
        "Did we talk about sports on Monday, April 1, 2024?", "Did we talk about your new job on Friday, April 12, 2024?",
        "What's today's forecast for Washington DC?", "What's the temperature in DC?", "Is the sun shining today?", "What's the weather like this time of year in DC?",
        # "What's the weather forecast for today?", "What's the weather forecast for tomorrow?", "What's the weather forecast for next week?",
        "Do you remember if we talked about the weather yesterday?", "Did we talk about the weather last week?", "Do you remember the last time we talked about the weather?"
    ]
    timer = Stopwatch( msg=f"Testing function mapping for {len(questions)} questions..." )
    for question in questions:#[ 0:1]:
        mapper = FunctionMapperSearch( question=question, last_question_asked=question, debug=False, verbose=False )
        prompt_response_dict = mapper.run_prompt()
        # print( json.dumps( prompt_response_dict, indent=4, sort_keys=True ) )
        du.print_banner( f"Question: {question}" )
        for item in mapper.xml_response_tag_names:
            print( f"{item}: {prompt_response_dict[ item ].strip()}" )
            
    timer.print( msg="Done!", use_millis=False )
    # Calculate average time for a question
    # Format So that milliseconds have a comma inserted every three digits
    print( f"Average time per question: {round( timer.get_delta_ms() / len(questions), 0):,} ms" )