import lib.utils.util               as du

from lib.memory.question_embeddings_table import QuestionEmbeddingsTable
from lib.memory.solution_snapshot         import SolutionSnapshot as ss
from lib.app.configuration_manager        import ConfigurationManager
from lib.utils.util_stopwatch             import Stopwatch

import lancedb


def singleton( cls ):
    
    instances = { }
    
    def wrapper( *args, **kwargs ):
        
        if cls not in instances:
            print( "Instantiating QueryAndResponseTable() singleton...", end="\n\n" )
            instances[ cls ] = cls( *args, **kwargs )
        else:
            print( "Reusing QueryAndResponseTable() singleton..." )
        
        return instances[ cls ]
    
    return wrapper


@singleton
class InputAndOutputTable():
    
    def __init__( self, debug=False, verbose=False ):
        
        self.debug       = debug
        self.verbose     = verbose
        self._config_mgr = ConfigurationManager( env_var_name="GIB_CONFIG_MGR_CLI_ARGS" )
        
        self.db = lancedb.connect( du.get_project_root() + self._config_mgr.get( "database_path_wo_root" ) )
        
        self._input_and_output_tbl    = self.db.open_table( "input_and_output_tbl" )
        self._question_embeddings_tbl = QuestionEmbeddingsTable( debug=self.debug, verbose=self.verbose )

        print( f"Opened _input_and_output_tbl w/ [{self._input_and_output_tbl.count_rows()}] rows" )

        if self.debug and self.verbose:
            du.print_banner( "Tables:" )
            print( self.db.table_names() )
            du.print_banner( "Table:" )
            print( self._input_and_output_tbl.select( [ "date", "time", "input", "output_final" ] ).head( 10 ) )
        
    def insert_io_row( self, date=du.get_current_date(), time=du.get_current_time( include_timezone=False ), input_type="", input="", input_embedding=[], output_raw="", output_raw_embedding=[], output_final="", output_final_embedding=[], solution_path_wo_root=None ):
        
        # ¡OJO! The embeddings are optional. If not provided, they will be generated.
        # In this case the only embedding that we are cashing is the one that corresponds to the query/input, otherwise known
        # as the 'question' in the solution snapshot object and the 'query' in the self._question_embeddings_tbl object.
        # TODO: Make consistent the use of the terms 'input', 'query' and 'question'. While they are synonymous that's not necessarily clear to the casual reader.
        timer = Stopwatch( msg="insert_io_row() called..." )
        new_row = [ {
            "date"                             : date,
            "time"                             : time,
            "input_type"                       : input_type,
            "input"                            : ss.remove_non_alphabetics( input ),
            "input_embedding"                  : input_embedding if input_embedding else self._question_embeddings_tbl.get_embedding( ss.remove_non_alphabetics( input ) ),
            "output_raw"                       : output_raw,
            "output_raw_embedding"             : output_raw_embedding if output_raw_embedding else ss.generate_embedding( output_raw ),
            "output_final"                     : output_final,
            "output_final_embedding"           : output_final_embedding if output_final_embedding else ss.generate_embedding( output_final ),
            "solution_path_wo_root"            : solution_path_wo_root
        } ]
        self._input_and_output_tbl.add( new_row )
        timer.print( "Done!", use_millis=True )
    
    def get_knn_by_input( self, search_terms, k=5 ):
        
        timer = Stopwatch( msg="get_knn_by_input() called..." )
        
        # First, convert the search_terms string into an embedding. The embedding table caches all question embeddings
        search_terms_embedding = self._question_embeddings_tbl.get_embedding( search_terms )
        
        knn = self._input_and_output_tbl.search(
            search_terms_embedding, vector_column_name="input_embedding"
        ).metric( "dot" ).limit( k ).select( [ "input", "output_final" ] ).to_list()
        timer.print( "Done!", use_millis=True )
        
        if self.debug and self.verbose:
            # Compare the embeddings for the search_terms and for the query_embedding fields
            for i in range( 32 ):
                print( knn[ 0 ][ "input_embedding" ][ i ] == search_terms_embedding[ i ], knn[ 0 ][ "input_embedding" ][ i ], search_terms_embedding[ i ] )
    
            # Are the search term embeddings and the query embeddings equal?
            print( 'knn[ 0 ][ "input_embedding" ] == search_terms_embedding:', knn[ 0 ][ "input_embedding" ] == search_terms_embedding )
        
        return knn
    
    def get_all_qna_pairs( self ):
        
        timer = Stopwatch( msg="get_all_qna_pairs() called..." )
        
        results = self._input_and_output_tbl.search().select( [ "input", "output_final" ] ).to_list()
        timer.print( "Done!", use_millis=True )
        
        return results
    
    def init_tbl( self ):

        self.db.drop_table( "input_and_output_tbl" )
        import pyarrow as pa

        schema = pa.schema(
            [
                pa.field( "date",                              pa.string() ),
                pa.field( "time",                              pa.string() ),
                pa.field( "input_type",                        pa.string() ),
                pa.field( "input",                             pa.string() ),
                pa.field( "input_embedding",                   pa.list_( pa.float32(), 1536 ) ),
                pa.field( "output_raw",                        pa.string() ),
                pa.field( "output_raw_embedding",              pa.list_( pa.float32(), 1536 ) ),
                pa.field( "output_final",                      pa.string() ),
                pa.field( "output_final_embedding", pa.list_( pa.float32(), 1536 ) ),
                pa.field( "solution_path_wo_root",             pa.string() ),
            ]
        )
        self._input_and_output_tbl = self.db.create_table( "input_and_output_tbl", schema=schema, mode="overwrite" )
        self._input_and_output_tbl.create_fts_index( "input", replace=True )
        self._input_and_output_tbl.create_fts_index( "input_type", replace=True )
        self._input_and_output_tbl.create_fts_index( "date", replace=True )
        self._input_and_output_tbl.create_fts_index( "time", replace=True )
        self._input_and_output_tbl.create_fts_index( "output_final", replace=True )
        print( f"New: Table.count_rows: {self._input_and_output_tbl.count_rows()}" )
        # self._query_and_response_tbl.add( df_dict )
        # print( f"New: Table.count_rows: {self._query_and_response_tbl.count_rows()}" )
        
        # du.print_banner( "Tables:" )
        # print( self.db.table_names() )
        # schema = self._query_and_response_tbl.schema
        #
        # du.print_banner( "Schema:" )
        # print( schema )

        # print( f"BEFORE: Table.count_rows: {self._input_and_output_tbl.count_rows()}" )
        # query = "you may ask yourself well how did I get here"
        # response_raw = "Same as it ever was, same as it ever was. Same as it ever was, same as it ever was. Same as it ever was, same as it ever was. Same as it ever was, same as it ever was."
        # response_conversational = "Same as it ever was"
        # self.insert_io_row( input=query, output_raw=response_raw, output_final=response_conversational )
        
        query = "what time is it"
        response_raw = "14:45:00 EST"
        response_conversational = "It's 2:45 PM EST."
        self.insert_io_row( input=query, output_raw=response_raw, output_final=response_conversational )
        
        query = "what day is today"
        response_raw = "03/25/2024"
        response_conversational = "Today is March 25th, 2024."
        self.insert_io_row( input=query, output_raw=response_raw, output_final=response_conversational )
        
        print( f"AFTER: Table.count_rows: {self._input_and_output_tbl.count_rows()}" )
        
        # querys = [ query ] + [ "what time is it", "what day is today", "well how did I get here" ]
        # timer = Stopwatch()
        # for query in querys:
        #     results = self._query_and_response_tbl.search().where( f"query = '{query}'" ).limit( 1 ).select( [ "date", "time", "input", "output_final", "output_raw" ] ).to_list()
        #     du.print_banner( f"Synonyms for '{query}': {len( results )} found" )
        #     for result in results:
        #         print( f"Date: [{result[ 'date' ]}], Time: [{result[ 'time' ]}], Query: [{result[ 'query' ]}], Response: [{result[ 'response_conversational' ]}] Raw: [{result[ 'response_raw' ]}]" )
        #
        # timer.print( "Search time", use_millis=True )
        # delta_ms = timer.get_delta_ms()
        # print( f"Average search time: {delta_ms / len( querys )} ms" )
        
if __name__ == '__main__':
    
    # import numpy as np
    # foo = ss.generate_embedding( "what time is it" )
    # print( "Sum of foo", np.sum( foo ) )
    # print( "dot product of foo and foo", np.dot( foo, foo ) * 100 )
    #
    query_and_response_tbl = InputAndOutputTable( debug=True )
    # query_and_response_tbl.init_tbl()
    # results = query_and_response_tbl.get_knn_by_input( "what time is it", k=5 )
    # for row in results:
    #     print( row[ "input" ], row[ "output_final" ], row[ "_distance" ] )
    results = query_and_response_tbl.get_all_qna_pairs()
    for row in results:
        print( row[ "input" ], "=", row[ "output_final" ] )
    
    # query_and_response_tbl.init_tbl()
    # query_1 = "what time is it"
    # print( f"'{query_1}': in embeddings table [{query_and_response_tbl.is_in( query_1 )}]" )
    # query_2 = "you may ask yourself well how did I get here"
    # print( f"'{query_2}': in embeddings table [{query_and_response_tbl.is_in( query_2 )}]" )