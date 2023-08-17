import os

import lib.util as du

import solution_snapshot as ss
class SolutionSnapshotManager:
    def __init__( self, path ):
        
        self.path = path
        self.snapshots = self.load_snapshots()
    
    def load_snapshots( self ):
        
        snapshots = [ ]
        for file in os.listdir( self.path ):
            
            if file.endswith( ".json" ):
                
                json_file = os.path.join( self.path, file )
                
                print( "loading snapshot from {0}... ".format( json_file ), end="" )
                snapshot = ss.SolutionSnapshot.from_json_file( json_file )
                snapshots.append( snapshot )
                print( "Done!" )
                
        return snapshots


if __name__ == "__main__":
    
    path_to_snapshots = du.get_project_root() + "/src/conf/long-term-memory/solutions/"
    manager = SolutionSnapshotManager( path_to_snapshots )
    
    print()
    print( f"[{len( manager.snapshots )}] snapshots loaded" )
