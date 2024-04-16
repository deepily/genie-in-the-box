import openai

from huggingface_hub            import InferenceClient

from groq                       import Groq

import google.generativeai      as genai

from lib.app.configuration_manager import ConfigurationManager
from lib.utils.util_stopwatch      import Stopwatch

import lib.utils.util as du


class Llm:
    
    GPT_4             = "OpenAI/gpt-4-turbo-2024-04-09"
    GPT_3_5           = "OpenAI/gpt-3.5-turbo-0125"
    PHIND_34B_v2      = "TGI/Phind-CodeLlama-34B-v2"
    GROQ_MIXTRAL_8X78 = "Groq/mixtral-8x7b-32768"
    GROQ_LLAMA2_70B   = "Groq/llama2-70b-4096"
    GOOGLE_GEMINI_PRO = "Google/gemini-1.5-pro-latest"

    @staticmethod
    def extract_model_name( compound_name ):
        
        # Model names are stored in the format "Groq/{model_name} in the config_mgr file
        if "/" in compound_name:
            return compound_name.split( "/" )[ 1 ]
        else:
            du.print_banner( f"WARNING: Model name [{compound_name}] doesn't isn't in 'Make/model' format! Returning entire string as is" )
            return compound_name

    def __init__( self, model=PHIND_34B_v2, config_mgr=None, default_url=None, debug=False, verbose=False ):
        
        self.timer          = None
        self.debug          = debug
        self.verbose        = verbose
        self.model          = model
        # Get the TGI server URL for this context
        self.tgi_server_url = du.get_tgi_server_url_for_this_context( default_url=default_url )
        self.config_mgr     = config_mgr

    def _start_timer( self, msg="Asking LLM [{model}]..." ):
        
        msg        = msg.format( model=self.model )
        self.timer = Stopwatch( msg=msg )
        
    def _stop_timer( self, msg="Done!", chunks=[ ] ):
        
        self.timer.print( msg=msg, use_millis=True )
        
        if chunks:
            chunks_per_second = len( chunks ) / ( self.timer.get_delta_ms() / 1000.0 )
            print( f"Chunks per second [{round( chunks_per_second, 1 )}]" )
        
    def _do_conditional_print( self, chunk, ellipsis_count=0, debug=False ):
        
        if debug:
            print( chunk, end="" )
        else:
            print( ".", end="" )
            ellipsis_count += 1
            if ellipsis_count == 120:
                ellipsis_count = 0
                print()
                
        return ellipsis_count
    
    def query_llm( self, model=None, prompt_yaml=None, prompt=None, preamble=None, question=None, max_new_tokens=1024, temperature=0.5, top_k=100, top_p=0.25, stop_sequences=None, debug=None, verbose=None ):
        
        try:
            if prompt_yaml is None and preamble is None and question is None and prompt is None:
                raise ValueError( "ERROR: Neither prompt_yaml, nor prompt, nor preamble, nor question has a value set!" )
            
            # Allow us to override the prompt, preamble, and question set when instantiated
            if model is not None: self.model = model
            
            if self.model == Llm.PHIND_34B_v2:
                
                # Quick sanity check
                if prompt is None: raise ValueError( "ERROR: Prompt is `None`!" )
                
                return self._query_llm_phind(
                    prompt, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, top_p=top_p, debug=debug, verbose=verbose, stop_sequences=stop_sequences
                )
            
            elif self.model == Llm.GOOGLE_GEMINI_PRO:
                
                # Quick sanity check
                if prompt is None: raise ValueError( "ERROR: Prompt is `None`!" )
                return self._query_llm_google(
                    prompt, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, top_p=top_p, stop_sequences=stop_sequences, debug=debug, verbose=verbose
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
                    
                if self.model.startswith( "OpenAI/" ):
                    return self._query_llm_openai( preamble, question, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, top_p=top_p, stop_sequences=stop_sequences, debug=debug, verbose=verbose )
                elif self.model.startswith( "Groq/" ):
                    return self._query_llm_groq( preamble, question, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, top_p=top_p, stop_sequences=stop_sequences, debug=debug, verbose=verbose )
                elif self.model.startswith( "Google/" ):
                    return self._query_llm_google( preamble, question, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, top_p=top_p, stop_sequences=stop_sequences, debug=debug, verbose=verbose )
                else:
                    raise ValueError( f"ERROR: Model [{self.model}] not recognized!" )
                
        except ConnectionError as ce:
            
            du.print_stack_trace( ce, explanation="ConnectionError: Server isn't responding", caller="Llm.query_llm()" )
            return "I'm sorry Dave, I'm afraid I can't do that because the LLM server isn't responding. Please check system logs."
    
    def _query_llm_google( self, prompt, max_new_tokens=1024, temperature=0.25, top_k=10, top_p=0.25, stop_sequences=[ "</response>" ], stream=True, debug=None, verbose=None ):
        
        if debug   is None: debug   = self.debug
        if verbose is None: verbose = self.verbose
        
        print( prompt )
        
        self._start_timer()
        genai.configure( api_key=du.get_api_key( "google" ) )
        
        generation_config = {
                  "temperature": temperature,
                        "top_p": top_p,
                        "top_k": top_k,
            "max_output_tokens": max_new_tokens,
               "stop_sequences": stop_sequences
        }
        model    = genai.GenerativeModel( "models/" + Llm.extract_model_name( self.model ) )
        response = model.generate_content( prompt, generation_config=generation_config, stream=stream )
        
        chunks = [ ]
        ellipsis_count = 0
        
        # Chunks are not the same as tokens, specifically for Google models
        for chunk in response:
            chunks.append( chunk.text )
            ellipsis_count = self._do_conditional_print( chunk.text, ellipsis_count, debug=debug )

        self._stop_timer( chunks=chunks )
        
        # According to the documentation, stop sequences will not be returned with the chunks, So append the most likely: response
        return "".join( chunks ).strip() + "</response>"
    
    def _query_llm_groq( self, preamble, query, prompt_yaml=None, max_new_tokens=1024, temperature=0.25, stop_sequences=[ "</response>" ], top_k=10, top_p=0.9, debug=False, verbose=False ):
        
        client = Groq( api_key=du.get_api_key( "groq" ) )
        stream = client.chat.completions.create(
            messages=[
                { "role"   : "system", "content": preamble },
                { "role"   : "user", "content": query }
            ],
            # Model names are stored in the format "Groq/{model_name} in the config_mgr file
            model=Llm.extract_model_name( self.model ),
            # model=self.model.split( "/" )[ 1 ],
            temperature=temperature,
            max_tokens=max_new_tokens,
            top_p=top_p,
            # Not used by groq: https://console.groq.com/docs/text-chat
            # top_k=top_k,
            stop=stop_sequences,
            stream=True,
        )
        self._start_timer()
        chunks = [ ]
        ellipsis_count = 0
        for chunk in stream:
            
            chunks.append( str( chunk.choices[ 0 ].delta.content ) )
            ellipsis_count = self._do_conditional_print( chunk.choices[ 0 ].delta.content, ellipsis_count, debug=debug )
            
        self._stop_timer( chunks=chunks )
        
        return "".join( chunks ).strip()
    
    def _query_llm_openai( self, preamble, query, max_new_tokens=1024, temperature=0.25, top_k=10, top_p=0.25, stop_sequences=[ "</response>" ], debug=False, verbose=False ):
        
        openai.api_key = du.get_api_key( "openai" )
        
        self._start_timer()
        
        stream = openai.chat.completions.create(
            # Model names are stored in the format "OpenAI/{model_name} in the config_mgr file
            # model=self.model.split( "/" )[ 1 ],
            model=Llm.extract_model_name( self.model ),
            messages=[
                { "role": "system", "content": preamble },
                { "role": "user", "content": query }
            ],
            max_tokens=max_new_tokens,
            # It's recommended to use top P or temperature but not both... TODO: decide which one to use
            # https://platform.openai.com/docs/api-reference/chat/create
            temperature=temperature,
            top_p=top_p,
            # Not used by open AI?
            # top_k=top_k,
            # Zero is default value for frequency and presence penalties
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=stop_sequences,
            stream=True
        )
        chunks         = [ ]
        ellipsis_count = 0
        for chunk in stream:
            if chunk.choices[ 0 ].delta.content is not None:
                chunks.append( chunk.choices[ 0 ].delta.content )
                ellipsis_count = self._do_conditional_print( chunk.choices[ 0 ].delta.content, ellipsis_count, debug=debug )
                
        self._stop_timer( chunks=chunks )
        response = "".join( chunks ).strip()
        
        return response
    
    def _query_llm_phind(
            self, prompt, max_new_tokens=1024, temperature=0.25, top_k=10, top_p=0.25, stop_sequences=[ "</response>", "></s>" ], debug=False, verbose=False
    ):
        self._start_timer()
        
        client = InferenceClient( self.tgi_server_url )
        token_list     = [ ]
        ellipsis_count = 0
        
        if self.debug and self.verbose:
            for line in prompt.split( "\n" ):
                print( line )
        
        for token in client.text_generation(
                prompt, max_new_tokens=max_new_tokens, stream=True, temperature=temperature, top_k=top_k, top_p=top_p,
                stop_sequences=stop_sequences
        ):
            ellipsis_count = self._do_conditional_print( token, ellipsis_count, debug=debug )
            token_list.append( token )
        
        response = "".join( token_list ).strip()
        
        self._stop_timer( chunks=token_list )
        
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
    <data>
      <row>
        <todo_item>bread</todo_item>
        <due_date>2024-03-08 00:00:00</due_date>
        <priority>normal</priority>
        <completed>no</completed>
        <list_name>trader joe's</list_name>
      </row>
      <row>
        <todo_item>talk to Yevon about total compensation</todo_item>
        <due_date>2024-03-08 00:00:00</due_date>
        <priority>normal</priority>
        <completed>no</completed>
        <list_name>ongoing google interview marathon</list_name>
      </row>
    </data>"""
    question = "What's on my todo list for today?"
    # question = "Do I have any concerts this week?"
    
    # raw_output = """
    #       <row>
    #         <start_date>2024-02-27 00:00:00</start_date>
    #         <end_date>2024-03-01 00:00:00</end_date>
    #         <start_time>00:00</start_time>
    #         <end_time>23:59</end_time>
    #         <event_type>concert</event_type>
    #         <recurrent>False</recurrent>
    #         <recurrence_interval/>
    #         <priority_level>low</priority_level>
    #         <name>Pablo</name>
    #         <relationship>friend</relationship>
    #         <description_who_what_where>Concert of Pablo at the city center</description_who_what_where>
    #       </row>
    #       <row>
    #         <start_date>2024-02-28 00:00:00</start_date>
    #         <end_date>2024-02-28 00:00:00</end_date>
    #         <start_time>00:00</start_time>
    #         <end_time>23:59</end_time>
    #         <event_type>concert</event_type>
    #         <recurrent>False</recurrent>
    #         <recurrence_interval/>
    #         <priority_level>highest</priority_level>
    #         <name>John</name>
    #         <relationship>coworker</relationship>
    #         <description_who_what_where>Concert of John at the city center</description_who_what_where>
    #       </row>
    #       <row>
    #         <start_date>2024-03-01 00:00:00</start_date>
    #         <end_date>2024-03-01 00:00:00</end_date>
    #         <start_time>00:00</start_time>
    #         <end_time>23:59</end_time>
    #         <event_type>concert</event_type>
    #         <recurrent>False</recurrent>
    #         <recurrence_interval/>
    #         <priority_level>medium</priority_level>
    #         <name>Sue</name>
    #         <relationship>sister</relationship>
    #         <description_who_what_where>Concert of Sue at the city center</description_who_what_where>
    #       </row>
    #       <row>
    #         <start_date>2024-03-01 00:00:00</start_date>
    #         <end_date>2024-03-03 00:00:00</end_date>
    #         <start_time>00:00</start_time>
    #         <end_time>23:59</end_time>
    #         <event_type>concert</event_type>
    #         <recurrent>False</recurrent>
    #         <recurrence_interval/>
    #         <priority_level>none</priority_level>
    #         <name>Inash</name>
    #         <relationship>girlfriend</relationship>
    #         <description_who_what_where>Concert of Inash at the city center</description_who_what_where>
    #       </row>
    #       <row>
    #         <start_date>2024-03-03 00:00:00</start_date>
    #         <end_date>2024-03-03 00:00:00</end_date>
    #         <start_time>00:00</start_time>
    #         <end_time>23:59</end_time>
    #         <event_type>concert</event_type>
    #         <recurrent>False</recurrent>
    #         <recurrence_interval/>
    #         <priority_level>high</priority_level>
    #         <name>Inash</name>
    #         <relationship>girlfriend</relationship>
    #         <description_who_what_where>Concert of Inash at the city center</description_who_what_where>
    #       </row>"""
    prompt  = prompt_template.format( question=question, raw_output=raw_output )
    results = llm.query_llm( prompt=prompt )
    print( results )
    