import os
import json
import abc

import lib.util as du
import lib.util_pandas as dup
import lib.util_code_runner as ucr
import lib.util_stopwatch as sw
import solution_snapshot as ss

import openai
import tiktoken

class CommonAgent( abc.ABC ):
    
    GPT_4   = "gpt-4-0613"
    GPT_3_5 = "gpt-3.5-turbo-0613"
    
    def __init__( self, debug=False, verbose=False ):
        
        self.debug         = debug
        self.verbose       = verbose
        
        self.code_response = None
    
    @staticmethod
    def _get_token_count( to_be_tokenized, model=GPT_4 ):
        
        encoding   = tiktoken.encoding_for_model( model )
        num_tokens = len( encoding.encode( to_be_tokenized ) )
        
        return num_tokens
    
    def _query_gpt( self, preamble, query, model=GPT_4, debug=False ):
        openai.api_key = os.getenv( "FALSE_POSITIVE_API_KEY" )
        
        if debug:
            timer = sw.Stopwatch( msg=f"Asking ChatGPT [{model}]...".format( model ) )
        
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                { "role": "system", "content": preamble },
                { "role": "user", "content": query }
            ],
            temperature=0,
            max_tokens=2000,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        
        if debug:
            timer.print( use_millis=True )
            if self.verbose:
                print( json.dumps( response, indent=4 ) )
        
        return response[ "choices" ][ 0 ][ "message" ][ "content" ].strip()
    
    @abc.abstractmethod
    def _get_system_message( self ):
        pass
    
    @abc.abstractmethod
    def _get_user_message( self ):
        pass
    
    @abc.abstractmethod
    def run_prompt( self, question="" ):
        pass
    
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