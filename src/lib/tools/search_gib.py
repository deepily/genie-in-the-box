"""
This object is a wrapper for the KagiSearch object.

Purpose: provide a simple vendor-neutral interface to the KagiSearch and/or other objects.
"""

from lib.tools.search_kagi           import KagiSearch
from lib.agents.raw_output_formatter import RawOutputFormatter

import lib.utils.util as du

class GibSearch:
    
    def __init__( self, query=None, url=None, debug=False, verbose=False ):
        
        self.debug     = debug
        self.verbose   = verbose
        self.query     = query
        self.url       = url
        self._searcher = KagiSearch( query=query, url=url, debug=debug, verbose=verbose )
        self._results  = None
    
    def search_and_summarize_the_web( self ):
        
        self._results = self._searcher.search_fastgpt()
        
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
    
    query   = "What's the temperature in Washington DC?"
    search  = GibSearch( query=query )
    search.search_and_summarize_the_web()
    results = search.get_results( scope="summary" )
    meta    = search.get_results( scope="meta" )
    
    print( results )
    
    formatter = RawOutputFormatter( query, results, routing_command="agent router go to weather", debug=False, verbose=False )
    output    = formatter.format_output()
    print( output )
    
    