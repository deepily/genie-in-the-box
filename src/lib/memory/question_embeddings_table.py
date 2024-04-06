import lib.utils.util as du

from lib.memory.solution_snapshot  import SolutionSnapshot as ss
from lib.app.configuration_manager import ConfigurationManager
from lib.utils.util_stopwatch      import Stopwatch

import lancedb


# def singleton( cls ):
#
#     instances = { }
#
#     def wrapper( *args, **kwargs ):
#
#         if cls not in instances:
#             print( "Instantiating QuestionEmbeddingsTable() singleton...", end="\n\n" )
#             instances[ cls ] = cls( *args, **kwargs )
#         else:
#             print( "Reusing QuestionEmbeddingsTable() singleton..." )
#
#         return instances[ cls ]
#
#     return wrapper

class QuestionEmbeddingsTable():
    
    def __init__( self, debug=False, verbose=False, *args, **kwargs ):
        
        self.debug       = debug
        self.verbose     = verbose
        self._config_mgr = ConfigurationManager( env_var_name="GIB_CONFIG_MGR_CLI_ARGS" )
        
        uri = du.get_project_root() + self._config_mgr.get( "database_path_wo_root" )
        
        db = lancedb.connect( uri )
        
        self._question_embeddings_tbl = db.open_table( "question_embeddings_tbl" )
        
        print( f"Opened question_embeddings_tbl w/ [{self._question_embeddings_tbl.count_rows()}] rows" )
        
    def has( self, question ):
        """
        checks if a question exists question embeddings table.

        Parameters:
            question (str): The question to check for.

        Returns:
            bool: True if the question exists, False otherwise.
        """
        if self.debug: timer = Stopwatch( msg=f"has( '{question}' )" )
        synonyms = self._question_embeddings_tbl.search().where( f"question = '{question}'" ).limit( 1 ).select( [ "question" ] ).to_list()
        if self.debug: timer.print( "Done!", use_millis=True )
        
        return len( synonyms ) > 0
    
    def get_embedding( self, question ):
        """
        Get the embedding for the given question string.
        
        NOTE: If it's not found in the table, then it generates the embedding, but does not add it to the table.

        Parameters:
            question (str): The input question to get the embedding for.

        Returns:
            embedding: The embedding for the given question.
        """
        if self.debug: timer = Stopwatch( msg=f"get_embedding( '{question}' )", silent=True )
        rows_returned = self._question_embeddings_tbl.search().where( f"question = '{question}'" ).limit( 1 ).select( [ "embedding" ] ).to_list()
        if self.debug: timer.print( f"Done! w/ {len( rows_returned )} rows returned", use_millis=True )
        
        if not rows_returned:
            return ss.generate_embedding( question )
        else:
            return rows_returned[ 0 ][ "embedding"]
        
    def add_embedding( self, question, embedding ):
        
        new_row = [ { "question": question, "embedding": embedding } ]
        self._question_embeddings_tbl.add( new_row )
    
    # def _init_tbl( self ):
    #
    #     # question_embeddings_dict = QuestionEmbeddingsDict()
    #     # question_embeddings_dict = dict( question_embeddings_dict )
    #     #
    #     # df = pd.DataFrame(list(question_embeddings_dict.items()), columns=[ "question", "embedding" ] )
    #     # print( df.head() )
    #     # print( df.info() )
    #     # print( type( df.iloc[ 0 ][ "embedding" ][ 0 ] ) )
    #     #
    #     # df_dict = df.to_dict( orient="records")
    #
    #     self.config_mgr = ConfigurationManager( env_var_name="GIB_CONFIG_MGR_CLI_ARGS" )
    #
    #     uri = du.get_project_root() + self.config_mgr.get( "database_path_wo_root" )
    #
    #     db = lancedb.connect( uri )
    #
    #     # db.drop_table( "question_embeddings_tbl" )
    #     # import pyarrow as pa
    #     #
    #     # schema = pa.schema(
    #     #     [
    #     #         pa.field( "question", pa.string() ),
    #     #         pa.field( "embedding", pa.list_( pa.float32(), 1536 ) )
    #     #     ]
    #     # )
    #     # self.question_embeddings_tbl = db.create_table( "question_embeddings_tbl", schema=schema )
    #     # self.question_embeddings_tbl.create_fts_index( "question" )
    #     # print( f"New: Table.count_rows: {self.question_embeddings_tbl.count_rows()}" )
    #     # self.question_embeddings_tbl.add( df_dict )
    #     # print( f"New: Table.count_rows: {self.question_embeddings_tbl.count_rows()}" )
    #
    #     print( db.table_names() )
    #     self.question_embeddings_tbl = db.open_table( "question_embeddings_tbl" )
    #     du.print_banner( "Table:" )
    #     print( self.question_embeddings_tbl.head( 10 ) )
    #
    #     schema = self.question_embeddings_tbl.schema
    #
    #     du.print_banner( "Schema:" )
    #     print( schema )
    #
    #     print( f"BEFORE: Table.count_rows: {self.question_embeddings_tbl.count_rows()}" )
    #     question = "and you may ask yourself well how did I get here"
    #     embedding = ss.generate_embedding( question )
    #     print( f"'{question}': embedding length: {len( embedding )}" )
    #     new_row = [ { "question": question, "embedding": embedding } ]
    #     self.question_embeddings_tbl.add( new_row )
    #     print( f"AFTER: Table.count_rows: {self.question_embeddings_tbl.count_rows()}" )
    #
    #     # question_embeddings_tbl.create_fts_index( "question" )
    #
    #     questions = [ question ] + [ "what time is it", "well how did I get here", "what is the time", "what is the time now", "what time is it now", "what is the current time", "What day is today", "Whats todays date" ]
    #     timer = Stopwatch()
    #     for question in questions:
    #         synonyms = self.question_embeddings_tbl.search().where( f"question = '{question}'" ).limit( 1 ).select( [ "question", "embedding" ] ).to_list()
    #         du.print_banner( f"Synonyms for '{question}': {len( synonyms )} found" )
    #         for synonym in synonyms:
    #             print( f"{synonym[ 'question' ]}: embedding length: {len( synonym[ 'embedding' ] )} embedding: {synonym[ 'embedding' ][ :5 ]}" )
    #
    #     timer.print( "Search time", use_millis=True )
    #     delta_ms = timer.get_delta_ms()
    #     print( f"Average search time: {delta_ms / len( questions )} ms" )
    #
    #     # result = self.question_embeddings_tbl.search( "what time is it" ).limit( 2 ).to_pandas()
    #     # print( result )
        

if __name__ == '__main__':
    
    question_embeddings_tbl = QuestionEmbeddingsTable()
    question_1 = "what time is it"
    print( f"'{question_1}': in embeddings table [{question_embeddings_tbl.has( question_1 )}]" )
    question_2 = "well how did I get here"
    print( f"'{question_2}': in embeddings table [{question_embeddings_tbl.has( question_2 )}]" )
    
    embedding = question_embeddings_tbl.get_embedding( question_1 )
    print( f"embedding length: {len( embedding )}" )
    