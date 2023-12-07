import os
import re
import json
import abc

import lib.utils.util as du
import lib.utils.util_stopwatch as sw

from lib.agents.runnable_code import RunnableCode

# from lib.memory.solution_snapshot import SolutionSnapshot

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
        
        self.question              = None
        self.answer_conversational = None
        
        # self.code_response_dict    = None
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
    
    def _query_llm( self, preamble, question, model=DEFAULT_MODEL, max_new_tokens=1024, temperature=0.5, top_k=100, top_p=0.25, debug=True ):
        
        if model == Agent.PHIND_34B_v2:
            
            prompt = preamble + "\n" + question
            
            self.debug = debug
            return self._query_llm_phind( prompt, model=model, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, top_p=top_p, debug=debug )
            
        else:
            if debug:
                print( f"Preamble: [{preamble}]" )
                print( f"Question: [{question}]" )
            return self._query_llm_openai( preamble, question, model=model, debug=debug )
        
    def _query_llm_openai( self, preamble, query, model=DEFAULT_MODEL, debug=False ):
        
        openai.api_key = os.getenv( "FALSE_POSITIVE_API_KEY" )
        
        timer = sw.Stopwatch( msg=f"Asking LLM [{model}]...".format( model ) )
        
        response = openai.chat.completions.create(
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
        
        timer.print( "Done!", use_millis=True )
        if debug and self.verbose:
            # print( json.dumps( response.to_dict(), indent=4 ) )
            print( response )
        
        return response.choices[ 0 ].message.content.strip()
    
    def _query_llm_phind( self, prompt, model=DEFAULT_MODEL, max_new_tokens=1024, temperature=0.5, top_k=100, top_p=0.9, debug=False ):
        
        timer = sw.Stopwatch( msg=f"Asking LLM [{model}]...".format( model ) )
        
        client         = InferenceClient( model=self.phind_tgi_url )
        token_list     = [ ]
        ellipsis_count = 0
        
        if self.debug:
            for line in prompt.split( "\n" ):
                print( line )
        
        for token in client.text_generation(
            prompt, max_new_tokens=max_new_tokens, stream=True, temperature=temperature, top_k=top_k, top_p=top_p, stop_sequences=[ "</response>" ]
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
            
        response = "".join( token_list ).strip()
        
        timer.print( msg="Done!", use_millis=True, prepend_nl=True )
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
    def is_prompt_executable( self ):
        pass
    
    @abc.abstractmethod
    def is_code_runnable( self ):
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

        Question: {self.question}
        Raw Answer: {self.code_response_dict[ "output" ]}
        
        Return your answer as a simple xml document with the following fields:
        <response>
            <rephrased_answer>Your rephrased answer</rephrased_answer>
        </response>
        """
        # Rephrase the raw answer in {data_format} format below and output it using brief yet conversational English to the <rephrased_answer> field so that it answers the question in the <question> field.
        #
        # Raw Answer: `{self.code_response_dict[ "output" ]}`
        #
        # Generate an XML document containing your response composed of one or more sentences. Each sentence of the output that you create should contain or reference one date, time, event or answer.
        # <response>
        #     <question>{self.question}</question>
        #     <raw_answer>{self.code_response_dict[ "output" ]}</raw_answer>
        #     <rephrased_answer>
        #         <sentence>Your rephrased answer</sentence>
        #     </rephrased_answer>
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
    
    # def serialize_to_json( self, question, current_step, total_steps, now ):
    #
    #     # Convert object's state to a dictionary
    #     state_dict = self.__dict__
    #
    #     # Remove any private attributes
    #     # Convert object's state to a dictionary, omitting specified fields
    #     state_dict = { k: v for k, v in self.__dict__.items() if k not in self.do_not_serialize }
    #
    #     # Constructing the filename
    #     # Format: "question_year-month-day-hour-minute-step-N-of-M.json"
    #     fn_question = SolutionSnapshot.clean_question( question ).replace( " ", "-" )
    #     filename = f"{du.get_project_root()}/io/log/{fn_question}-{now.year}-{now.month}-{now.day}-{now.hour}-{now.minute}-step-{(current_step + 1)}-of-{total_steps}.json"
    #
    #     # Serialize and save to file
    #     with open( filename, 'w' ) as file:
    #         json.dump( state_dict, file, indent=4 )
    #
    #     print( f"Serialized to {filename}" )