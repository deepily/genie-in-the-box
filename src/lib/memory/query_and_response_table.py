import lib.utils.util               as du

from lib.memory.solution_snapshot  import SolutionSnapshot as ss
from lib.app.configuration_manager import ConfigurationManager
from lib.utils.util_stopwatch      import Stopwatch

import lancedb
class QueryAndResponseTable():
    
    def __init__( self, debug=False, verbose=False, *args, **kwargs ):
        
        self.debug       = debug
        self.verbose     = verbose
        self._config_mgr = ConfigurationManager( env_var_name="GIB_CONFIG_MGR_CLI_ARGS" )
        
        uri = du.get_project_root() + self._config_mgr.get( "database_path_wo_root" )
        
        self.db = lancedb.connect( uri )
        
        self._query_and_response_tbl = self.db.open_table( "query_and_response_tbl" )

        # print( f"Opened query_and_response_tbl w/ [{self._query_and_response_tbl.count_rows()}] rows" )
        #
        # du.print_banner( "Table:" )
        # print( self.query_and_response_tbl.head( 10 ) )
    
    def insert_row( self, date=du.get_current_date(), time=du.get_current_time(), query="", query_embedding=[], response_raw="", response_raw_embedding=[], response_conversational="", response_conversational_embedding=[], solution_path_wo_root=None ):
        
        timer = Stopwatch( msg="insert_row() called..." )
        new_row = [ {
            "date"                             : date,
            "time"                             : time,
            "query"                            : query,
            "query_embedding"                  : query_embedding if query_embedding else ss.generate_embedding( query ),
            "response_raw"                     : response_raw,
            "response_raw_embedding"           : response_raw_embedding if response_raw_embedding else ss.generate_embedding( response_raw ),
            "response_conversational"          : response_conversational,
            "response_conversational_embedding": response_conversational_embedding if response_conversational_embedding else ss.generate_embedding( response_conversational ),
            "solution_path_wo_root"            : solution_path_wo_root
        } ]
        self.query_and_response_tbl.add( new_row )
        timer.print( "Done!", use_millis=True )
    
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
        self.query_and_response_tbl = self.db.create_table( "query_and_response_tbl", schema=schema, mode="overwrite" )
        self.query_and_response_tbl.create_fts_index( "query", replace=True )
        self.query_and_response_tbl.create_fts_index( "date", replace=True )
        self.query_and_response_tbl.create_fts_index( "time", replace=True )
        # self.query_and_response_tbl.create_fts_index( "response_conversational" )
        print( f"New: Table.count_rows: {self.query_and_response_tbl.count_rows()}" )
        # self.query_and_response_tbl.add( df_dict )
        # print( f"New: Table.count_rows: {self.query_and_response_tbl.count_rows()}" )
        
        du.print_banner( "Tables:" )
        print( self.db.table_names() )
        # du.print_banner( "Table:" )
        # print( self.query_and_response_tbl.head( 10 ) )
        #
        # schema = self.query_and_response_tbl.schema
        #
        # du.print_banner( "Schema:" )
        # print( schema )

        print( f"BEFORE: Table.count_rows: {self.query_and_response_tbl.count_rows()}" )
        query = "you may ask yourself well how did I get here"
        response_raw = "Same as it ever was, same as it ever was. Same as it ever was, same as it ever was. Same as it ever was, same as it ever was. Same as it ever was, same as it ever was."
        response_conversational = "Same as it ever was"
        self.insert_row( query=query, response_raw=response_raw, response_conversational=response_conversational )
        print( f"AFTER: Table.count_rows: {self.query_and_response_tbl.count_rows()}" )
        
        querys = [ query ] + [ "what time is it", "well how did I get here" ]
        timer = Stopwatch()
        for query in querys:
            results = self.query_and_response_tbl.search().where( f"query = '{query}'" ).limit( 1 ).select( [ "date", "time", "query", "response_conversational", "response_raw" ] ).to_list()
            du.print_banner( f"Synonyms for '{query}': {len( results )} found" )
            for result in results:
                print( f"Date: [{result[ 'date' ]}], Time: [{result[ 'time' ]}], Query: [{result[ 'query' ]}], Response: [{result[ 'response_conversational' ]}] Raw: [{result[ 'response_raw' ]}]" )

        timer.print( "Search time", use_millis=True )
        delta_ms = timer.get_delta_ms()
        print( f"Average search time: {delta_ms / len( querys )} ms" )

        # result = self.query_and_response_tbl.search( "what time is it" ).limit( 2 ).to_pandas()
        # print( result )
        
if __name__ == '__main__':
    
    query_and_response_tbl = QueryAndResponseTable( debug=True)
    # query_and_response_tbl.init_tbl()
    # query_1 = "what time is it"
    # print( f"'{query_1}': in embeddings table [{query_and_response_tbl.is_in( query_1 )}]" )
    # query_2 = "you may ask yourself well how did I get here"
    # print( f"'{query_2}': in embeddings table [{query_and_response_tbl.is_in( query_2 )}]" )