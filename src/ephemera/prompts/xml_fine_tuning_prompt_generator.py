import os
import re
import random

import pandas as pd
import json
import openai

from xmlschema                import XMLSchema
from sklearn.model_selection  import train_test_split

import lib.utils.util          as du
import lib.utils.util_xml      as dux
import lib.app.util_llm_client as du_llm_client

from huggingface_hub          import InferenceClient

# from lib.agents.function_mapping_search import FunctionMappingSearch
from lib.app.configuration_manager      import ConfigurationManager
from lib.utils.util_stopwatch           import Stopwatch
from lib.agents.llm                     import Llm

class XmlFineTuningPromptGenerator:
    
    def __init__( self, path_prefix=du.get_project_root(), tgi_url="http://172.17.0.5:3000", debug=False, verbose=False, silent=False, init_prompt_templates=True ):
        
        self.debug              = debug
        self.verbose            = verbose
        self.silent             = silent
        
        self.path_prefix        = path_prefix
        self.tgi_url            = tgi_url
        
        self.config_mgr         = ConfigurationManager( env_var_name="GIB_CONFIG_MGR_CLI_ARGS" )
        
        # ¡OJO! This is a giant KLUDGE
        # TODO: re-factor this!
        if init_prompt_templates:
            
            # For inserting hemming and hawing into the prompts
            self.interjections                   = self.get_interjections()
            self.salutations                     = self.get_salutations()
            
            # Build up lists of browser command categories
            self.vox_cmd_compound_commands       = self._get_compound_vox_commands()
            self.vox_cmd_simple_commands         = self._get_simple_vox_commands()
            self.vox_cmd_commands                = self._compile_vox_cmd_commands()
            
            # These are set by self._init_common_templates()
            self.common_input_template           = None
            self.common_human_says_template      = None
            self.common_response_format          = None
            self.common_output_template          = None
            # self.router_output_template        = None
            self._init_common_templates()
            
            # These two are set by the call to self._init_vox_cmd_templates()
            self.vox_cmd_instruction_template_gpt = None
            self.vox_cmd_instruction_template     = None
            self._init_vox_cmd_templates()
            
            # Build up lists of agent routing command categories
            self.agent_function_mapping_compound_commands = self._get_compound_agent_function_mapping_commands()
            self.agent_router_compound_commands           = self._get_compound_agent_router_commands()
            self.agent_router_simple_commands             = self._get_simple_agent_router_commands()
            self.agent_router_commands                    = self._compile_agent_router_commands()
            
            # These two are set by the call to self._init_agent_router_templates()
            self.agent_router_instruction_template_gpt = None
            self.agent_router_instruction_template     = None
            self._init_agent_router_templates()
            
            # These hold intermediate results
            self.compound_vox_cmd_qna_df       = pd.DataFrame()
            self.simple_vox_cmd_qna_df         = pd.DataFrame()
            self.compound_agent_router_qna_df  = pd.DataFrame()
            self.simple_agent_router_qna_df    = pd.DataFrame()
            # This holds the final results
            self.all_qna_df                    = pd.DataFrame()
            
            self._call_counter        = 0
            self._xml_schema          = self._get_xml_schema()
    
    def _get_compound_vox_commands( self ):
        
        compound_commands = {
            # "go to current tab"                : "/src/ephemera/prompts/data/synthetic-data-load-url-current-tab.txt",
            # "go to new tab"                    : "/src/ephemera/prompts/data/synthetic-data-load-url-new-tab.txt",
            # "search current tab"               : "/src/ephemera/prompts/data/synthetic-data-search-in-current-tab.txt",
            # "search new tab"                   : "/src/ephemera/prompts/data/synthetic-data-search-in-new-tab.txt",
            # "search google current tab"        : "/src/ephemera/prompts/data/synthetic-data-search-google-in-current-tab.txt",
            # "search google new tab"            : "/src/ephemera/prompts/data/synthetic-data-search-google-in-new-tab.txt",
            # "search google scholar current tab": "/src/ephemera/prompts/data/synthetic-data-search-google-scholar-in-current-tab.txt",
            # "search google scholar new tab"    : "/src/ephemera/prompts/data/synthetic-data-search-google-scholar-in-new-tab.txt",
            # "search kagi new tab"              : "/src/ephemera/prompts/data/synthetic-data-search-kagi-in-new-tab.txt",
            # "search kagi current tab"          : "/src/ephemera/prompts/data/synthetic-data-search-kagi-in-current-tab.txt",
            # "search perplexity current tab"    : "/src/ephemera/prompts/data/synthetic-data-search-perplexity-in-current-tab.txt",
            # "search perplexity new tab"        : "/src/ephemera/prompts/data/synthetic-data-search-perplexity-in-new-tab.txt",
            # "search phind current tab"         : "/src/ephemera/prompts/data/synthetic-data-search-phind-in-current-tab.txt",
            # "search phind new tab"             : "/src/ephemera/prompts/data/synthetic-data-search-phind-in-new-tab.txt",
        }
        self._test_command_paths( compound_commands )
        
        return compound_commands
    
    def _get_compound_agent_router_commands( self ):
        
        agent_routing_compound_commands = {
            # "agent router go to date and time"   : "/src/ephemera/prompts/data/synthetic-data-agent-routing-date-and-time.txt",
            # "agent router go to weather"         : "/src/ephemera/prompts/data/synthetic-data-agent-routing-weather.txt",
            # "agent router go to calendar"        : "/src/ephemera/prompts/data/synthetic-data-agent-routing-calendaring.txt",
            # "agent router go to receptionist"    : "/src/ephemera/prompts/data/synthetic-data-agent-routing-receptionist.txt",
        }
        self._test_command_paths( agent_routing_compound_commands )
        
        return agent_routing_compound_commands
    
    def _get_compound_agent_function_mapping_commands( self ):
        
        agent_function_mapping_compound_commands = {
            # This data set is not only static vs. dynamic, but also memory search vs. web search
            # ¡OJO! Using 'agent router go to function mapping' may not be the best key name: ¡rethink this!
            "agent router go to search function mapping": self.config_mgr.get( "path_to_search_function_mapping_data_wo_root" )
        }
        self._test_command_paths( agent_function_mapping_compound_commands )
        
        return agent_function_mapping_compound_commands
    
    def _get_simple_vox_commands( self ):
        
        simple_commands = {
            # "search using clipboard current tab"               : "/src/ephemera/prompts/data/synthetic-data-search-clipboard-in-current-tab.txt",
            # "search using clipboard new tab"                   : "/src/ephemera/prompts/data/synthetic-data-search-clipboard-in-new-tab.txt",
            # "search google using clipboard current tab"        : "/src/ephemera/prompts/data/synthetic-data-search-clipboard-google-in-current-tab.txt",
            # "search google using clipboard new tab"            : "/src/ephemera/prompts/data/synthetic-data-search-clipboard-google-in-new-tab.txt",
            # "search google scholar using clipboard current tab": "/src/ephemera/prompts/data/synthetic-data-search-clipboard-google-scholar-in-current-tab.txt",
            # "search google scholar using clipboard new tab"    : "/src/ephemera/prompts/data/synthetic-data-search-clipboard-google-scholar-in-new-tab.txt",
            # "search kagi using clipboard current tab"          : "/src/ephemera/prompts/data/synthetic-data-search-clipboard-kagi-in-current-tab.txt",
            # "search kagi using clipboard new tab"              : "/src/ephemera/prompts/data/synthetic-data-search-clipboard-kagi-in-new-tab.txt",
            # "search perplexity using clipboard current tab"    : "/src/ephemera/prompts/data/synthetic-data-search-clipboard-perplexity-in-current-tab.txt",
            # "search perplexity using clipboard new tab"        : "/src/ephemera/prompts/data/synthetic-data-search-clipboard-perplexity-in-new-tab.txt",
            # "search phind using clipboard current tab"         : "/src/ephemera/prompts/data/synthetic-data-search-clipboard-phind-in-current-tab.txt",
            # "search phind using clipboard new tab"             : "/src/ephemera/prompts/data/synthetic-data-search-clipboard-phind-in-new-tab.txt",
            # "none"                                             : "/src/ephemera/prompts/data/synthetic-data-none-of-the-above.txt",
        }
        self._test_command_paths( simple_commands )
        
        return simple_commands
    
    def _get_simple_agent_router_commands( self ):
        
        simple_commands = {
            "agent router go to todo list": "/src/ephemera/prompts/data/synthetic-data-agent-routing-todo-lists.txt",
            "none": "/src/ephemera/prompts/data/synthetic-data-none-of-the-above.txt",
        }
        self._test_command_paths( simple_commands )
        
        return simple_commands
    
    def _test_command_paths( self, commands ):
        
        for command in commands.keys():
            path_exists = os.path.exists( self.path_prefix + commands[ command ] )
            if not self.silent: print( f"Commands file for command [{command}] exists: {path_exists}" )
            if not path_exists:
                raise Exception( f"Commands file for command [{command}] [{self.path_prefix + commands[ command ]}] doesn't exist!" )
        print()
        
    def _compile_vox_cmd_commands( self ):
    
        compound_categories = "".join( [ "        <command>" + command + "</command>\n" for command in self.vox_cmd_compound_commands.keys() ] )
        simple_categories   = "".join( [ "        <command>" + command + "</command>\n" for command in self.vox_cmd_simple_commands.keys() ] )
        
        return ( compound_categories + simple_categories ).strip()
    
    def _compile_agent_router_commands( self ):
    
        compound_categories = "".join( [ "        <command>" + command + "</command>\n" for command in self.agent_router_compound_commands.keys() ] )
        simple_categories   = "".join( [ "        <command>" + command + "</command>\n" for command in self.agent_router_simple_commands.keys() ] )
        
        return ( compound_categories + simple_categories ).strip()
    
    # TODO: These two methods can be re-factored!
    def _get_search_terms( self, requested_length=100 ):
        
        return self._get_placeholder_values( "/src/ephemera/prompts/data/placeholders-search-terms.txt", requested_length=requested_length )
    
    # Get a list of placeholders for cities and countries
    def _get_cities_and_countries( self, requested_length=100 ):
       
        return self._get_placeholder_values( "/src/ephemera/prompts/data/placeholders-cities-and-countries.txt", requested_length=requested_length )
       
    # Get a list of placeholders for The receptionist agent
    def _get_receptionist_titles( self, requested_length=10 ):
        
        return self._get_placeholder_values( "/src/ephemera/prompts/data/placeholders-receptionist-titles.txt", requested_length=requested_length )
    
    def get_interjections( self, requested_length=None ):
        
        return self._get_placeholder_values( "/src/ephemera/prompts/data/placeholders-interjections-um-er-uh-etc.txt", requested_length=requested_length )
    
    def get_salutations( self, requested_length=500 ):
        """
        Get randomized salutations with randomized COMPUTER_NAME placeholder values.
        
        NOTE: Current empty to non-empty string ratios are 1:3. This means that ~1/3 of the salutations will be a zero len string and that ~1/3 of the non-empty salutations will have no name inserted into them.

        Parameters:
            requested_length (int): The length of salutations requested.

        Returns:
            list: A list of salutations with customized placeholder values.
        """
        names       = self._get_placeholder_values( "/src/ephemera/prompts/data/placeholders-receptionist-names.txt", requested_length=None )
        salutations = self._get_placeholder_values( "/src/ephemera/prompts/data/placeholders-receptionist-salutations.txt", requested_length=requested_length )
        
        for idx, salutation in enumerate( salutations ):
            name = random.choice( names )
            # If we don't have any names, return the salutation sans the placeholder
            if name == "":
                salutations[ idx ] = salutation.replace( " COMPUTER_NAME", "" )
            else:
                salutations[ idx ] = salutation.replace( "COMPUTER_NAME", name )
        
        return salutations
    
    def insert_interjection( self, text, interjections ):
        """
        Inserts a random interjection into the provided text at a random position.

        Parameters:
            text (str): The text to insert an interjection into.
            interjections (list): A list of interjections to choose from.

        Returns:
            tuple: A tuple containing the inserted interjection and the modified text.
        """
        interjection = random.choice( interjections )
        
        # If we don't have any interjections, return the text as is
        if interjection == "": return "", text
        
        # Split on spaces and insert randomly
        words = text.split()
        index = random.randint( 0, len( words ) )
        # Capitalize the first word, otherwise lowercase it
        if index == 0:
            words.insert( index, interjection.capitalize() )
        else:
            words.insert( index, interjection.lower() )
            
        return interjection, " ".join( words )
    
    def prepend_salutation( self, text, salutations ):
        """
        Prepends a random salutation to the given text.

        Parameters:
            text (str): The text to prepend the salutation to.
            salutations (list): List of salutations to choose from.

        Returns:
            tuple: If the chosen salutation is empty, returns a tuple with an empty string and the original text.
                   Otherwise, returns a tuple with the chosen salutation and the text with salutation prepended.
        """
        salutation = random.choice( salutations )
        
        # If we don't have any salutation to prepend, return the text as is
        if salutation == "":
            return "", text
        else:
            # Lowercase the first word of the text
            return salutation, salutation + " " + text[ 0 ].lower() + text[ 1: ]
        
    def _get_events_values( self, requested_length=100 ):
        
        events      = self._get_placeholder_values( "/src/ephemera/prompts/data/placeholders-calendaring-events.txt", requested_length=None )
        locations   = self._get_placeholder_values( "/src/ephemera/prompts/data/placeholders-calendaring-locations.txt", requested_length=None )
        start_times = self._get_placeholder_values( "/src/ephemera/prompts/data/placeholders-calendaring-dates-and-times.txt", requested_length=None )
        people      = self._get_placeholder_values( "/src/ephemera/prompts/data/placeholders-calendaring-people.txt", requested_length=None )
        
        events_values = []
        
        for i in range( requested_length ):
            events_values.append( {
                "EVENT_TYPE": random.choice( events ),
                "LOCATION"  : random.choice( locations ),
                "START_TIME": random.choice( start_times ),
                "PEOPLE"    : random.choice( people ),
                "PLACE"     : ""
            } )
        return events_values
    
    def _get_placeholder_values( self, placeholder_file, requested_length=None ):
        
        # A requested_length of None used as the second value in a list slice returns the entire list
        placeholders = du.get_file_as_list(
            self.path_prefix + placeholder_file, lower_case=False, clean=True, randomize=True
        )[ :requested_length ]
        
        # If we don't have enough search terms, append copies of the search term list until we do
        while requested_length is not None and requested_length > len( placeholders ):
            # advise that we're inserting duplicate search terms into the search term list
            print( f"Inserting DUPLICATE placeholders into the list. Requested length [{requested_length}] > list length [{len( placeholders )}]" )
            placeholders += placeholders
            
        # Truncate the search terms list to equal the requested len
        placeholders = placeholders[ :requested_length ]
        
        return placeholders
    
    def _get_goto_urls( self, requested_length ):
        
        return du.generate_domain_names( requested_length )

    def _init_common_templates( self ):
        
        self.common_input_template = """
        Below is the raw human voice command transcription formatted using simple XML:
        {human_says}

        The standardized command that you translate MUST be returned wrapped in simple, well-formed XML:
        {response_format}"""
        
        self.common_human_says_template = """
        <human>
            <voice-command>{voice_command}</voice-command>
        </human>"""
        
        self.common_response_format = """
        <response>
            <command></command>
            <args></args>
        </response>"""
        
        self.common_output_template = """
        <response>
            <command>{command}</command>
            <args>{args}</args>
        </response>"""
        
        # self.router_output_template = """
        # <response>
        #     <command>{command}</command>
        #     <salutation>{salutation}</salutation>
        #     <args>{args}</args>
        # </response>"""
    
    def _init_vox_cmd_templates( self ):
        
        self.vox_cmd_instruction_template_gpt = """INSTRUCTIONS:
        Your job is to discern the intent of a human voice command transcription and translate it into a standardized command that a browser on your computer would understand.

        You will be given a human voice command as INPUT as well as a list of possible standardized commands. You must choose the correct standardized command from the following list:
        
        <browser-commands>
            {command_choices}
        </browser-commands>
        
        RESPONSE FORMAT: MUST be returned wrapped in simple, well-formed XML
        <response>
            <command></command>
            <args></args>
        </response>
        """
        
        self.vox_cmd_instruction_template = """Your job is to discern the intent of a human voice command transcription and translate it into a standardized command that a browser on your computer would understand.

        You will be given a human voice command and a list of possible standardized commands. You must choose the correct standardized command from the following list:
        <browser-commands>
        {command_choices}
        </browser-commands>

        Requirement: You MUST NOT use python code to answer this question.
        Requirement: You MUST use your linguistic knowledge and intuition to answer this question.
        Requirement: The first word of your response MUST be `<response>`
        Hint: Anything that isn't a part of the command itself should be treated as arguments related to the command."""
        
        # self.command_input_template = """
        # Below is the raw human voice command transcription formatted using simple XML:
        # {human_says}
        #
        # The standardized command that you translate MUST be returned wrapped in simple, well-formed XML:
        # {response_format}"""
        #
        # self.common_human_says_template = """
        # <human>
        #     <voice-command>{voice_command}</voice-command>
        # </human>"""
        #
        # self.common_response_format = """
        # <response>
        #     <command></command>
        #     <args></args>
        # </response>"""
        #
        # self.common_output_template = """
        # <response>
        #     <command>{command}</command>
        #     <args>{args}</args>
        # </response>"""
        
        return
    
    def _init_agent_router_templates( self ):
        
        self.agent_router_instruction_template_gpt = """INSTRUCTIONS:
        Your job is to discern the intent of a human voice command transcription and translate it into a standardized agent routing command that another LLM would understand.

        You will be given a human voice command as INPUT as well as a list of possible standardized commands. You must choose the correct standardized command from the following list:

        <agent-routing-commands>
            {command_choices}
        </agent-routing-commands>

        RESPONSE FORMAT: MUST be returned wrapped in simple, well-formed XML
        <response>
            <command></command>
            <args></args>
        </response>
        """
        
        self.agent_router_instruction_template = """Your job is to discern the intent of a human voice command transcription and translate it into a standardized agent routing command that another LLM would understand.

        You will be given a human voice command as INPUT as well as a list of possible standardized commands. You must choose the correct standardized command from the following list:
        <agent-routing-commands>
            {command_choices}
        </agent-routing-commands>

        Requirement: You MUST NOT use python code to answer this question.
        Requirement: You MUST use your linguistic knowledge and intuition to answer this question.
        Requirement: The first word of your response MUST be `<response>`
        Hint: Anything that isn't a part of the command itself should be treated as arguments related to the command."""
        
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
    
    def build_compound_vox_cmd_training_prompts( self, sample_size_per_command=2000 ):
        
        instructions, inputs, outputs, prompts, gpt_messages, commands = self._get_6_empty_lists()
        
        gpt_instruction = self.vox_cmd_instruction_template_gpt.format( command_choices=self.vox_cmd_commands )
        
        # For each browser command, load the corresponding file and generate prompts
        for compound_command in self.vox_cmd_compound_commands.keys():
            
            du.print_banner( f"Building prompts for compound VOX command [{compound_command}]", prepend_nl=True, end="\n" )
            counter = 1
            # First 100 lines are properly spelled
            raw_lines = du.get_file_as_list( self.path_prefix + self.vox_cmd_compound_commands[ compound_command ], clean=True )[ 0:100 ]
            
            # Determine which kind of compound synthetically created lines we need to build prompts for
            if compound_command.startswith( "search " ):
                arguments   = self._get_search_terms( len( raw_lines ) )
                placeholder = "SEARCH_TERMS"
            elif compound_command.startswith( "go to " ):
                arguments   = self._get_goto_urls( len( raw_lines ) )
                placeholder = "DOMAIN_NAME"
            else:
                raise Exception( f"Unknown voice command [{compound_command}]" )
            
            for raw_line in raw_lines:
                
                for args in arguments:
                    
                    voice_command = raw_line.replace( placeholder, args )
                    
                    instruction = self.vox_cmd_instruction_template.format( command_choices=self.vox_cmd_commands )
                    human_says  = self.common_human_says_template.format( voice_command=voice_command )
                    input       = self.common_input_template.format( human_says=human_says, response_format=self.common_response_format )
                    output      = self.common_output_template.format( command=compound_command, args=args )
                    prompt      = self._get_prompt_instruction_format( instruction, input )
                    
                    instructions.append( instruction )
                    inputs.append( input )
                    outputs.append( output )
                    prompts.append( prompt )
                    commands.append( compound_command )
                    
                    gpt_messages.append( self._get_gpt_messages_dict( gpt_instruction, voice_command, compound_command, args ) )
                    
                    self._do_conditional_print( counter, voice_command )
                    counter += 1
            
            print()
        
        compound_qna_df = pd.DataFrame( { "command": commands, "instruction": instructions, "input": inputs, "output": outputs, "prompt": prompts, "gpt_message": gpt_messages } )
        compound_qna_df = self._prune_duplicates_and_sample( compound_qna_df, sample_size=( sample_size_per_command * len( self.vox_cmd_compound_commands ) ), sample_size_per_command=sample_size_per_command )
        
        self.compound_vox_cmd_qna_df = compound_qna_df
        
        return self.compound_vox_cmd_qna_df
    
    def _get_6_empty_lists( self ):
        
        return [], [], [], [], [], []
    
    def _get_gpt_messages_dict( self, gpt_instruction, voice_command, compound_command, args ):
        
        return {
            "messages": [
                { "role": "system", "content": gpt_instruction },
                { "role": "user", "content": voice_command },
                { "role": "assistant", "content": self.common_output_template.format( command=compound_command, args=args ) }
            ]
        }
    
    def _do_conditional_print( self, counter, voice_command, interval=10 ):
        
        if counter % interval == 0:
            if self.debug:
                print( voice_command )
            else:
                print( ".", end="" )
                if counter % ( interval * 100 ) == 0:
                    print()
                
    def build_compound_agent_router_training_prompts( self, sample_size_per_command=2000 ):
        
        instructions, inputs, outputs, prompts, gpt_messages, commands = self._get_6_empty_lists()
    
        gpt_instruction = self.agent_router_instruction_template_gpt.format( command_choices=self.agent_router_commands )
        
        # For each browser command, load the corresponding file and generate prompts
        for compound_command in self.agent_router_compound_commands.keys():
            
            du.print_banner( f"Building prompts for compound AGENT ROUTER command [{compound_command}]", prepend_nl=True, end="\n" )
            counter = 1
            
            raw_lines = du.get_file_as_list( self.path_prefix + self.agent_router_compound_commands[ compound_command ], clean=True, randomize=True )[ 0:100 ]
            
            if compound_command in [ "agent router go to weather", "agent router go to date and time" ]:
                arguments   = self._get_cities_and_countries( len( raw_lines ) )
                placeholder = "GEOGRAPHIC_LOCATION"
            elif compound_command == "agent router go to receptionist":
                arguments   = self._get_receptionist_titles( len( raw_lines ) )
                placeholder = "RECEPTIONIST_TITLE"
            elif compound_command == "agent router go to calendar":
                arguments   = self._get_events_values( len( raw_lines ) )
                placeholder = ""
            else:
                raise Exception( f"Unknown voice command [{compound_command}]" )
            
            for raw_line in raw_lines:
                    
                for args in arguments:
                    
                    if compound_command == "agent router go to calendar":
                        voice_command = raw_line.replace( "PLACE", "" )
                        for key in args.keys():
                            voice_command = voice_command.replace( key, args[ key ] )
                        # Reset args to an empty string, NOT a dictionary
                        args = ""
                    else:
                        voice_command = raw_line.replace( placeholder, args )
                        
                    _, voice_command = self.insert_interjection( voice_command, self.interjections )
                    _, voice_command = self.prepend_salutation( voice_command, self.salutations )
                    
                    instruction   = self.agent_router_instruction_template.format( command_choices=self.agent_router_commands )
                    human_says    = self.common_human_says_template.format( voice_command=voice_command )
                    input         = self.common_input_template.format( human_says=human_says, response_format=self.common_response_format )
                    output        = self.common_output_template.format( command=compound_command, args=args )
                    prompt        = self._get_prompt_instruction_format( instruction, input )
                    
                    instructions.append( instruction )
                    inputs.append( input )
                    outputs.append( output )
                    prompts.append( prompt )
                    commands.append( compound_command )
                    
                    gpt_messages.append( self._get_gpt_messages_dict( gpt_instruction, voice_command, compound_command, args ) )
                    
                    self._do_conditional_print( counter, voice_command )
                    counter += 1
            
            print()
        
        compound_agent_router_qna_df = pd.DataFrame( { "command": commands, "instruction": instructions, "input": inputs, "output": outputs, "prompt": prompts, "gpt_message": gpt_messages } )
        compound_agent_router_qna_df = self._prune_duplicates_and_sample( compound_agent_router_qna_df, sample_size=( sample_size_per_command * len( self.vox_cmd_compound_commands ) ), sample_size_per_command=sample_size_per_command )
        
        self.compound_agent_router_qna_df = compound_agent_router_qna_df
        
        return self.compound_agent_router_qna_df
    
    def build_compound_function_mapping_training_prompts( self, sample_size_per_command=2000, analyze_bigrams=False, max_questions=2 ):
        
        instructions, inputs, outputs, prompts, gpt_messages, commands = self._get_6_empty_lists()
    
        gpt_instruction = self.agent_router_instruction_template_gpt.format( command_choices=self.agent_router_commands )
        
        # For each function mapping entry, load the corresponding file and generate prompts
        for routing_key in self.agent_function_mapping_compound_commands.keys():
            
            du.print_banner( f"Building prompts for compound FUNCTION MAPPING [{routing_key}]", prepend_nl=True, end="\n" )
            
            path     = self.path_prefix + self.agent_function_mapping_compound_commands[ routing_key ]
            boundary = "<!-- QnR Boundary -->"
            if path.endswith( ".txt" ):
                
                print( f"Loading RAW question data from [{path}]..." )
                raw_lines = du.get_file_as_list( path, clean=True, randomize=True )
                if analyze_bigrams: self._analyze_bigrams( raw_lines, "DEFAULT_LOCATION" )
                
                locations = self._get_cities_and_countries( requested_length=None )
                placeholders_and_values = { "DEFAULT_LOCATION": locations }
                
                questions = self._build_function_mapping_questions( raw_lines, placeholders_and_values )
                responses = self._generate_function_mapping_response_objects( questions, max_questions=max_questions )
                count     = len( responses )
                counter   = 0
                
                
                # Write the responses to an XML file of the same name
                output_path = path.replace( ".txt", ".xml" )
                with open( output_path, "w", encoding="utf-8" ) as f:
                    
                    f.write( "<qnrs>\n" )
                    for response in responses:
                        if self.debug and self.verbose:
                            print( f"Writing '{response[ 'last_question_asked' ]}'..." )
                        elif self.debug:
                            print( ".", end="" )
                        f.write( "<qnr>\n" )
                        f.write( "<question>" + response[ "last_question_asked" ] + "</question>\n" )
                        f.write( response[ "xml_response" ] + "\n" )
                        f.write( "</qnr>\n" )
                        counter += 1
                        # Don't write a boundary after the last question
                        if counter < count: f.write( f"{boundary}\n" )
                    f.write( "</qnrs>\n" )
                
                if self.debug and not self.verbose: print()
                print( f"Saved {counter} QnRs to [{output_path}]" )
                
            elif path.endswith( ".xml" ):
                
                msg = f"Loading XML QnR data from [{path}]..."
                print( msg )
                xml_data = du.get_file_as_string( path )
                qnrs     = xml_data.split( boundary )
                msg      = f"{msg} Done! Loaded {len( qnrs )} QnR pairs."
                print( msg )
                
            else:
                
                extension = path.split( "." )[ -1 ]
                raise Exception( f"Unknown function mapping file type [*.{extension}] for routing_key [{routing_key}]" )

        #     for raw_line in raw_lines:
        #
        #         for args in arguments:
        #
        #             if routing_key == "agent router go to calendar":
        #                 voice_command = raw_line.replace( "PLACE", "" )
        #                 for key in args.keys():
        #                     voice_command = voice_command.replace( key, args[ key ] )
        #                 # Reset args to an empty string, NOT a dictionary
        #                 args = ""
        #             else:
        #                 voice_command = raw_line.replace( placeholder, args )
        #
        #             _, voice_command = self.insert_interjection( voice_command, self.interjections )
        #             _, voice_command = self.prepend_salutation( voice_command, self.salutations )
        #
        #             instruction   = self.agent_router_instruction_template.format( command_choices=self.agent_router_commands )
        #             human_says    = self.common_human_says_template.format( voice_command=voice_command )
        #             input         = self.common_input_template.format( human_says=human_says, response_format=self.common_response_format )
        #             output        = self.common_output_template.format( command=routing_key, args=args )
        #             prompt        = self._get_prompt_instruction_format( instruction, input )
        #
        #             instructions.append( instruction )
        #             inputs.append( input )
        #             outputs.append( output )
        #             prompts.append( prompt )
        #             commands.append( routing_key )
        #
        #             gpt_messages.append( self._get_gpt_messages_dict( gpt_instruction, voice_command, routing_key, args ) )
        #
        #             self._do_conditional_print( counter, voice_command )
        #             counter += 1
        #
        #     print()
        #
        # compound_agent_router_qna_df = pd.DataFrame( { "command": commands, "instruction": instructions, "input": inputs, "output": outputs, "prompt": prompts, "gpt_message": gpt_messages } )
        # compound_agent_router_qna_df = self._prune_duplicates_and_sample( compound_agent_router_qna_df, sample_size=( sample_size_per_command * len( self.vox_cmd_compound_commands ) ), sample_size_per_command=sample_size_per_command )
        #
        # self.compound_agent_router_qna_df = compound_agent_router_qna_df
        #
        # return self.compound_agent_router_qna_df
        return None
    
    def _generate_function_mapping_response_objects( self, questions, max_questions=None ):
        
        # If max_questions is None, the slice will be all the questions
        questions = questions[ 0:max_questions ]
        responses = [ ]
        counter   = 0
        
        timer = Stopwatch( msg=f"Generating function mapping for {len( questions )} questions..." )
        for question in questions:
            
            counter += 1
            from lib.agents.function_mapping_search import FunctionMappingSearch
            mapper = FunctionMappingSearch(  question=question, last_question_asked=question, debug=self.debug, verbose=self.verbose )
            du.print_banner( f"Question {counter} of {len( questions )}: {question}", end="\n", prepend_nl=True )
            prompt_response_dict = mapper.run_prompt( include_raw_response=True )
            
            responses.append( prompt_response_dict )
            
            # Print out some ~progress stats
            delta_ms            = timer.get_delta_ms()
            time_elapsed        = int( delta_ms / 1000 )
            ms_per_question     = int( round( delta_ms / counter, 0 ) )
            time_per_question   = int( ms_per_question / 1000 )
            questions_remaining = len( questions ) - counter
            seconds_remaining   = int( ms_per_question * questions_remaining / 1000 )
            
            print( f"Time elapsed {time_elapsed:,} seconds. Average time per question: {time_per_question:,} seconds. {questions_remaining} questions remaining, ETA: {seconds_remaining:,} seconds...", end="\n\n" )
        
        timer.print( msg="Done!", use_millis=False )
        print( f"Average time per question: {round( timer.get_delta_ms() / len( questions ), 0 ):,} ms" )
        
        return responses
        
    def _build_function_mapping_questions( self, raw_lines, placeholders_and_values ):
        
        du.print_banner( "Building function mapping questions...", prepend_nl=True)
        lines   = [ ]
        for line in raw_lines:
            
            # Iterate over placeholders and substitute random values for them
            for placeholder, values in placeholders_and_values.items():
                line = line.replace( placeholder, random.choice( values ) )
            
            # Insert interjections and salutations
            _, line = self.insert_interjection( line, self.interjections )
            _, line = self.prepend_salutation( line, self.salutations )
            lines.append( line )
            if self.debug:print( line )
        
        return lines
    
    def _analyze_bigrams( self, raw_lines, placeholder ):
        
        du.print_banner( f"Analyzing bigrams for placeholder [{placeholder}]...", prepend_nl=True )
        
        # Do a quick and dirty search and summary for DEFAULT_LOCATION
        bigrams = [ ]
        
        for line in raw_lines:
            
            found = False
            words = line.split( " " )
            
            for idx, word in enumerate( words ):
                if placeholder in word and idx >= 1:
                    bigrams.append( words[ idx - 1 ] + " " + words[ idx ] )
                    found = True
                    break
                    
            if not found:
                bigrams.append( f"No placeholder '{placeholder}' provided" )
                
        # Count the bigrams
        from collections import Counter
        bigram_counter = Counter( bigrams )
        # Print out the most common bigrams sorted descending
        for bigram, count in bigram_counter.most_common():
            print( f"{bigram}: {count}" )
        
    def get_prompt_template( self, name ):
        
        if name == "vox command":
                instruction = self.vox_cmd_instruction_template.format( command_choices=self.vox_cmd_commands )
        elif name == "agent router":
                instruction = self.agent_router_instruction_template.format( command_choices=self.agent_router_commands )
        else:
            raise ValueError( f"Unknown prompt template name [{name}] Please use one of ['vox command', 'agent router']" )
        
        human_says  = self.common_human_says_template.format( voice_command="{voice_command}" )
        input       = self.common_input_template.format( human_says=human_says, response_format=self.common_response_format )
        prompt      = self._get_prompt_instruction_format( instruction, input )
        
        reformatted_prompt = [ ]
        
        # Splitting on '\n will consume some of the lines
        for line in prompt.split( "\n" ):
            
            # Remove the first 8 and then 4 leading space characters if they exist
            if line.startswith( "        " ):
                line = line[ 8: ]
            elif line.startswith( "    " ):
                line = line[ 4: ]
            
            # Adhoc insertion of space before command items
            if line.startswith( "<command>" ):
                line = "    " + line
                
            reformatted_prompt.append( line )

        prompt = "\n".join( reformatted_prompt )
        
        return prompt
    
    def serialize_prompt( self, prompt, prompt_path ):
        
        path = self.path_prefix + prompt_path
        
        du.print_banner( f"Serializing prompt to [{path}]", prepend_nl=True )
        du.write_string_to_file( path, prompt )
        
    def serialize_prompts( self, prompt_path_prefix ):
        
        self.serialize_prompt( self.get_prompt_template( "vox command" ),  prompt_path_prefix + "vox-command-template.txt" )
        self.serialize_prompt( self.get_prompt_template( "agent router" ), prompt_path_prefix + "agent-router-template.txt" )
        
    def build_simple_vox_cmd_training_prompts( self, sample_size_per_command=400 ):
        
        instructions, inputs, outputs, prompts, gpt_messages, commands = self._get_6_empty_lists()
        
        gpt_instruction = self.vox_cmd_instruction_template_gpt.format( command_choices=self.vox_cmd_commands )
        
        for simple_command in self.vox_cmd_simple_commands.keys():
            
            du.print_banner( f"Building prompts for simple VOX command [{simple_command}]", prepend_nl=True, end="\n" )
            counter = 1
            
            raw_lines = du.get_file_as_list( self.path_prefix + self.vox_cmd_simple_commands[ simple_command ], clean=True )
            
            for raw_line in raw_lines:
                
                instruction = self.vox_cmd_instruction_template.format( command_choices=self.vox_cmd_commands )
                human_says  = self.common_human_says_template.format( voice_command=raw_line )
                input       = self.common_input_template.format( human_says=human_says, response_format=self.common_response_format )
                output      = self.common_output_template.format( command=simple_command, args="" )
                prompt      = self._get_prompt_instruction_format( instruction, input )
                
                instructions.append( instruction )
                inputs.append( input )
                outputs.append( output )
                prompts.append( prompt )
                commands.append( simple_command )
                
                gpt_messages.append( self._get_gpt_messages_dict( gpt_instruction, raw_line, simple_command, "" ) )
                
                self._do_conditional_print( counter, raw_line )
                counter += 1
            
        simple_command_qna_df = pd.DataFrame( { "command": commands, "instruction": instructions, "input": inputs, "output": outputs, "prompt": prompts, "gpt_message": gpt_messages } )
        simple_command_qna_df = self._prune_duplicates_and_sample( simple_command_qna_df, sample_size=( sample_size_per_command * len( self.vox_cmd_simple_commands ) ), sample_size_per_command=sample_size_per_command )
        
        self.simple_vox_cmd_qna_df = simple_command_qna_df
        
        return self.simple_vox_cmd_qna_df
    
    def build_simple_agent_router_training_prompts( self, sample_size_per_command=400 ):
        
        instructions, inputs, outputs, prompts, gpt_messages, commands = self._get_6_empty_lists()
        
        gpt_instruction = self.agent_router_instruction_template_gpt.format( command_choices=self.agent_router_commands )
        
        for simple_command in self.agent_router_simple_commands.keys():
            
            du.print_banner( f"Building prompts for simple AGENT ROUTER command [{simple_command}]", prepend_nl=True, end="\n" )
            counter = 1
            
            raw_lines = du.get_file_as_list( self.path_prefix + self.agent_router_simple_commands[ simple_command ], clean=True )
            
            for raw_line in raw_lines:
                
                _, raw_line = self.insert_interjection( raw_line, self.interjections )
                _, raw_line = self.prepend_salutation( raw_line, self.salutations )
                
                instruction = self.vox_cmd_instruction_template.format( command_choices=self.agent_router_commands )
                human_says  = self.common_human_says_template.format( voice_command=raw_line )
                input       = self.common_input_template.format( human_says=human_says, response_format=self.common_response_format )
                output      = self.common_output_template.format( command=simple_command, args="" )
                prompt      = self._get_prompt_instruction_format( instruction, input )
                
                instructions.append( instruction )
                inputs.append( input )
                outputs.append( output )
                prompts.append( prompt )
                commands.append( simple_command )
                
                gpt_messages.append( self._get_gpt_messages_dict( gpt_instruction, raw_line, simple_command, "" ) )
                
                self._do_conditional_print( counter, raw_line )
                counter += 1
            
        simple_agent_router_qna_df = pd.DataFrame( { "command": commands, "instruction": instructions, "input": inputs, "output": outputs, "prompt": prompts, "gpt_message": gpt_messages } )
        simple_agent_router_qna_df = self._prune_duplicates_and_sample( simple_agent_router_qna_df, sample_size=( sample_size_per_command * len( self.vox_cmd_simple_commands ) ), sample_size_per_command=sample_size_per_command )
        
        self.simple_agent_router_qna_df = simple_agent_router_qna_df
        
        return self.simple_agent_router_qna_df
    def build_all_training_prompts( self, sample_size_per_compound_command=2000, sample_size_per_simple_command=400 ):
        
        compound_vox_cmd_qna_df       = self.build_compound_vox_cmd_training_prompts( sample_size_per_command=sample_size_per_compound_command )
        simple_vox_cmd_qna_df         = self.build_simple_vox_cmd_training_prompts( sample_size_per_command=sample_size_per_simple_command )
        
        compound_router_qna_df        = self.build_compound_agent_router_training_prompts( sample_size_per_command=sample_size_per_compound_command )
        simple_router_qna_df          = self.build_simple_agent_router_training_prompts( sample_size_per_command=sample_size_per_simple_command )
        
        # Stack both dataframes vertically
        self.all_qna_df = pd.concat( [ compound_vox_cmd_qna_df, simple_vox_cmd_qna_df, compound_router_qna_df, simple_router_qna_df ], ignore_index=True )
        
        # Group by command and count the number of rows per command
        command_counts = self.all_qna_df.groupby( "command" ).count().reset_index()[ [ "command", "input" ] ]
        # sort by command ascending
        command_counts = command_counts.sort_values( "command", ascending=True )
        du.print_banner( f"Command counts for all {self.all_qna_df.shape[ 0 ]:,} training prompts", prepend_nl=True)
        print( command_counts )
        
        # Calculate Max, min, and mean prompt lengths
        self.all_qna_df[ "prompt_length" ] = self.all_qna_df[ "prompt" ].apply( lambda cell: len( cell ) )
        max_prompt_length  = self.all_qna_df[ "prompt_length" ].max()
        min_prompt_length  = self.all_qna_df[ "prompt_length" ].min()
        mean_prompt_length = self.all_qna_df[ "prompt_length" ].mean()
        
        # Delete the prompt_length column
        self.all_qna_df.drop( columns=[ "prompt_length" ], inplace=True )
        
        du.print_banner( f"Max, min, and mean prompt CHARACTER counts for all {self.all_qna_df.shape[ 0 ]:,} training prompts", prepend_nl=True)
        print( f"Max  prompt length [{max_prompt_length:,}] characters" )
        print( f"Min  prompt length [{min_prompt_length:,}] characters" )
        print( f"Mean prompt length [{round( mean_prompt_length, 1 ):,}] characters" )
        
        # Now calculate max min and mean word counts in the prompt column
        self.all_qna_df[ "prompt_word_count" ] = self.all_qna_df[ "prompt" ].apply( lambda cell: len( cell.split( " " ) ) )
        max_prompt_word_count  = self.all_qna_df[ "prompt_word_count" ].max()
        min_prompt_word_count  = self.all_qna_df[ "prompt_word_count" ].min()
        mean_prompt_word_count = self.all_qna_df[ "prompt_word_count" ].mean()
        
        # Delete the prompt_word_count column
        self.all_qna_df.drop( columns=[ "prompt_word_count" ], inplace=True )
        
        du.print_banner( f"Max, min, and mean prompt WORD counts for all {self.all_qna_df.shape[ 0 ]:,} training prompts", prepend_nl=True )
        print( f"Max  prompt length [{max_prompt_word_count:,}] words" )
        print( f"Min  prompt length [{min_prompt_word_count:,}] words" )
        print( f"Mean prompt length [{round( mean_prompt_word_count, 1 ):,}] words" )
        
        return self.all_qna_df
    
    def _prune_duplicates_and_sample( self, df, sample_size=1000, sample_size_per_command=-1 ):
        
        du.print_banner( "Pruning potential duplicates by 'input' values...", prepend_nl=True )
        
        rows_pre = df.shape[ 0 ]
        print( f" PRE {rows_pre:,} training inputs..." )
        df.drop_duplicates( subset=[ "input" ], inplace=True )
        rows_post  = df.shape[ 0 ]
        dupes_rows = rows_pre - rows_post
        dupes_pct  = dupes_rows / rows_pre * 100.0
        print( f"POST {rows_post:,} training inputs. Deleted {dupes_rows:,} rows = {dupes_pct:.1f}% duplicate questions" )
        
        if rows_post < sample_size:
            print( f"WARNING: Sample size [{sample_size:,}] > rows_post [{rows_post:,}]. Returning all [{rows_post:,}] rows.")
            return df
        else:
            # Sample the dataframe Using proportional distributions represented by the weights value
            du.print_banner( f"Sampling {sample_size:,} rows/command from the pruned dataframe using the following weights:", prepend_nl=True )
            weights = df[ "command" ].value_counts( normalize=True )
            print( weights )
            weights = df[ "command" ].value_counts( normalize=False )
            print( weights )
            
            # https://www.phind.com/search?cache=herzljuhqqc7qt9uuf84ng8v
            return df.groupby( "command" ).sample( sample_size_per_command, random_state=42 )
    
    def _get_xml_schema( self ):
        
        xsd_string = """
        <xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">
          <xs:element name="response">
            <xs:complexType>
              <xs:sequence>
                <xs:element name="command" type="xs:string"/>
                <xs:element name="args" type="xs:string"/>
              </xs:sequence>
            </xs:complexType>
          </xs:element>
        </xs:schema>
        """
        
        return XMLSchema( xsd_string )
    
    def is_valid_xml( self, xml_str ):
        
        try:
            return self._xml_schema.is_valid( xml_str )
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
        # response = re.sub( r'>\s+<', '><', response.strip() )
        response = dux.strip_all_white_space( response )
        
        # Remove white space outside XML tags
        # answer = re.sub( r'>\s+<', '><', answer.strip() )
        answer = dux.strip_all_white_space( answer )
        
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
    
    def tag_values_are_equal( self, response, answer, tag_name="command" ):
    
        command_response = dux.get_value_by_xml_tag_name( response, tag_name, default_value="broken" )
        command_answer   = dux.get_value_by_xml_tag_name(   answer, tag_name, default_value="broken" )
        
        return command_response != "broken" and command_answer != "broken" and command_response == command_answer
    
    def _query_llm_in_memory( self, tokenizer, model, prompt, max_new_tokens=1024, model_name="ACME LLMs, Inc.", device="cuda:0", silent=False ):
        
        # We need this exact method in other places too, so do the simplest extraction and reuse here
        response = du_llm_client.query_llm_in_memory( model, tokenizer, prompt, device=device, model_name=model_name, max_new_tokens=max_new_tokens, silent=silent )
        
        if self.debug:
            print( f"Response: [{response}]", end="\n\n" )
            
        return response

    def query_llm_tgi( self, prompt, model_name=Llm.PHIND_34B_v2, max_new_tokens=1024, temperature=0.25, top_k=10, top_p=0.9, silent=False ):
    
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
    
    def _query_llm_openai( self, messages, model_name="OpenAI/gpt-3.5-turbo-1106" ):
        
        openai.api_key = du.get_api_key( "openai", project_root=du.get_project_root() )
        
        timer    = Stopwatch( msg=f"Asking LLM [{model_name}]...".format( model_name ) )
        
        response = openai.chat.completions.create(
            # model=model_name.split( "/" )[ 1 ] if "/" in model_name else model_name,
            model=Llm.extract_model_name( model_name ),
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
    
    def get_response_to_prompt( self, prompt, rows, switch="tgi", model_name=Llm.PHIND_34B_v2, tokenizer=None, model=None, max_new_tokens=1024, temperature=0.25, top_k=10, top_p=0.9, device="cuda:0", silent=False  ):
        
        self._call_counter += 1
        
        print( f"Processing call [{self._call_counter:03d}] out of [{rows}] = [{round( self._call_counter / rows * 100.0, 1 )}%]... ")
        
        if switch == "tgi":
            return self.query_llm_tgi( prompt, model_name=model_name, max_new_tokens=max_new_tokens, temperature=temperature, top_k=top_k, top_p=top_p, silent=silent )
        elif switch == "openai":
            return self._query_llm_openai( prompt[ "messages" ], model_name=model_name )
        elif switch == "huggingface":
            return self._query_llm_in_memory( tokenizer, model, prompt, model_name=model_name, max_new_tokens=max_new_tokens, device=device, silent=silent )
        else:
            raise Exception( f"Unknown switch [{switch}]" )

    def generate_responses( self, df, tokenizer=None, model=None, switch="tgi", model_name=Llm.PHIND_34B_v2, max_new_tokens=1024, temperature=0.25, top_k=10, top_p=0.9, device="cuda:0", silent=False ):
        
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
        print( f"[{round( ms_per_item, 1 ):,}] ms per item" )
        
        return df
    def validate_responses( self, df ):
        
        # Validate the structure and content of the xml response
        df[ "response_xml_is_valid" ]       = df[ "response" ].apply( lambda cell: self.is_valid_xml( cell ) )
        df[ "contains_response" ]           = df[ "response" ].apply( lambda cell: self.contains_valid_xml_tag( cell, "response" ) )
        df[ "contains_command" ]            = df[ "response" ].apply( lambda cell: self.contains_valid_xml_tag( cell, "command" ) )
        df[ "contains_args" ]               = df[ "response" ].apply( lambda cell: self.contains_valid_xml_tag( cell, "args" ) )
        df[ "response_is_exact" ]           = df.apply( lambda row: self.is_response_exact_match( row[ "response" ], row[ "output" ] ), axis=1 )
        df[ "response_has_correct_values" ] = df.apply( lambda row: self.contains_correct_response_values( row[ "response" ], row[ "output" ] ), axis=1 )
        df[ "command_is_correct" ]          = df.apply( lambda row: self.tag_values_are_equal( row[ "response" ], row[ "output" ], tag_name="command" ), axis=1 )
        df[ "args_is_correct" ]             = df.apply( lambda row: self.tag_values_are_equal( row[ "response" ], row[ "output" ], tag_name="args" ), axis=1 )
        
        return df
    
    def print_validation_stats( self, df, title="Validation Stats" ):
        
        du.print_banner( title, prepend_nl=True )
        print( f"               Is valid xml {df.response_xml_is_valid.mean() * 100:.1f}%" )
        print( f"        Contains <response> {df.contains_response.mean() * 100:.1f}%" )
        print( f"         Contains <command> {df.contains_command.mean() * 100:.1f}%" )
        print( f"            Contains <args> {df.contains_args.mean() * 100:.1f}%" )
        print( f"          Response is exact {df.response_is_exact.mean() * 100:.1f}%" )
        print( f"Response has correct values {df.response_has_correct_values.mean() * 100:.1f}%" )
        print( f"         Command is correct {df.command_is_correct.mean() * 100:.1f}%" )
        print( f"            Args is correct {df.args_is_correct.mean() * 100:.1f}%" )
        
        # Calculate accuracy per command
        cols = [ "command", "response_is_exact" ]
        stats_df           = df[ cols ].copy()
        stats_df           = stats_df.groupby( "command" )[ "response_is_exact" ].agg( [ "mean", "sum", "count" ] ).reset_index()
        
        # Format the percentages
        stats_df[ "mean" ] = stats_df[ "mean" ].apply( lambda cell: f"{cell * 100:.2f}%" )
        # Sorts by mean ascending: Remember it's now a string we're sorting
        stats_df           = stats_df.sort_values( "mean", ascending=False )
        # Since I can't delete the index and not affect the other values, I'll just set the index to an empty string
        stats_df.index     = [ "" ] * stats_df.shape[ 0 ]

        du.print_banner( f"{title}: Accuracy per command", prepend_nl=True )
        print( stats_df )
        
        return stats_df
    
    def get_train_test_validate_split( self, df, sample_size=1000, test_size=0.2, test_validate_size=0.5, stratify="command" ):
        
        sampled_df = df[ [ "command", "instruction", "input", "output", "prompt", "gpt_message" ] ].sample( sample_size, random_state=42 ).copy()
        
        # Split the dataframe into train and (test+validate)
        train_df, test_validate_df = train_test_split( sampled_df, test_size=test_size, random_state=42, stratify=sampled_df[ stratify ] )
        
        # Then split (test+validate) into test and validate
        test_df, validate_df = train_test_split( test_validate_df, test_size=test_validate_size, random_state=42, stratify=test_validate_df[ stratify ] )
        
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
        
        path = self.path_prefix + "/src/ephemera/prompts/data/voice-commands-xml-validate-gpt.jsonl"
        validate_df.to_json( path, orient="records", lines=True )
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
    
    # Generating ~320 responses cost about $15, and take about 2.5 hours
    xml_ftp_generator       = XmlFineTuningPromptGenerator( debug=True )
    # So, for now just generate 10 responses
    xml_ftp_generator.build_compound_function_mapping_training_prompts( analyze_bigrams=True, max_questions=10 )
    
    # xml_ftp_generator       = XmlFineTuningPromptGenerator( tgi_url="http://127.0.0.1:3000", debug=False, silent=True, init_prompt_templates=False )
    # xml_ftp_generator       = XmlFineTuningPromptGenerator( init_prompt_templates=False )
    # interjections           = xml_ftp_generator.get_interjections()
    # salutations             = xml_ftp_generator.get_salutations()
    # # print( interjections )
    #
    # for i in range( 20 ):
    #
    #     _, foo = xml_ftp_generator.insert_interjection( "So glad you made it!", interjections )
    #     print( foo )
    #     _, foo = xml_ftp_generator.prepend_salutation( foo, salutations )
    #     print( foo )
    #
    #     _, bar = xml_ftp_generator.insert_interjection( "Could you please check your memory and see if we've spoken about DC United this week?", interjections )
    #     print( bar )
    #     _, bar = xml_ftp_generator.prepend_salutation( bar, salutations )
    #     print( bar )
    #
    #     _, baz = xml_ftp_generator.insert_interjection( "I'm trying to get a hold of the boss. Can you help me out?", interjections )
    #     print( baz )
    #     _, baz = xml_ftp_generator.prepend_salutation( baz, salutations )
    #     print( baz )
        
    # print( salutations )
    
    # # vox_cmd_prompt_template = xml_ftp_generator.get_prompt_template( "vox command" )
    # # print( vox_cmd_prompt_template )
    # # xml_ftp_generator.serialize_prompt( vox_cmd_prompt_template, "/src/conf/prompts/vox-command-template.txt" )
    #
    # # agent_prompt_template   = xml_ftp_generator.get_prompt_template( "agent router" )
    # # print( agent_prompt_template )
    # # xml_ftp_generator.serialize_prompt( agent_prompt_template,   "/src/conf/prompts/agent-router-template.txt" )
    #
    # xml_ftp_generator.serialize_prompts( "/src/conf/prompts/" )
    #
    # # xml_ftp_generator     = XmlFineTuningPromptGenerator( tgi_url="http://127.0.0.1:8080", debug=True )
    # # compound_qna_df       = xml_ftp_generator.build_compound_vox_cmd_training_prompts()
    # # simple_command_qna_df = xml_ftp_generator.build_simple_vox_cmd_training_prompts()
    #
    # # compound_agent_router_qna_df   = xml_ftp_generator.build_compound_agent_router_training_prompts()
    # # simple_agent_router_qna_df     = xml_ftp_generator.build_simple_agent_router_training_prompts()
    # #
    # # print( compound_agent_router_qna_df.shape )
    # # print( compound_agent_router_qna_df.head( 10 ) )
    # #
    # # print( simple_agent_router_qna_df.shape )
    # # print( simple_agent_router_qna_df.head( 10 ) )
    #
    # all_qna_df            = xml_ftp_generator.build_all_training_prompts()
    #
    # # for line in compound_qna_df.prompt[ 0 ].split( "\n" ): print( line )
    # # for line in simple_command_qna_df.prompt[ 0 ].split( "\n" ): print( line )
    # # for line in all_qna_df.prompt[ 0 ].split( "\n" ): print( line )
    #
    # train_df, test_df, validate_df = xml_ftp_generator.get_train_test_validate_split( all_qna_df, sample_size=all_qna_df.shape[ 0 ], test_size=0.2, test_validate_size=0.5 )
    # xml_ftp_generator.write_ttv_split_to_jsonl( train_df, test_df, validate_df )
    #
    # # validation block
    # validate_df    = pd.read_json( xml_ftp_generator.path_prefix + "/src/ephemera/prompts/data/voice-commands-xml-validate.jsonl", lines=True ).sample( 1000, random_state=42 )
    # timer          = Stopwatch( msg=f"Validating {validate_df.shape[ 0 ]:,} responses...", silent=False )
    # #
    # model_name     = "mistralai/Mistral-7B-Instruct-v0.2-AWQ"
    # validate_df    = xml_ftp_generator.generate_responses( validate_df, switch="tgi", model_name=model_name )
    # validate_df    = xml_ftp_generator.validate_responses( validate_df )
    #
    # xml_ftp_generator.print_validation_stats( validate_df, title=f"Validation Stats for `{model_name}`" )
    #
    # timer.print( msg="Done!", use_millis=False, prepend_nl=True, end="\n" )44