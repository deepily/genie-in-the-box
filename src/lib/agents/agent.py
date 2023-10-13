import os
import json
import abc

import lib.utils.util as du
import lib.utils.util_stopwatch as sw

from lib.agents.runnable import Runnable

import openai
import tiktoken

class Agent( Runnable, abc.ABC ):
    
    GPT_4   = "gpt-4-0613"
    GPT_3_5 = "gpt-3.5-turbo-0613"
    
    def __init__( self, debug=False, verbose=False ):
        
        super().__init__( debug=debug, verbose=verbose )
        
        self.debug         = debug
        self.verbose       = verbose
        
        # self.code_response_dict    = None
        self.answer_conversational = None
        
        # self.prompt_response = None
        # self.prompt_response_dict = None
    
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
    
    @abc.abstractmethod
    def is_promptable( self ):
        pass
    
    @abc.abstractmethod
    def is_runnable( self ):
        pass
        
    @abc.abstractmethod
    def format_output( self ):
        pass
    
    def _print_token_count( self, message, message_name="system_message", model=GPT_4 ):
        
        if self.debug:
            
            count = self._get_token_count( message, model=model )
            if self.verbose:
                du.print_banner( f"Token count for `{message_name}`: [{count}]", prepend_nl=True )
                print( message )
            else:
                print( f"Token count for `{message_name}`: [{count}]" )
    
    def _get_formatting_instructions( self ):
        
        data_format = "JSONL " if du.is_jsonl( self.code_response_dict[ "output" ] ) else ""
        
        instructions = f"""
        Reformat and rephrase the {data_format}data that I just showed you in conversational English so that it answers this question: `{self.question}`

        Each line of the output that you create should contain or reference one event."
        """
        return instructions
    
    def _get_formatting_preamble( self ):
        
        if du.is_jsonl( self.code_response_dict[ "output" ] ):
            
            return self._get_jsonl_formatting_preamble()
        
        else:
            
            preamble = f"""
            You are an expert in converting raw data into conversational English.

            The output is the result of a query on a pandas dataframe about events on my calendar.

            The query is: `{self.question}`

            The output is: `{self.code_response_dict[ "output" ]}`
            """
            return preamble
    
    def _get_jsonl_formatting_preamble( self ):
        
        rows = self.code_response_dict[ "output" ].split( "\n" )
        row_count = len( rows )
        
        lines = [ ]
        line_number = 1
        
        for row in rows:
            lines.append( f"{line_number}) {row}" )
            line_number += 1
        
        lines = "\n".join( lines )
        
        preamble = f"""
        You are an expert in converting raw data into conversational English.

        The following {row_count} rows of JSONL formatted data are the output from a query on a pandas dataframe about events on my calendar.

        The query was: `{self.question}`

        JSONL output:

        {lines}
        """
        return preamble