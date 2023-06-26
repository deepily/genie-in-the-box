import re

from lib import util as du

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
transcription_mode_default            = transcription_mode_text_punctuation

modes_to_methods_dict = {
    
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

    def __init__(self, raw_transcription, prefix="", prompt_key="generic", config_path="conf/modes-vox.json", debug=False, verbose=False ):

        self.debug                  = debug
        self.verbose                = verbose
        self.config_path            = config_path
        self.raw_transcription      = raw_transcription
        self.prefix                 = prefix

        self.punctuation            = du.get_file_as_dictionary( "conf/translation-dictionary.map", lower_case=True, debug=self.debug )
        self.domain_names           = du.get_file_as_dictionary( "conf/domain-names.map", lower_case=True )
        self.numbers                = du.get_file_as_dictionary( "conf/numbers.map", lower_case=True )
        self.contact_info           = du.get_file_as_dictionary( "conf/contact-information.map", lower_case=True )
        self.prompt_dictionary      = du.get_file_as_dictionary( "conf/prompt-dictionary.map", lower_case=True )
        self.prompt                 = du.get_file_as_string( self.prompt_dictionary.get( prompt_key, "generic" ) )
        
        print( "prompt_key:", prompt_key )
        if self.debug and self.verbose:
            print( "prompt:", self.prompt )
        
        self.modes_to_methods_dict  = modes_to_methods_dict
        self.methods_to_modes_dict  = self._get_methods_to_modes_dict( modes_to_methods_dict )
        
        if self.debug and self.verbose:
            print( "modes_to_methods_dict", self.modes_to_methods_dict, end="\n\n" )
            print( "methods_to_modes_dict", self.methods_to_modes_dict, end="\n\n" )
        
        # This field added to hold the data of a calculation, e.g.: ddg search, contact information, or eventually proofreading
        # When all processing is refactored and consistent across all functionality. ¡TODO!
        self.results       = ""
        
        parsing_results = self.parse( raw_transcription )
        self.transcription = parsing_results[ 0 ]
        self.mode          = parsing_results[ 1 ]
        
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
        
            du.print_banner( "MODE: [{}]".format( self.prefix ), end="\n" )
            result, mode = self.munge_text_punctuation( raw_transcription, transcription_mode_default )
            
            if result in [ "zoom in", "zoom out", "zoom reset" ]:
                print( "Exact match [{}]".format( result ) )
            else:
                # TODO: fuzzy match, e.g.: "zooming" -> "zoom in"
                print( "NOT exact match [{}]".format( result ) )
                print( "TODO: to find a fuzzy/interpreted match..." )
                
            print()
            return result, mode
        
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
            
        result, mode = getattr( self, method_name )( raw_transcription, mode )
        if self.debug:
            print( "result after:", result )
            print( "mode:", mode )
        
        return result, mode
        
    def _adhoc_prefix_cleanup( self, raw_transcription ):
        
        # Find the first instance of "multi________" and replace it with "multimodal".
        multimodal_regex  = re.compile( "multi([ -]){0,1}mod[ae]l", re.IGNORECASE )
        raw_transcription = multimodal_regex.sub( "multimodal", raw_transcription, 1 )

        multimodal_regex = re.compile( "t[ao]ggle", re.IGNORECASE )
        raw_transcription = multimodal_regex.sub( "toggle", raw_transcription, 1 )
        
        return raw_transcription
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
    
    def munge_text_punctuation( self, raw_transcription, mode ):
    
        # print( "BEFORE raw_transcription:", raw_transcription )
        prose = raw_transcription.lower()
    
        # Encode domain names
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
        
        self.results = contact_info
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
    # transcription = "multimodal editor proof"
    
    # transcription = "multimodal python punctuation Deaf, Munch, Underscore Python, Underscore Punctuation, Open Parenthesis, Space, Self, Comma, Raw Underscore transcription, Comma, Space, Mode, Space, Close Parenthesis, Colon, newline newline foo equals six divided by four newline newline bar equals brackets"
    
    # transcription = "multimodal contact information name"
    # transcription = "multimodal contact information address"
    transcription = "City, State, Zip."
    prefix        = "multimodal contact information"
    # prefix = ""
    
    # transcription = "full"
    # transcription = "multimodal ai fetch this information: Large, language models."
    
    # prefix = transcription_mode_run_prompt
    # transcription = "you are a professional prompt creator"
    #
    munger = MultiModalMunger( transcription, prefix=prefix, debug=True )
    print( munger, end="\n\n" )
    print( munger.get_json(), end="\n\n" )
    print( "munger.is_ddg_search()", munger.is_ddg_search() )
    print( "munger.is_run_prompt()", munger.is_run_prompt(), end="\n\n" )
    
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
    