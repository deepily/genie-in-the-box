import lib.utils.util               as du

from lib.memory.question_embeddings_table import QuestionEmbeddingsTable
from lib.memory.solution_snapshot         import SolutionSnapshot as ss
from lib.app.configuration_manager        import ConfigurationManager
from lib.utils.util_stopwatch             import Stopwatch

import lancedb


# def singleton( cls ):
#
#     instances = { }
#
#     def wrapper( *args, **kwargs ):
#
#         if cls not in instances:
#             print( "Instantiating QueryAndResponseTable() singleton...", end="\n\n" )
#             instances[ cls ] = cls( *args, **kwargs )
#         else:
#             print( "Reusing QueryAndResponseTable() singleton..." )
#
#         return instances[ cls ]
#
#     return wrapper


# @singleton
class InputAndOutputTable():
    
    def __init__( self, debug=False, verbose=False ):
        
        self.debug       = debug
        self.verbose     = verbose
        self._config_mgr = ConfigurationManager( env_var_name="GIB_CONFIG_MGR_CLI_ARGS" )
        
        self.db = lancedb.connect( du.get_project_root() + self._config_mgr.get( "database_path_wo_root" ) )
        self._input_and_output_tbl    = self.db.open_table( "input_and_output_tbl" )
        self._question_embeddings_tbl = QuestionEmbeddingsTable( debug=self.debug, verbose=self.verbose )

        print( f"Opened input_and_output_tbl w/ [{self._input_and_output_tbl.count_rows()}] rows" )

        # if self.debug and self.verbose:
        #     du.print_banner( "Tables:" )
        #     print( self.db.table_names() )
        #     du.print_banner( "Table:" )
        #     print( self._input_and_output_tbl.select( [ "date", "time", "input", "output_final" ] ).head( 10 ) )
        
    def insert_io_row( self, date=du.get_current_date(), time=du.get_current_time( include_timezone=False ),
        input_type="", input="", input_embedding=[], output_raw="", output_final="", output_final_embedding=[], solution_path_wo_root=None
    ):
        
        # ¡OJO! The embeddings are optional. If not provided, they will be generated.
        # In this case the only embedding that we are cashing is the one that corresponds to the query/input, otherwise known
        # as the 'question' in the solution snapshot object and the 'query' in the self._question_embeddings_tbl object.
        # TODO: Make consistent the use of the terms 'input', 'query' and 'question'. While they are synonymous that's not necessarily clear to the casual reader.
        timer = Stopwatch( msg=f"insert_io_row( '{input[ :64 ]}...' )", silent=True )
        new_row = [ {
            "date"                             : date,
            "time"                             : time,
            "input_type"                       : input_type,
            "input"                            : input,
            # "input"                            : ss.remove_non_alphabetics( input ),
            "input_embedding"                  : input_embedding if input_embedding else self._question_embeddings_tbl.get_embedding( input ),
            # "input_embedding"                  : input_embedding if input_embedding else self._question_embeddings_tbl.get_embedding( ss.remove_non_alphabetics( input ) ),
            "output_raw"                       : output_raw,
            "output_final"                     : output_final,
            "output_final_embedding"           : output_final_embedding if output_final_embedding else ss.generate_embedding( output_final ),
            "solution_path_wo_root"            : solution_path_wo_root
        } ]
        self._input_and_output_tbl.add( new_row )
        timer.print( "Done! I/O table now has {self._input_and_output_tbl.count_rows()} rows", use_millis=True, end="\n" )
        
    def get_knn_by_input( self, search_terms, k=10 ):
        
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
    
    def get_all_io( self, max_rows=1000 ):
        
        timer = Stopwatch( msg=f"get_all_io( max_rows={max_rows} ) called..." )
        
        results = self._input_and_output_tbl.search().select( [ "date", "time", "input_type", "input", "output_final" ] ).limit( max_rows ).to_list()
        row_count = len( results )
        timer.print( f"Done! Returning [{row_count}] rows", use_millis=True )
        
        if row_count == max_rows:
            print( f"WARNING: Only returning [{max_rows}] rows out of [{self._input_and_output_tbl.count_rows()}]. Increase max_rows to see more data." )
        
        return results
    
    def get_io_stats_by_input_type( self, max_rows=1000 ):
        
        timer = Stopwatch( msg=f"get_io_stats_by_input_type( max_rows={max_rows} ) called..." )
        
        stats_df = self._input_and_output_tbl.search().select( [ "input_type" ] ).limit( max_rows ).to_pandas()
        row_count = len( stats_df )
        timer.print( f"Done! Returning [{row_count}] rows for summarization", use_millis=True )
        if row_count == max_rows:
            print( f"WARNING: Only returning [{max_rows}] rows out of [{self._input_and_output_tbl.count_rows()}]. Increase max_rows to see more data." )
        
        # Add a count column to the dataframe, which will be used to summarize the data
        stats_df[ "count" ] = stats_df.groupby( [ "input_type" ] )[ "input_type" ].transform( "count" )
        # Create a dictionary from the dataframe, setting the input_type as the index (key) and the count column as the value
        stats_dict = stats_df.set_index( 'input_type' )[ 'count' ].to_dict()
        
        return stats_dict
    
    # Method to bitch all input an output where input_type starts with "go to agent"
    def get_all_qnr( self, max_rows=1000 ):
        
        timer = Stopwatch( msg=f"get_all_qnr( max_rows={max_rows} ) called..." )
        
        where_clause = "input_type LIKE 'agent router go to %'"
        results = self._input_and_output_tbl.search().where( where_clause ).limit( max_rows ).select(
            [ "date", "time", "input_type", "input", "output_final" ]
        ).to_list()
        
        row_count = len( results )
        timer.print( f"Done! Returning [{row_count}] rows of QnR", use_millis=True )
        if row_count == max_rows:
            print( f"WARNING: Only returning [{max_rows}] rows. Increase max_rows to see more data." )
        
        return results
    
    def init_tbl( self ):
        
        du.print_banner( "Tables:" )
        print( self.db.table_names() )
        
        # self.db.drop_table( "input_and_output_tbl" )
        import pyarrow as pa

        schema = pa.schema(
            [
                pa.field( "date",                     pa.string() ),
                pa.field( "time",                     pa.string() ),
                pa.field( "input_type",               pa.string() ),
                pa.field( "input",                    pa.string() ),
                pa.field( "input_embedding",          pa.list_( pa.float32(), 1536 ) ),
                pa.field( "output_raw",               pa.string() ),
                pa.field( "output_final",             pa.string() ),
                pa.field( "output_final_embedding",   pa.list_( pa.float32(), 1536 ) ),
                pa.field( "solution_path_wo_root",    pa.string() ),
            ]
        )
        self._input_and_output_tbl = self.db.create_table( "input_and_output_tbl", schema=schema, mode="overwrite" )
        self._input_and_output_tbl.create_fts_index( "input", replace=True )
        self._input_and_output_tbl.create_fts_index( "input_type", replace=True )
        self._input_and_output_tbl.create_fts_index( "date", replace=True )
        self._input_and_output_tbl.create_fts_index( "time", replace=True )
        self._input_and_output_tbl.create_fts_index( "output_final", replace=True )
        
        # self._query_and_response_tbl.add( df_dict )
        # print( f"New: Table.count_rows: {self._query_and_response_tbl.count_rows()}" )
        
        # du.print_banner( "Tables:" )
        # print( self.db.table_names() )
        
        # schema = self._query_and_response_tbl.schema
        #
        # du.print_banner( "Schema:" )
        # print( schema )

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
    io_tbl = InputAndOutputTable( debug=True )
    qnr = io_tbl.get_all_qnr( max_rows=100 )
    # qnr = io_tbl.get_all_io( max_rows=100 )
    for row in qnr:
        print( row[ "date" ], row[ "time" ], row[ "input_type" ], row[ "input" ], row[ "output_final" ] )
    
    # query_and_response_tbl.init_tbl()
    # results = query_and_response_tbl.get_knn_by_input( "what time is it", k=5 )
    # for row in results:
    #     print( row[ "input" ], row[ "output_final" ], row[ "_distance" ] )
    
    # stats_dict = io_tbl.get_io_stats_by_input_type()
    # for k, v in stats_dict.items():
    #     print( f"input_type: [{k}] called [{v}] times" )
    