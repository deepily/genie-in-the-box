import os
import json

import lib.utils.util             as du
import lib.utils.util_stopwatch   as sw
import lib.utils.util_code_runner as ucr

from lib.agents.agent      import Agent

import lib.utils.util_xml as dux
class IterativeDebuggingAgent( Agent ):
    
    def __init__( self, error_message, path_to_code, debug=False, verbose=False ):
        
        super().__init__( debug=debug, verbose=verbose )
        
        self.code                  = []
        self.path_to_code          = path_to_code
        self.formatted_code        = du.get_file_as_source_code_with_line_numbers( self.path_to_code )
        self.token_count           = 0
        self.prompt_components     = None
        self.prompt_response_dict  = None
        self.available_llms        = self._inialize_available_llms()
        self.error_message         = error_message
        self.successfully_debugged = False
        
        self.do_not_serialize     = []
        
    def _inialize_available_llms( self ):
        
        # TODO: make run-time configurable, like AMPE's dynamic configuration
        prompt_run_llms = [
            { "model": Agent.PHIND_34B_v2, "short_name": "phind34b", "temperature": 0.5, "top_k": 10, "top_p": 0.25, "max_new_tokens": 1024 },
            { "model": Agent.GPT_3_5, "short_name": "gpt3.5" },
            { "model": Agent.GPT_4, "short_name": "gpt4" }
        ]
        return prompt_run_llms
    
    def _initialize_prompt_components( self ):
        
        step_1 = f"""
        You are a cheerful and helpful assistant, with proven expertise using Python to query pandas dataframes.
        
        Your job is to debug the code that produced the following error message and generate valid Python code that will correct the bug. You will return your response to each question using XML format.
        
        {self.error_message}
        
Source code:
{self.formatted_code}
        
        In order to successfully address the error message above, you must follow my instructions step by step. As you complete each step I will recount your progress on the previous steps and provide you with the next step's instructions.
        
        Step one) Think: think out loud about what you are being asked, including what are the steps that you will need to take to solve this problem. Be critical of your thought process!
        
        Hint: When joining multiple filtering condition clauses in pandas, you must use the single bitwise operators `&` and `|` instead of the double logical operators `&&` and `||`.
        """
        
        xml_formatting_instructions_step_1 = """
        You must respond to the step one directive using the following XML format:
        <response>
            <thoughts>Your thoughts</thoughts>
        </response>
        
        Begin!
        """
        step_2 = """
        In response to the instructions that you received for step one you replied:
        
        {response}
        
        Step two) Code: Now that you have thought about how you are going to solve the problem, it's time to generate the Python code that fix the buggy code. The code must be complete, syntactically correct, and capable of running to completion. The last line of your function code must be `return solution`. Remember: You must make the least amount of changes that will fix the bug
        """
        xml_formatting_instructions_step_2 = """
        You must respond to the step 2 directive using the following XML format:
        <response>
            <code>
                <line>def function_name_here( df, arg1 ):</line>
                <line>    ...</line>
                <line>    ...</line>
                <line>    return solution</line>
                <line>solution = function_name_here( df, arg1 )</line>
                <line>print( solution )</line>
            </code>
        </response>
        
        Begin!
        """
        
        step_3 = """
        In response to the instructions that you received for step two, you replied:

        {response}

        Now that you have generated the code that addresses the bug mentioned above, you will need to perform the following three steps:

        Step three) Return: Report on the object type of the variable `solution` returned in your last line of code. Use one word to represent the object type.

        Step four) Example: Create a one line example of how to call your code.

        Step five) Explain: Explain how your code works, including any assumptions that you have made.
        """
        xml_formatting_instructions_step_3 = """
        You must respond to the directives in steps three, four and five using the following XML format:

        <response>
            <returns>Object type of the variable `solution`</returns>
            <example>solution = function_name_here( arguments )</example>
            <explanation>Explanation of how the code works</explanation>
        </response>

        Begin!
        """
        
        step_4 = """
        In response to the instructions that you received for step three, you replied:

        {response}

        Congratulations! We're finished 😀

        """
        
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
    
    def run_prompts( self ):
        
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
            
            prompt_response_dict = self.run_prompt( run_descriptor=run_descriptor, model=model_name, short_name=short_name, temperature=temperature, top_p=top_p, top_k=top_k, max_new_tokens=max_new_tokens )
            
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
    
    def run_prompt( self, run_descriptor="Run 1 of 1", model=Agent.PHIND_34B_v2, short_name="phind34b", max_new_tokens=1024, temperature=0.5, top_p=0.25, top_k=10, debug=False ):
        
        self.prompt_components      = self._initialize_prompt_components()
        
        steps                       = self.prompt_components[ "steps" ]
        xml_formatting_instructions = self.prompt_components[ "xml_formatting_instructions" ]
        response_tag_names          = self.prompt_components[ "response_tag_names" ]
        responses                   = self.prompt_components[ "responses" ]
        running_history             = self.prompt_components[ "running_history" ]
        timer                       = sw.Stopwatch( msg=f"Executing iterative prompt(s) on {short_name} with {len( steps )} steps..." )
        
        self.token_count            = 0
        prompt_response_dict        = { }
        
        # Get the current time so that we can track all the steps in this iterative prompt using the same timestamp
        now = du.get_current_datetime_raw()
        
        for step in range( len( steps ) ):
            
            print()
            print( f"Step [{step + 1}] of [{len( steps )}]" )
            if step == 0:
                # the first step doesn't have any previous responses to incorporate into it
                running_history = steps[ step ]
            else:
                # incorporate the previous response into the current step, then append it to the running history
                running_history = running_history + steps[ step ].format( response=responses[ step - 1 ] )
            
            # we're not going to execute the last step, it's been added just to keep the running history current
            if step != len( steps ) - 1:
                
                response = self._query_llm(
                    running_history, xml_formatting_instructions[ step ], model=model, max_new_tokens=max_new_tokens, temperature=temperature, top_p=top_p, top_k=top_k, debug=debug
                )
                responses.append( response )
                
                # Incrementally update the contents of the response dictionary according to the results of the XML-esque parsing
                prompt_response_dict = self._update_response_dictionary(
                    step, response, prompt_response_dict, response_tag_names, debug=debug
                )
            else:
                if debug:
                    print( "LAST STEP: Skipping execution. Response from the previous step:" )
                    print( responses[ step - 1 ] )
            
            # Update the prompt component's state before serializing a copy of it
            self.prompt_components[ "running_history" ] = running_history
            self.prompt_response_dict = prompt_response_dict
            
            self.serialize_to_json( "code-debugging", step, self.step_len, now, run_descriptor=run_descriptor, short_name=short_name )
            
        timer.print( "Done!", use_millis=True, prepend_nl=False )
        # tokens_per_second = self.token_count / (timer.get_delta_ms() / 1000.0 )
        # print( f"Tokens per second [{round( tokens_per_second, 1 )}]" )
        
        return self.prompt_response_dict
    
    def _update_response_dictionary( self, step, response, prompt_response_dict, tag_names, debug=True ):
        
        if debug: print( f"update_response_dictionary called with step [{step}]..." )

        # Parse response and update response dictionary
        xml_tags_for_step_n = tag_names[ step ]

        for xml_tag in xml_tags_for_step_n:

            if debug: print( f"Looking for xml_tag [{xml_tag}]" )

            if xml_tag == "code":
                
                xml_string = dux.get_value_by_xml_tag_name( response, xml_tag, default_value="" )
                if xml_string == "":
                    print( f"WARNING: No <code> tags found, falling back to the default tick tick tick syntax..." )
                    xml_string = dux.rescue_code_using_tick_tick_tick_syntax( response, debug=debug )
                    # TODO: Find a principal the way to update the response object with the newly rescued and reformatted code
                
                # the get_code method expects enclosing tags
                xml_string = "<code>" + xml_string + "</code>"
                prompt_response_dict[ xml_tag ] = dux.get_code_list( xml_string, debug=debug )
                
                # # the get_code method expects enclosing tags
                # xml_string = "<code>" + dux.get_value_by_xml_tag_name( response, xml_tag ) + "</code>"
                # prompt_response_dict[ xml_tag ] = dux.get_code_list( xml_string, debug=debug )
            else:
                prompt_response_dict[ xml_tag ] = dux.get_value_by_xml_tag_name( response, xml_tag ).strip()

        return prompt_response_dict
    
    def serialize_to_json( self, topic, current_step, total_steps, now, run_descriptor="Run 1 of 1", short_name="phind34b" ):

        # Convert object's state to a dictionary
        state_dict = self.__dict__

        # Convert object's state to a dictionary, omitting specified fields
        state_dict = { key: value for key, value in self.__dict__.items() if key not in self.do_not_serialize }

        # Constructing the filename, format: "topic-run-on-year-month-day-at-hour-minute-run-1-of-3-using-llm-short_name-step-N-of-M.json"
        run_descriptor = run_descriptor.replace( " ", "-" ).lower()
        short_name     = short_name.replace( " ", "-" ).lower()
        file_path       = f"{du.get_project_root()}/io/log/{topic}-on-{now.year}-{now.month}-{now.day}-at-{now.hour}-{now.minute}-{run_descriptor}-using-llm-{short_name}-step-{( current_step + 1 )}-of-{total_steps}.json"

        # Serialize and save to file
        with open( file_path, 'w' ) as file:
            json.dump( state_dict, file, indent=4 )
        os.chmod( file_path, 0o666 )
        
        print( f"Serialized to {file_path}" )
        
    def _get_system_message( self ):
        
        print( " _get_system_message NOT implemented" )
        
    def _get_user_message( self ):
        
        print( " _get_user_message NOT implemented" )
        
    def format_output( self ):
        
        print( " format_output NOT implemented" )
        
    def is_code_runnable( self ):
        
        if self.prompt_response_dict is not None and len( self.prompt_response_dict[ "code" ] ) > 0:
            return True
        else:
            print( "No code to run: self.response_dict[ 'code' ] = [ ]" )
            return False
        
    def is_prompt_executable( self ):
        
        return self.prompt_components is not None
        
if __name__ == "__main__":
    
#     error_message = """
# ERROR executing code:
#
# File "/Users/rruiz/Projects/projects-sshfs/genie-in-the-box/io/code.py", line 12
#     mask = (df['start_date'] <= today) && (df['end_date'] >= today)
#                                         ^
# SyntaxError: invalid syntax"""
    
    error_message = ""
    
    debugging_agent = IterativeDebuggingAgent( error_message, du.get_project_root() + "/io/code.py", debug=False, verbose=False )
    
    debugging_agent.run_prompts()
    
    # du.print_banner( "This may fail to run the completion due to a library version conflict 😢", expletive=True )
    # print( f"Is promptable? {debugging_agent.is_prompt_executable()}, is runnable? {debugging_agent.is_code_runnable()}" )
    # prompt_response = debugging_agent.run_prompt()
    # print( f"Is promptable? {debugging_agent.is_prompt_executable()}, is runnable? {debugging_agent.is_code_runnable()}" )
    #
    # code_response     = debugging_agent.run_code()
    # ran_to_completion = debugging_agent.ran_to_completion()
    #
    # du.print_banner( f"Ran to completion? ¡{ran_to_completion}!", prepend_nl=False )
    