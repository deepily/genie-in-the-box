from lib.tools.search_kagi import KagiSearch

import lib.utils.util as du

class SearchGib:
    
    def __init__( self, query=None ):
        
        self.query    = query
        self._kagi    = KagiSearch( query=query )
        self._results = None
    
    def search( self ):
        
        self._results = self._kagi.search_fastgpt()
        
    def get_results( self, scope="all" ):
        
        if scope == "all":
            return self._results
        elif scope == "meta":
            return self._results[ "meta" ]
        elif scope == "data":
            return self._results[ "data" ]
        elif scope == "summary":
            return self._results[ "data" ][ "output" ]
        elif scope == "references":
            return self._results[ "data" ][ "references" ]
        else:
            du.print_banner( f"ERROR: Invalid scope: {scope}.  Must be { 'all', 'meta', 'data', 'summary', 'references' }", expletive=True )
            return None
        
if __name__ == '__main__':
    
    query   = "What's the current temperature in Washington DC?"
    search  = SearchGib( query=query )
    search.search()
    results = search.get_results( scope="summary" )
    
    print( results )