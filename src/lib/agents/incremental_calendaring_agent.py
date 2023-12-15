import os
import re
import json
import datetime

from lib.agents.calendaring_agent         import CalendaringAgent
from lib.memory.solution_snapshot         import SolutionSnapshot
from lib.agents.agent                     import Agent
from lib.agents.iterative_debugging_agent import IterativeDebuggingAgent

import lib.utils.util as du
import lib.utils.util_xml as dux
import lib.utils.util_stopwatch as sw

from huggingface_hub import InferenceClient

class IncrementalCalendaringAgent( CalendaringAgent ):
    
    def __init__( self, path_to_df, question="", default_model=Agent.PHIND_34B_v2, push_counter=-1, debug=False, verbose=False ):
        
        super().__init__( path_to_df, question=question, default_model=default_model, push_counter=push_counter, debug=debug, verbose=verbose )
        
        self.step_len             = -1
        self.token_count          = 0
        self.prompt_components    = None
        self.question             = SolutionSnapshot.clean_question( question )
        self.prompt_response_dict = None
        # Initialization of prompt components pushed to run_prompt
        # self.prompt_components = self._initialize_prompt_components( self.df, self.question )
        self.do_not_serialize     = [ "df" ]
    
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
    
    def _initialize_prompt_components( self, df ):
        
        head, event_value_counts = self._get_df_metadata( df )
        
        # The only Python libraries that you may use: You must only use the datetime and Pandas libraries, which have been imported in the following manner: `import pandas as pd` and`import datetime as dt`.
        step_1 = f"""
        You are a cheerfully and helpful assistant, with proven expertise using Python to query pandas dataframes.
        
        Your job is to translate human questions about calendars, dates, and events into a self-contained Python functions that can be used to answer the question now and reused in the future.
        
        About the Pandas dataframe: The name of the events dataframe is `df` and is already loaded in memory ready to be queried.
        
        Here are some hints to keep in mind and guide you as you craft your solution:
        Start and end dates: An event that I have today may have started before today and may end tomorrow or next week, so be careful how you filter on dates.
        Filtering: When filtering by dates, use `pd.Timestamp( day )` to convert a Python datetime object into a Pandas `datetime64[ns]` value.
        Return values: You should always return a dataframe, and it must always include all columns in the dataframe, and never a subset.
        
        This is the ouput from `print(df.head().to_xml())`, in XML format:
        {head}
        
        This is the output from `print(self.df.event_type.value_counts())`:
        
        {event_value_counts}
        
        Given the context I have provided above, I want you to write a Python function to answer the following question:
        
        Question: `{self.question}`
        
        In order to successfully write a function that answers the question above, you must follow my instructions step by step. As you complete each step I will recount your progress on the previous steps and provide you with the next step's instructions.
        
        Step one) Think: think out loud about what the question means in technical terms, in addition to what are the steps that you will need to take in your code to solve this problem. Be critical of your thought process! And make sure to consider what you will call the entry point to your python solution, such as `def get_events_for_today( df )`, or `def get_events_for_tomorrow( df )`, `def count_appointments_this_month( df )`, or `def get_events_for_this_week( df )` or even `def get_birthday_for( df, name )`.
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
        
        Step two) Code: Now that you have thought about how you are going to solve the problem, it's time to generate the Python code that you will use to arrive at your answer. The code must be complete, syntactically correct, and capable of running to completion. The last line of your function code must be `return solution`.  Remember: You must never return a subset of a dataframe's columns.
        """
        xml_formatting_instructions_step_2 = """
        You must respond to the step 2 directive using the following XML format:
        <response>
            <code>
                <line>def function_name_here( df, arg1, arg2 ):</line>
                <line>    ...</line>
                <line>    ...</line>
                <line>    return solution</line>
            </code>
        </response>
        
        Begin!
        """
        
        step_3 = """
        In response to the instructions that you received for step two, you replied:
        
        {response}
        
        Now that you have generated the code, you will need to perform the following three steps:
        
        Step three) Return: Report on the object type of the variable `solution` returned in your last line of code. Use one word to represent the object type.
        
        Step four) Example: Create a one line example of how to call your code.
        
        Step five) Explain: Explain how your code works, including any assumptions that you have made.
        """
        xml_formatting_instructions_step_3 = """
        You must respond to the directives in steps three, four and five using the following XML format:
        
        <response>
            <returns>Object type of the variable `solution`</returns>
            <example>One-line example of how to call your code: solution = function_name_here( arguments )</example>
            <explanation>Explanation of how the code works</explanation>
        </response>
        
        Begin!
        """
        
        step_4 = """
        In response to the instructions that you received for step three, you replied:
        
        {response}
        """
        
        steps = [ step_1, step_2, step_3, step_4 ]
        self.step_len = len( steps )
        prompt_components = {
            "steps"                      : steps,
            "responses"                  : [ ],
            "response_tag_names"         : [ [ "thoughts" ], [ "code" ], [ "returns", "example", "explanation" ] ],
            "running_history"            : "",
            "xml_formatting_instructions": [
                xml_formatting_instructions_step_1, xml_formatting_instructions_step_2,
                xml_formatting_instructions_step_3
            ]
        }
        
        return prompt_components
    
    def _get_df_metadata( self, df ):
    
        head = df.head( 3 ).to_xml( index=False )
        head = head + df.tail( 3 ).to_xml( index=False )
        head = head.replace( "data>", "events>" ).replace( "<?xml version='1.0' encoding='utf-8'?>", "" )
        
        event_value_counts = df.event_type.value_counts()
        
        return head, event_value_counts
    
    def run_prompt( self ):
        
        self.prompt_components      = self._initialize_prompt_components( self.df )

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
                
                response = self._query_llm_phind( running_history, xml_formatting_instructions[ step ], debug=self.debug, verbose=self.verbose )
                responses.append( response )
                
                # Incrementally update the contents of the response dictionary according to the results of the XML-esque parsing
                prompt_response_dict = self._update_response_dictionary(
                    step, response, prompt_response_dict, response_tag_names, debug=False
                )
            
            # Update the prompt component's state before serializing a copy of it
            self.prompt_components[ "running_history" ] = running_history
            self.prompt_response_dict = prompt_response_dict
            
            self.serialize_to_json( self.question, step, self.step_len, now )
            
        # self.prompt_components[ "running_history" ] = running_history
        # self.prompt_response_dict = prompt_response_dict
        
        tokens_per_second = self.token_count / ( timer.get_delta_ms() / 1000.0 )
        timer.print( f"Done! Tokens per second [{round( tokens_per_second, 1 )}]", use_millis=True, prepend_nl=True )
        
        return self.prompt_response_dict

    def _query_llm_phind( self, preamble, instructions, model=Agent.PHIND_34B_v2, temperature=0.50, max_new_tokens=1024, debug=False, verbose=False ):
    
        timer = sw.Stopwatch( msg=f"Asking LLM [{model}]..." )
        
        client         = InferenceClient( du.get_tgi_server_url() )
        token_list     = [ ]
        
        prompt = f"{preamble}{instructions}\n"
        if debug and verbose: print( prompt )
        
        for token in client.text_generation(
            prompt, max_new_tokens=max_new_tokens, stream=True, stop_sequences=[ "</response>" ], temperature=temperature
        ):
            print( token, end="" )
            token_list.append( token )
            
        response         = "".join( token_list ).strip()
        self.token_count = self.token_count + len( token_list )
        
        print()
        print( f"Response tokens [{len( token_list )}]" )
        timer.print( "Done!", use_millis=True, prepend_nl=True )
        
        return response
    
    def _update_response_dictionary( self, step, response, prompt_response_dict, tag_names, debug=True ):
    
        if debug: print( f"update_response_dictionary called with step [{step}]..." )
        
        # Parse response and update response dictionary
        xml_tags_for_step_n = tag_names[ step ]
        
        for xml_tag in xml_tags_for_step_n:
            
            if debug: print( f"Looking for xml_tag [{xml_tag}]" )
            
            if xml_tag == "code":
                # the get_code method expects enclosing tags
                xml_string = "<code>" + dux.get_value_by_xml_tag_name( response, xml_tag ) + "</code>"
                prompt_response_dict[ xml_tag ] = self._get_code( xml_string, debug=debug )
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
                line = line.replace( "&gt;", ">" ).replace( "&lt;", "<" ).replace( "&amp;", "&" )
                code_list.append( line )
                if debug: print( line )
            else:
                code_list.append( "" )
                if debug: print( "[]" )
    
        return code_list
    
    def run_code( self, auto_debug=False, inject_bugs=False ):
        
        # TODO: figure out where this should live, i suspect it will be best located in util_code_runner.py
        print( f"Executing super().run_code() with inject_bugs [{inject_bugs}] and auto_debug [{auto_debug}]...")
        code_response_dict = super().run_code(  inject_bugs=inject_bugs )
        if self.ran_to_completion():
            
            self.error  = None
            return self.code_response_dict
            
        elif auto_debug:
            
            self.error = self.code_response_dict[ "output" ]
            
            debugging_agent = IterativeDebuggingAgent( code_response_dict[ "output" ], du.get_project_root() + "/io/code.py", debug=self.debug, verbose=self.verbose )
            debugging_agent.run_prompts()
            
            if debugging_agent.was_successfully_debugged():
                
                self.code_response_dict = debugging_agent.get_code_and_metadata()
                self.error              = None

            else:
                
                du.print_banner( "Debugging failed, returning original code, such as it is... 😢 sniff 😢" )
                
        return self.code_response_dict
                
if __name__ == "__main__":
    
    path_to_df      = "/src/conf/long-term-memory/events.csv"
    question        = "How many birthdays are on my calendar this month?"
    # question        = "How many birthdays do I have on my calendar this month?"
    # question        = "What birthdays do I have on my calendar this week?"
    # question        = "What's today's date?"
    # question        = "What time is it?"
    agent           = IncrementalCalendaringAgent( path_to_df, question=question, debug=True, verbose=False )
    prompt_response = agent.run_prompt()
    code_response   = agent.run_code( auto_debug=True, inject_bugs=False )
    du.print_banner( f"code_response[ 'return_code' ] = [{code_response[ 'return_code' ]}]", prepend_nl=False )
    for line in code_response[ "output" ].split( "\n" ):
        print( line )
        
    # formatted_output = agent.format_output()
    #
    # du.print_banner( question, prepend_nl=False )
    # for line in formatted_output.split( "\n" ):
    #     print( line )
    #
    # # code_response_dict = prompt_response_dict[ "code" ]
    #
    # du.print_banner( "Done! prompt_response_dict:", prepend_nl=True )
    # print( prompt_response_dict )
    