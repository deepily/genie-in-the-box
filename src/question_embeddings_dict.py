import os
import pickle

import lib.util as du

class QuestionEmbeddingsDict( dict ):
    
    PATH_TO_DICT = os.path.join( du.get_project_root(), "src/conf/long-term-memory/solutions/question-embeddings-dictionary.pickle" )
    loading = False
    def __init__( self, *args, **kwargs ):
        
        self.update( *args, **kwargs )
        
        if os.path.exists( QuestionEmbeddingsDict.PATH_TO_DICT ):
            QuestionEmbeddingsDict.loading = True
            print( "Loading question embeddings dictionary ", end="" )
            with open( QuestionEmbeddingsDict.PATH_TO_DICT, "rb" ) as f:
                data = pickle.load( f )
                self.update( data )
            QuestionEmbeddingsDict.loading = False
            print( " Done!" )
            
    def __setitem__( self, key, value ):
        
        super().__setitem__( key, value )
        # only save if we are not loading
        if not QuestionEmbeddingsDict.loading:
            self._save()
        else:
            print( ".", end="" )
            
    # add method to delete an item
    def __delitem__( self, key ):
        
        super().__delitem__( key )
        self._save()

    def _save( self ):

        print( "Pickling question embeddings dictionary..." )
        with open( QuestionEmbeddingsDict.PATH_TO_DICT, "wb" ) as f:
            pickle.dump( self, f )