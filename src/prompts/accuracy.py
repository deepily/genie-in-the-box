import os

from src import genie_client as gc
from src.lib import util as du

import json


class Accuracy:
    
    def __init__( self ):
        
        # print( "GENIE_IN_THE_BOX_ROOT [{}]".format( os.getenv( "GENIE_IN_THE_BOX_ROOT" ) ) )
        # if os.getenv( "GENIE_IN_THE_BOX_ROOT" ) is not None:
        #     self.project_root = os.getenv( "GENIE_IN_THE_BOX_ROOT" )
        # else:
        #     self.project_root = proj_root
        
        self.project_root = du.get_project_root_path()
        self.prompt       = du.get_file_as_string( self.project_root + "/src/prompts/classification-experiment.txt" )
    
    def load_json( self, path ):
        
        with open( path, 'r' ) as f:
            data = json.load( f )
        
        return data
    
    

if __name__ == "__main__":
    
    # print( "Calculating accuracy..." )
    accuracy = Accuracy()
    print( accuracy.project_root )
    # load data
    data = accuracy.load_json( "data/synthetic-data-load-url-current-tab.json" )
    # get total number of prompts
    total = len( data )
    print( "Total number of prompts: {}".format( total ) )
    print( data[0] )

    genie_client = gc.GenieClient()
    print( genie_client )
    
    # if os.getenv( "GENIE_IN_THE_BOX_ROOT" ):
    #     print( os.getenv( "GENIE_IN_THE_BOX_ROOT" ) )
    # else:
    #     print( "GENIE_IN_THE_BOX_ROOT not set!" )