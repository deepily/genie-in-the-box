import os
import json

import lib.utils.util             as du
import lib.utils.util_code_runner as ucr

from lib.agents.agent_base import AgentBase
from lib.agents.llm        import Llm

class IterativeDebuggingAgent( AgentBase ):
    
    def __init__( self, error_message, path_to_code, debug=False, verbose=False ):
        
        super().__init__( routing_command="agent router go to debugger", debug=debug, verbose=verbose )
        
        self.code                   = []
        self.project_root           = du.get_project_root()
        self.path_to_code           = path_to_code
        self.formatted_code         = du.get_file_as_source_code_with_line_numbers( self.project_root + self.path_to_code )
        self.error_message          = error_message
        self.prompt                 = self._get_prompt()
        self.prompt_response_dict   = None
        self.available_llms         = self._inialize_available_llms()
        self.successfully_debugged  = False
        self.xml_response_tag_names = [ "thoughts", "code", "example", "returns", "explanation" ]
        
        self.do_not_serialize       = [ "config_mgr" ]
        
    def _inialize_available_llms( self ):
        
        # TODO: make run-time configurable, like AMPE's dynamic configuration
        prompt_run_llms = [
            { "model": Llm.PHIND_34B_v2, "short_name": "phind34b", "temperature": 0.5, "top_k": 10, "top_p": 0.25, "max_new_tokens": 1024 },
            { "model": Llm.GROQ_MIXTRAL_8X78, "short_name": "mixtral8x7", "temperature": 0.5, "top_k": 10, "top_p": 0.25, "max_new_tokens": 1024 },
            { "model": Llm.GPT_3_5, "short_name": "gpt3.5" },
            { "model": Llm.GPT_4, "short_name": "gpt4" }
        ]
        return prompt_run_llms
    
    def _get_prompt( self ):
        
        return self.prompt_template.format( error_message=self.error_message, formatted_code=self.formatted_code )
    
    def run_prompts( self, debug=None ):
        
        if debug is not None: self.debug = debug
        
        idx = 1
        self.successfully_debugged = False
        
        for llm in self.available_llms:
            
            run_descriptor = f"Run {idx} of {len( self.available_llms )}"
            
            if self.successfully_debugged:
                break
                
            model_name     = llm[ "model" ]
            short_name     = llm[ "short_name" ]
            temperature    = llm[ "temperature"    ] if "temperature"    in llm else 0.50
            top_p          = llm[ "top_p"          ] if "top_p"          in llm else 0.25
            top_k          = llm[ "top_k"          ] if "top_k"          in llm else 10
            max_new_tokens = llm[ "max_new_tokens" ] if "max_new_tokens" in llm else 1024
            
            du.print_banner( f"{run_descriptor}: Executing debugging prompt using model [{model_name}] and short name [{short_name}]...", end="\n" )
            
            prompt_response_dict = self.run_prompt( model_name=model_name, temperature=temperature, top_p=top_p, top_k=top_k, max_new_tokens=max_new_tokens )
            self.serialize_to_json( "code-debugging", du.get_current_datetime_raw(), run_descriptor=run_descriptor, short_name=short_name )
            
            code_response_dict = ucr.initialize_code_response_dict()
            if self.is_code_runnable():
                
                code_response_dict         = self.run_code()
                self.successfully_debugged = self.ran_to_completion()
                
                # Only update the code if it was successfully debugged and run to completion
                if self.successfully_debugged:
                    self.code = prompt_response_dict[ "code" ]
                    print( f"Successfully debugged? 😊¡Sí! 😊 Exiting LLM loop..." )
                else:
                    print( f"Successfully debugged? 😢¡Nooooooo! 😢 ", end="" )
                    
                    # test for the last llm in this list
                    if llm == self.available_llms[ -1 ]:
                        print( "No more LLMs to try. Exiting LLM loop..." )
                    else:
                        print( "Moving on to the next LLM..." )
            else:
                print( "Skipping code execution step because the prompt did not produce any code to run." )
                code_response_dict[ "output" ] = "Code was deemed un-runnable by iterative debugging agent"
                
            idx += 1
            
        return code_response_dict
    
    def was_successfully_debugged( self ):
        
        return self.successfully_debugged
    
    def serialize_to_json( self, topic, now, run_descriptor="Run 1 of 1", short_name="phind34b" ):

        # Convert object's state to a dictionary
        state_dict = self.__dict__

        # Convert object's state to a dictionary, omitting specified fields
        state_dict = { key: value for key, value in self.__dict__.items() if key not in self.do_not_serialize }

        # Constructing the filename, format: "topic-run-on-year-month-day-at-hour-minute-run-1-of-3-using-llm-short_name-step-N-of-M.json"
        run_descriptor = run_descriptor.replace( " ", "-" ).lower()
        short_name     = short_name.replace( " ", "-" ).lower()
        file_path       = f"{du.get_project_root()}/io/log/{topic}-on-{now.year}-{now.month}-{now.day}-at-{now.hour}-{now.minute}-{now.second}-{run_descriptor}-using-llm-{short_name}.json"

        # Serialize and save to file
        with open( file_path, 'w' ) as file:
            json.dump( state_dict, file, indent=4 )
        os.chmod( file_path, 0o666 )
        
        print( f"Serialized to {file_path}" )
    
    @staticmethod
    def restore_from_serialized_state( file_path ):
        
        print( f"Restoring from {file_path}..." )
        
        # Read the file and parse JSON
        with open( file_path, 'r' ) as file:
            data = json.load( file )
        
        # Create a new object instance with the parsed data
        restored_agent = IterativeDebuggingAgent(
            data[ "error_message" ], data[ "path_to_code" ],
            debug=data[ "debug" ], verbose=data[ "verbose" ]
        )
        # Set the remaining attributes from the parsed data, skipping the ones that we've already set
        keys_to_skip = [ "error_message", "path_to_code", "debug", "verbose" ]
        for k, v in data.items():
            if k not in keys_to_skip:
                setattr( restored_agent, k, v )
            else:
                print( f"Skipping key [{k}], it's already been set" )
        
        return restored_agent
    
    def is_code_runnable( self ):
        
        if self.prompt_response_dict is not None and len( self.prompt_response_dict[ "code" ] ) > 0:
            return True
        else:
            print( "No code to run: self.response_dict[ 'code' ] = [ ]" )
            return False
        
if __name__ == "__main__":
    
    error_message = """
    File "/Users/rruiz/Projects/projects-sshfs/genie-in-the-box/io/code.py", line 18
    mask = (df['event_type'] == 'concert') && (df['start_date'] >= start_date) && (df['start_date'] < end_date)
                                            ^
    SyntaxError: invalid syntax"""
    #     error_message = """
    #     Traceback (most recent call last):
    #   File "/Users/rruiz/Projects/projects-sshfs/genie-in-the-box/io/code.py", line 20, in <module>
    #     solution = get_concerts_this_week( df )
    #   File "/Users/rruiz/Projects/projects-sshfs/genie-in-the-box/io/code.py", line 14, in get_concerts_this_week
    #     mask = (df['event_type'] == 'concert') & (df['start_date'] >= start_date) & (df['start_date'] < end_date)
    #   File "/Users/rruiz/Projects/genie-in-the-box/venv/lib/python3.10/site-packages/pandas/core/ops/common.py", line 81, in new_method
    #     return method(self, other)
    #   File "/Users/rruiz/Projects/genie-in-the-box/venv/lib/python3.10/site-packages/pandas/core/arraylike.py", line 60, in __ge__
    #     return self._cmp_method(other, operator.ge)
    #   File "/Users/rruiz/Projects/genie-in-the-box/venv/lib/python3.10/site-packages/pandas/core/series.py", line 6096, in _cmp_method
    #     res_values = ops.comparison_op(lvalues, rvalues, op)
    #   File "/Users/rruiz/Projects/genie-in-the-box/venv/lib/python3.10/site-packages/pandas/core/ops/array_ops.py", line 279, in comparison_op
    #     res_values = op(lvalues, rvalues)
    #   File "/Users/rruiz/Projects/genie-in-the-box/venv/lib/python3.10/site-packages/pandas/core/ops/common.py", line 81, in new_method
    #     return method(self, other)
    #   File "/Users/rruiz/Projects/genie-in-the-box/venv/lib/python3.10/site-packages/pandas/core/arraylike.py", line 60, in __ge__
    #     return self._cmp_method(other, operator.ge)
    #   File "/Users/rruiz/Projects/genie-in-the-box/venv/lib/python3.10/site-packages/pandas/core/arrays/datetimelike.py", line 937, in _cmp_method
    #     return invalid_comparison(self, other, op)
    #   File "/Users/rruiz/Projects/genie-in-the-box/venv/lib/python3.10/site-packages/pandas/core/ops/invalid.py", line 36, in invalid_comparison
    #     raise TypeError(f"Invalid comparison between dtype={left.dtype} and {typ}")
    # TypeError: Invalid comparison between dtype=datetime64[ns] and date"""

    source_code_path = "/io/code.py"
    debugging_agent  = IterativeDebuggingAgent( error_message, source_code_path, debug=True, verbose=False )
    # Deserialize from file
    # debugging_agent = IterativeDebuggingAgent.restore_from_serialized_state( du.get_project_root() + "/io/log/code-debugging-on-2024-2-28-at-14-28-run-1-of-3-using-llm-phind34b-step-1-of-1.json" )
    debugging_agent.run_prompts( debug=False )
    debugging_agent.run_code()
    
    # du.print_banner( "This may fail to run the completion due to a library version conflict 😢", expletive=True )
    # print( f"Is promptable? {debugging_agent.is_prompt_executable()}, is runnable? {debugging_agent.is_code_runnable()}" )
    # prompt_response = debugging_agent.run_prompt()
    # print( f"Is promptable? {debugging_agent.is_prompt_executable()}, is runnable? {debugging_agent.is_code_runnable()}" )
    #
    # code_response     = debugging_agent.run_code()
    # ran_to_completion = debugging_agent.ran_to_completion()
    #
    # du.print_banner( f"Ran to completion? ¡{ran_to_completion}!", prepend_nl=False )
    