import os
import re
import json
import datetime

from lib.agents.xxx.xxx_data_querying_agent import XXX_DataQueryingAgent
from lib.memory.solution_snapshot         import SolutionSnapshot
from lib.agents.iterative_debugging_agent import IterativeDebuggingAgent
from lib.agents.raw_output_formatter      import RawOutputFormatter
from lib.agents.llm                       import Llm

import lib.utils.util as du
import lib.utils.util_xml as dux
import lib.utils.util_stopwatch as sw

class IncrementalCalendaringAgent( XXX_DataQueryingAgent ):
    
    def __init__( self, df_path_key="path_to_events_df_wo_root", routing_command="agent router go to calendar", question="", default_model=Llm.PHIND_34B_v2, push_counter=-1, debug=False, verbose=False, auto_debug=False, inject_bugs=False ):
        
        super().__init__( df_path_key=df_path_key, routing_command=routing_command, question=question, default_model=default_model, push_counter=push_counter, debug=debug, verbose=verbose, auto_debug=auto_debug, inject_bugs=inject_bugs )
        
        self.step_len             = -1
        self.token_count          = 0
        self.model_name           = self.config_mgr.get( "agent_model_name_for_calendaring" )
        self.project_root         = du.get_project_root()
        self.path_to_prompts      = self.config_mgr.get( "path_to_event_prompts_wo_root" )
        self.prompt_components    = None
        self.question             = SolutionSnapshot.clean_question( question )
        self.prompt_response_dict = None
        # Initialization of prompt components pushed to run_prompt
        # self.prompt_components = self._initialize_prompt_components( self.df, self.question )
        self.default_url          = self.config_mgr.get( "tgi_server_codegen_url", default=None )
        self.llm                  = Llm( model=self.model_name, default_url=self.default_url, debug=self.debug, verbose=self.verbose )
        self.do_not_serialize     = [ "df", "config_mgr", "llm" ]
    
    def serialize_to_json( self, question, current_step, total_steps, now ):
        
        # Convert object's state to a dictionary
        state_dict = self.__dict__
        
        # Remove any private attributes
        # Convert object's state to a dictionary, omitting specified fields
        state_dict = { key: value for key, value in self.__dict__.items() if key not in self.do_not_serialize }
        
        # Constructing the filename
        # Format: "question_year-month-day-hour-minute-step-N-of-M.json"
        print( f"Q: {question}" )
        # limit question to the first 96 characters
        topic     = SolutionSnapshot.clean_question( question[ :96 ] ).replace( " ", "-" )
        file_path = f"{du.get_project_root()}/io/log/{topic}-{now.year}-{now.month}-{now.day}-{now.hour}-{now.minute}-step-{(current_step + 1)}-of-{total_steps}.json"
        
        # Serialize and save to file
        with open( file_path, 'w' ) as file:
            json.dump( state_dict, file, indent=4 )
        os.chmod( file_path, 0o666 )
        
        print( f"Serialized to {file_path}" )
    
    @classmethod
    def restore_from_serialized_state( cls, file_path ):
        
        print( f"Restoring from {file_path}..." )
        
        # Read the file and parse JSON
        with open( file_path, 'r' ) as file:
            data = json.load( file )
        
        # Extract the question attribute for the constructor
        question = data.pop( 'question', None )
        if question is None:
            raise ValueError( "JSON file does not contain 'question' attribute" )
        
        # Create a new object instance with the parsed data
        restored_agent = IncrementalCalendaringAgent(
            data[ "path_to_df" ], question=data[ "last_question_asked" ], default_model=data[ "default_model" ], push_counter=data[ "push_counter" ],
            debug=data[ "debug" ], verbose=data[ "verbose" ]
        )
        # Set the remaining attributes from the parsed data, skipping the ones that we've already set
        keys_to_skip = [ "path_to_df", "last_question_asked", "default_model", "push_counter", "debug", "verbose" ]
        for k, v in data.items():
            if k not in keys_to_skip:
                setattr( restored_agent, k, v )
            else:
                print( f"Skipping key [{k}], it's already been set" )
        
        return restored_agent
    
    def _initialize_prompt_components( self ):
        
        head, value_counts = self._get_df_metadata()
        
        step_1 = du.get_file_as_string( self.project_root + self.path_to_prompts + "calendaring-step-1.txt" ).format(
            head=head, value_counts=value_counts, question=self.question
        )
        step_2 = du.get_file_as_string( self.project_root + self.path_to_prompts + "calendaring-step-2.txt" )
        step_3 = du.get_file_as_string( self.project_root + self.path_to_prompts + "calendaring-step-3.txt" )
        step_4 = du.get_file_as_string( self.project_root + self.path_to_prompts + "calendaring-step-4.txt" )
        
        xml_formatting_instructions_step_1 = du.get_file_as_string( self.project_root + self.path_to_prompts + "calendaring-xml-formatting-instructions-step-1.txt" )
        xml_formatting_instructions_step_2 = du.get_file_as_string( self.project_root + self.path_to_prompts + "calendaring-xml-formatting-instructions-step-2.txt" )
        xml_formatting_instructions_step_3 = du.get_file_as_string( self.project_root + self.path_to_prompts + "calendaring-xml-formatting-instructions-step-3.txt" )
        
        steps = [ step_1, step_2, step_3, step_4 ]
        self.step_len = len( steps )
        prompt_components = {
            "steps"                      : steps,
            "responses"                  : [ ],
            "response_tag_names"         : [ [ "thoughts" ], [ "code" ], [ "returns", "example", "explanation" ] ],
            "running_history"            : "",
            "xml_formatting_instructions": [
                xml_formatting_instructions_step_1, xml_formatting_instructions_step_2, xml_formatting_instructions_step_3
            ]
        }
        
        return prompt_components
    
    def _get_df_metadata( self ):
    
        head = self.df.head( 3 ).to_xml( index=False )
        head = head + self.df.tail( 3 ).to_xml( index=False )
        head = head.replace( "data>", "events>" ).replace( "<?xml version='1.0' encoding='utf-8'?>", "" )
        
        value_counts = self.df.event_type.value_counts()
        
        return head, value_counts
    
    def run_prompt( self ):
        
        self.prompt_components      = self._initialize_prompt_components()

        self.token_count = 0
        timer = sw.Stopwatch( msg=f"Running iterative prompt with {len( self.prompt_components[ 'steps' ] )} steps..." )
        prompt_response_dict = { }
        
        steps                       = self.prompt_components[ "steps" ]
        xml_formatting_instructions = self.prompt_components[ "xml_formatting_instructions" ]
        response_tag_names          = self.prompt_components[ "response_tag_names" ]
        responses                   = self.prompt_components[ "responses" ]
        running_history             = self.prompt_components[ "running_history" ]
        
        # Get the current time so that we can track all the steps in this iterative prompt using the same time stamp
        now = datetime.datetime.now()
        
        for step in range( len( steps ) ):
            
            if step == 0:
                # the first step doesn't have any previous responses to incorporate into it
                running_history = steps[ step ]
            else:
                # incorporate the previous response into the current step, then append it to the running history
                running_history = running_history + steps[ step ].format( response=responses[ step - 1 ] )
                
            # we're not going to execute the last step, it's been added just to keep the running history current
            if step != len( steps ) - 1:
                
                response = self.llm.query_llm( prompt=running_history + xml_formatting_instructions[ step ], debug=self.debug, verbose=self.verbose )
                # response = self._query_llm_phind( running_history, xml_formatting_instructions[ step ], debug=self.debug, verbose=self.verbose )
                responses.append( response )
                
                # Incrementally update the contents of the response dictionary according to the results of the XML-esque parsing
                prompt_response_dict = self._update_response_dictionary(
                    step, response, prompt_response_dict, response_tag_names, debug=False
                )
            
            # Update the prompt component's state before serializing a copy of it
            self.prompt_components[ "running_history" ] = running_history
            self.prompt_response_dict = prompt_response_dict
            
            self.serialize_to_json( self.question, step, self.step_len, now )
            
        tokens_per_second = self.token_count / ( timer.get_delta_ms() / 1000.0 )
        timer.print( f"Done! Tokens per second [{round( tokens_per_second, 1 )}]", use_millis=True, prepend_nl=True )
        
        return self.prompt_response_dict

    # def _query_llm_phind( self, preamble, instructions, model=Llm.PHIND_34B_v2, temperature=0.50, max_new_tokens=1024, debug=False, verbose=False ):
    #
    #     timer = sw.Stopwatch( msg=f"Asking LLM [{model}]..." )
    #
    #     # Get the TGI server URL for this context
    #     default_url    = self.config_mgr.get( "tgi_server_codegen_url", default=None )
    #     tgi_server_url = du.get_tgi_server_url_for_this_context( default_url=default_url )
    #
    #     client         = InferenceClient( tgi_server_url )
    #     token_list     = [ ]
    #
    #     prompt = f"{preamble}{instructions}\n"
    #     if debug and verbose: print( prompt )
    #
    #     for token in client.text_generation(
    #         prompt, max_new_tokens=max_new_tokens, stream=True, stop_sequences=[ "</response>" ], temperature=temperature
    #     ):
    #         print( token, end="" )
    #         token_list.append( token )
    #
    #     response         = "".join( token_list ).strip()
    #     self.token_count = self.token_count + len( token_list )
    #
    #     print()
    #     print( f"Response tokens [{len( token_list )}]" )
    #     timer.print( "Done!", use_millis=True, prepend_nl=True )
    #
    #     return response
    
    def _update_response_dictionary( self, step, response, prompt_response_dict, tag_names, debug=True ):
    
        if debug: print( f"update_response_dictionary called with step [{step}]..." )
        
        # Parse response and update response dictionary
        xml_tags_for_step_n = tag_names[ step ]
        
        for xml_tag in xml_tags_for_step_n:
            
            if debug: print( f"Looking for xml_tag [{xml_tag}]" )
            
            if xml_tag == "code":
                # the get_code method expects enclosing tags
                xml_string = "<code>" + dux.get_value_by_xml_tag_name( response, xml_tag ) + "</code>"
                prompt_response_dict[ xml_tag ] = dux.get_code_list( xml_string, debug=debug )
            else:
                prompt_response_dict[ xml_tag ] = dux.get_value_by_xml_tag_name( response, xml_tag ).strip()

        return prompt_response_dict
    
    def _get_code( self, xml_string, debug=False ):
    
        skip_list = []#[ "import pandas", "import datetime" ]
        
        # Matches all text between the opening and closing line tags, including the white space after the opening line tag
        pattern   = re.compile( r"<line>(.*?)</line>" )
        code      = dux.get_value_by_xml_tag_name( xml_string, "code" )
        code_list = []
    
        for line in code.split( "\n" ):
    
            match = pattern.search( line )
            
            for skip in skip_list:
                if skip in line:
                    if debug: print( f"[SKIPPING '{skip}']" )
                    match = None
                    break
                    
            if match:
                line = match.group( 1 )
                # replace the XML escape sequences with their actual characters
                line = line.replace( "&gt;", ">" ).replace( "&lt;", "<" ).replace( "&amp;", "&" )
                code_list.append( line )
                if debug: print( line )
            else:
                code_list.append( "" )
                if debug: print( "[]" )
    
        return code_list
    
    def run_code( self, auto_debug=None, inject_bugs=None ):
        
        # Use this object's settings, if overriding values not provided
        if auto_debug  is None: auto_debug  = self.auto_debug
        if inject_bugs is None: inject_bugs = self.inject_bugs
        
        # TODO: figure out where this should live, i suspect it will be best located in util_code_runner.py
        print( f"Executing super().run_code() with inject_bugs [{inject_bugs}] and auto_debug [{auto_debug}]...")
        path_to_df = self.config_mgr.get( "path_to_events_df_wo_root" )
        code_response_dict = super().run_code( path_to_df=path_to_df, inject_bugs=inject_bugs )
        if self.ran_to_completion():
            
            self.error  = None
            return self.code_response_dict
            
        elif auto_debug:
            
            self.error = self.code_response_dict[ "output" ]
            
            debugging_agent = IterativeDebuggingAgent( code_response_dict[ "output" ], "/io/code.py", debug=self.debug, verbose=self.verbose )
            debugging_agent.run_prompts()
            
            if debugging_agent.was_successfully_debugged():
                
                self.code_response_dict = debugging_agent.get_code_and_metadata()
                self.error              = None

            else:
                
                du.print_banner( "Debugging failed, returning original code, such as it is... 😢 sniff 😢" )
                
        return self.code_response_dict
    
    def format_output( self ):

        formatter = RawOutputFormatter( self.last_question_asked, self.code_response_dict[ "output" ], self.routing_command )
        self.answer_conversational = formatter.format_output()
        
        # if we've just received an xml-esque string then pull `<rephrased_answer>` from it. Otherwise, just return the string
        if self.debug and self.verbose: print( f" PRE self.answer_conversational: [{self.answer_conversational}]" )
        self.answer_conversational = dux.get_value_by_xml_tag_name( self.answer_conversational, "rephrased-answer", default_value=self.answer_conversational )
        if self.debug and self.verbose: print( f"POST self.answer_conversational: [{self.answer_conversational}]" )
        
        return self.answer_conversational
        
if __name__ == "__main__":
    
    # question        = "How many birthdays are on my calendar this month?"
    # question        = "How many birthdays do I have on my calendar this month?"
    # question        = "What birthdays do I have on my calendar this week?"
    # question        = "Who has birthdays this week?"
    question         = "Do i have any concerts this week?"
    agent            = IncrementalCalendaringAgent( question=question, debug=True, verbose=True, auto_debug=True, inject_bugs=False )
    prompt_response  = agent.run_prompt()
    code_response    = agent.run_code( auto_debug=True, inject_bugs=False )
    formatted_output = agent.format_output()
    
    du.print_banner( f"code_response[ 'return_code' ] = [{code_response[ 'return_code' ]}]", prepend_nl=False )
    for line in code_response[ "output" ].split( "\n" ):
        print( line )
        
    du.print_banner( question, prepend_nl=False )
    for line in formatted_output.split( "\n" ):
        print( line )
    #
    # # code_response_dict = prompt_response_dict[ "code" ]
    #
    # du.print_banner( "Done! prompt_response_dict:", prepend_nl=True )
    # print( prompt_response_dict )
    