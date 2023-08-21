import os
import pickle

import lib.util as du

class QuestionEmbeddingsDict( dict ):
    
    PATH_TO_DICT = os.path.join( du.get_project_root(), "src/conf/long-term-memory/solutions/question-embeddings-dictionary.pickle" )
    def __init__( self, *args, **kwargs ):
        
        self.update( *args, **kwargs )
        
        if os.path.exists( QuestionEmbeddingsDict.PATH_TO_DICT ):
            with open( QuestionEmbeddingsDict.PATH_TO_DICT, "rb" ) as f:
                data = pickle.load( f )
                self.update( data )
    
    def __setitem__( self, key, value ):
        
        super().__setitem__( key, value )
        
        with open( QuestionEmbeddingsDict.PATH_TO_DICT, "wb" ) as f:
            pickle.dump( self, f )
