import json

import lib.util             as du
import lib.util_pandas      as dup
import lib.util_code_runner as ucr
import lib.util_stopwatch   as sw
import solution_snapshot    as ss

from agent import CommonAgent

import pandas as pd

class FunctionMappingAgent( CommonAgent ):
    
    def __init__( self, path_to_df, question="", debug=False, verbose=False ):
        
        super().__init__( debug=debug, verbose=verbose )
        
        self.path_to_df = du.get_project_root() + path_to_df
        self.df         = pd.read_csv( self.path_to_df )
        self.df         = dup.cast_to_datetime( self.df )
        
        self.signatures_dict       = self._get_signatures_dict()
        self.system_message        = self._get_system_message()
        
        self.question              = ss.SolutionSnapshot.clean_question( question )
        
        # self.response              = None
        # self.response_dict         = None
        # self.error                 = None
    
    def _get_signatures_dict( self):
        
        signature_paths = du.find_files_with_prefix_and_suffix( du.get_project_root() + "/src/lib/autogen/", "util_calendaring", ".json" )
        
        # Given a list of file paths, load each file into a string and append to a list
        signatures = du.get_files_as_strings( signature_paths )
        signatures = [ json.loads( s ) for s in signatures ]
        
        signatures_dict = { }
        for signature in signatures:
            signatures_dict[ signature[ "name" ] ] = signature
        
        return signatures_dict
    
    
    def _get_system_message( self ):
        
        events_list = list( self.df[ "event_type" ].unique() )
        keys_list   = self.df.columns.tolist()
        
        system_message = f"""
        You are an expert at managing events in a calendaring database.
        I'm going to ask you a question that may be about an event. if it is, I want you to map it to a list of `functions` described below.
        If you do not think that the question maps to any of the functions included, please say so in `is_event_function_call`.
        I want you to think aloud about how you are going to answer this question within the `thoughts` field below in the JSON response.
        These are the only `event_type` that we are interested in: {events_list},
        These are the only database fields and kwargs `keys` that we are interested in: {keys_list}.
        
        Functions: {list( self.signatures_dict.values() )}
        
        Please return your response in JSON format:
        {{
                          "thoughts": "Your thoughts about how you are going to answer this question",
            "is_event_function_call": "True or False (Python values)",
                          "question": "The question that you are responding to",
                     "function_name": "The name of the function that you think this question maps to",
                        "kwargs_key": "The kwargs key value that you think this question maps to.  This MUST be inserted into the call template below",
                       "kwargs_value: "The kwargs value that you think this question contains.  This MUST be inserted into the call template below",
                         "import_as": "The import statement that you think is required to use this function",
                     "call_template": "The function call template required to use this function. This MUST include a syntactically correct function name, along with kwargs key and value."
        }}
        
        Hint: Pay careful attention to the semantic mapping you make between any references to time, both in the question and the functions.
        Words like `today`, `tomorrow`, `this week`, and `next month` have very specific meanings and mappings.
        """
        
        return system_message
    
    def _get_user_message( self, question="" ):
        
        if question != "":
            self.question = ss.SolutionSnapshot.clean_question( question )
        
        if self.question == "":
            raise ValueError( "No question was provided" )
        
        self.user_message = f"""
        Question: {self.question}

        Begin!
        """
        return self.user_message
    
    def is_promptable( self ):
        
        return self.question != "" and self.signatures_dict != { }
        
    def run_prompt( self, question="", prompt_model=CommonAgent.GPT_4 ):
        
        self.user_message = self._get_user_message( question=question )
        
        self._print_token_count( self.system_message, message_name="system_message", model=prompt_model )
        self._print_token_count( self.user_message, message_name="user_message", model=prompt_model )
        
        self.response      = self._query_gpt( self.system_message, self.user_message, model=prompt_model, debug=self.debug )
        self.response_dict = json.loads( self.response )
        
        if self.debug and self.verbose: print( json.dumps( self.response_dict, indent=4 ) )
        
        # Set up code for future execution
        if self.response_dict[ "is_event_function_call" ]:
            self.response_dict[ "code" ] = [
                self.response_dict[ "import_as" ],
                self.response_dict[ "call_template" ]
            ]
        else:
            print( "No code to run: is_event_function_call = False" )
            self.response_dict[ "code" ] = [ ]
        
        return self.response_dict
    
    def is_runnable( self ):
        
        if self.response_dict[ "code" ] != [ ]:
            return True
        else:
            print( "No code to run: self.response_dict[ 'code' ] = [ ]" )
            return False
        
    def run_code( self ):

        self.code_response = ucr.assemble_and_run_solution(
            self.response_dict[ "code" ], path="/src/conf/long-term-memory/events.csv",
            solution_code_returns=self.response_dict.get( "returns", "string" ), debug=self.debug
        )
        if self.debug and self.verbose:
            du.print_banner( "Code output", prepend_nl=True )
            for line in self.code_response[ "output" ].split( "\n" ):
                print( line )

        return self.code_response
    
if __name__ == "__main__":
    
    agent = FunctionMappingAgent( "/src/conf/long-term-memory/events.csv", debug=True, verbose=True )
    
    # question         = "What todo items do I have on my calendar for this week?"
    # question         = "What todo items do I have on my calendar for today?"
    # question         = "Do I have any birthdays on my calendar this week?"
    # question         = "When is Juan's birthday?"
    question         = "When is Jimmy's birthday?"
    
    timer            = sw.Stopwatch( msg=f"Processing [{question}]..." )
    response_dict    = agent.run_prompt( question=question )
    # code_response    = agent.run_code()
    timer.print( use_millis=True )
    
    print( json.dumps( response_dict, indent=4 ) )
        
    