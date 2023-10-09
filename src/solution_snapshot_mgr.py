import os
import regex as re
import pprint

import lib.util as du
import solution_snapshot as ss
from question_embeddings_dict import QuestionEmbeddingsDict

class SolutionSnapshotManager:
    def __init__( self, path, debug=False, verbose=False ):
        
        self.debug                             = debug
        self.path                              = path
        self.snapshots_by_question             = self.load_snapshots_by_question()
        self.snapshots_by_synomymous_questions = self.get_snapshots_by_synomymous_questions( self.snapshots_by_question )
        self.embeddings_by_question            = QuestionEmbeddingsDict()
        
        if debug:
            print( self )
            if verbose:
                self.print_snapshots()
        
    def load_snapshots_by_question( self ):
        
        snapshots_by_question = { }
        if self.debug: print( f"Loading snapshots from [{self.path}]..." )
        
        filtered_files = [ file for file in os.listdir( self.path ) if not file.startswith( "._" ) and file.endswith( ".json" ) ]
        if self.debug: du.print_list( filtered_files )
        
        for file in filtered_files:
            json_file = os.path.join( self.path, file )
            snapshot = ss.SolutionSnapshot.from_json_file( json_file, debug=self.debug )
            snapshots_by_question[ snapshot.question ] = snapshot
    
        return snapshots_by_question
    
    def get_snapshots_by_synomymous_questions( self, snapshots_by_question ):
        
        snapshots_by_synomymous_questions = { }
        
        for _, snapshot in snapshots_by_question.items():
            for question, similarity_score in snapshot.synonymous_questions.items():
                snapshots_by_synomymous_questions[ question ] = ( similarity_score, snapshot )
                
        du.print_banner( f"Found [{len( snapshots_by_synomymous_questions )}] synonymous questions", prepend_nl=True )
        for question in snapshots_by_synomymous_questions.keys():
            print( f"Synonymous question [{question}] for snapshot.question [{snapshots_by_synomymous_questions[ question ][ 1 ].question}]" )
            
        print()
        return snapshots_by_synomymous_questions
    
    def add_snapshot( self, snapshot ):
        
        self.snapshots_by_question[ snapshot.question ] = snapshot
        snapshot.write_to_file()
    
    # get the questions embedding if it exists otherwise generate it and add it to the dictionary
    def get_question_embedding( self, question ):
        
        if question in self.embeddings_by_question:
            return self.embeddings_by_question[ question ]
        else:
            question_embedding = ss.SolutionSnapshot.generate_embedding( question )
    
        return question_embedding
    
    def question_exists( self, question ):
        
        return question in self.snapshots_by_question
    
    # create a method to delete a snapshot by exact match with the question string
    def delete_snapshot( self, question ):
        
        # clean up the question string before querying
        question = ss.SolutionSnapshot.clean_question( question )
        
        print( f"Deleting snapshot with question [{question}]..." )
        if self.question_exists( question ):
            del self.snapshots_by_question[ question ]
            print( f"Snapshot with question [{question}] deleted!" )
            return True
        else:
            print( f"Snapshot with question [{question}] does not exist!" )
            return False
        
    def get_snapshots_by_question_similarity( self, question, threshold=85.0, limit=7 ):
        
        # Generate the embedding for the question, if it doesn't already exist
        if question not in self.embeddings_by_question:
            question_embedding = ss.SolutionSnapshot.generate_embedding( question )
            self.embeddings_by_question[ question ] = question_embedding
        else:
            print( f"Embedding for question [{question}] already exists!" )
            question_embedding = self.embeddings_by_question[ question ]
            
        question_snapshot  = ss.SolutionSnapshot( question=question, question_embedding=question_embedding )
        similar_snapshots  = [ ]
        
        for snapshot in self.snapshots_by_question.values():
            
            similarity_score = snapshot.get_question_similarity( question_snapshot )
            
            if similarity_score >= threshold:
                similar_snapshots.append( ( similarity_score, snapshot ) )
                if self.debug: print( f"Score [{similarity_score}] for question [{snapshot.question}] IS similar enough to [{question}]" )
            else:
                if self.debug: print( f"Score [{similarity_score}] for question [{snapshot.question}] is NOT similar enough to [{question}]" )
        
        # Sort by similarity score, descending
        similar_snapshots.sort( key=lambda x: x[ 0 ], reverse=True )
        
        return similar_snapshots[ :limit ]
    
    import numpy as np
    
    def get_snapshots_by_code_similarity( self, exemplar_snapshot, threshold=85.0, limit=-1 ):
        
        # code_snapshot      = ss.SolutionSnapshot( code_embedding=source_snapshot.code_embedding )
        question_truncated = du.truncate_string( exemplar_snapshot.question, max_len=32 )
        similar_snapshots  = [ ]
        
        # Iterate the code in the code list and print it to the console
        if self.debug:
            du.print_banner( f"Source code for [{question_truncated}]:", prepend_nl=True)
            for line in exemplar_snapshot.code: print( line )
            print()
        
        for snapshot in self.snapshots_by_question.values():
            
            similarity_score   = snapshot.get_code_similarity( exemplar_snapshot )
            question_truncated = du.truncate_string( snapshot.question, max_len=32 )
            
            if similarity_score >= threshold:
                similar_snapshots.append( ( similarity_score, snapshot ) )
                if self.debug:
                    du.print_banner( f"Code score [{similarity_score}] for snapshot [{question_truncated}] IS similar to the provided code", end="\n" )
                    for line in snapshot.code:
                        print( line )
                    print()
            else:
                if self.debug:
                    print( f"Code score [{similarity_score}] for snapshot [{question_truncated}] is NOT similar to the provided code", end="\n" )
            
        # Sort by similarity score, descending
        similar_snapshots.sort( key=lambda x: x[ 0 ], reverse=True )
        
        print()
        for snapshot in similar_snapshots:
            print( f"Code similarity score [{snapshot[ 0 ]}] for [{question_truncated}] == [{du.truncate_string( snapshot[ 1 ].question, max_len=32 )}]" )
        
        if limit == -1:
            return similar_snapshots
        else:
            return similar_snapshots[ :limit ]
    
    def get_snapshots_by_question( self, question, threshold=85.0, limit=7, debug=False ):
        
        question = ss.SolutionSnapshot.clean_question( question )
        
        if self.debug: print( f"get_snapshots_by_question( '{question}' )..." )
        # print( "question in self.snapshots_by_synomymous_questions:", question in self.snapshots_by_synomymous_questions)
        
        if self.question_exists( question ):
            
            if debug: print( f"Exact match: Snapshot with question [{question}] exists!" )
            similar_snapshots = [ (100.0, self.snapshots_by_question[ question ]) ]
            
        elif question in self.snapshots_by_synomymous_questions:
            
            snapshot = self.snapshots_by_synomymous_questions[ question ][ 1 ]
            score    = self.snapshots_by_synomymous_questions[ question ][ 0 ]
            similar_snapshots = [ (score, snapshot) ]
            print( f"Snapshot with synonymous question for [{question}] exists: [{snapshot.question}] similarity score [{score}]" )
        
        else:
            print( "No exact match or synonymous question found, searching for similar questions..." )
            similar_snapshots = self.get_snapshots_by_question_similarity( question, threshold=threshold, limit=limit )
        
        if len( similar_snapshots ) > 0:
            
            if debug: print( f"Found [{len( similar_snapshots )}] similar snapshots" )
            for snapshot in similar_snapshots:
                if debug: print( f"score [{snapshot[ 0 ]}] for [{question}] == [{snapshot[ 1 ].question}]" )
        else:
            if debug: print( f"Could not find any snapshots similar to [{question}]" )
            
        return similar_snapshots
        
    def __str__( self ):
        
        return f"[{len( self.snapshots_by_question )}] snapshots by question loaded from [{self.path}]"

    # method to print the snapshots dictionary
    def print_snapshots( self ):
        
        du.print_banner( f"Total snapshots: [{len( self.snapshots_by_question )}]", prepend_nl=True )
        
        for question, snapshot in self.snapshots_by_question.items():
            print( f"Question: [{question}]" )
            
        print()

if __name__ == "__main__":
    
    path_to_snapshots = du.get_project_root() + "/src/conf/long-term-memory/solutions/"
    snapshot_mgr = SolutionSnapshotManager( path_to_snapshots, debug=False )
    # print( snapshot_mgr )
    
    exemplar_snapshot = snapshot_mgr.get_snapshots_by_question( "What concerts do I have this week?" )[ 0 ][ 1 ]
    
    similar_snapshots = snapshot_mgr.get_snapshots_by_code_similarity( exemplar_snapshot, threshold=90.0 )
    
    # questions = [
    #     "what day comes after tomorrow?",
    #     "what day is today?",
    #     "Why is the sky blue?",
    #     "What's today's date?",
    #     "What is today's date?"
    # ]
    # for question in questions:
    #
    #     du.print_banner( f"Question: [{question}]", prepend_nl=True )
    #     similar_snapshots = snapshot_mgr.get_snapshots_by_question( question )
    #
    #     if len( similar_snapshots ) > 0:
    #             lines_of_code = similar_snapshots[ 0 ][ 1 ].code
    #             for line in lines_of_code:
    #                 print( line )
        
        