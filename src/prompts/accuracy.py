from src import genie_client as gc
from src.lib import util as du

import json


class Accuracy:
    
    def __init__( self, proj_root="/Users/rruiz/Projects/projects-sshfs/genie-in-the-box" ):
        
        self.proj_root = proj_root
        self.prompt    = du.get_file_as_string( proj_root + "/src/prompts/classification-experiment.txt" )
    
    def load_json( path ):
        
        with open( path, 'r' ) as f:
            data = json.load( f )
        
        return data
    
    

if __name__ == "__main__":
    
    print( "Calculating accuracy..." )
    accuracy = Accuracy()
    # load data
    data = accuracy.load_json( "data/synthetic-data-load-url-current-tab.json" )
    # get total number of prompts
    total = len( data )
    print( "Total number of prompts: {}".format( total ) )
    print( data[0] )
    
    genie_client = gc.GenieClient()
    print( genie_client )
    #