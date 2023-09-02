import os
import glob
import json
from datetime import datetime
import time
import regex as re

import lib.util as du

import openai
import numpy as np


class Stopwatch:
    
    def __init__( self, msg=None ):
        
        if msg: print( msg )
        self.start = time.time()
    
    def __enter__( self, msg=None ):
        
        if msg: print( msg )
        self.start = time.time()
        
        return self
    
    def __exit__( self, *args ):
        
        self.end = time.time()
        self.interval = int( (self.end - self.start) * 1000 )
        
        print( f"Done in {self.interval:,} milliseconds" )


class SolutionSnapshot:
    
    @staticmethod
    def get_timestamp():
        
        now = datetime.now()
        return now.strftime( "%Y-%m-%d @ %H-%M-%S" )
    
    @staticmethod
    def clean_question( question ):
        
        regex = re.compile( "[^a-zA-Z ]" )
        cleaned_question = regex.sub( '', question ).lower()
        
        return cleaned_question
    
    @staticmethod
    def generate_embedding( text ):

        with Stopwatch( f"Generating embedding for [{text}]..." ):
            openai.api_key = os.getenv( "FALSE_POSITIVE_API_KEY" )

            response = openai.Embedding.create(
                input=text,
                model="text-embedding-ada-002"
            )
        return response[ "data" ][ 0 ][ "embedding" ]
    
    def __init__( self, question="", answer="", created_date=get_timestamp(), updated_date=get_timestamp(), solution_summary="", code=[],
                  programming_language="Python", language_version="3.10",
                  question_embedding=[ ], solution_embedding=[ ], code_embedding=[ ],
                  solution_directory="/src/conf/long-term-memory/solutions/", solution_file=None
        ):
        
        # The question, sans anything that's not alphanumeric
        self.question             = SolutionSnapshot.clean_question( question )
        self.answer               = answer
        self.solution_summary     = solution_summary
        self.code                 = code
        
        # metadata surrounding the question and the solution
        self.updated_date         = updated_date
        self.created_date         = created_date
        self.programming_language = programming_language
        self.language_version     = language_version
        self.solution_directory   = solution_directory
        self.solution_file        = solution_file
        
        # If the question embedding is empty, generate it
        if not question_embedding:
            self.question_embedding = self.generate_embedding( question )
        else:
            self.question_embedding = question_embedding
        
        self.solution_embedding = solution_embedding
        self.code_embedding     = code_embedding
    
    @classmethod
    def from_json_file( cls, filename ):
        
        with open( filename, "r" ) as f:
            data = json.load( f )
            
        return cls( **data )

    def complete( self, answer, code=[ ], solution_summary="" ):
        
        self.answer = answer
        self.set_code( code )
        self.set_solution_summary( solution_summary )
        # self.completion_date  = SolutionSnapshot.get_current_datetime()
        
    def set_solution_summary( self, solution_summary ):

        self.solution_summary = solution_summary
        self.solution_embedding = self.generate_embedding( solution_summary )
        self.updated_date = self.get_timestamp()

    def set_code( self, code ):

        # ¡OJO! code is a list of strings, not a string!
        self.code           = code
        self.code_embedding = self.generate_embedding( " ".join( code ) )
        self.updated_date   = self.get_timestamp()
    
    def get_question_similarity( self, other_snapshot ):
        
        if not self.question_embedding or not other_snapshot.question_embedding:
            raise ValueError( "Both snapshots must have a question embedding to compare." )
        return np.dot( self.question_embedding, other_snapshot.question_embedding ) * 100
    
    def get_solution_summary_similarity( self, other_snapshot ):
        
        if not self.solution_embedding or not other_snapshot.solution_embedding:
            raise ValueError( "Both snapshots must have a solution summary embedding to compare." )
        
        return np.dot( self.solution_embedding, other_snapshot.solution_embedding ) * 100
    
    def get_code_similarity( self, other_snapshot ):
        
        if not self.code_embedding or not other_snapshot.code_embedding:
            raise ValueError( "Both snapshots must have a code embedding to compare." )
        
        return np.dot( self.code_embedding, other_snapshot.code_embedding ) * 100
    
    def to_jsons( self, verbose=True ):
        
        if verbose:
            return json.dumps( self.__dict__ )
        else:
            fields_to_exclude = [ field for field in self.__dict__ if field.endswith( '_embedding' ) ]
            data = { field: value for field, value in self.__dict__.items() if field not in fields_to_exclude }
            return json.dumps( data )
    
    def get_html( self ):
        
        if self.answer != "":
            return f"<li>Q: {self.question}. A: {self.answer}</li>"
        else:
            return f"<li>Q: {self.question}</li>"
    
    def write_to_file( self ):
        
        # Get the project root directory
        project_root = du.get_project_root()
        # Define the directory where the file will be saved
        directory = f"{project_root}{self.solution_directory}"
        
        if self.solution_file is None:
            
            print( "NO solution_file value provided (Must be a new object). Generating a unique file name..." )
            # Generate filename based on first 64 characters of the question
            filename_base = self.question[ :64 ].replace( " ", "-" )
            # Get a list of all files that start with the filename base
            existing_files = glob.glob( f"{directory}{filename_base}-*.json" )
            # The count of existing files will be used to make the filename unique
            file_count = len( existing_files )
            # generate the file name
            filename = f"{filename_base}-{file_count}.json"
            self.solution_file = filename
        
        else:
            
            print( f"solution_file value provided: [{self.solution_file}]..." )
        
        # Generate the full file path
        file_path = f"{directory}{self.solution_file}"
        # Print the file path for debugging purposes
        print( f"File path: {file_path}" )
        # Write the JSON string to the file
        with open( file_path, "w" ) as f:
            f.write( self.to_jsons() )


# Add main method
if __name__ == "__main__":
    
    today = SolutionSnapshot( question="what day is today" )
    # tomorrow = SolutionSnapshot( question="what day is tomorrow" )
    # blah = SolutionSnapshot( question="i feel so blah today" )
    # color = SolutionSnapshot( question="what color is the sky" )
    # date = SolutionSnapshot( question="what is today's date" )
    
    # snapshots = [ today, tomorrow, blah, color, date ]
    snapshots = [ today ]
    
    for snapshot in snapshots:
        score = today.get_question_similarity( snapshot )
        print( f"Score: [{score}] for [{snapshot.question}] == [{today.question}]" )
        snapshot.write_to_file()
    
    # foo = SolutionSnapshot.from_json_file( du.get_project_root() + "/src/conf/long-term-memory/solutions/what-day-is-today-0.json" )
    # print( foo.to_json() )
    # pass
