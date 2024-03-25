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
class QueryAndResponseTable():
    
    def __init__( self, debug=False, verbose=False, *args, **kwargs ):
        
        self.debug       = debug
        self.verbose     = verbose
        self._config_mgr = ConfigurationManager( env_var_name="GIB_CONFIG_MGR_CLI_ARGS" )
        
        uri = du.get_project_root() + self._config_mgr.get( "database_path_wo_root" )
        
        self.db = lancedb.connect( uri )
        
        self._query_and_response_tbl  = self.db.open_table( "query_and_response_tbl" )
        self._question_embeddings_tbl = QuestionEmbeddingsTable( debug=self.debug, verbose=self.verbose )

        print( f"Opened query_and_response_tbl w/ [{self._query_and_response_tbl.count_rows()}] rows" )

        if self.debug and self.verbose:
            du.print_banner( "Tables:" )
            print( self.db.table_names() )
            du.print_banner( "Table:" )
            print( self._query_and_response_tbl.head( 10 ) )
        
    def insert_row( self, date=du.get_current_date(), time=du.get_current_time( include_timezone=False), query="", query_embedding=[], response_raw="", response_raw_embedding=[], response_conversational="", response_conversational_embedding=[], solution_path_wo_root=None ):
        
        # ¡OJO! The embeddings are optional. If not provided, they will be generated.
        # In this case the only embedding that we are cashing is the one that corresponds to the query, otherwise known
        # as the 'question' in the solution snapshot object and the 'query' in the self._question_embeddings_tbl object.
        timer = Stopwatch( msg="insert_row() called..." )
        new_row = [ {
            "date"                             : date,
            "time"                             : time,
            "query"                            : query,
            "query_embedding"                  : query_embedding if query_embedding else self._question_embeddings_tbl.get_embedding( query ),
            "response_raw"                     : response_raw,
            "response_raw_embedding"           : response_raw_embedding if response_raw_embedding else ss.generate_embedding( response_raw ),
            "response_conversational"          : response_conversational,
            "response_conversational_embedding": response_conversational_embedding if response_conversational_embedding else ss.generate_embedding( response_conversational ),
            "solution_path_wo_root"            : solution_path_wo_root
        } ]
        self._query_and_response_tbl.add( new_row )
        timer.print( "Done!", use_millis=True )
    
    def get_knn_by_query( self, search_terms, k=5 ):
        
        timer = Stopwatch( msg="get_knn_by_query() called..." )
        
        # First, convert the search_terms string into an embedding. The embedding table caches all question embeddings
        search_terms_embedding = self._question_embeddings_tbl.get_embedding( search_terms )
        
        knn = self._query_and_response_tbl.search(
            search_terms_embedding, vector_column_name="query_embedding"
        ).metric( "dot" ).limit( k ).select( [ "query", "response_conversational" ] ).to_list()
        timer.print( "Done!", use_millis=True )
        
        if self.debug and self.verbose:
            # Compare the embeddings for the search_terms and for the query_embedding fields
            for i in range( 32 ):
                print( knn[ 0 ][ "query_embedding" ][ i ] == search_terms_embedding[ i ], knn[ 0 ][ "query_embedding" ][ i ], search_terms_embedding[ i ] )
    
            # Are the search term embeddings and the query embeddings equal?
            print( 'knn[ 0 ][ "query_embedding" ] == search_terms_embedding:', knn[ 0 ][ "query_embedding" ] == search_terms_embedding )
        
        return knn
    def init_tbl( self ):

        self.db.drop_table( "query_and_response_tbl" )
        import pyarrow as pa

        schema = pa.schema(
            [
                pa.field( "date",                              pa.string() ),
                pa.field( "time",                              pa.string() ),
                pa.field( "query",                             pa.string() ),
                pa.field( "query_embedding",                   pa.list_( pa.float32(), 1536 ) ),
                pa.field( "response_raw",                      pa.string() ),
                pa.field( "response_raw_embedding",            pa.list_( pa.float32(), 1536 ) ),
                pa.field( "response_conversational",           pa.string() ),
                pa.field( "response_conversational_embedding", pa.list_( pa.float32(), 1536 ) ),
                pa.field( "solution_path_wo_root",             pa.string() ),
            ]
        )
        self._query_and_response_tbl = self.db.create_table( "query_and_response_tbl", schema=schema, mode="overwrite" )
        self._query_and_response_tbl.create_fts_index( "query", replace=True )
        self._query_and_response_tbl.create_fts_index( "date", replace=True )
        self._query_and_response_tbl.create_fts_index( "time", replace=True )
        # self._query_and_response_tbl.create_fts_index( "response_conversational" )
        print( f"New: Table.count_rows: {self._query_and_response_tbl.count_rows()}" )
        # self._query_and_response_tbl.add( df_dict )
        # print( f"New: Table.count_rows: {self._query_and_response_tbl.count_rows()}" )
        
        # du.print_banner( "Tables:" )
        # print( self.db.table_names() )
        # schema = self._query_and_response_tbl.schema
        #
        # du.print_banner( "Schema:" )
        # print( schema )

        print( f"BEFORE: Table.count_rows: {self._query_and_response_tbl.count_rows()}" )
        query = "you may ask yourself well how did I get here"
        response_raw = "Same as it ever was, same as it ever was. Same as it ever was, same as it ever was. Same as it ever was, same as it ever was. Same as it ever was, same as it ever was."
        response_conversational = "Same as it ever was"
        self.insert_row( query=query, response_raw=response_raw, response_conversational=response_conversational )
        
        query = "what time is it"
        response_raw = "14:45:00 EST"
        response_conversational = "It's 2:45 PM EST."
        self.insert_row( query=query, response_raw=response_raw, response_conversational=response_conversational )
        
        query = "what day is today"
        response_raw = "03/25/2024"
        response_conversational = "Today is March 25th, 2024."
        self.insert_row( query=query, response_raw=response_raw, response_conversational=response_conversational )
        
        print( f"AFTER: Table.count_rows: {self._query_and_response_tbl.count_rows()}" )
        
        # querys = [ query ] + [ "what time is it", "what day is today", "well how did I get here" ]
        # timer = Stopwatch()
        # for query in querys:
        #     results = self._query_and_response_tbl.search().where( f"query = '{query}'" ).limit( 1 ).select( [ "date", "time", "query", "response_conversational", "response_raw" ] ).to_list()
        #     du.print_banner( f"Synonyms for '{query}': {len( results )} found" )
        #     for result in results:
        #         print( f"Date: [{result[ 'date' ]}], Time: [{result[ 'time' ]}], Query: [{result[ 'query' ]}], Response: [{result[ 'response_conversational' ]}] Raw: [{result[ 'response_raw' ]}]" )
        #
        # timer.print( "Search time", use_millis=True )
        # delta_ms = timer.get_delta_ms()
        # print( f"Average search time: {delta_ms / len( querys )} ms" )
        
if __name__ == '__main__':
    
    import numpy as np
    foo = ss.generate_embedding( "what time is it" )
    print( "Sum of foo", np.sum( foo ) )
    print( "dot product of foo and foo", np.dot( foo, foo ) * 100 )
    
    query_and_response_tbl = QueryAndResponseTable( debug=True )
    # query_and_response_tbl.init_tbl()
    results = query_and_response_tbl.get_knn_by_query( "what time is it", k=5 )

    for row in results:
        print( row[ "query" ], row[ "response_conversational" ], row[ "_distance" ] )
    
    # query_and_response_tbl.init_tbl()
    # query_1 = "what time is it"
    # print( f"'{query_1}': in embeddings table [{query_and_response_tbl.is_in( query_1 )}]" )
    # query_2 = "you may ask yourself well how did I get here"
    # print( f"'{query_2}': in embeddings table [{query_and_response_tbl.is_in( query_2 )}]" )