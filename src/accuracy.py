import os

from src     import genie_client as gc
from src.lib import util as du
from src.lib import util_stopwatch as sw

import json
import pandas as pd

class Accuracy:
    
    def __init__( self ):
        
        self.project_root = du.get_project_root_path()
        self.prompt       = du.get_file_as_string( self.project_root + "/src/prompts/classification-experiment-template.txt" )
        
        print( "Using project root [{}]".format( self.project_root ) )
        
        pd.set_option( "display.width", 512)
        pd.set_option( "display.max_columns", 6 )
    
    def load_json( self, path ):
        
        df = pd.read_json( path )
        
        return df
    
    def load_training_data( self ):
        
        # load data
        paths = [
            self.project_root + "/src/prompts/data/synthetic-data-load-url-current-tab.json",
            self.project_root + "/src/prompts/data/synthetic-data-load-url-new-tab.json"
        ]
        dfs = []
        for path in paths:
            
            df = self.load_json( path )
            total = df.shape[ 0 ]
            print( "prompts in this df: {}".format( total ) )
            dfs.append( df )
            
        df = pd.concat( dfs )
        df.reset_index( inplace=True )
        df.drop( "index", axis=1, inplace=True )
        
        return df
    
    
    
if __name__ == "__main__":
    
    accuracy = Accuracy()
    
    df = accuracy.load_training_data()
    print( "Total number of prompts: {}".format( df.shape[ 0 ] ) )
    # print( df )

    commands        = df[ "synonymous_command" ].tolist()
    system_commands = df[ "system_command"     ].tolist()
    correct         = [ 0 ] * len( commands)

    genie_client  = gc.GenieClient()
    timer         = sw.Stopwatch()
    correct_count = 0

    for idx, command in enumerate( commands ):

        prompt = accuracy.prompt.replace( "{synonymous_command}", command )

        timer_item = sw.Stopwatch()
        response = genie_client.ask_chat_gpt_using_raw_prompt_and_content( prompt )
        response = json.loads( response )

        print( idx, command, response )
        timer_item.print( "Done interpreting one command", use_millis=True )
        # print( "-" * 120 )

        if system_commands[ 0 ] == response[ "classification" ]:
            correct_count += 1
            correct[ idx ] = 1

    timer.print( "Done Iterating commands", use_millis=False )
    df[ "correct" ] = correct

    accuracy = 100.0 * correct_count / len( commands )
    accuracy = round( accuracy, 1 )

    du.print_banner( "[{}] correct out of [{}] commands. Accuracy: {}%".format( correct_count, len( commands ), accuracy ) )
    
    print( df )
    