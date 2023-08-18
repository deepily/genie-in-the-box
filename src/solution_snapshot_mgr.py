import os
import regex as re

import lib.util as du
import solution_snapshot as ss

class SolutionSnapshotManager:
    def __init__( self, path, debug=False ):
        
        self.debug                           = debug
        self.path                            = path
        self.snapshots_by_question           = self.load_snapshots()
    
    def load_snapshots( self ):
        
        snapshots_by_question = { }
        
        for file in os.listdir( self.path ):
            
            if file.endswith( ".json" ):
                json_file = os.path.join( self.path, file )
                snapshot = ss.SolutionSnapshot.from_json_file( json_file )
                snapshots_by_question[ snapshot.question ] = snapshot
        
        return snapshots_by_question
    
    def question_exists( self, question ):
        
        return question in self.snapshots_by_question
    
    def get_snapshots_by_question_similarity( self, question, threshold=85.0, limit=7 ):
        
        similar_snapshots = [ ]
        question_snapshot = ss.SolutionSnapshot( question=question )
        
        for snapshot in self.snapshots_by_question.values():
            
            similarity_score = snapshot.get_question_similarity( question_snapshot )
            
            if similarity_score >= threshold:
                similar_snapshots.append( ( similarity_score, snapshot ) )
            else:
                if self.debug: print( f"Score [{similarity_score}] for question [{snapshot.question}] is not similar enough to [{question}]" )
        
        similar_snapshots.sort( key=lambda x: x[ 0 ], reverse=True )
        
        return similar_snapshots[ :limit ]
    
    def __str__( self ):
        
        return f"[{len( self.snapshots_by_question )}] snapshots by question loaded from [{self.path}]"


if __name__ == "__main__":
    
    path_to_snapshots = os.path.join( du.get_project_root(), "src/conf/long-term-memory/solutions/" )
    manager = SolutionSnapshotManager( path_to_snapshots )
    print( manager )

    # Let's see if we can find a sap shot using the question, what day is today?
    # question = "what day is today"
    # question = "what day comes after tomorrow?"
    question = "what day comes after today?"
    regex = re.compile( '[^a-zA-Z ]' )
    question = regex.sub( '', question ).lower()
    
    print( f"Looking for snapshot with question: [{question}]" )
    similar_snapshots = [ ]
    if manager.question_exists( question ):
        print( f"Exact match: Snapshot with question [{question}] exists!" )
        similar_snapshots.append( ( 100.0, manager.snapshots_by_question[ question ] ) )
    else:
        similar_snapshots = manager.get_snapshots_by_question_similarity( question )
        
    if len( similar_snapshots ) > 0:
        print( f"Found [{len( similar_snapshots )}] similar snapshots!" )
        for snapshot in similar_snapshots:
            print( f"score [{snapshot[ 0 ]}] for [{question}] == [{snapshot[ 1 ].question}]" )
    else:
        print( f"Could not find any snapshots similar to [{question}]" )
        