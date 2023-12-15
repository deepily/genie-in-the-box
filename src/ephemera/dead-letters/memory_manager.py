import time as time
import random, string

from lib.utils import util as du


class MemoryManager:
    
    def __init__( self ):
        
        self.memory_dir = du.get_project_root() + "/src/conf/memory"
        self.current_memory = dict()
        
    def __str__( self ):
        
        return "MemoryManager: current memory timestamp count: [{}]".format( len( self.current_memory.keys() ) )
        
    def random_hexish( self, length ):
        
        letters = string.ascii_lowercase[ 0:5 ] + string.digits
        return ''.join( random.choice( letters ) for i in range( length ) )
    
    def get_timestamp( self ):
        
        return str( time.strftime( "%Y-%m-%d @ %H:%M:%S hash-ish: {}".format( self.random_hexish( 6 ) ) ) )
    
    def stash_utterance( self, utterances ):
    
        timestamp = self.get_timestamp()
        print( "Stashing utterance with timestamp: [{}]".format( timestamp ) )
        print( "Utterance: {}".format( utterances ) )
        self.current_memory[ timestamp ] = utterances
        
    def get_current_memory( self ):
        
        return self.current_memory
    
#     messages=[
#         {"role": "system", "content": "You are a helpful assistant."},
#         {"role": "user", "content": "Who won the world series in 2020?"},

#         {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
#         {"role": "user", "content": "Where was it played?"}
#     ]
if __name__ == "__main__":
    
    mm = MemoryManager()
    
    messages = [
        { "role": "system", "content": "You are a helpful assistant." },
        { "role": "user", "content": "Who won the world series in 2020?" },
    ]
    mm.stash_utterance( messages )
    
    response  = [
        { "role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020." }
    ]
    mm.stash_utterance( response )
    
    print( mm.get_current_memory().keys() )
    
    print( mm )
    