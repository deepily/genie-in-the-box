import os
import json

import lib.util             as du
import lib.util_pandas      as dup
import lib.util_code_runner as ucr
import lib.util_stopwatch   as sw

from agent import CommonAgent
from solution_snapshot_mgr import SolutionSnapshotManager

# import openai
# import tiktoken
#
# GPT_4   = "gpt-4-0613"
# GPT_3_5 = "gpt-3.5-turbo-0613"

class RefactoringAgent( CommonAgent ):
    
    def __init__( self, similar_snapshots=[], path_to_solutions="/src/conf/long-term-memory/solutions", debug=False, verbose=False ):
        
        self.debug             = debug
        self.verbose           = verbose
        
        self.path_to_solutions = path_to_solutions
        self.similar_snapshots = similar_snapshots
        self.snippets          = None
        self.snippets_string   = None
        self.system_message    = self._get_system_message()
        self.user_message      = self._get_user_message()
        self.response          = None
        self.response_dict     = None
        self.error             = None
    
    def _process_similar_snapshots( self ):
        
        i = 1
        self.snippets = []
        
        for snapshot in self.similar_snapshots:
            
            snippet = f"Question {i}: {snapshot[ 1 ].question}"
            self.snippets.append( snippet )
            
            snippet = "\n".join( snapshot[ 1 ].code )
            snippet = f"Snippet {i}: \n\n{snippet}"
            self.snippets.append( snippet )
            
            if self.debug: print( snippet, end="\n\n" )
            i += 1
    
    def _get_system_message( self ):
        
        self._process_similar_snapshots()
        snippet_count = int( len( self.snippets ) / 2 )
        
        system_message = f"""
        I'm going to show you {snippet_count} Python code snippets that are similar, along with the questions they were created to answer.
        How would you coalesce or refactor them so that you only need to call one function in all {snippet_count} scenarios?
        How would you name the function in a way that clearly explains exactly what the function does?
        Descriptive function names look like: `get_birthday_by_name`, or `get_birthdays_by_day`, `get_events_by_week_and_type`,`get_events_by_day_and_type`, etc.,

        As you generate the Python 3.10 code needed to answer this question, I want you to:

        1) Think: Before you do anything, think out loud about what I'm asking you to do, including the steps that you will need to take to solve this problem.
        Be critical of your thought process! How will you handle the edge cases? For example, what will you do if your query does not return a result?
        2) Code: Generate a verbatim list of code that you used to arrive at your answer, one line of code per item on the list. The code must be complete,
        syntactically correct, and capable of running to completion. You must allow for the possibility that your query may not return a result.
        3) Return: Report on the object type returned by your last line of code. Use one word to represent the object type.
        4) Example: Generate a verbatim list of code examples needed to call the function you created, one line of code per question provided. The example function calls
        must be complete, syntactically correct, and capable of running to completion.
        5) Explain: Briefly and succinctly explain your code in plain English.

        Format: return your response as a JSON object in the following fields:
        {{
            "thoughts": "Your thoughts",
            "code": [],
            "returns": "Object type of the variable `solution`",
            "examples": []
            "python_version": "3.10",
            "explanation": "A brief explanation of your code",
            "error": "Verbatim stack trace or description of issues encountered while attempting to carry out this task."
        }}"""
        
        return system_message
    
    def _get_user_message( self ):
        
        snippets_string = "\n\n".join( self.snippets )
        
        user_message = f"""
        {snippets_string}

        Begin!
        """
        
        return user_message
    
    def run_prompt( self ):
        
        prompt_model = CommonAgent.GPT_4
        if self.debug:
            
            count = self._get_token_count( self.system_message, model=prompt_model )
            msg = f"Token count for self.system_message: [{count}]"
            if self.verbose:
                du.print_banner( msg=msg, prepend_nl=True )
                print( self.system_message )
            else:
                print( msg )
            
            count = self._get_token_count( self.user_message, model=prompt_model )
            msg = f"Token count for self.user_message: [{count}]"
            if self.verbose:
                du.print_banner( msg=msg, prepend_nl=True )
                print( self.user_message )
            else:
                print( msg )
                
        self.response      = self._query_gpt( self.system_message, self.user_message, model=prompt_model, debug=self.debug )
        self.response_dict = json.loads( self.response )

        if self.debug and self.verbose: print( json.dumps( self.response_dict, indent=4 ) )

        # Test for no code returned and throw error
        if self.response_dict[ "code" ] == [ ]:
            self.error = self.response_dict[ "error" ]
            raise ValueError( "No code was returned, please check the logs" )

        return self.response_dict
    
    # def run_code( self ):
    #
    #     self.code_response = ucr.assemble_and_run_solution(
    #         self.response_dict[ "code" ], path="/src/conf/long-term-memory/events.csv",
    #         solution_code_returns=self.response_dict[ "returns" ], debug=self.debug
    #     )
    #     if self.debug and self.verbose:
    #         du.print_banner( "Code output", prepend_nl=True )
    #         for line in self.code_response[ "output" ].split( "\n" ):
    #             print( line )
    #
    #     return self.code_response
    
if __name__ == "__main__":
    
    path_to_snapshots = du.get_project_root() + "/src/conf/long-term-memory/solutions/"
    snapshot_mgr      = SolutionSnapshotManager( path_to_snapshots, debug=False )
    exemplar_snapshot = snapshot_mgr.get_snapshots_by_question( "What concerts do I have this week?" )[ 0 ][ 1 ]
    similar_snapshots = snapshot_mgr.get_snapshots_by_code_similarity( exemplar_snapshot, threshold=90.0 )
    
    agent         = RefactoringAgent( similar_snapshots=similar_snapshots, path_to_solutions="/src/conf/long-term-memory/solutions", debug=True, verbose=True )
    response_dict = agent.run_prompt()