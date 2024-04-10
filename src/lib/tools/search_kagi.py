from kagiapi import KagiClient
# import requests

import lib.utils.util as du

from lib.utils.util_stopwatch import Stopwatch

class KagiSearch:
    
    def __init__( self, query=None, url=None, debug=False, verbose=False ):
        
        self.debug    = debug
        self.verbose  = verbose
        self.query    = query
        self.url      = url
        self._key     = du.get_api_key( "kagi" )
        self._kagi    = KagiClient( du.get_api_key( "kagi" ) )
        
    # def search_fastgpt_req( self ):
    #
    #     base_url = 'https://kagi.com/api/v0/fastgpt'
    #     data = {
    #         "query": self.query,
    #     }
    #     headers = { 'Authorization': f'Bot {self._key}' }
    #
    #     timer = Stopwatch( "Kagi FastGPT: via requests.post" )
    #     response = requests.post( base_url, headers=headers, json=data )
    #     timer.print( "Done!", use_millis=True)
    #
    #     return response.json()
    
    def search_fastgpt( self ):
        
        timer    = Stopwatch( f"Kagi FastGPT query: [{self.query}]" )
        response = self._kagi.fastgpt( query=self.query )
        timer.print( "Done!", use_millis=True )
        
        return response
    
    # def get_summary_req( self ):
    #
    #     import requests
    #
    #     base_url = 'https://kagi.com/api/v0/summarize'
    #     params = {
    #         "url"         : self.url,
    #         "summary_type": "summary",
    #         "engine"      : "agnes"
    #     }
    #     headers = { 'Authorization': f'Bot {self._key}' }
    #
    #     timer = Stopwatch( "Kagi: Summary: Request" )
    #     response = requests.get( base_url, headers=headers, params=params )
    #     timer.print( "Done!", use_millis=True )
    #
    #     return response.json()
    
    def get_summary( self ):
        
        timer = Stopwatch( "Kagi: Summarize" )
        if self.debug: print( f"Kagi: Summarize: URL: [{self.url}]" )
        response = self._kagi.summarize( url=self.url, engine="agnes", summary_type="summary" )
        timer.print( "Done!", use_millis=True )
        
        return response
    
if __name__ == '__main__':
    
    # url  = "https://weather.com/weather/tenday/l/Washington+DC?canonicalCityId=4c0ca6d01716c299f53606df83d99d5eb96b2ee0efbe3cd15d35ddd29dee93b2"
    # kagi = KagiSearch( url=url )
    
    # summary = kagi.get_summary_req()
    # # summary = kagi.get_summary()
    # du.print_banner( "Kagi: Summary: Meta" )
    # print( summary[ "meta" ] )
    # du.print_banner( "Kagi: Summary: Data" )
    # print( summary[ "data" ] )
    
    date     = du.get_current_date()
    time     = du.get_current_time()
    
    question = "The current date and time is {date} at {time}. What's the current temperature in Washington DC?"
    # question = "What's the weather forecast for Washington DC?"
    # question = "What's the weather forecast for Puerto Rico?"
    kagi     = KagiSearch( query=question )

    # fastgpt = kagi.search_fastgpt_req()
    fastgpt = kagi.search_fastgpt()

    du.print_banner( "Kagi: FastGPT: Meta" )
    print( fastgpt[ "meta" ] )
    du.print_banner( "Kagi: FastGPT: Data" )
    print( fastgpt[ "data" ] )
    du.print_banner( "Kagi: FastGPT: Output" )
    print( fastgpt[ "data" ][ "output" ] )
    du.print_banner( "Kagi: FastGPT: References" )
    references = fastgpt[ "data" ][ "references" ]
    for reference in references:
        print( reference )
    
    
    