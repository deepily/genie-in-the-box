import os
import pickle

import lib.utils.util as du

class QuestionEmbeddingsDict( dict ):
    
    PATH_TO_DICT = os.path.join( du.get_project_root(), "src/conf/long-term-memory/question-embeddings-dictionary.pickle" )
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
            
        else:
            print( "No question embeddings dictionary found" )
            
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
        # Set pickled file rights to world readable/writable
        os.chmod( QuestionEmbeddingsDict.PATH_TO_DICT, 0o666 )
        
        
if __name__ == '__main__':
    
    # question_embeddings_dict = QuestionEmbeddingsDict()
    PATH_TO_DICT = os.path.join( du.get_project_root(), "src/conf/long-term-memory/question-embeddings-dictionary.pickle" )
    question_embeddings_dict = None
    with open( PATH_TO_DICT, "rb" ) as f:
        question_embeddings_dict = pickle.load( f )
    print( type( question_embeddings_dict ) )
    question_embeddings_dict = dict( question_embeddings_dict )
    print( type( question_embeddings_dict ) )
    print( len( question_embeddings_dict ) )