import abc
import json
import os

import pandas as pd

import lib.utils.util               as du
import lib.utils.util_pandas        as dup
import lib.utils.util_xml           as dux
import lib.memory.solution_snapshot as ss

from lib.agents.llm                  import Llm
from lib.agents.raw_output_formatter import RawOutputFormatter
from lib.agents.runnable_code        import RunnableCode
from lib.app.configuration_manager   import ConfigurationManager
from lib.memory.solution_snapshot    import SolutionSnapshot

class AgentBase( RunnableCode, abc.ABC ):
    
    # DEFAULT_MODEL = Llm.PHIND_34B_v2
    
    def __init__( self, df_path_key=None, question="", push_counter=-1, routing_command=None, debug=False, verbose=False, auto_debug=False, inject_bugs=False ):
        
        self.debug                 = debug
        self.verbose               = verbose
        self.auto_debug            = auto_debug
        self.inject_bugs           = inject_bugs
        self.df_path_key           = df_path_key
        self.routing_command       = routing_command
        
        # Added to allow behavioral compatibility with solution snapshot object
        self.run_date              = ss.SolutionSnapshot.get_timestamp()
        self.push_counter          = push_counter
        self.id_hash               = ss.SolutionSnapshot.generate_id_hash( self.push_counter, self.run_date )
        
        self.last_question_asked   = question # This is a bit of a misnomer, it's the unprocessed question that was asked of the agent
        self.question              = ss.SolutionSnapshot.clean_question( question )
        self.answer_conversational = None
        
        self.config_mgr            = ConfigurationManager( env_var_name="GIB_CONFIG_MGR_CLI_ARGS" )
        
        self.df                    = None
        self.do_not_serialize      = [ "df", "config_mgr" ]
        
        # ¡OJO! This one server a key may need to become more diversified in the future
        self.default_url           = self.config_mgr.get( "tgi_server_codegen_url", default=None )
        
        self.prompt_template_paths = {
            "agent router go to date and time": self.config_mgr.get( "agent_prompt_for_date_and_time" ),
            "agent router go to calendar"     : self.config_mgr.get( "agent_prompt_for_calendaring" ),
            "agent router go to weather"      : self.config_mgr.get( "agent_prompt_for_weather" ),
            "agent router go to todo list"    : self.config_mgr.get( "agent_prompt_for_todo_list" ),
            "agent router go to debugger"     : self.config_mgr.get( "agent_prompt_for_debugger" ),
            "agent router go to bug injector" : self.config_mgr.get( "agent_prompt_for_bug_injector" ),
        }
        self.models = {
            "agent router go to date and time": self.config_mgr.get( "agent_model_name_for_date_and_time" ),
            "agent router go to calendar"     : self.config_mgr.get( "agent_model_name_for_calendaring" ),
            "agent router go to weather"      : self.config_mgr.get( "agent_model_name_for_weather" ),
            "agent router go to todo list"    : self.config_mgr.get( "agent_model_name_for_todo_list" ),
            "agent router go to debugger"     : self.config_mgr.get( "agent_model_name_for_debugger" ),
            "agent router go to bug injector" : self.config_mgr.get( "agent_model_name_for_bug_injector" ),
        }
        self.serialization_topics = {
            "agent router go to date and time": "date-and-time",
            "agent router go to calendar"     : "calendar",
            "agent router go to weather"      : "weather",
            "agent router go to todo list"    : "todo-list",
            "agent router go to debugger"     : "code-debugger",
            "agent router go to bug injector" : "bug-injector",
        }
        self.model_name              = self.models[ routing_command ]
        self.prompt_template         = du.get_file_as_string( du.get_project_root() + self.prompt_template_paths[ routing_command ] )
        self.prompt                  = None
        
        if self.df_path_key is not None:
            
            self.df = pd.read_csv( du.get_project_root() + self.config_mgr.get( self.df_path_key ) )
            self.df = dup.cast_to_datetime( self.df )
    
    def get_html( self ):
        
        return f"<li id='{self.id_hash}'>{self.run_date} Q: {self.last_question_asked}</li>"
    
    @abc.abstractmethod
    def restore_from_serialized_state( file_path ):
        pass
    
    def serialize_to_json( self, subtopic=None ):

        # Convert object's state to a dictionary
        state_dict = self.__dict__

        # Convert object's state to a dictionary, omitting specified fields
        state_dict = { key: value for key, value in self.__dict__.items() if key not in self.do_not_serialize }

        # Constructing the filename
        # Format: "topic-year-month-day-hour-minute-second.json", limit question to the first 96 characters
        question_short = SolutionSnapshot.clean_question( self.question[ :96 ] ).replace( " ", "-" )
        topic          = self.serialization_topics[ self.routing_command ]
        topic          = topic + "-" + subtopic if subtopic is not None else topic
        now            = du.get_current_datetime_raw()
        file_path = f"{du.get_project_root()}/io/log/{topic}-{question_short}-{now.year}-{now.month}-{now.day}-{now.hour}-{now.minute}-{now.second}.json"

        # Serialize and save to file
        with open( file_path, 'w' ) as file:
            json.dump( state_dict, file, indent=4 )
        os.chmod( file_path, 0o666 )

        print( f"Serialized to {file_path}" )
        
    def _update_response_dictionary( self, response ):
        
        if self.debug: print( f"update_response_dictionary called..." )
        
        prompt_response_dict = { }
        
        for xml_tag in self.xml_response_tag_names:
            
            if self.debug: print( f"Looking for xml_tag [{xml_tag}]" )
            
            if xml_tag == "code":
                # the get_code method expects enclosing tags
                xml_string = "<code>" + dux.get_value_by_xml_tag_name( response, xml_tag ) + "</code>"
                prompt_response_dict[ xml_tag ] = dux.get_code_list( xml_string, debug=self.debug )
            else:
                prompt_response_dict[ xml_tag ] = dux.get_value_by_xml_tag_name( response, xml_tag ).strip()
        
        return prompt_response_dict
    
    def run_prompt( self, model_name=None, temperature=0.5, top_p=0.25, top_k=10, max_new_tokens=1024, stop_sequences=None ):
        
        # from lib.agents.llm import Llm
        
        if model_name is not None: self.model_name = model_name
        
        llm = Llm( config_mgr=self.config_mgr, model=self.model_name, default_url=self.default_url, debug=self.debug, verbose=self.verbose )
        response = llm.query_llm( prompt=self.prompt, temperature=temperature, top_p=top_p, top_k=top_k, max_new_tokens=max_new_tokens, stop_sequences=stop_sequences, debug=self.debug, verbose=self.verbose )
        
        self.prompt_response_dict = self._update_response_dictionary( response )
        
        return self.prompt_response_dict
    
    def is_code_runnable( self ):
        pass
    
    def run_code( self, auto_debug=None, inject_bugs=None ):
        
        # Use this object's settings, if temporary overriding values aren't provided
        if auto_debug  is None: auto_debug  = self.auto_debug
        if inject_bugs is None: inject_bugs = self.inject_bugs
        
        # TODO: figure out where this should live, i suspect it will be best located in util_code_runner.py
        if self.debug: print( f"Executing super().run_code() with inject_bugs [{inject_bugs}] and auto_debug [{auto_debug}]..." )
        
        if self.df_path_key is not None:
            path_to_df = self.config_mgr.get( self.df_path_key, default=None )
        else:
            path_to_df = None
            
        code_response_dict = super().run_code( path_to_df=path_to_df, inject_bugs=inject_bugs )
        
        if self.ran_to_completion():
            
            self.error = None
            return self.code_response_dict
        
        elif auto_debug:
            
            from lib.agents.iterative_debugging_agent import IterativeDebuggingAgent

            self.error = self.code_response_dict[ "output" ]
            
            debugging_agent = IterativeDebuggingAgent(
                code_response_dict[ "output" ], "/io/code.py", debug=self.debug, verbose=self.verbose
            )
            debugging_agent.run_prompts()
            
            if debugging_agent.was_successfully_debugged():
                
                self.prompt_response_dict[ "code" ] = debugging_agent.code
                self.code_response_dict             = debugging_agent.code_response_dict
                self.error                          = None
                
                self.print_code( msg="Debugging successful, corrected code returned to AgentBase:" )
                
            else:
                
                du.print_banner( "Debugging failed, returning original code, such as it is... 😢 sniff 😢" )
        
        return self.code_response_dict
    
    def is_format_output_runnable( self ):
        pass
    
    def format_output( self ):
        
        formatter = RawOutputFormatter( self.last_question_asked, self.code_response_dict[ "output" ], self.routing_command, debug=self.debug, verbose=self.verbose )
        self.answer_conversational = formatter.format_output()
        
        return self.answer_conversational