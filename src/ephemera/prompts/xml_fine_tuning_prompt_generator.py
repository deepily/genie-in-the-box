import os
import re

import pandas as pd

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
        
        # All five are set by the call to self._set_templates()
        self.instruction_template = None
        self.input_template       = None
        self.human_says_template  = None
        self.response_format      = None
        self.output_template      = None
        
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
            
        return browser_commands
    
    def _get_search_terms( self, requested_length ):
        
        # Load search terms file
        search_terms = du.get_file_as_list(
            self.path_prefix + "/src/ephemera/prompts/data/search-terms.txt", lower_case=False, clean=True, randomize=True
        )
        
        # If we don't have enough search terms, append copies of the search term list until we do
        while requested_length > len( search_terms ):
            search_terms += search_terms
        
        # Truncate the search terms list to equal the requested len
        search_terms = search_terms[ :requested_length ]
        
        return search_terms

    def _set_templates( self ):
        
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
    
    ### Input:{input}
    
    ### Response:
    """
    
    def build_training_prompts( self ):
        
        instructions = [ ]
        inputs       = [ ]
        outputs      = [ ]
        prompts      = [ ]
        
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
                    
                    if counter % 10 == 0:
                        print( ".", end="" )
                    counter += 1
                    if counter == 1200:
                        print()
                        counter = 0
            
            print()
        
        qna_df = pd.DataFrame( { "instruction": instructions, "input": inputs, "output": outputs, "prompt": prompts } )
        self.qna_df = qna_df
        
        return self.qna_df
    
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
        
        return response == answer
    
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
    
    def _query_llm_phind( self, prompt, model=Agent.PHIND_34B_v2, max_new_tokens=1024, temperature=0.25, top_k=10, top_p=0.9, debug=False, verbose=False, silent=False ):
    
        timer = Stopwatch( msg=f"Asking LLM [{model}]...".format( model ), silent=silent )
        
        client         = InferenceClient( self.tgi_url )
        token_list     = [ ]
        ellipsis_count = 0
        
        if debug and verbose:
            for line in prompt.split( "\n" ):
                print( line )
        
        for token in client.text_generation(
            prompt, max_new_tokens=max_new_tokens, stream=True, temperature=temperature, top_k=top_k, top_p=top_p, stop_sequences=[ "</response>" ]
        ):
            if debug:
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
        
        if debug:
            print( f"Token list length [{len( token_list )}]" )
            if verbose:
                for line in response.split( "\n" ):
                    print( line )
        
        
        return response

    def reset_call_counter( self ):
        
        self._call_counter = 0
    
    def get_response_to_prompt( self, prompt, rows ):
        
        self._call_counter += 1
        
        print( f"On call [{self._call_counter:03d}] out of [{rows}] = [{round( self._call_counter / rows * 100.0, 1 )}%]... ", end="" )
        
        return self._query_llm_phind( prompt, debug=self.debug, silent=self.silent )

    def generate_responses( self, df ):
        
        self.reset_call_counter()
        rows = df.shape[ 0 ]
        
        df[ "response" ]                    = df[ "prompt" ].apply( lambda cell: self.get_response_to_prompt( cell, rows ) )
        
        return df
    def validate_prompts_and_responses( self, df ):
        
        # self.reset_call_counter()
        # rows = df.shape[ 0 ]
        #
        # df[ "response" ]                    = df[ "prompt" ].apply( lambda cell: self.get_response_to_prompt( cell, rows ) )
        
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
    
    def print_validation_stats( self, df ):
        
        du.print_banner( "Validation Stats" )
        print( f"               Is valid xml {df.response_xml_is_valid.mean() * 100:.1f}%" )
        print( f"          Contains response {df.contains_response.mean() * 100:.1f}%" )
        print( f"   Contains browser command {df.contains_browser_command.mean() * 100:.1f}%" )
        print( f"              Contains args {df.contains_args.mean() * 100:.1f}%" )
        print( f"          Response is exact {df.response_is_exact.mean() * 100:.1f}%" )
        print( f"Response has correct values {df.response_has_correct_values.mean() * 100:.1f}%" )
        print( f" Browser command is correct {df.browser_command_is_correct.mean() * 100:.1f}%" )
        print( f"            Args is correct {df.args_is_correct.mean() * 100:.1f}%" )
    
    def get_train_test_validate_split( self, df, sample_size=1000, test_size=0.2, test_validate_size=0.5 ):
        
        sampled_df = df[ [ "instruction", "input", "output", "prompt" ] ].sample( sample_size, random_state=42 ).copy()
        
        # Split the dataframe into train and (test+validate)
        train_df, test_validate_df = train_test_split( sampled_df, test_size=test_size, random_state=42 )
        
        # Then split (test+validate) into test and validate
        test_df, validate_df = train_test_split( test_validate_df, test_size=test_validate_size, random_state=42 )
        
        return train_df, test_df, validate_df
    
    def write_ttv_split_to_jsonl( self, train_df, test_df, validate_df ):
        
        path = self.path_prefix + "/src/ephemera/prompts/data/voice-commands-xml-train.jsonl"
        train_df.to_json( path, orient="records", lines=True )
        os.chmod( path, 0o666 )
        
        path = self.path_prefix + "/src/ephemera/prompts/data/voice-commands-xml-test.jsonl"
        test_df.to_json( path, orient="records", lines=True )
        os.chmod( path, 0o666 )
        
        path = self.path_prefix + "/src/ephemera/prompts/data/voice-commands-xml-validate.jsonl"
        validate_df.to_json( path, orient="records", lines=True )
        os.chmod( path, 0o666 )
        
        
if __name__ == "__main__":
    
    print( "Running XmlFineTuningPromptGenerator..." )
    # print( os.getcwd() )
    # os.chdir( "/var/model/genie-in-the-box/src" )
    # print( os.getcwd() )
    # #
    # xml_ftp_generator = XmlFineTuningPromptGenerator( tgi_url="http://127.0.0.1:3000", debug=True )
    # qna_df            = xml_ftp_generator.build_training_prompts()
    #
    # train_df, test_df, validate_df = xml_ftp_generator.get_train_test_validate_split( qna_df, sample_size=10000, test_size=0.2, test_validate_size=0.5 )
    # #
    # xml_ftp_generator.write_ttv_split_to_jsonl( train_df, test_df, validate_df )
    
    # prompt = qna_df[ "prompt" ].iloc[ 0 ]
    # for line in prompt.split( "\n" ):
    #     print( line )
    #
    # sampled_qna_df    = qna_df.sample( 25 ).copy()
    # sampled_qna_df    = xml_ftp_generator.validate_prompts_and_responses( sampled_qna_df )
    #
    # xml_ftp_generator.print_validation_stats( sampled_qna_df )
    
    # xml_ftp_generator.reset_call_counter()
#     prompt = """
# Your job is to discern the intent of a human voice command transcription and translate it into a standardized command that a browser on your computer would understand.
#
# You will be given a human voice command and a list of possible standardized commands. You must choose the correct standardized command from the following list: `'search new tab', 'search current tab', 'search google new tab', 'search google current tab', 'search google scholar new tab', 'search google scholar current tab' and 'none'`.
#
# Requirement: You MUST NOT use python code to answer this question.
# Requirement: You MUST use your linguistic knowledge and intuition to answer this question.
# Hint: Anything that isn't a part of the command itself should be treated as arguments related to the command.
#
#
# Below is the raw human voice command transcription formatted using simple XML:
#
# <human>
#     <voice-command>BufferError new tab search</voice-command>
# </human>
#
# The standardized command that you translate MUST be returned wrapped in simple, well-formed XML:
#
# <response>
#     <browser-command></browser-command>
#     <args></args>
# </response>
#
# Requirement: The FIRST word of your response MUST be `<response>`
# Requirement: The LAST word of your response MUST be `</response>`
# """
#     response = xml_ftp_generator.get_response_to_prompt( prompt, 1 )
#     print( response )

    # qna_df = xml_fine_tuning_prompt_generator.build_training_prompts()
    
    # xml_str_1 = """
    # <response>
    #   <browser-command></browser-command>
    #   <args></args>
    # </response>
    # """
    # xml_str_2 = """
    # <response>
    #   <browser_command></browser_command>
    #   <args></args>
    # </response>
    # """
    # xml_str_3 = """
    # Sure here's your command!
    # <response>
    #   <browser-command></browser-command>
    #   <args></args>
    # </response>
    # """
    # xml_str_4 = """
    # ```xml
    # <response>
    #   <browser-command></browser-command>
    #   <args></args>
    # </response>
    # """
    # print( xml_ftp_generator.is_valid_xml( xml_str_1 ) )  # Output: True
    # print( xml_ftp_generator.is_valid_xml( xml_str_2 ) )  # Output: False
    # print( xml_ftp_generator.is_valid_xml( xml_str_3 ) )  # Output: False
    # print( xml_ftp_generator.is_valid_xml( xml_str_4 ) )  # Output: False
    # print( xml_ftp_generator.contains_valid_xml_tag( "```xml<response><browser-command></browser-command><args></args></response>", "browser-command" ) )
    # print( xml_ftp_generator.is_response_exact_match(
    #     "<response><browser-command>Whos your favorite browser?</browser-command><args>Bar browser</args></response>",
    #      "<response><browser-command>Whos your favorite browser?</browser-command><args>Bar browser</args></response>"
    # ) )
    # print( xml_ftp_generator.contains_correct_response_values(
    #     "```xml\n<response><browser-command>Whos your favorite browser?</browser-command><args>Bar browser</args></response>```",
    #      "<response><browser-command>Whos your favorite browser?</browser-command><args>Bar browser</args></response>"
    # ) )