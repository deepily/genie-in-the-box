import re

import util as du # du = "deepily's utils"

# Currently, comma, all transcription mode descriptors are four words long.
# This will become important or more important in the future.
transcription_mode_prose_raw          = "transcription mode pros raw"
transcription_mode_prose_email        = "transcription mode pros email"
transcription_mode_prose_punctuation  = "transcription mode pros punctuation"
transcription_mode_prose_proofread    = "transcription mode pros proofread"
transcription_mode_python_punctuation = "transcription mode python punctuation"
transcription_mode_python_proofread   = "transcription mode python proofread"
transcription_mode_default            = transcription_mode_prose_raw

modes_to_methods_dict = {
     transcription_mode_prose_raw          : "transcribe_prose_raw",
     transcription_mode_prose_email        : "transcribe_prose_email",
     transcription_mode_prose_punctuation  : "transcribe_prose_punctuation",
     transcription_mode_prose_proofread    : "transcribe_prose_proofread",
     transcription_mode_python_punctuation : "transcribe_python_punctuation",
     transcription_mode_python_proofread   : "transcribe_python_proofread"
}
class Mode:

    def __init__(self, raw_transcription, config_path="conf/modes-vox.json", debug=True ):

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
        
        self.transcription_tuple    = self._transcribe( raw_transcription )
        self.transcription          = self.transcription_tuple[ 0 ]
        self.mode                   = self.transcription_tuple[ 1 ]
        
    def __str__(self):

        summary = """
                       Mode: [{}]
          Raw transcription: [{}]
        Final transcription: [{}]""".format( self.mode, self.raw_transcription, self.transcription )
        return summary

    def _get_methods_to_modes_dict( self, modes_to_methods_dict ):
        
        methods_to_modes_dict = { }
        
        for mode, method in modes_to_methods_dict.items():
            methods_to_modes_dict[ method ] = mode
        
        return methods_to_modes_dict
    def _transcribe( self, raw_transcription ):
        
        # knock everything down to alphabetic characters and spaces so that we can analyze what transcription mode we're in.
        regex = re.compile( '[^a-zA-Z ]' )
        transcription = regex.sub( '', raw_transcription ).lower()
        print( transcription )
        words = transcription.split()
        
        # If we have fewer than four words, just assign default transcription mode.
        if len( words ) < 4:
            method_name = self.modes_to_methods_dict[ transcription_mode_default ]
        else:
            
            first_four_words = " ".join( words[ 0:4 ] )
            print( "first_four_words:", first_four_words )
            default_method = self.modes_to_methods_dict[ transcription_mode_default ]
            method_name = self.modes_to_methods_dict.get( first_four_words, default_method )
            
            # Pull the first four words before we send them to be transcribed.
            raw_transcription = " ".join( words[ 4: ] )
        
        print( "method_name:", method_name )
        mode = self.methods_to_modes_dict[ method_name ]
        if self.debug: print( "Calling [{}] w/ mode [{}]...".format( method_name, mode ) )
        result = getattr( self, method_name )( raw_transcription, mode )
        
        return result
        
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
    def transcribe_prose_raw( self, raw_transcription, mode ):
        
        return raw_transcription, mode
    
    def transcribe_prose_email( self, raw_transcription, mode ):
    
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
        
        return prose, mode
    
    def transcribe_prose_punctuation( self, raw_transcription, mode ):
        
        prose = re.sub( r'[,.]', '', raw_transcription.lower() )

        # Translate punctuation mark words into single characters.
        for key, value in self.punctuation.items():
            prose = prose.replace( key, value )

        # Remove extra spaces.
        prose = self._remove_spaces_around_punctuation( prose )
        
        return prose, mode
    
    def transcribe_prose_proofread( self, raw_transcription, mode ):
    
        prose = re.sub( r'[,.]', '', raw_transcription.lower() )
        
        return raw_transcription, mode
    
    def transcribe_python_punctuation( self, raw_transcription, mode ):
        
        return raw_transcription, mode
    
    def transcribe_python_proofread( self, raw_transcription, mode ):
        
        return raw_transcription, mode
    
if __name__ == "__main__":

    # transcription = "DOM fully loaded and parsed, Checking permissions.... Done!"
    # transcription = "transcription mode pros punctuation Less then, Robert at somewhere.com greater than. DOM fully loaded and parsed comma Checking permissions.... Done exclamation point."
    # transcription = "transcription mode pros email r-i-c-a-r-d-o dot f-e-l-i-p-e dot r-u-i-z at gmail.com"
    transcription = "transcription mode pros punctuation Here 's my email address. r-i-c-a-r-d-o.f-e-l-i-p-e-.r-u-i-z at gmail.com."
    mode = Mode( transcription, debug=False )
    print( mode )
    
    