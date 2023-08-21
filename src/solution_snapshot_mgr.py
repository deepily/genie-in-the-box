import os
import regex as re

import lib.util as du
import solution_snapshot as ss

class SolutionSnapshotManager:
    def __init__( self, path, debug=False ):
        
        self.debug                           = debug
        self.path                            = path
        self.snapshots_by_question           = self.load_snapshots()
        # add a dictionary to cache previously and generated embeddings
        self.embeddings_by_question          = { }
    
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
        
        # Generate the embedding for the question, if it doesn't already exist
        if question not in self.embeddings_by_question:
            question_embedding = ss.SolutionSnapshot.generate_embedding( question )
        else:
            print( f"Embedding for question [{question}] already exists!" )
            question_embedding = self.embeddings_by_question[ question ]
            
        question_snapshot  = ss.SolutionSnapshot( question=question, question_embedding=question_embedding )
        similar_snapshots  = [ ]
        
        for snapshot in self.snapshots_by_question.values():
            
            similarity_score = snapshot.get_question_similarity( question_snapshot )
            
            if similarity_score >= threshold:
                similar_snapshots.append( ( similarity_score, snapshot ) )
            else:
                if self.debug: print( f"Score [{similarity_score}] for question [{snapshot.question}] is not similar enough to [{question}]" )
        
        # Sort by similarity score, descending
        similar_snapshots.sort( key=lambda x: x[ 0 ], reverse=True )
        
        return similar_snapshots[ :limit ]
        
    def get_snapshots_by_question( self, question, threshold=85.0, limit=7 ):
        
        question = ss.SolutionSnapshot.clean_question( question )
        
        print( f"get_snapshots_by_question( '{question}' )..." )
        
        if self.question_exists( question ):
            
            print( f"Exact match: Snapshot with question [{question}] exists!" )
            similar_snapshots = [ (100.0, self.snapshots_by_question[ question ]) ]
        
        else:
            similar_snapshots = self.get_snapshots_by_question_similarity( question, threshold=threshold, limit=limit )
        
        if len( similar_snapshots ) > 0:
            
            print( f"Found [{len( similar_snapshots )}] similar snapshots" )
            for snapshot in similar_snapshots:
                print( f"score [{snapshot[ 0 ]}] for [{question}] == [{snapshot[ 1 ].question}]" )
        else:
            print( f"Could not find any snapshots similar to [{question}]" )
            
        return similar_snapshots
        
    def __str__( self ):
        
        return f"[{len( self.snapshots_by_question )}] snapshots by question loaded from [{self.path}]"


if __name__ == "__main__":
    
    path_to_snapshots = os.path.join( du.get_project_root(), "src/conf/long-term-memory/solutions/" )
    self = SolutionSnapshotManager( path_to_snapshots )
    print( self )
    
    # Let's see if we can find a snapshot using a question
    # question = "what day comes after tomorrow?"
    # question = "what day is today?"
    question = "Why is the sky blue?"
    similar_snapshots = self.get_snapshots_by_question( question )
    
    if len( similar_snapshots ) > 0:
        lines_of_code = similar_snapshots[ 0 ][ 1 ].code
        for line in lines_of_code:
            print( line )
    
        