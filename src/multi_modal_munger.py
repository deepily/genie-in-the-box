import re
import os
import ast
from collections import defaultdict

import openai
import numpy as np

from lib import util as du
from lib import util_stopwatch as sw

# Currently, comma, all transcription mode descriptors are three words long.
# This will become important or more important in the future.
transcription_mode_text_raw           = "multimodal text raw"
transcription_mode_text_email         = "multimodal text email"
transcription_mode_text_punctuation   = "multimodal text punctuation"
transcription_mode_text_proofread     = "multimodal text proofread"
transcription_mode_text_contact       = "multimodal contact information"
transcription_mode_python_punctuation = "multimodal python punctuation"
transcription_mode_python_proofread   = "multimodal python proofread"
transcription_mode_server_search      = "multimodal server search"
transcription_mode_run_prompt         = "multimodal run prompt"
transcription_mode_vox_command        = "multimodal editor"
transcription_mode_default            = transcription_mode_text_punctuation

modes_to_methods_dict = {
    
    transcription_mode_vox_command       : "munge_vox_command",
    transcription_mode_text_raw          : "munge_text_raw",
    transcription_mode_text_email        : "munge_text_email",
    transcription_mode_text_punctuation  : "munge_text_punctuation",
    transcription_mode_text_proofread    : "munge_text_proofread",
    transcription_mode_text_contact      : "munge_text_contact",
    transcription_mode_python_punctuation: "munge_python_punctuation",
    transcription_mode_python_proofread  : "munge_python_proofread",
    transcription_mode_server_search     : "do_ddg_search",
    transcription_mode_run_prompt        : "do_run_prompt",
}
class MultiModalMunger:

    def __init__( self, raw_transcription, prefix="", prompt_key="generic", config_path="conf/modes-vox.json",
                  use_exact_matching=True, use_ai_matching=True, vox_command_model="ada:ft-deepily-2023-07-10-23-39-03",
                  debug=False, verbose=False ):

        self.debug                  = debug
        self.verbose                = verbose
        self.config_path            = config_path
        self.raw_transcription      = raw_transcription
        self.prefix                 = prefix
        self.use_ai_matching        = use_ai_matching
        self.use_exact_matching     = use_exact_matching
        self.vox_command_model      = vox_command_model
        self.vox_command_threshold  = 50.0

        self.punctuation            = du.get_file_as_dictionary( "conf/translation-dictionary.map", lower_case=True, debug=self.debug )
        self.domain_names           = du.get_file_as_dictionary( "conf/domain-names.map",           lower_case=True )
        self.numbers                = du.get_file_as_dictionary( "conf/numbers.map",                lower_case=True )
        self.contact_info           = du.get_file_as_dictionary( "conf/contact-information.map",    lower_case=True )
        self.prompt_dictionary      = du.get_file_as_dictionary( "conf/prompt-dictionary.map",      lower_case=True )
        self.prompt                 = du.get_file_as_string( self.prompt_dictionary.get( prompt_key, "generic" ) )
        self.command_strings        = self._get_command_strings()
        self.class_dictionary       = self._get_class_dictionary()
        
        print( "prompt_key:", prompt_key )
        if self.debug and self.verbose:
            print( "prompt:", self.prompt )
        
        self.modes_to_methods_dict  = modes_to_methods_dict
        self.methods_to_modes_dict  = self._get_methods_to_modes_dict( modes_to_methods_dict )
        
        if self.debug and self.verbose:
            print( "modes_to_methods_dict", self.modes_to_methods_dict, end="\n\n" )
            print( "methods_to_modes_dict", self.methods_to_modes_dict, end="\n\n" )
        
        # This field added to hold the Results of a calculation, e.g.: ddg search, contact information, or eventually proofreading
        # When all processing is refactored and consistent across all functionality. ¡TODO!
        self.results       = ""
        
        parsed_fields      = self.parse( raw_transcription )
        self.transcription = parsed_fields[ 0 ]
        self.mode          = parsed_fields[ 1 ]
        
        
    def __str__(self):

        summary = """
                       Mode: [{}]
                     Prefix: [{}]
          Raw transcription: [{}]
        Final transcription: [{}]
                    Results: [{}]""".format( self.mode, self.prefix, self.raw_transcription, self.transcription, self.results )
        return summary

    def get_json( self ):
        
        json = { "mode": self.mode, "prefix": self.prefix, "raw_transcription": self.raw_transcription, "transcription": self.transcription, "results": self.results }
        
        return json
        
    def _get_methods_to_modes_dict( self, modes_to_methods_dict ):
        
        methods_to_modes_dict = { }
        
        for mode, method in modes_to_methods_dict.items():
            methods_to_modes_dict[ method ] = mode
        
        return methods_to_modes_dict
    def parse( self, raw_transcription ):
        
        # ¡OJO! super special ad hoc prefix cleanup due to the use of multi, please don't do this often!
        raw_transcription = self._adhoc_prefix_cleanup( raw_transcription )
        
        # knock everything down to alphabetic characters and spaces so that we can analyze what transcription mode we're in.
        regex = re.compile( '[^a-zA-Z ]' )
        transcription = regex.sub( '', raw_transcription ).replace( "-", " " ).lower()

        print( transcription )
        words = transcription.split()

        prefix_count = len( transcription_mode_default.split() )
        
        # First and foremost: Are we in multi-modal editor/command mode?
        if self.prefix == "multimodal editor":
        
            transcription, mode = self._handle_vox_command_parsing( raw_transcription )
            du.print_banner( "  END MODE: [{}] for [{}] == [{}]".format( self.prefix, raw_transcription, self.results ), end="\n\n" )
            
            # du.print_banner( "START MODE: [{}] for [{}]".format( self.prefix, transcription ), end="\n" )
            # transcription, mode = self.munge_vox_command( raw_transcription, transcription_mode_vox_command )
            #
            # # Try exact match first, then AI match if no exact match is found.
            # if self.use_exact_matching:
            #
            #     if self._is_exact_match( transcription ):
            #
            #         print( "Exact match [{}]".format( transcription ) )
            #         self.results = transcription
            #
            #         return transcription, mode
            #
            #     else:
            #
            #         # Set results to something just in case we're not using AI matching below.
            #         print( "NOT exact match [{}]".format( transcription ) )
            #         self.results = transcription
            #
            # if self.use_ai_matching:
            #
            #     # TODO: fuzzy match, e.g.: "zooming" -> "zoom in"
            #     self.results = self._get_ai_match( transcription )
            #     print( "Results [{}]".format( self.results ) )
            #
            # du.print_banner( "  END MODE: [{}] for [{}]".format( self.prefix, transcription ), end="\n\n" )

            return transcription, mode
        
        # If we have fewer than 'prefix_count' words, just assign default transcription mode.
        if len( words ) < prefix_count and ( self.prefix == "" or self.prefix not in self.modes_to_methods_dict ):
            method_name = self.modes_to_methods_dict[ transcription_mode_default ]
        else:
            
            first_words = " ".join( words[ 0:prefix_count ] )
            print( "first_words:", first_words )
            default_method = self.modes_to_methods_dict[ transcription_mode_default ]
            method_name    = self.modes_to_methods_dict.get( first_words, default_method )
            
            # Conditionally pull the first n words before we send them to be transcribed.
            if first_words in self.modes_to_methods_dict:
                raw_words = raw_transcription.split()
                raw_transcription = " ".join( raw_words[ prefix_count: ] )
            else:
                print( "first_words [{}] of raw_transcription not found in modes_to_methods_dict".format( first_words ) )
                # If we have a prefix, try to use it to determine the transcription mode.
                if self.prefix in self.modes_to_methods_dict:
                    print( "prefix [{}] in modes_to_methods_dict".format( self.prefix ) )
                    method_name = self.modes_to_methods_dict[ self.prefix ]
                else:
                    print( "prefix [{}] not found in modes_to_methods_dict either".format( self.prefix ) )
                
        mode = self.methods_to_modes_dict[ method_name ]
        
        if self.debug:
            print( "Calling [{}] w/ mode [{}]...".format( method_name, mode ) )
            print( "raw_transcription [{}]".format( raw_transcription ) )
            
        transcription, mode = getattr( self, method_name )( raw_transcription, mode )
        if self.debug:
            print( "result after:", transcription )
            print( "mode:", mode )
        
        return transcription, mode
        
    def _handle_vox_command_parsing( self, raw_transcription ):
    
        du.print_banner( "START MODE: [{}] for [{}]".format( self.prefix, raw_transcription ), end="\n" )
        transcription, mode = self.munge_vox_command( raw_transcription, transcription_mode_vox_command )

        # Try exact match first, then AI match if no exact match is found.
        if self.use_exact_matching:

            if self._is_match( transcription ):

                self.results = transcription
                return transcription, mode

            else:

                # Set results to something just in case we're not using AI matching below.
                self.results = transcription

        if self.use_ai_matching:

            print( "Attempting fuzzy match, e.g.: zooming -> zoom in..." )
            self.results = self._get_ai_match( transcription )
            print( "Attempting fuzzy match, e.g.: zooming -> zoom in... Done: results [{}]".format( self.results ) )

        return transcription, mode
    
    def _adhoc_prefix_cleanup( self, raw_transcription ):
        
        # Find the first instance of "multi________" and replace it with "multimodal".
        multimodal_regex  = re.compile( "multi([ -]){0,1}mod[ae]l", re.IGNORECASE )
        raw_transcription = multimodal_regex.sub( "multimodal", raw_transcription, 1 )

        multimodal_regex = re.compile( "t[ao]ggle", re.IGNORECASE )
        raw_transcription = multimodal_regex.sub( "toggle", raw_transcription, 1 )
        
        return raw_transcription
    
    def _remove_protocols( self, words ):
        
        multimodal_regex = re.compile( "http([s]){0,1}://", re.IGNORECASE )
        words = multimodal_regex.sub( "", words, 1 )
        
        return words
    
    def _remove_spaces_around_punctuation( self, prose ):
    
        # Remove extra spaces.
        prose = prose.replace( " / ", "/" )
        prose = prose.replace( "[ ", "[" )
        prose = prose.replace( " ]", "]" )
    
        prose = prose.replace( "< ", "<" )
        prose = prose.replace( " >", ">" )
    
        prose = prose.replace( " )", ")" )
        prose = prose.replace( "( ", "(" )
        prose = prose.replace( " .", "." )
        prose = prose.replace( " ,", "," )
        prose = prose.replace( "??", "?" )
        prose = prose.replace( " ?", "?" )
        prose = prose.replace( "!!", "!" )
        prose = prose.replace( " !", "!" )
        prose = prose.replace( " :", ":" )
        prose = prose.replace( " ;", ";" )
        prose = prose.replace( ' "', '"' )
        
        return prose
    def munge_text_raw( self, raw_transcription, mode ):
        
        return raw_transcription, mode
    
    def munge_text_email( self, raw_transcription, mode ):
    
        # Add special considerations for the erratic nature of email transcriptions when received raw from the whisper.
        # prose = raw_transcription.replace( ".", " dot " )
        print( "BEFORE raw_transcription:", raw_transcription )
        email = raw_transcription.lower()
        
        # Decode domain names
        for key, value in self.domain_names.items():
            email = email.replace( key, value )
        
        # Decode numbers
        for key, value in self.numbers.items():
            email = email.replace( key, value )

        # Remove space between individual numbers.
        regex = re.compile( '(?<=[0-9]) (?=[0-9])' )
        email = regex.sub( "", email )
        
        print( " AFTER raw_transcription:", raw_transcription )
        
        email = re.sub( r'[,]', '', email )
        
        # phonetic spellings often contain -'s
        regex = re.compile( "(?<=[a-z])([-])(?=[a-z])", re.IGNORECASE )
        email = regex.sub( "", email )

        # Translate punctuation mark words into single characters.
        for key, value in self.punctuation.items():
            email = email.replace( key, value )

        # Remove extra spaces around punctuation.
        email = self._remove_spaces_around_punctuation( email )
        
        # Remove extra spaces
        email = email.replace( " ", "" )
        
        # Add back in the dot: yet another ad hoc fix up
        # if not prose.endswith( ".com" ) and prose.endswith( "com" ):
        #     prose = prose.replace( "com", ".com" )
        
        # Remove trailing periods.
        email = email.rstrip( "." )
        
        return email, mode
    
    def munge_vox_command( self, raw_transcription, mode ):
        
        command = raw_transcription.lower()

        # Remove the protocol from URLs
        command = self._remove_protocols( command )
        
        # Encode domain names as plain text before removing dots below
        for key, value in self.domain_names.items():
            command = command.replace( key, value )
            
        command = re.sub( r'[,.?!]', '', command )
        
        # Translate punctuation mark words into single characters.
        for key, value in self.punctuation.items():
            command = command.replace( key, value )
        
        # Remove extra spaces.
        command = self._remove_spaces_around_punctuation( command )
        
        # Remove protocol from URLs
        # https: // npr.org
        
        return command, mode
    
    def munge_text_punctuation( self, raw_transcription, mode ):
    
        # print( "BEFORE raw_transcription:", raw_transcription )
        prose = raw_transcription.lower()
        
        # Remove the protocol from URLs
        prose = self._remove_protocols( prose )
    
        # Encode domain names as plain text before removing dots below
        for key, value in self.domain_names.items():
            prose = prose.replace( key, value )

        prose = re.sub( r'[,.]', '', prose )

        # Translate punctuation mark words into single characters.
        for key, value in self.punctuation.items():
            prose = prose.replace( key, value )
            
        # Remove extra spaces.
        prose = self._remove_spaces_around_punctuation( prose )
        
        return prose, mode
    
    def munge_text_contact( self, raw_transcription, mode, extra_words="" ):
        
        # multimodal contact information ___________
        raw_transcription = raw_transcription.lower()
        regex = re.compile( '[^a-zA-Z ]' )
        raw_transcription = regex.sub( '', raw_transcription ).replace( "-", " " )
        # # There could be more words included here, but they're superfluous, we're only looking for the 1st word After three have been stripped out already.
        # contact_info_key = raw_transcription.split()[ 0 ]
        contact_info_key = raw_transcription
        contact_info     = self.contact_info.get( contact_info_key, "N/A" )
        
        print( "contact_info_key:", contact_info_key )
        print( "    contact_info:", contact_info )
        
        if contact_info_key in "full all":
            
            contact_info = "{}\n{}\n{} {}, {}\n{}\n{}".format(
                self.contact_info[ "name" ].title(),
                self.contact_info[ "address" ].title(),
                self.contact_info[ "city" ].title(), self.contact_info[ "state" ].upper(), self.contact_info[ "zip" ],
                self.contact_info[ "email" ],
                self.contact_info[ "telephone" ]
            )
        elif contact_info_key == "city state zip":
        
            contact_info = "{} {}, {}".format(
                self.contact_info[ "city" ].title(), self.contact_info[ "state" ].upper(), self.contact_info[ "zip" ]
            )
        
        elif contact_info_key == "state":
            contact_info = contact_info.upper()
        elif contact_info_key != "email":
            contact_info = contact_info.title()
        
        self.results     = contact_info
        print( "    self.results:", self.results )
        
        return raw_transcription, mode
    def munge_text_proofread( self, raw_transcription, mode ):
    
        transcription, mode = self.munge_text_punctuation( raw_transcription, mode )
        
        return transcription, mode
    
    def munge_python_punctuation( self, raw_transcription, mode ):
    
        code = raw_transcription.lower()

        # Remove "space, ", commas, and periods.
        code = re.sub( r'space, |[,.-]', '', code.lower() )

        # Translate punctuation mark words into single characters.
        for key, value in self.punctuation.items():
            code = code.replace( key, value )

            # Decode numbers
        for key, value in self.numbers.items():
            code = code.replace( key, value )

        # Remove extra spaces.
        code = code.replace( " _ ", "_" )
        code = code.replace( " ,", ", " )
        code = code.replace( "self . ", "self." )
        code = code.replace( " . ", "." )
        code = code.replace( "[ { } ]", "[{}]" )
        code = code.replace( " [", "[" )
        code = code.replace( " ( )", "()" )
        code = code.replace( ") :", "):" )
        code = code.replace( " ( ", "( " )
        # code = code.replace( " ) ", " ) " )

        # Remove extra spaces.
        code = ' '.join( code.split() )
        
        return code, mode
    
    def munge_python_proofread( self, raw_transcription, mode ):
        
        return raw_transcription, mode
    
    def do_ddg_search( self, raw_transcription, mode ):
        
        transcription, mode = self.munge_text_punctuation( raw_transcription, mode )
        
        if "this information" in transcription:
            print( "KLUDGE: 'THIS information' munged into 'DISinformation'" )
            transcription = transcription.replace( "this information", "disinformation" )
            
        return transcription, mode
    
    def do_run_prompt( self, raw_transcription, mode ):
        
        # Not doing much preparation work here. For the moment.
        raw_transcription = raw_transcription.lower()
        
        return raw_transcription, mode
    
    def is_text_proofread( self ):
        
        return self.mode == transcription_mode_text_proofread
    
    def is_ddg_search( self ):
        
        return self.mode == transcription_mode_server_search
    
    def is_run_prompt( self ):
        
        return self.mode == transcription_mode_run_prompt
    
    def _is_match( self, transcription ):
        
        for command in self.command_strings:
            
            if transcription == command:
                print( "EXACT MATCH: Transcription [{}] == command [{}]".format( transcription, command ) )
                return True
            elif transcription.startswith( command ):
                print( "Transcription [{}] STARTS WITH command [{}]".format( transcription, command ) )
                print( "TODO: Make sure we are handling startswith() properly. Can we do better than this?" )
                return True
            elif command.startswith( transcription ):
                print( "Command [{}] STARTS WITH transcription [{}]".format( command, transcription ) )
                print( "TODO: Make sure we are handling startswith() properly. Can we do better than this?" )
                return True
        
        print( "NO exact match        [{}]".format( transcription ) )
        print( "NO startswith() match [{}]".format( transcription ) )
        
        return False
    
    def _get_ai_match( self, transcription ):
        
        best_guess = self._get_best_guess( transcription )
        
        # Setting a threshold allows us to return a raw transcription when an utterance represents a command that's not currently fine-tuned within the model.
        if best_guess[ 1 ] >= self.vox_command_threshold:
        
            print( "TODO: Create a second model That's trained to extract arguments from within the voice command string, such as URLs and search terms" )
            print( "Best guess is GREATER than threshold [{}]".format( self.vox_command_threshold ) )
            return best_guess[ 0 ]
        
        else:
            
            print( "Best guess is LESS than threshold [{}], returning raw transcription".format( self.vox_command_threshold ) )
            return transcription
    
    def _log_odds_to_probabilities( self, log_odds ):
        
        # Convert dictionary to a sorted list of tuples
        log_odds = sorted( log_odds.items(), key=lambda tup: tup[ 1 ], reverse=True )
        
        probabilities = [ ]
        
        for item in log_odds:
            
            class_name = self.class_dictionary[ item[ 0 ].strip() ]
            print( "{}: {:.4f}%".format( class_name, np.exp( float( item[ 1 ] ) ) * 100 ) )
            probabilities.append( (class_name, np.exp( item[ 1 ] ) * 100) )
        
        return probabilities
    
    def _get_best_guess( self, command_str ):
        
        openai.api_key = os.getenv( "FALSE_POSITIVE_API_KEY" )
        
        timer = sw.Stopwatch()
        
        response = openai.Completion.create(
            model=self.vox_command_model,
            prompt=command_str + "\n\n###\n\n",
            max_tokens=1,
            temperature=0,
            logprobs=len( self.class_dictionary.keys() )
        )
        
        timer.print( "Call to [{}]".format( self.vox_command_model ), use_millis=True, end="\n" )
        
        # convert OPENAI object into a native Python dictionary... ugly!
        best_guess = ast.literal_eval( str( response[ "choices" ][ 0 ][ "logprobs" ][ "top_logprobs" ][ 0 ] ) )
        
        # Return the first value in the sorted list of tuples.
        return self._log_odds_to_probabilities( best_guess )[ 0 ]
    
    def extract_domain_name( self, raw_text ):
        
        openai.api_key = os.getenv( "FALSE_POSITIVE_API_KEY" )
        print( "Using FALSE_POSITIVE_API_KEY [{}]".format( os.getenv( "FALSE_POSITIVE_API_KEY" ) ) )
        
        if self.debug: print( " raw_text [{}]".format( raw_text ) )
        
        timer = sw.Stopwatch()
        system   = "You are an expert in internet protocols and naming conventions."
        content  = """Extract the domain name contained within the text delimited by three backticks. If you are unable
                      to find a valid domain name, return NO_VALID_DOMAIN_NAME_FOUND.```""" + raw_text + "```"
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo-0613",
            # Not yet available, comma, still waiting for July's bill to be submitted before I can get access.
            # model="gpt-4",
            messages=[
                { "role": "system", "content": system },
                { "role": "user",   "content": content }
            ],
            # From: https://community.openai.com/t/cheat-sheet-mastering-temperature-and-top-p-in-chatgpt-api-a-few-tips-and-tricks-on-controlling-the-creativity-deterministic-output-of-prompt-responses/172683
            temperature=0.0,
            top_p=0.0,
            max_tokens=12,
            frequency_penalty=0.0,
            presence_penalty=0.0
        )
        timer.print( "Call to [{}]".format( "gpt-3.5-turbo-0613" ), use_millis=True, end="\n" )
        
        if self.debug: print( response )
        
        return response[ "choices" ][ 0 ][ "message" ][ "content" ].strip()
    
    def extract_args( self, raw_text, model="ada:ft-deepily-2023-07-11-20-18-37" ):
        
        openai.api_key = os.getenv( "FALSE_POSITIVE_API_KEY" )
        print( "Using FALSE_POSITIVE_API_KEY [{}]".format( os.getenv( "FALSE_POSITIVE_API_KEY" ) ) )
        
        if self.debug: print( " raw_text [{}]".format( raw_text ) )
        
        timer = sw.Stopwatch()
        
        response = openai.Completion.create(
            model=model,
            prompt=raw_text,
            # From: https://community.openai.com/t/cheat-sheet-mastering-temperature-and-top-p-in-chatgpt-api-a-few-tips-and-tricks-on-controlling-the-creativity-deterministic-output-of-prompt-responses/172683
            temperature=0.0,
            top_p=0.0,
            max_tokens=12,
            frequency_penalty=0.0,
            presence_penalty=0.0,
            stop=["\n"]
        )
        timer.print( "Call to [{}]".format( model ), use_millis=True, end="\n" )
        
        if self.debug: print( response )
        
        return response.choices[ 0 ].text.strip()
        
    def _get_command_strings( self ):
    
        exact_matches = du.get_file_as_list( "conf/constants.js", lower_case=True, clean=True )
        vox_commands = [ ]
        
        for raw_line in exact_matches :
            
            # Skip comments and other lines that don't split into two pieces.
            if len( raw_line.split( " = " ) ) == 1:
                continue
            
            match = raw_line.split( " = " )[ 1 ].strip()
            
            if match.startswith( '"' ) and match.endswith( '";' ) and not match.startswith( '"http' ):
                # Remove quotes and semicolon.
                match = match[ 1 : -2 ]
                vox_commands.append( match )
            else:
                if self.debug: print( "SKIPPING [{}]...".format( match ) )
                
        
        if self.debug:
            # Sort keys alphabetically before printing them out.
            vox_commands.sort()
            for vox_command in vox_commands: print( vox_command )
        
        # Sort the sending order by length of string, longest first.  From: https://stackoverflow.com/questions/60718330/sort-list-of-strings-in-decreasing-order-according-to-length
        vox_commands = sorted( vox_commands, key=lambda command: ( -len( command ), command) )
        
        return vox_commands
    
    def _get_class_dictionary( self ):
        
        class_dictionary = defaultdict( lambda: "unknown command" )
        # class_dictionary = { }
        class_dictionary[ "0" ] =                       "in current tab"
        class_dictionary[ "1" ] =                         "open new tab"
        class_dictionary[ "2" ] =                    "none of the above"
        class_dictionary[ "3" ] =            "search google current tab"
        class_dictionary[ "4" ] =                "search google new tab"
        class_dictionary[ "5" ] =    "search google scholar current tab"
        class_dictionary[ "6" ] =        "search google scholar new tab"
        class_dictionary[ "7" ] =                   "search current tab"
        class_dictionary[ "8" ] =                       "search new tab"
    

if __name__ == "__main__":

    prefix = ""
    # transcription = "DOM fully loaded and parsed, Checking permissions.... Done!"
    # transcription = "multi-mode text raw Less then, Robert at somewhere.com greater than. DOM fully loaded and parsed comma Checking permissions.... Done exclamation point."
    # transcription = "multi-mode text proofread Less then, Robert at somewhere.com greater than. DOM fully loaded and parsed comma Checking permissions.... Done exclamation point."
    # transcription = "Multi-mode text punctuation Less then, Robert at somewhere.com greater than. DOM fully loaded and parsed comma Checking permissions.... Done exclamation point."
    # transcription = "multi-modal text email r-i-c-a-r-d-o dot f-e-l-i-p-e dot r-u-i-z at gmail.com"
    # transcription = "multi model text email r-i-c-a-r-d-o dot f-e-l-i-p-e dot r-u-i-z six two at sign gmail. com."
    # transcription = "multi-mode text punctuation Here's my email address. r-i-c-a-r-d-o.f-e-l-i-p-e-.r-u-i-z at gmail.com."
    # transcription = "blah blah blah"
    # transcription = "multimodal text proofread i go to market yesterday comma Tonight i go to the dance, comma, and im very happy that exclamation point."
    
    # transcription = "multimodal python punctuation Deaf, Munch, Underscore Python, Underscore Punctuation, Open Parenthesis, Space, Self, Comma, Raw Underscore transcription, Comma, Space, Mode, Space, Close Parenthesis, Colon, newline newline foo equals six divided by four newline newline bar equals brackets"
    
    # transcription = "multimodal contact information name"
    # transcription = "multimodal contact information address"
    # transcription = "City, State, Zip."
    # prefix        = "multimodal contact information"
    # prefix = ""
    
    # transcription = "full"
    # transcription = "multimodal ai fetch this information: Large, language models."
    
    prefix        = "multimodal editor"
    # transcription = "Take Me Too https://NPR.org!"
    # transcription = "Zoom, In!"
    # transcription = "Go ZoomInG!"
    # transcription = "Open a new tab and go to blahblah"
    # transcription = "Open the door and go to blahblah"
    transcription = "In a new tab, search for blah blah blah."
    munger = MultiModalMunger( transcription, prefix="", debug=True )
    # munger = MultiModalMunger( transcription )
    # print( "munger.use_exact_matching [{}]".format( munger.use_exact_matching ) )
    # print( "munger.use_ai_matching    [{}]".format( munger.use_ai_matching ) )
    print( munger.extract_args( transcription ) )
    # print( "munger.is_ddg_search()", munger.is_ddg_search() )
    # print( "munger.is_run_prompt()", munger.is_run_prompt(), end="\n\n" )
    # print( munger, end="\n\n" )
    # print( munger.get_json(), end="\n\n" )
    # exact_matches = munger._get_exact_matching_strings()
    #
    # for match in exact_matches: print( match )
    
    # transcription = "http://npr.org"
    
    # multimodal_regex = re.compile( "http([s]){0,1}://", re.IGNORECASE )
    # transcription = multimodal_regex.sub( "", transcription, 1 )
    # transcription = transcription.replace( ("https://")|("http://"), "" )
    # print( transcription )
    
    
    # raw_prompt = """
    # Your task is to generate a short summary of a product review from an ecommerce site.
    # Summarize the review below, delimited by triple backticks, in at most 30 words.
    # Review: ```Got this panda plush toy for my daughter's birthday,
    # who loves it and takes it everywhere. It's soft and
    # super cute, and its face has a friendly look. It's
    # a bit small for what I paid though. I think there
    # might be other options that are bigger for the same price. It arrived a day
    # earlier than expected, so I got to play with it myself before I gave it to her. ```
    # """
    # preamble = raw_prompt.split( "```" )[ 0 ].strip()
    # content = raw_prompt.split( "```" )[ 1 ].strip()
    # print( "preamble [{}]".format( preamble ) )
    # print( "  review [{}]".format( content ) )
    
    # regex = re.compile( "[.]$", re.IGNORECASE )
    # foo = regex.sub( "", "foo.", 1 )
    # print( foo )
    #
    # bar = "1 2 3 4"
    # regex = re.compile( "((?P<before>[0-9])([ ]{0,1})(?P<after>[0-9]))", re.IGNORECASE )
    # # bar = regex.sub( "multimodal", bar, 1 )
    # bar = regex.sub( "\g<before>\g<after>", bar )
    # print( bar )
    #
    # foo = " 1 2 3ab4 5 6 7 "
    # regex = re.compile( '(?<=[0-9]) (?=[0-9])' )
    # foo = regex.sub( "", foo )
    # print( "[{}]".format( foo ) )
    #
    # blah = "a-b-c-d-e-f-g-h-i-j-k-l -- -members-only- -- n-o-p-q-r-s-t-u-v-w-x-y-z"
    # regex = re.compile( "(?<=[a-z])([-])(?=[a-z])", re.IGNORECASE )
    # blah = regex.sub( "", blah )
    # print( blah )
    
    
    
    # print( "munger.get_json()", munger.get_json() )
    # print( "type( munger.get_json() )", type( munger.get_json() ) )
    # print( munger.get_json()[ "transcription" ] )
    # print( munger.is_text_proofread() )

    # genie_client = gc.GenieClient( debug=True )
    # timer = sw.Stopwatch()
    # preamble = "You are an expert proofreader. Correct grammar. Correct tense. Correct spelling. Correct contractions. Correct punctuation. Correct capitalization. Correct word choice. Correct sentence structure. Correct paragraph structure. Correct paragraph length. Correct paragraph flow. Correct paragraph topic. Correct paragraph tone. Correct paragraph style. Correct paragraph voice. Correct paragraph mood. Correct paragraph theme."
    # response = genie_client.ask_chat_gpt_text( munger.transcription, preamble=preamble )
    # print( response )
    # timer.print( "Proofread", use_millis=True )
    
    