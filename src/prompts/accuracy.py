from src import genie_client as gc

import json
def load_json( path ):
    
    with open( path, 'r' ) as f:
        data = json.load( f )
    
    return data

if __name__ == "__main__":
    
    print( "Calculating accuracy..." )
    # load data
    data = load_json( "data/synthetic-data-load-url-current-tab.json" )
    # get total number of prompts
    total = len( data )
    print( "Total number of prompts: {}".format( total ) )
    print( data[0] )
    
    genie_client = gc.GenieClient()
    print( genie_client )
    #