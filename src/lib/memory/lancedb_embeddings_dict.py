import os
import pickle

import lib.utils.util as du

import lancedb
import pandas as pd

from lib.memory.question_embeddings_dict import QuestionEmbeddingsDict

class LanceDbQuestionEmbeddingsDict():
    
    def __init__( self, *args, **kwargs ):
        
        # question_embeddings_dict = QuestionEmbeddingsDict()
        # print( type( question_embeddings_dict ) )
        # question_embeddings_dict = dict( question_embeddings_dict )
        # print( type( question_embeddings_dict ) )
        #
        # # The first five keys in the first 24 items and then beddings
        # for key in list( question_embeddings_dict.keys() )[ 0:5 ]:
        #     print( key, question_embeddings_dict[ key ][ 0:24 ] )
        #
        # df = pd.DataFrame(list(question_embeddings_dict.items()), columns=[ "question", "embedding" ] )
        # print( df.head() )
        #
        # df_dict = df.to_dict( orient="records")
        # print( df_dict[ 0 ] )
        
        uri = os.path.join( du.get_project_root(), "src/conf/long-term-memory/gib.lancedb" )
        db = lancedb.connect( uri )
        # self.question_embeddings_tbl = db.create_table( "question_embeddings", data=df_dict )
        
        print( db.table_names() )
        question_embeddings_tbl = db.open_table( "question_embeddings" )
        print( question_embeddings_tbl.head() )
        
        # question_embeddings_tbl.create_fts_index( "question" )
        
        synonyms = question_embeddings_tbl.search( "what time is it", vector_column_name="embedding" ).limit( 10 ).select( [ "question" ] ).to_list()
        for synonym in synonyms:
            print( synonym )
        
        # print( tbl )
        # tbl.create_fts_index( [ '<field_names>' ] )
        #
        # result = tbl.search( "what time is it" ).limit( 2 ).to_pandas()
        # print( result )
        

if __name__ == '__main__':
    
    lance_db_question_embeddings_dict = LanceDbQuestionEmbeddingsDict()
    
    # # question_embeddings_dict = QuestionEmbeddingsDict()
    # PATH_TO_DICT = os.path.join( du.get_project_root(), "src/conf/long-term-memory/question-embeddings-dictionary.pickle" )
    #
    # with open( PATH_TO_DICT, "rb" ) as f:
    #     question_embeddings_dict = pickle.load( f )
    #
    # print( type( question_embeddings_dict ) )
    # question_embeddings_dict = dict( question_embeddings_dict )
    # print( type( question_embeddings_dict ) )
    #
    # print( len( question_embeddings_dict ) )
    #
    # # The first five keys in the first 24 items and then beddings
    # for key in list( question_embeddings_dict.keys() )[ 0:5 ]:
    #     print( key, question_embeddings_dict[ key ][ 0:24 ] )