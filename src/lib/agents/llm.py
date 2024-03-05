import os

import openai

from huggingface_hub            import InferenceClient

from groq                       import Groq

from lib.utils.util_stopwatch   import Stopwatch

import lib.utils.util as du


class Llm:
    
    GPT_4             = "gpt-4-0613"
    GPT_3_5           = "gpt-3.5-turbo-1106"
    PHIND_34B_v2      = "TGI/Phind-CodeLlama-34B-v2"
    GROQ_MIXTRAL_8X78 = "Groq/mixtral-8x7b-32768"
    GROQ_LLAMA2_70B   = "Groq/llama2-70b-4096"

    def __init__( self, model=PHIND_34B_v2, default_url=None, debug=False, verbose=False ):
        
        self.debug          = debug
        self.verbose        = verbose
        self.model          = model
        # Get the TGI server URL for this context
        self.tgi_server_url = du.get_tgi_server_url_for_this_context( default_url=default_url )

    def query_llm( self, model=None, prompt=None, preamble=None, question=None, max_new_tokens=1024, temperature=0.5, top_k=100, top_p=0.25, debug=False, verbose=False ):
        
        if preamble is None and question is None and prompt is None:
            raise ValueError( "ERROR: Neither prompt, preamble, nor question has a value set!" )
        
        # Allow us to override the prompt, preamble, and question set when instantiated
        if model is not None: self.model = model
        
        if self.model == Llm.PHIND_34B_v2:
            
            # Quick sanity check
            if prompt is None: raise ValueError( "ERROR: Prompt is `None`!" )
            
            return self._query_llm_phind(
                prompt, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, top_p=top_p, debug=debug, verbose=verbose
            )
        
        else:
            # Test for divisibility if receiving an "all in one" non chatbot type prompt
            if prompt is not None:
                
                input_present        = "### Input:" in prompt
                user_message_present = "### User Message" in prompt
                
                if not input_present and not user_message_present:
                    msg = "ERROR: Prompt isn't divisible, '### Input:' and '### User Message:' not found in prompt!"
                    print( msg )
                    print( f"Prompt: [{prompt}]" )
                    raise ValueError( msg )
                
                if input_present:
                    preamble = prompt.split( "### Input:" )[ 0 ]
                    question = prompt.split( "### Input:" )[ 1 ]
                
                if user_message_present:
                    preamble = prompt.split( "### User Message" )[ 0 ]
                    question = prompt.split( "### User Message" )[ 1 ]
                    
                # Strip out prompt markers
                preamble = preamble.replace( "### System Prompt", "" )
                preamble = preamble.replace( "### Input:", "" )
                preamble = preamble.replace( "### Instruction:", "" )
                preamble = preamble.replace( "### Task:", "" )
                preamble = preamble.replace( "Use the Task and Input given below to write a Response that can solve the following Task.", "" )

                question = question.replace( "### Input:", "" )
                question = question.replace( "### User Message", "" )
                question = question.replace( "### Assistant", "" )
                question = question.replace( "### Response:", "" )
                
                
                if debug:
                    print( f"Preamble: [{preamble}]" )
                    print( f"Question: [{question}]" )
                
            elif preamble is None or question is None:
                raise ValueError( "ERROR: Preamble or question is `None`!" )
                
            if self.model.startswith( "gpt-" ):
                return self._query_llm_openai( preamble, question, debug=debug, verbose=verbose )
            elif self.model.startswith( "Groq/" ):
                return self._query_llm_groq( preamble, question, debug=debug, verbose=verbose )
            else:
                raise ValueError( f"ERROR: Model [{self.model}] not recognized!" )
    
    def _query_llm_groq( self, preamble, query, max_new_tokens=1024, temperature=0.25, stop_tokens=[ "</response>" ], top_k=10, top_p=0.9, stream=True, debug=False, verbose=False ):
        
        client = Groq(
            api_key=du.get_api_key( "groq" )
        )
        stream = client.chat.completions.create(
            messages=[
                { "role"   : "system", "content": preamble },
                { "role"   : "user", "content": query }
            ],
            # model="mixtral-8x7b-32768",
            # Model names are stored in the format "Groq/{model_name} in the config_mgr file
            model=self.model.split( "/" )[ 1 ],
            temperature=temperature,
            max_tokens=max_new_tokens,
            top_p=top_p,
            stop=stop_tokens,
            stream=stream,
        )
        timer = Stopwatch( msg=f"Asking Groq [{self.model}]..." )
        chunks = [ ]
        for chunk in stream:
            
            chunks.append( str( chunk ) )
            print( chunk.choices[ 0 ].delta.content, end="" )
            
        timer.print( "Done!", use_millis=True )
        
        chunks_per_second = len( chunks ) / ( timer.get_delta_ms() / 1000.0 )
        print( f"Chunks per second [{round( chunks_per_second, 1 )}]" )
        
        return "".join( chunks ).strip()
    
    def _query_llm_openai( self, preamble, query, debug=False, verbose=False ):
        
        openai.api_key = os.getenv( "FALSE_POSITIVE_API_KEY" )
        
        timer = Stopwatch( msg=f"Asking OpenAI [{self.model}]...".format( self.model ) )
        
        response = openai.chat.completions.create(
            model=self.model,
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
    
    def _query_llm_phind(
            self, prompt, max_new_tokens=1024, temperature=0.25, top_k=10, top_p=0.9, debug=False, verbose=False
    ):
        timer = Stopwatch( msg=f"Asking LLM [{self.model}]...".format( self.model ) )
        
        client = InferenceClient( self.tgi_server_url )
        token_list = [ ]
        ellipsis_count = 0
        
        if self.debug:
            for line in prompt.split( "\n" ):
                print( line )
        
        for token in client.text_generation(
                prompt, max_new_tokens=max_new_tokens, stream=True, temperature=temperature, top_k=top_k, top_p=top_p,
                stop_sequences=[ "</response>" ]
        ):
            if self.debug:
                print( token, end="" )
            else:
                print( ".", end="" )
                ellipsis_count += 1
                if ellipsis_count == 120:
                    ellipsis_count = 0
                    print()
            
            token_list.append( token )
        
        response = "".join( token_list ).strip()
        
        timer.print( msg="Done!", use_millis=True, prepend_nl=True, end="\n" )
        tokens_per_second = len( token_list ) / ( timer.get_delta_ms() / 1000.0 )
        print( f"Tokens per second [{round( tokens_per_second, 1 )}]" )
        
        if self.debug:
            print( f"Token list length [{len( token_list )}]" )
            if self.verbose:
                for line in response.split( "\n" ):
                    print( line )
        
        return response
    
    
# Add main method
if __name__ == "__main__":
    
    # llm = Llm( model=Llm.PHIND_34B_v2, debug=True, verbose=True )
    #
    # prompt_template = du.get_file_as_string( du.get_project_root() + "/src/conf/prompts/incremental-agents/events/calendaring.txt" )
    # prompt = prompt_template.format( question="Do I have any concerts this week?" )
    # # print( prompt)
    # response = llm.query_llm( prompt=prompt, debug=False, verbose=False )

    llm = Llm( model=Llm.PHIND_34B_v2, debug=True, verbose=True )
    
    prompt_template = du.get_file_as_string( du.get_project_root() + "/src/conf/prompts/formatters/calendaring.txt" )
    raw_output = """
          <row>
            <start_date>2024-02-27 00:00:00</start_date>
            <end_date>2024-03-01 00:00:00</end_date>
            <start_time>00:00</start_time>
            <end_time>23:59</end_time>
            <event_type>concert</event_type>
            <recurrent>False</recurrent>
            <recurrence_interval/>
            <priority_level>low</priority_level>
            <name>Pablo</name>
            <relationship>friend</relationship>
            <description_who_what_where>Concert of Pablo at the city center</description_who_what_where>
          </row>
          <row>
            <start_date>2024-02-28 00:00:00</start_date>
            <end_date>2024-02-28 00:00:00</end_date>
            <start_time>00:00</start_time>
            <end_time>23:59</end_time>
            <event_type>concert</event_type>
            <recurrent>False</recurrent>
            <recurrence_interval/>
            <priority_level>highest</priority_level>
            <name>John</name>
            <relationship>coworker</relationship>
            <description_who_what_where>Concert of John at the city center</description_who_what_where>
          </row>
          <row>
            <start_date>2024-03-01 00:00:00</start_date>
            <end_date>2024-03-01 00:00:00</end_date>
            <start_time>00:00</start_time>
            <end_time>23:59</end_time>
            <event_type>concert</event_type>
            <recurrent>False</recurrent>
            <recurrence_interval/>
            <priority_level>medium</priority_level>
            <name>Sue</name>
            <relationship>sister</relationship>
            <description_who_what_where>Concert of Sue at the city center</description_who_what_where>
          </row>
          <row>
            <start_date>2024-03-01 00:00:00</start_date>
            <end_date>2024-03-03 00:00:00</end_date>
            <start_time>00:00</start_time>
            <end_time>23:59</end_time>
            <event_type>concert</event_type>
            <recurrent>False</recurrent>
            <recurrence_interval/>
            <priority_level>none</priority_level>
            <name>Inash</name>
            <relationship>girlfriend</relationship>
            <description_who_what_where>Concert of Inash at the city center</description_who_what_where>
          </row>
          <row>
            <start_date>2024-03-03 00:00:00</start_date>
            <end_date>2024-03-03 00:00:00</end_date>
            <start_time>00:00</start_time>
            <end_time>23:59</end_time>
            <event_type>concert</event_type>
            <recurrent>False</recurrent>
            <recurrence_interval/>
            <priority_level>high</priority_level>
            <name>Inash</name>
            <relationship>girlfriend</relationship>
            <description_who_what_where>Concert of Inash at the city center</description_who_what_where>
          </row>"""
    prompt = prompt_template.format( question="Do I have any concerts this week?", raw_output=raw_output )
    llm.query_llm( prompt=prompt, debug=False, verbose=False )
    # llm.query_llm( preamble="You are the most helpful and cheeriest assistant ever!", question="What is the importance of low latency LLMs?" )