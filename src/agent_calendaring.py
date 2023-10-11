import json

import lib.util             as du
import lib.util_pandas      as dup
import lib.util_code_runner as ucr
import lib.util_stopwatch   as sw
import solution_snapshot    as ss

from agent import CommonAgent

import pandas as pd

class CalendaringAgent( CommonAgent ):
    
    def __init__( self, path_to_df, question="", push_counter=-1, debug=False, verbose=False ):
        
        super().__init__( debug=debug, verbose=verbose )
        
        # self.debug      = debug
        # self.verbose    = verbose
        
        self.path_to_df = du.get_project_root() + path_to_df
        self.df         = pd.read_csv( self.path_to_df )
        self.df         = dup.cast_to_datetime( self.df )
        
        self.system_message        = self._get_system_message()
        
        # Added to allow behavioral compatibility with solution snapshot object
        self.run_date              = ss.SolutionSnapshot.get_timestamp()
        self.push_counter          = push_counter
        self.id_hash               = ss.SolutionSnapshot.generate_id_hash( self.push_counter, self.run_date )

        self.question              = ss.SolutionSnapshot.clean_question( question)
        self.user_message          = None
        
        # We'll set these later
        self.answer_conversational = None
        self.response              = None
        self.response_dict         = None
        self.error                 = None
    
    def get_html( self ):
        
        return f"<li id='{self.id_hash}'>{self.run_date} Q: {self.question}</li>"
    
    
    def _get_system_message( self ):
        
        csv = self.df.head( 3 ).to_csv( header=True, index=False )
        csv = csv + self.df.tail( 3 ).to_csv( header=False, index=False )
        
        pandas_system_prompt = f"""
        You are an expert software engineer working with a pandas dataframe in Python containing calendaring and events information. The name of the dataframe is `df`.

        This is the ouput from `print(df.head().to_csv())`, in CSV format:

        {csv}

        This is the output from `print(self.df.event_type.value_counts())`:

        {self.df.event_type.value_counts()}

        As you generate the python code needed to answer the events and calendaring question asked of you below, I want you to:

        1) Question: Ask yourself if you understand the question that I am asking you.  Pay attention to the details!
        2) Think: Before you do anything, think out loud about what I'm asking you to do, including what are the steps that you will need to take to solve this problem. Be critical of your thought process!
        3) Code: Generate a verbatim list of code that you used to arrive at your answer, one line of code per item on the list. The code must be complete, syntactically correct, and capable of runnning to completion. The last line of your code must be the variable `solution`, which represents the answer. Make sure that any filtering you perform matches the question asked of you by the user!
        4) Return: Report on the object type of the variable `solution` in your last line of code. Use one word to represent the object type.
        5) Explain: Briefly and succinctly explain your code in plain English.

        Format: return your response as a JSON object in the following fields:
        {{
            "question": "The question, verbatim and without modification",
            "thoughts": "Your thoughts",
            "code": [],
            "returns": "Object type of the variable `solution`",
            "explanation": "A brief explanation of your code",
            "error": "Your description of any issues or errors that you encountered while attempting to answer the question"
        }}

        Hint: An event that I have today may have started before today and may end tomorrow or next week, so be careful how you filter on dates.
        Hint: When filtering by dates, use `pd.Timestamp( day )` to convert a Python datetime object into a Pandas `datetime64[ns]` value.
        Hint: If your solution variable is a dataframe, it should include all columns in the dataframe.
        Hint: If you cannot answer the question, explain why in the `error` field
        Hint: Allow for the possibility that your query may return no results.
        """
        
        return pandas_system_prompt
    
    def _get_user_message( self, question="" ):
        
        # Odd little two-step sanity check: allows us to set the question when instantiated or when run_prompt is called
        if question != "":
            self.question = question
        if self.question == "":
            raise ValueError( "No question was provided!" )
        
        return self.question
        
    def is_promptable( self ):
        
        du.print_banner( "TODO: Implement is_promptable()", expletive=True )
        return True
    
    def is_runnable( self ):
        
        du.print_banner( "TODO: Implement is_runnable()", expletive=True )
        return True
    
    def run_prompt( self, question="" ):
        
        prompt_model      = CommonAgent.GPT_4
        self.user_message = self._get_user_message( question )
        
        self._print_token_count( self.system_message, message_name="system_message", model=prompt_model )
        self._print_token_count( self.user_message, message_name="user_message", model=prompt_model )
        
        self.response      = self._query_gpt( self.system_message, self.user_message, model=prompt_model, debug=self.debug )
        self.response_dict = json.loads( self.response )
        
        if self.debug and self.verbose: print( json.dumps( self.response_dict, indent=4 ) )
        
        # Test for no code returned
        if self.response_dict[ "code" ] == [ ]:
            self.error = self.response_dict[ "error" ]
            raise ValueError( "No code was returned, please check the logs" )
        
        return self.response_dict
    
    def run_code( self ):
        
        self.code_response = ucr.assemble_and_run_solution(
            self.response_dict[ "code" ], path="/src/conf/long-term-memory/events.csv",
            solution_code_returns=self.response_dict[ "returns" ], debug=self.debug
        )
        if self.debug and self.verbose:
            du.print_banner( "Code output", prepend_nl=True )
            for line in self.code_response[ "output" ].split( "\n" ):
                print( line )
        
        return self.code_response
    
    def format_output( self ):
        
        format_model = CommonAgent.GPT_3_5
        preamble     = self._get_formatting_preamble()
        instructions = self._get_formatting_instructions()
        
        self._print_token_count( preamble, message_name="formatting preamble", model=format_model )
        self._print_token_count( instructions, message_name="formatting instructions", model=format_model )
        
        self.answer_conversational = self._query_gpt( preamble, instructions, model=format_model, debug=self.debug )
        
        return self.answer_conversational
    
    # def get_formatting_preamble( self ):
    #
    #     if du.is_jsonl( self.code_response[ "output" ] ):
    #
    #         return self.get_jsonl_formatting_preamble()
    #
    #     else:
    #
    #         preamble = f"""
    #         You are an expert in converting raw data into conversational English.
    #
    #         The output is the result of a query on a pandas dataframe about events on my calendar.
    #
    #         The query is: `{self.question}`
    #
    #         The output is: `{self.code_response[ "output" ]}`
    #         """
    #         return preamble
        
        
    # def get_jsonl_formatting_preamble( self ):
    #
    #     rows = self.code_response[ "output" ].split( "\n" )
    #     row_count = len( rows )
    #
    #     lines = [ ]
    #     line_number = 1
    #
    #     for row in rows:
    #         lines.append( f"{line_number}) {row}" )
    #         line_number += 1
    #
    #     lines = "\n".join( lines )
    #
    #     preamble = f"""
    #     You are an expert in converting raw data into conversational English.
    #
    #     The following {row_count} rows of JSONL formatted data are the output from a query on a pandas dataframe about events on my calendar.
    #
    #     The query was: `{self.question}`
    #
    #     JSONL output:
    #
    #     {lines}
    #     """
    #     return preamble
    
    # def get_formatting_instructions( self ):
    #
    #     data_format = "JSONL " if du.is_jsonl( self.code_response[ "output" ] ) else ""
    #
    #     instructions = f"""
    #     Reformat and rephrase the {data_format}data that I just showed you in conversational English so that it answers this question: `{self.question}`
    #
    #     Each line of the output that you create should contain one event."
    #     """
    #     return instructions
    
if __name__ == "__main__":
    
    agent = CalendaringAgent( path_to_df="/src/conf/long-term-memory/events.csv", debug=True, verbose=True )
    
    # question         = "What todo items do I have on my calendar for this week?"
    # question         = "What todo items do I have on my calendar for today?"
    # question         = "Do I have any birthdays on my calendar this week?"
    # question         = "When is Juan's birthday?"
    question         = "When is Jimmy's birthday?"
    timer            = sw.Stopwatch( msg=f"Processing [{question}]..." )
    response_dict    = agent.run_prompt( question )
    code_response    = agent.run_code()
    formatted_output = agent.format_output()
    
    timer.print( use_millis=True )
    
    du.print_banner( question, prepend_nl=True )
    for line in formatted_output.split( "\n" ):
        print( line )
        
    