import re

import util as du # du = "deepily's utils"
import genie_client as gc
import util_stopwatch as sw

# Currently, comma, all transcription mode descriptors are three words long.
# This will become important or more important in the future.
transcription_mode_text_raw           = "multimodal text raw"
transcription_mode_text_email         = "multimodal text email"
transcription_mode_text_punctuation   = "multimodal text punctuation"
transcription_mode_text_proofread     = "multimodal text proofread"
transcription_mode_python_punctuation = "multimodal python punctuation"
transcription_mode_python_proofread   = "multimodal python proofread"
transcription_mode_default            = transcription_mode_text_punctuation

modes_to_methods_dict = {
     transcription_mode_text_raw          : "munge_text_raw",
     transcription_mode_text_email        : "munge_text_email",
     transcription_mode_text_punctuation  : "munge_text_punctuation",
     transcription_mode_text_proofread    : "munge_text_proofread",
     transcription_mode_python_punctuation : "munge_python_punctuation",
     transcription_mode_python_proofread   : "munge_python_proofread"
}
class MultiModalMunger:

    def __init__(self, raw_transcription, config_path="conf/modes-vox.json", debug=False ):

        self.debug                  = debug
        self.config_path            = config_path
        self.raw_transcription      = raw_transcription

        # load transcription munging map and handle a problematic right hand value: "space"
        self.punctuation            = du.get_file_as_dictionary( "conf/translation-dictionary.map", lower_case=True, debug=self.debug )
        self.punctuation[ "space" ] = " "
        
        self.modes_to_methods_dict  = modes_to_methods_dict
        self.methods_to_modes_dict  = self._get_methods_to_modes_dict( modes_to_methods_dict )
        
        if self.debug:
            print( "modes_to_methods_dict", self.modes_to_methods_dict, end="\n\n" )
            print( "methods_to_modes_dict", self.methods_to_modes_dict, end="\n\n" )
        
        result = self.parse( raw_transcription )
        self.transcription = result[ 0 ]
        self.mode          = result[ 1 ]
        
    def __str__(self):

        summary = """
                       Mode: [{}]
          Raw transcription: [{}]
        Final transcription: [{}]""".format( self.mode, self.raw_transcription, self.transcription )
        return summary

    def get_json( self ):
        
        json = { "mode": self.mode, "raw_transcription": self.raw_transcription, "transcription": self.transcription }
        
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
        
        # If we have fewer than 'prefix_count' words, just assign default transcription mode.
        if len( words ) < prefix_count:
            method_name = self.modes_to_methods_dict[ transcription_mode_default ]
        else:
            
            first_words = " ".join( words[ 0:prefix_count ] )
            print( "first_words:", first_words )
            default_method = self.modes_to_methods_dict[ transcription_mode_default ]
            method_name = self.modes_to_methods_dict.get( first_words, default_method )
            
            # Conditionally pull the first four words before we send them to be transcribed.
            if first_words in self.modes_to_methods_dict:
                raw_transcription = " ".join( words[ prefix_count: ] )
            else:
                print( "first_words [{}] not in modes_to_methods_dict".format( first_words ) )
                
        print( "method_name:", method_name )
        mode = self.methods_to_modes_dict[ method_name ]
        print( "mode:", mode )
        if self.debug: print( "Calling [{}] w/ mode [{}]...".format( method_name, mode ) )
        result, mode = getattr( self, method_name )( raw_transcription, mode )
        print( "result[ 0 ]:", result[ 0 ] )
        print( "result[ 1 ]:", result[ 1 ] )
        print( "mode:", mode )
        
        return result[ 0 ], mode
        
    def _adhoc_prefix_cleanup( self, raw_transcription ):
        
        # I'm sure a regular expression would do a much more concise job of this, but I'm not sure how to do it QUICKLY right now
        prefixes = [ "Multimodal", "multi-mode", "Multi-mode", "multimode", "Multimode" ]
        for prefix in prefixes:
            if raw_transcription.startswith( prefix ):
                raw_transcription = raw_transcription.replace( prefix, "multimodal" )
                break
                
        return raw_transcription
    def _remove_spaces_around_punctuation( self, prose ):
    
        # Remove extra spaces.
        prose = prose.replace( "[ ", "[" )
        prose = prose.replace( " ]", "]" )
    
        prose = prose.replace( "< ", "<" )
        prose = prose.replace( " >", ">" )
    
        prose = prose.replace( " )", ")" )
        prose = prose.replace( "( ", "(" )
        prose = prose.replace( " .", "." )
        prose = prose.replace( " ,", "," )
        prose = prose.replace( " ?", "?" )
        # prose = prose.replace( "??", "?" )
        prose = prose.replace( " !", "!" )
        # prose = prose.replace( "!!", "!" )
        prose = prose.replace( " :", ":" )
        prose = prose.replace( " ;", ";" )
        prose = prose.replace( ' "', '"' )
        
        return prose
    def munge_text_raw( self, raw_transcription, mode ):
        
        return raw_transcription, mode
    
    def munge_text_email( self, raw_transcription, mode ):
    
        # Add special considerations for the erratic nature of email transcriptions when received raw from the whisper.
        prose = raw_transcription.replace( ".", " dot " )
        
        prose = re.sub( r'[,]', '', prose.lower() )
        prose = prose.replace( "-", "" )

        # Translate punctuation mark words into single characters.
        for key, value in self.punctuation.items():
            prose = prose.replace( key, value )

        # Remove extra spaces around punctuation.
        prose = self._remove_spaces_around_punctuation( prose )
        
        # Remove extra spaces
        prose = prose.replace( " ", "" )
        
        # Add back in the dot: yet another ad hoc fix up
        if not prose.endswith( ".com" ) and prose.endswith( "com" ):
            prose = prose.replace( "com", ".com" )
        
        return prose, mode
    
    def munge_text_punctuation( self, raw_transcription, mode ):
        
        prose = re.sub( r'[,.]', '', raw_transcription.lower() )

        # Translate punctuation mark words into single characters.
        for key, value in self.punctuation.items():
            prose = prose.replace( key, value )

        # Remove extra spaces.
        prose = self._remove_spaces_around_punctuation( prose )
        
        return prose, mode
    
    def munge_text_proofread( self, raw_transcription, mode ):
    
        transcription = self.munge_text_punctuation( raw_transcription, mode )
        
        return transcription, mode
    
    def munge_python_punctuation( self, raw_transcription, mode ):
        
        return raw_transcription, mode
    
    def munge_python_proofread( self, raw_transcription, mode ):
        
        return raw_transcription, mode
    
    def is_text_proofread( self ):
        
        return self.mode == transcription_mode_text_proofread
    
if __name__ == "__main__":

    # transcription = "DOM fully loaded and parsed, Checking permissions.... Done!"
    # transcription = "multi-mode text raw Less then, Robert at somewhere.com greater than. DOM fully loaded and parsed comma Checking permissions.... Done exclamation point."
    # transcription = "multi-mode text proofread Less then, Robert at somewhere.com greater than. DOM fully loaded and parsed comma Checking permissions.... Done exclamation point."
    # transcription = "multi-mode text punctuation Less then, Robert at somewhere.com greater than. DOM fully loaded and parsed comma Checking permissions.... Done exclamation point."
    # transcription = "multi-modal text email r-i-c-a-r-d-o dot f-e-l-i-p-e dot r-u-i-z at gmail.com"
    # transcription = "multi-mode text punctuation Here's my email address. r-i-c-a-r-d-o.f-e-l-i-p-e-.r-u-i-z at gmail.com."
    # transcription = "blah blah blah"
    transcription = "multimodal text proofread I go to market yesterday comma Tonight I go to the dance, comma, and I'm very happy that exclamation point."
    munger = MultiModalMunger( transcription, debug=False )
    print( munger )
    
    print( "munger.get_json()", munger.get_json() )
    print( "type( munger.get_json() )", type( munger.get_json() ) )
    print( munger.get_json()[ "transcription" ] )
    print( munger.is_text_proofread() )

    genie_client = gc.GenieClient( debug=True )
    timer = sw.Stopwatch()
    preamble = "You are an expert proofreader. Correct grammar. Correct tense. Correct spelling. Correct contractions. Correct punctuation. Correct capitalization. Correct word choice. Correct sentence structure. Correct paragraph structure. Correct paragraph length. Correct paragraph flow. Correct paragraph topic. Correct paragraph tone. Correct paragraph style. Correct paragraph voice. Correct paragraph mood. Correct paragraph theme."
    response = genie_client.ask_chat_gpt_text( munger.transcription, preamble=preamble )
    print( response )
    timer.print( "Proofread", use_millis=True )
    