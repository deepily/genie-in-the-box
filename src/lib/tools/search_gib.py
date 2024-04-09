"""
This object is a wrapper for the KagiSearch object.

Purpose: provide a simple vendor-neutral interface to the KagiSearch object.
"""

from lib.tools.search_kagi           import KagiSearch
from lib.agents.raw_output_formatter import RawOutputFormatter

import lib.utils.util as du

class GibSearch:
    
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
    search  = GibSearch( query=query )
    search.search()
    results = search.get_results( scope="summary" )
    meta    = search.get_results( scope="meta" )
    
    print( results )
    
    formatter = RawOutputFormatter( query, results, routing_command="agent router go to weather", debug=False, verbose=False )
    output    = formatter.format_output()
    print( output )
    
    