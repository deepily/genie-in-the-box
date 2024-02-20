import os
import openai

from huggingface_hub import InferenceClient

from lib.utils import util as du

from lib.utils.util_stopwatch      import Stopwatch
from lib.app.configuration_manager import ConfigurationManager

class RawOutputFormatter:
    
    GPT_4        = "gpt-4-0613"
    GPT_3_5      = "gpt-3.5-turbo-1106"
    PHIND_34B_v2 = "Phind/Phind-CodeLlama-34B-v2"
    
    def __init__(self, question, raw_output, routing_command, debug=False, verbose=False ):
        
        self.debug       = debug
        self.verbose     = verbose
        
        self.question    = question
        self.raw_output  = raw_output
        
        self.config_mgr = ConfigurationManager( env_var_name="GIB_CONFIG_MGR_CLI_ARGS" )

        self.routing_command_paths = {
            "agent router go to date and time": self.config_mgr.get( "raw_output_formatter_date_and_time" ),
            "agent router go to calendar"     : self.config_mgr.get( "raw_output_formatter_calendaring" ),
            "agent router go to weather"      : self.config_mgr.get( "raw_output_formatter_weather" ),
            "agent router go to todo list"    : self.config_mgr.get( "raw_output_formatter_todo_list" )
        }
        self.llms = {
            "agent router go to date and time": self.config_mgr.get( "formatter_llm_for_date_and_time" ),
            "agent router go to calendar"     : self.config_mgr.get( "formatter_llm_for_calendaring" ),
            "agent router go to weather"      : self.config_mgr.get( "formatter_llm_for_weather" ),
            "agent router go to todo list"    : self.config_mgr.get( "formatter_llm_for_todo_list" )
        }
        self.routing_command       = routing_command
        self.formatting_template   = du.get_file_as_string( du.get_project_root() + self.routing_command_paths.get( routing_command ) )
        self.prompt                = self._get_prompt()
        self.llm                   = self.llms[ routing_command ]
    
    def format_output( self ):
        
        return self._query_llm( model=self.llm )
    
    def _get_prompt( self ):
        
        # ¡OJO! This is a pretty simple case, but there will be formatting types that will require more sophisticated formatting
        return self.formatting_template.format( question=self.question, raw_output=self.raw_output )
    
    def _query_llm( self, model=PHIND_34B_v2, max_new_tokens=1024, temperature=0.5, top_k=100, top_p=0.25, debug=True ):
        
        if model == RawOutputFormatter.PHIND_34B_v2:
            
            # self.debug = debug
            return self._query_llm_phind( self.prompt, model=model, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, top_p=top_p, debug=debug )
            
        else:
            preamble = self.prompt.split( "### Input:" )[ 0 ]
            question = self.prompt.split( "### Input:" )[ 1 ]
            question = "### Input:" + question
            if debug:
                print( f"Preamble: [{preamble}]" )
                print( f"Question: [{question}]" )
            return self._query_llm_openai( preamble, question, model=model, debug=debug )

    def _query_llm_openai( self, preamble, query, model=GPT_3_5, debug=False ):
        openai.api_key = os.getenv( "FALSE_POSITIVE_API_KEY" )
        
        timer = Stopwatch( msg=f"Asking LLM [{model}]...".format( model ) )
        
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
    
    
    def _query_llm_phind(
            self, prompt, model=PHIND_34B_v2, max_new_tokens=1024, temperature=0.25, top_k=10, top_p=0.9,
            debug=False
    ):
        timer = Stopwatch( msg=f"Asking LLM [{model}]...".format( model ) )
        
        # Get the TGI server URL for this context
        default_url = self.config_mgr.get( "tgi_server_codegen_url", default=None )
        tgi_server_url = du.get_tgi_server_url_for_this_context( default_url=default_url )
        
        client = InferenceClient( tgi_server_url )
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
        tokens_per_second = len( token_list ) / (timer.get_delta_ms() / 1000.0)
        print( f"Tokens per second [{round( tokens_per_second, 1 )}]" )
        
        if self.debug:
            print( f"Token list length [{len( token_list )}]" )
            if self.verbose:
                for line in response.split( "\n" ):
                    print( line )
        
        return response

if __name__ == "__main__":
    
    routing_command = "agent router go to date and time"
    # question        = "What time is it now?"
    # question        = "What day is today?"
    question        = "Is it daytime or nighttime?"
    raw_output      = "8:57PM EST, Monday, February 19, 2024"
    formatter = RawOutputFormatter( question, raw_output, routing_command )
    print( formatter.format_output() )