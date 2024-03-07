import os
import re
import json
import abc

import lib.utils.util           as du
import lib.utils.util_stopwatch as sw

from lib.agents.llm                import Llm
from lib.agents.runnable_code      import RunnableCode
from lib.app.configuration_manager import ConfigurationManager

import openai
import tiktoken
from huggingface_hub import InferenceClient

class XXX_Agent( RunnableCode, abc.ABC ):
    
    DEFAULT_MODEL = Llm.PHIND_34B_v2
    
    def __init__( self, routing_command="", debug=False, verbose=False, auto_debug=False, inject_bugs=False ):
        
        super().__init__( debug=debug, verbose=verbose )
        
        self.debug                  = debug
        self.verbose                = verbose
        self.auto_debug             = auto_debug
        self.inject_bugs            = inject_bugs
        self.routing_command        = routing_command
        
        self.question               = None
        self.answer_conversational  = None
        
        self.config_mgr             = ConfigurationManager( env_var_name="GIB_CONFIG_MGR_CLI_ARGS" )
        
        # self.code_response_dict   = None
        # self.prompt_response      = None
        # self.prompt_response_dict = None
        # self.tgi_server_codegen_url = self.config_mgr.get( "tgi_server_codegen_url" )
    
    @staticmethod
    def _get_token_count( to_be_tokenized, model=DEFAULT_MODEL ):
        
        if model == Llm.PHIND_34B_v2:
            num_tokens = -1
        else:
            encoding   = tiktoken.encoding_for_model( model )
            num_tokens = len( encoding.encode( to_be_tokenized ) )
        
        return num_tokens
    
    def _query_llm( self, preamble, question, model=Llm.PHIND_34B_v2, max_new_tokens=1024, temperature=0.5, top_k=100, top_p=0.25, debug=True ):
        
        llm = Llm( model=model, default_url=self.tgi_server_codegen_url, debug=debug, verbose=self.verbose )
        
        response = llm.query_llm( preamble, question, model=model, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, top_p=top_p, debug=debug )
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
    def is_prompt_executable( self ):
        pass
    
    @abc.abstractmethod
    def is_code_runnable( self ):
        pass
        
    @abc.abstractmethod
    def format_output( self ):
        pass
    
    def _print_token_count( self, message, message_name="system_message", model=DEFAULT_MODEL ):
        
        if self.debug and model != Llm.PHIND_34B_v2:
            
            count = self._get_token_count( message, model=model )
            if self.verbose:
                du.print_banner( f"Token count for `{message_name}`: [{count}]", prepend_nl=True )
                print( message )
            else:
                print( f"Token count for `{message_name}`: [{count}]" )
                
        elif self.debug and model == Llm.PHIND_34B_v2:
                
                print( f"Token count for `{message_name}`: [Not yet available for {model}]" )
    
    def _get_formatting_preamble( self ):
        
        if du.is_jsonl( self.code_response_dict[ "output" ] ):
            
            return self._get_jsonl_formatting_preamble()
        
        else:
            
            preamble = """
            You are an expert in converting raw data into conversational English and outputting it as XML document.

            The answer below is the result of a query on a pandas dataframe about events, dates, and times on my calendar.
            """
            return preamble

    
    def _get_formatting_instructions( self ):
        
        if du.is_jsonl( self.code_response_dict[ "output" ] ):
            data_format = "JSONL"
        elif "<xml" in self.code_response_dict[ "output" ]:
            data_format = "XML"
        else:
            data_format = "plain text"
        
        # instructions = f"""
        # Reformat and rephrase the {data_format} data that I just showed you in brief yet conversational English so that it answers this question: `{self.question}`
        #
        # 1) Question: Ask yourself if you understand the question being asked of the data. Is the question asking for a type of event, the date, the day, the time, or both date and time?
        #
        # 2) Think: Before you do anything, think out loud about what are the steps that you will need to take to answer this question. Be critical of your thought process!
        #
        # 3) Answer: Generate an XML document containing your answer composed of one or more sentences. Each sentence must contain or reference only one date, one time, one event or one answer.
        #
        # Question: {{question}}
        #
        # Format: return your response as an XML document with the following fields:
        #
        # <response>
        #     <question>{self.question}</question>
        #     <thoughts>Your thought process</thoughts>
        #     <answer>
        #         <sentence>...</sentence>
        #         <sentence>...</sentence>
        #     </answer>
        # </response>
        # """
        
        # instructions = f"""
        # You are an expert in converting raw data into conversational English and outputting it as XML document.
        #
        # The answer below is the result of a query on a pandas dataframe about events, dates, and times on my calendar.
        #
        instructions = f"""
        Rephrase the raw answer in {data_format} format below so that it briefly answers the question below, and nothing more.

        Raw Answer: {self.code_response_dict[ "output" ]}
        Question: {self.question}
        
        Return your rephrased answer as a simple xml document with the following fields:
        <response>
            <rephrased-answer></rephrased-answer>
        </response>
        """
        # Rephrase the raw answer in {data_format} format below and output it using brief yet conversational English to the <rephrased_answer> field so that it answers the question in the <question> field.
        #
        # Raw Answer: `{self.code_response_dict[ "output" ]}`
        #
        # Generate an XML document containing your response composed of one or more sentences. Each sentence of the output that you create should contain or reference one date, time, event or answer.
        # <response>
        #     <question>{self.question}</question>
        #     <raw-answer>{self.code_response_dict[ "output" ]}</raw-answer>
        #     <rephrased-answer>
        #         <sentence>Your rephrased answer</sentence>
        #     </rephrased-answer>
        # </response>
        # """
        return instructions
    
    
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
    
