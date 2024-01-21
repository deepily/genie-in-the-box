import os
import re

import pandas as pd
import json
import openai

from xmlschema                import XMLSchema
from sklearn.model_selection  import train_test_split

import lib.utils.util         as du
import lib.utils.util_xml     as dux

from huggingface_hub          import InferenceClient
from lib.utils.util_stopwatch import Stopwatch
from lib.agents.agent         import Agent

class XmlFineTuningPromptGenerator:
    
    def __init__( self, path_prefix=du.get_project_root(), tgi_url="http://172.17.0.5:3000", debug=False, verbose=False, silent=False ):
        
        self.debug            = debug
        self.verbose          = verbose
        self.silent           = silent
        
        self.path_prefix      = path_prefix
        self.tgi_url          = tgi_url
        self.browser_commands = self._get_browser_command()
        self.command_choices  = "'" + "', '".join( self.browser_commands.keys() ) + "' and 'none'"
        
        # All six, well-formed XML templates are set by the call to self._set_templates()
        self.gpt_instruction_template = None
        self.instruction_template     = None
        self.input_template           = None
        self.human_says_template      = None
        self.response_format          = None
        self.output_template          = None
        
        self._set_templates()
        
        self.qna_df               = None
        self._call_counter        = 0
        self._xml_schema          = self._get_xml_schema()
    
    def _get_browser_command( self ):
        
        browser_commands = {
            "search new tab"                   : "/src/ephemera/prompts/data/synthetic-data-search-in-new-tab.txt",
            "search current tab"               : "/src/ephemera/prompts/data/synthetic-data-search-in-current-tab.txt",
            "search google new tab"            : "/src/ephemera/prompts/data/synthetic-data-search-google-in-new-tab.txt",
            "search google current tab"        : "/src/ephemera/prompts/data/synthetic-data-search-google-in-current-tab.txt",
            "search google scholar new tab"    : "/src/ephemera/prompts/data/synthetic-data-search-google-scholar-in-new-tab.txt",
            "search google scholar current tab": "/src/ephemera/prompts/data/synthetic-data-search-google-scholar-in-current-tab.txt",
        }
        for command in browser_commands.keys():
            print( f"Commands file for [{command}] exists: { os.path.exists( self.path_prefix + browser_commands[ command ] ) }" )
        print()
            
        return browser_commands
    
    def _get_search_terms( self, requested_length ):
        
        # Load search terms file
        search_terms = du.get_file_as_list(
            self.path_prefix + "/src/ephemera/prompts/data/search-terms.txt", lower_case=False, clean=True, randomize=True
        )
        
        # If we don't have enough search terms, append copies of the search term list until we do
        while requested_length > len( search_terms ):
            # advise that we're inserting duplicate search terms into the search term list
            print( f"Inserting duplicate search terms into the search term list. Requested length [{requested_length}] > search term list length [{len( search_terms )}]" )
            search_terms += search_terms
        
        # Truncate the search terms list to equal the requested len
        search_terms = search_terms[ :requested_length ]
        
        return search_terms

    def _set_templates( self ):
        
        self.gpt_instruction_template = """INSTRUCTIONS:
        Your job is to discern the intent of a human voice command transcription and translate it into a standardized command that a browser on your computer would understand.

        You will be given a human voice command as INPUT as well as a list of possible standardized commands. You must choose the correct standardized command from the following list: `{command_choices}`.

        RESPONSE FORMAT: MUST be returned wrapped in simple, well-formed XML
        <response>
            <browser-command></browser-command>
            <args></args>
        </response>
        """
        
        self.instruction_template = """Your job is to discern the intent of a human voice command transcription and translate it into a standardized command that a browser on your computer would understand.

        You will be given a human voice command and a list of possible standardized commands. You must choose the correct standardized command from the following list: `{command_choices}`.

        Requirement: You MUST NOT use python code to answer this question.
        Requirement: You MUST use your linguistic knowledge and intuition to answer this question.
        Hint: Anything that isn't a part of the command itself should be treated as arguments related to the command."""
        
        self.input_template = """
        Below is the raw human voice command transcription formatted using simple XML:
        {human_says}
        
        The standardized command that you translate MUST be returned wrapped in simple, well-formed XML:
        {response_format}"""
        
        self.human_says_template = """
        <human>
            <voice-command>{voice_command}</voice-command>
        </human>"""
        
        self.response_format = """
        <response>
            <browser-command></browser-command>
            <args></args>
        </response>

        Requirement: The first word of your response MUST be `<response>`"""
        
        self.output_template = """
        <response>
            <browser-command>{browser_command}</browser-command>
            <args>{args}</args>
        </response>"""
        
        return
    
    def _get_prompt_instruction_format( self, instruction, input ):

        return f"""### Instruction:
    Use the Task and Input given below to write a Response that can solve the following Task.
    
    ### Task:
    {instruction}
    
    ### Input:
    {input}
    
    ### Response:
    """
    
    def build_training_prompts( self ):
        
        instructions = [ ]
        inputs       = [ ]
        outputs      = [ ]
        prompts      = [ ]
        gpt_messages = [ ]
        
        gpt_instruction = self.gpt_instruction_template.format( command_choices=self.command_choices )
        
        # For each browser command, load the corresponding file and generate prompts
        for browser_command in self.browser_commands.keys():
            
            du.print_banner( browser_command, prepend_nl=True, end="\n" )
            counter = 0
            
            raw_lines = du.get_file_as_list( self.path_prefix + self.browser_commands[ browser_command ], clean=True )
            for line in raw_lines[ 0:100 ]:  # [ 0:2 ]:#
                
                # get newly randomized search terms on every iteration
                for search in self._get_search_terms( len( raw_lines ) ):  # [ 0:10 ]: #[ 0:2]:#:
                    
                    voice_command = line.replace( "SEARCH_TERMS", search )
                    # print( voice_command )
                    instruction = self.instruction_template.format( command_choices=self.command_choices )
                    human_says  = self.human_says_template.format( voice_command=voice_command )
                    input       = self.input_template.format( human_says=human_says, response_format=self.response_format )
                    output      = self.output_template.format( browser_command=browser_command, args=search )
                    prompt      = self._get_prompt_instruction_format( instruction, input )
                    
                    instructions.append( instruction )
                    inputs.append( input )
                    outputs.append( output )
                    prompts.append( prompt )
                    
                    gpt_messages.append( {
                        "messages": [
                            { "role": "system", "content": gpt_instruction },
                            { "role": "user", "content": voice_command },
                            { "role": "assistant", "content": self.output_template.format( browser_command=browser_command, args=search ) }
                        ]
                    }
                    )
                    
                    if counter % 10 == 0:
                        print( ".", end="" )
                    counter += 1
                    if counter == 1200:
                        print()
                        counter = 0
            
            print()
        
        qna_df = pd.DataFrame( { "instruction": instructions, "input": inputs, "output": outputs, "prompt": prompts, "gpt_message": gpt_messages } )
        qna_df = self._prune_duplicates( qna_df )
        
        self.qna_df = qna_df
        
        return self.qna_df
    def _prune_duplicates( self, df ):
        
        du.print_banner( "Pruning duplicates...", prepend_nl=True )
        rows_pre = df.shape[ 0 ]
        print( f" PRE {rows_pre:,} training inputs..." )
        df.drop_duplicates( subset=[ "input" ], inplace=True )
        rows_post  = df.shape[ 0 ]
        dupes_rows = rows_pre - rows_post
        dupes_pct  = dupes_rows / rows_pre * 100.0
        print( f"POST {rows_post:,} training inputs. Deleted {dupes_rows:,} rows = {dupes_pct:.1f}% duplicate questions" )
        
        return df
    
    def _get_xml_schema( self ):
        
        xsd_string = """
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
          <xs:element name="response">
            <xs:complexType>
              <xs:sequence>
                <xs:element name="browser-command" type="xs:string"/>
                <xs:element name="args" type="xs:string"/>
              </xs:sequence>
            </xs:complexType>
          </xs:element>
        </xs:schema>
        """
        
        self.schema = XMLSchema( xsd_string )
    
    def is_valid_xml( self, xml_str ):
        
        try:
            return self.schema.is_valid( xml_str )
        except Exception as e:
            return False
    
    # %%
    def contains_valid_xml_tag( self, xml_str, tag_name ):
        
        try:
            return "<" + tag_name + ">" in xml_str and "</" + tag_name + ">" in xml_str
        except Exception as e:
            return False
    
    def is_response_exact_match( self, response, answer ):
        
        # Remove white space outside XML tags
        response = re.sub( r'>\s+<', '><', response.strip() )
        
        # Remove white space outside XML tags
        answer = re.sub( r'>\s+<', '><', answer.strip() )
        
        if self.debug and self.verbose:
            print( f"response: [{response}]" )
            print( f"  answer: [{answer}]" )
            
        return response == answer
    
    def contains_correct_response_values( self, response, answer ):
        
        """Check to see if the most common formatting error (```xml) is hiding a correct <response>...</response>"""
        response = dux.get_xml_tag_and_value_by_name( response, "response", default_value="broken" )
        if response == "broken":
            return False
        
        return self.is_response_exact_match( response, answer )
    
    def tag_values_are_equal( self, response, answer, tag_name="browser-command" ):
    
        command_response = dux.get_value_by_xml_tag_name( response, tag_name, default_value="broken" )
        command_answer   = dux.get_value_by_xml_tag_name(   answer, tag_name, default_value="broken" )
        
        return command_response != "broken" and command_answer != "broken" and command_response == command_answer
    
    def _query_llm_in_memory( self, tokenizer, model, prompt, max_new_tokens=1024, model_name=Agent.PHIND_34B_v2, device = "cuda:0", silent=False ):
        
        timer = Stopwatch( msg=f"Asking LLM [{model_name}]...".format( model_name ), silent=silent )
        
        inputs = tokenizer( prompt, return_tensors="pt" ).to( device )
        
        stop_token_id = tokenizer.encode( "</response>" )[ 0 ]
        
        generation_output = model.generate(
            input_ids=inputs[ "input_ids" ],
            attention_mask=inputs[ "attention_mask" ],
            max_new_tokens=max_new_tokens,
            eos_token_id=stop_token_id,
            pad_token_id=stop_token_id
        )
        
        # if self.debug:
        #     print( "generation_output[ 0 ]:", generation_output[ 0 ], end="\n\n" )
        #     print( "generation_output[ 0 ].shape:", generation_output[ 0 ].shape, end="\n\n" )
        
        # Skip decoding the prompt part of the output
        input_length = inputs[ "input_ids" ].size( 1 )
        raw_output = tokenizer.decode( generation_output[ 0 ][ input_length: ] )
        
        timer.print( msg="Done!", use_millis=True, end="\n" )
        tokens_per_second = len( raw_output ) / ( timer.get_delta_ms() / 1000.0 )
        print( f"Tokens per second [{round( tokens_per_second, 1 )}]" )
        
        # response   = raw_output.split( "### Response:" )[ 1 ]
        
        response = raw_output.replace( "</s><s>", "" ).strip()
        response = re.sub( r'>\s+<', '><', response )
        if self.debug:
            print( f"Response: [{response}]", end="\n\n" )
            
        return response

        
    def _query_llm_tgi( self, prompt, model_name=Agent.PHIND_34B_v2, max_new_tokens=1024, temperature=0.25, top_k=10, top_p=0.9, silent=False ):
    
        timer = Stopwatch( msg=f"Asking LLM [{model_name}]...".format( model_name ), silent=silent )
        
        client         = InferenceClient( self.tgi_url )
        token_list     = [ ]
        ellipsis_count = 0
        
        if self.debug and self.verbose:
            for line in prompt.split( "\n" ):
                print( line )
        
        for token in client.text_generation(
            prompt, max_new_tokens=max_new_tokens, stream=True, temperature=temperature, top_k=top_k, top_p=top_p, stop_sequences=[ "</response>" ]
        ):
            if self.debug:
                print( token, end="" )
            else:
                if not silent: print( ".", end="" )
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
    
    def _query_llm_openai( self, messages, model_name="gpt-3.5-turbo-1106" ):
        
        openai.api_key = du.get_api_key( "openai", project_root=du.get_project_root() )
        
        timer    = Stopwatch( msg=f"Asking LLM [{model_name}]...".format( model_name ) )
        
        response = openai.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0,
            max_tokens=256,
            top_p=1.0,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        
        timer.print( "Done!", use_millis=True )
        if self.debug and self.verbose:
            print( response )
        
        return response.choices[ 0 ].message.content.strip()
    
    def reset_call_counter( self ):
        
        self._call_counter = 0
    
    def get_response_to_prompt( self, prompt, rows, switch="tgi", model_name=Agent.PHIND_34B_v2, tokenizer=None, model=None, max_new_tokens=1024, temperature=0.25, top_k=10, top_p=0.9, device="cuda:0", silent=False  ):
        
        self._call_counter += 1
        
        print( f"Processing call [{self._call_counter:03d}] out of [{rows}] = [{round( self._call_counter / rows * 100.0, 1 )}%]... ")
        
        if switch == "tgi":
            return self._query_llm_tgi( prompt, model_name=model_name, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, top_p=top_p, silent=silent )
        elif switch == "openai":
            return self._query_llm_openai( prompt[ "messages" ], model_name=model_name )
        elif switch == "huggingface":
            return self._query_llm_in_memory( tokenizer, model, prompt, model_name=model_name, max_new_tokens=max_new_tokens, device=device, silent=silent )
        else:
            raise Exception( f"Unknown switch [{switch}]" )

    def generate_responses( self, df, tokenizer=None, model=None, switch="tgi", model_name=Agent.PHIND_34B_v2, max_new_tokens=1024, temperature=0.25, top_k=10, top_p=0.9, device="cuda:0", silent=False ):
        
        self.reset_call_counter()
        rows = df.shape[ 0 ]
        
        timer = Stopwatch( msg=f"Generating responses for {rows:,} rows...", silent=silent )
        
        if switch == "tgi":
            print( f"Using TGI w/ model_name [{model_name}]..." )
            df[ "response" ]  = df[ "prompt" ].apply( lambda cell: self.get_response_to_prompt( cell, rows, switch=switch, model_name=model_name, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, top_p=top_p, silent=silent ) )
        elif switch == "openai":
            print( f"Using OPENAI w/ model_name [{model_name}]..." )
            df[ "response" ]  = df[ "gpt_message" ].apply( lambda cell: self.get_response_to_prompt( cell, rows, switch=switch, model_name=model_name, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, top_p=top_p, silent=silent ) )
        elif switch == "huggingface":
            print( f"Using HuggingFace model_name [{model_name}] in memory...", end="\n\n" )
            df[ "response" ]  = df[ "prompt" ].apply( lambda cell: self.get_response_to_prompt( cell, rows, switch=switch, model_name=model_name, tokenizer=tokenizer, model=model, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, top_p=top_p, device=device, silent=silent ) )
        else:
            raise Exception( f"Unknown switch [{switch}]" )
        
        timer.print( msg="Done!", use_millis=False, prepend_nl=True, end="\n" )
        ms_per_item = timer.get_delta_ms() / ( rows * 1.0 )
        print( f"[{round( ms_per_item, 1 )}] ms per item" )
        
        return df
    def validate_responses( self, df ):
        
        # Validate the structure and content of the xml response
        df[ "response_xml_is_valid" ]       = df[ "response" ].apply( lambda cell: self.is_valid_xml( cell ) )
        df[ "contains_response" ]           = df[ "response" ].apply( lambda cell: self.contains_valid_xml_tag( cell, "response" ) )
        df[ "contains_browser_command" ]    = df[ "response" ].apply( lambda cell: self.contains_valid_xml_tag( cell, "browser-command" ) )
        df[ "contains_args" ]               = df[ "response" ].apply( lambda cell: self.contains_valid_xml_tag( cell, "args" ) )
        df[ "response_is_exact" ]           = df.apply( lambda row: self.is_response_exact_match( row[ "response" ], row[ "output" ] ), axis=1 )
        df[ "response_has_correct_values" ] = df.apply( lambda row: self.contains_correct_response_values( row[ "response" ], row[ "output" ] ), axis=1 )
        df[ "browser_command_is_correct" ]  = df.apply( lambda row: self.tag_values_are_equal( row[ "response" ], row[ "output" ], tag_name="browser-command" ), axis=1 )
        df[ "args_is_correct" ]             = df.apply( lambda row: self.tag_values_are_equal( row[ "response" ], row[ "output" ], tag_name="args" ), axis=1 )
        
        return df
    
    def print_validation_stats( self, df, title="Validation Stats" ):
        
        du.print_banner( title, prepend_nl=True )
        print( f"               Is valid xml {df.response_xml_is_valid.mean() * 100:.1f}%" )
        print( f"          Contains response {df.contains_response.mean() * 100:.1f}%" )
        print( f" Contains <browser-command> {df.contains_browser_command.mean() * 100:.1f}%" )
        print( f"            Contains <args> {df.contains_args.mean() * 100:.1f}%" )
        print( f"          Response is exact {df.response_is_exact.mean() * 100:.1f}%" )
        print( f"Response has correct values {df.response_has_correct_values.mean() * 100:.1f}%" )
        print( f" Browser command is correct {df.browser_command_is_correct.mean() * 100:.1f}%" )
        print( f"            Args is correct {df.args_is_correct.mean() * 100:.1f}%" )
    
    def get_train_test_validate_split( self, df, sample_size=1000, test_size=0.2, test_validate_size=0.5 ):
        
        sampled_df = df[ [ "instruction", "input", "output", "prompt", "gpt_message" ] ].sample( sample_size, random_state=42 ).copy()
        
        # Split the dataframe into train and (test+validate)
        train_df, test_validate_df = train_test_split( sampled_df, test_size=test_size, random_state=42 )
        
        # Then split (test+validate) into test and validate
        test_df, validate_df = train_test_split( test_validate_df, test_size=test_validate_size, random_state=42 )
        
        return train_df, test_df, validate_df
    
    def write_ttv_split_to_jsonl( self, train_df, test_df, validate_df ):
        
        du.print_banner( "Writing train, test, validate splits to jsonl...", prepend_nl=True)
        print( f"   train_df.shape: {train_df.shape[ 0 ]:,} x {train_df.shape[ 1 ]}" )
        print( f"    test_df.shape: {test_df.shape[ 0 ]:,} x {test_df.shape[ 1 ]}" )
        print( f"validate_df.shape: {validate_df.shape[ 0 ]:,} x {validate_df.shape[ 1 ]}" )
        
        path = self.path_prefix + "/src/ephemera/prompts/data/voice-commands-xml-train.jsonl"
        train_df.to_json( path, orient="records", lines=True )
        os.chmod( path, 0o666 )
        
        path = self.path_prefix + "/src/ephemera/prompts/data/voice-commands-xml-test.jsonl"
        test_df.to_json( path, orient="records", lines=True )
        os.chmod( path, 0o666 )
        
        path = self.path_prefix + "/src/ephemera/prompts/data/voice-commands-xml-validate.jsonl"
        validate_df.to_json( path, orient="records", lines=True )
        os.chmod( path, 0o666 )
        
        # GPT Training set
        
        path = self.path_prefix + "/src/ephemera/prompts/data/voice-commands-xml-train-gpt.jsonl"
        train_df.gpt_message.to_json( path, orient="records", lines=True )
        os.chmod( path, 0o666 )
        
        path = self.path_prefix + "/src/ephemera/prompts/data/voice-commands-xml-test-gpt.jsonl"
        test_df.gpt_message.to_json( path, orient="records", lines=True )
        os.chmod( path, 0o666 )
        
        
if __name__ == "__main__":
    
    # ------------------------------------------------------------------------------------------------------------------------
    # - Validation Stats: Before fine tuning PEFT adapter on phind
    # ------------------------------------------------------------------------------------------------------------------------
    #
    #                Is valid xml 100.0%
    #           Contains response 100.0%
    #    Contains browser command 100.0%
    #               Contains args 100.0%
    #           Response is exact 46.6%
    # Response has correct values 46.6%
    #  Browser command is correct 55.3%
    #             Args is correct 75.5%
    #
    # Validating 1,000 responses... Done! in 22:18
    # Items per second [0.7]
    # Seconds per item [1.3]
    
    # ------------------------------------------------------------------------------------------------------------------------
    # - Validation Stats: Before fine tuning GPT 3.5
    # ------------------------------------------------------------------------------------------------------------------------
    # 
    #                Is valid xml 98.0%
    #           Contains response 100.0%
    #    Contains browser command 100.0%
    #               Contains args 100.0%
    #           Response is exact 94.0%
    # Response has correct values 95.0%
    #  Browser command is correct 97.0%
    #             Args is correct 96.0%
    # 
    # Validating 100 responses... Done! in 04:59
    # Items per second [0.3]
    # Seconds per item [3.0]
    #
    # ------------------------------------------------------------------------------------------------------------------------
    # - Validation Stats for Mistral-7B-Instruct-v0.2, fine tuned on 1000 rows and loaded w/ bnb 4nf quantization
    # ------------------------------------------------------------------------------------------------------------------------
    #
    #                Is valid xml 100.0%
    #           Contains response 100.0%
    #    Contains browser command 100.0%
    #               Contains args 100.0%
    #           Response is exact 99.0%
    # Response has correct values 99.0%
    #  Browser command is correct 99.0%
    #             Args is correct 100.0%
    #
    # Validating 100 responses... Done! in 01:03
    # Items per second [1.6]
    # Seconds per item [0.6]
    #
    # ------------------------------------------------------------------------------------------------------------------------
    # - Validation Stats for `mistralai/Mistral-7B-Instruct-v0.2-AWQ`
    # ------------------------------------------------------------------------------------------------------------------------
    #
    #                Is valid xml 100.0%
    #           Contains response 100.0%
    #    Contains browser command 100.0%
    #               Contains args 100.0%
    #           Response is exact 92.0%
    # Response has correct values 92.0%
    #  Browser command is correct 93.0%
    #             Args is correct 99.0%`
    
    print( "Running XmlFineTuningPromptGenerator..." )
    print( os.getcwd() )
    # os.chdir( "/var/model/genie-in-the-box/src" )
    # print( os.getcwd() )
    # #
    xml_ftp_generator = XmlFineTuningPromptGenerator( tgi_url="http://127.0.0.1:3000", debug=True )
    # xml_ftp_generator = XmlFineTuningPromptGenerator( tgi_url="http://127.0.0.1:8080", debug=True )
    qna_df            = xml_ftp_generator.build_training_prompts()
    for line in qna_df.prompt[ 0 ].split( "\n" ): print( line )
    
    # train_df, test_df, validate_df = xml_ftp_generator.get_train_test_validate_split( qna_df, sample_size=10000, test_size=0.2, test_validate_size=0.5 )
    # xml_ftp_generator.write_ttv_split_to_jsonl( train_df, test_df, validate_df )

    # validation block
    # validate_df    = pd.read_json( xml_ftp_generator.path_prefix + "/src/ephemera/prompts/data/voice-commands-xml-validate.jsonl", lines=True ).sample( 100, random_state=42 )
    # timer          = Stopwatch( msg=f"Validating {validate_df.shape[ 0 ]:,} responses...", silent=False )
    #
    # model_name     = "mistralai/Mistral-7B-Instruct-v0.2-AWQ"
    # validate_df    = xml_ftp_generator.generate_responses( validate_df, switch="tgi", model_name=model_name )
    # validate_df    = xml_ftp_generator.validate_responses( validate_df )
    #
    # # model_name     = "gpt-3.5-turbo-1106"
    # # validate_df    = xml_ftp_generator.generate_responses( validate_df, switch="openai", model_name= )
    # # validate_df    = xml_ftp_generator.validate_responses( validate_df )
    #
    # xml_ftp_generator.print_validation_stats( validate_df, title=f"Validation Stats for `{model_name}`" )
    
    # timer.print( msg="Done!", use_millis=False, prepend_nl=True, end="\n" )
    # delta_ms         = timer.get_delta_ms()
    # items_per_second = validate_df.shape[ 0 ] / ( delta_ms / 1000.0 )
    # seconds_per_item = ( delta_ms / 1000.0 ) / validate_df.shape[ 0 ]
    #
    # print( f"Items per second [{round( items_per_second, 1 )}]" )
    # print( f"Seconds per item [{round( seconds_per_item, 1 )}]" )
    