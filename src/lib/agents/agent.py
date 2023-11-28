import os
import json
import abc

import lib.utils.util as du
import lib.utils.util_stopwatch as sw

from lib.agents.runnable_code import RunnableCode

import openai
import tiktoken
from huggingface_hub import InferenceClient

class Agent( RunnableCode, abc.ABC ):
    
    GPT_4         = "gpt-4-0613"
    GPT_3_5       = "gpt-3.5-turbo-1106"
    PHIND_34B_v2  = "Phind/Phind-CodeLlama-34B-v2"
    
    DEFAULT_MODEL = PHIND_34B_v2
    
    def __init__( self, debug=False, verbose=False ):
        
        super().__init__( debug=debug, verbose=verbose )
        
        self.debug         = debug
        self.verbose       = verbose
        
        # self.code_response_dict    = None
        self.answer_conversational = None
        
        # self.prompt_response = None
        # self.prompt_response_dict = None
        self.phind_tgi_url = du.get_tgi_server_url()
    
    @staticmethod
    def _get_token_count( to_be_tokenized, model=DEFAULT_MODEL ):
        
        if model == Agent.PHIND_34B_v2:
            num_tokens = -1
        else:
            encoding   = tiktoken.encoding_for_model( model )
            num_tokens = len( encoding.encode( to_be_tokenized ) )
        
        return num_tokens
    
    def _query_llm( self, preamble, query, model=DEFAULT_MODEL, debug=False ):
        
        if model == Agent.PHIND_34B_v2:
            
            # insert question into template
            prompt = preamble.format( question=query )
            if self.debug and self.verbose:
                print( f"Prompt:\n[{prompt}]" )
            elif self.debug:
                print( f"Query: [{query}]" )
            
            return self._query_llm_phind( prompt, model=model )
            
        else:
            
            return self._query_llm_openai( preamble,query, model=model, debug=debug )
        
    def _query_llm_openai( self, preamble, query, model=DEFAULT_MODEL, debug=False ):
        
        openai.api_key = os.getenv( "FALSE_POSITIVE_API_KEY" )
        
        timer = sw.Stopwatch( msg=f"Asking LLM [{model}]...".format( model ) )
        
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
        
        timer.print( use_millis=True )
        if debug and self.verbose:
            print( json.dumps( response, indent=4 ) )
        
        return response[ "choices" ][ 0 ][ "message" ][ "content" ].strip()
    
    def _query_llm_phind( self, prompt, model=DEFAULT_MODEL ):
        
        timer = sw.Stopwatch( msg=f"Asking LLM [{model}]...".format( model ) )
        
        client         = InferenceClient( model=self.phind_tgi_url )
        token_list     = [ ]
        ellipsis_count = 0
        
        for token in client.text_generation(
            prompt, max_new_tokens=1024, stream=True, stop_sequences=[ "</response>" ], temperature=1.0
        ):
            if self.debug:
                print( token, end="" )
            else:
                print( ".", end="" )
                ellipsis_count += 1
                if ellipsis_count == 100:
                    ellipsis_count = 0
                    print()
                
            token_list.append( token )
            
        # print()
        response = "".join( token_list ).strip()
        
        timer.print( use_millis=True, prepend_nl=True )
        if self.debug:
            print( f"Token list length [{len( token_list )}]" )
            if self.verbose:
                for line in response.split( "\n" ):
                    print( line )
        
        return response
    
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
    
    def _print_token_count( self, message, message_name="system_message", model=DEFAULT_MODEL ):
        
        if self.debug and model != Agent.PHIND_34B_v2:
            
            count = self._get_token_count( message, model=model )
            if self.verbose:
                du.print_banner( f"Token count for `{message_name}`: [{count}]", prepend_nl=True )
                print( message )
            else:
                print( f"Token count for `{message_name}`: [{count}]" )
                
        elif self.debug and model == Agent.PHIND_34B_v2:
                
                print( f"Token count for `{message_name}`: [Not yet available for {model}]" )
    
    def _get_formatting_instructions( self ):
        
        data_format = "JSONL " if du.is_jsonl( self.code_response_dict[ "output" ] ) else ""
        
        instructions = f"""
        Reformat and rephrase the {data_format} data that I just showed you in conversational English so that it answers this question: `{self.question}`

        Each line of the output that you create should contain or reference one date, time, event or answer."
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