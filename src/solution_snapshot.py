import os
import glob
import json
from datetime import datetime
import time

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

        self.end      = time.time()
        self.interval = int( ( self.end - self.start ) * 1000 )

        print( f'Done in {self.interval:,} milliseconds' )
        
class SolutionSnapshot:

    @staticmethod
    def get_timestamp():

        now = datetime.now()
        return now.strftime( "%Y-%m-%d @ %H-%M-%S" )

    def __init__( self, problem, created_date=get_timestamp(), updated_date=get_timestamp(), solution_summary="", code="",
                  programming_language="python", language_version="3.10",
                  problem_embedding=[], solution_embedding=[ ], code_embedding=[ ],
                  solution_directory="/src/conf/long-term-memory/solutions/", solution_file=None
        ):

        self.created_date         = created_date
        self.updated_date         = updated_date
        self.problem              = problem
        self.solution_summary     = solution_summary
        self.code                 = code
        self.programming_language = programming_language
        self.language_version     = language_version
        self.solution_directory   = solution_directory
        self.solution_file        = solution_file

        # If the problem embedding is empty, generate it
        if not problem_embedding:
            self.problem_embedding = self._generate_embedding( problem )
        else:
            self.problem_embedding = problem_embedding

        self.solution_embedding   = solution_embedding
        self.code_embedding       = code_embedding


    def set_solution_summary( self, solution_summary ):

        self.solution_summary   = solution_summary
        self.solution_embedding = self._generate_embedding( solution_summary )
        self.updated_date       = self.get_timestamp()

    def set_code( self, code ):

        self.code           = code
        self.code_embedding = self._generate_embedding( code )
        self.updated_date   = self.get_timestamp()

    def _generate_embedding( self, text ):

        with Stopwatch( f"Generating embedding for [{text}]..." ):
            
            openai.api_key = os.getenv( "FALSE_POSITIVE_API_KEY" )
            
            response = openai.Embedding.create(
                input=text,
                model="text-embedding-ada-002"
            )
        return response[ "data" ][ 0 ][ "embedding" ]

    def get_problem_similarity( self, other_snapshot ):

        if not self.problem_embedding or not other_snapshot.problem_embedding:
            raise ValueError( "Both snapshots must have a problem embedding to compare." )
        return np.dot( self.problem_embedding, other_snapshot.problem_embedding )

    def get_solution_summary_similarity( self, other_snapshot ):

        if not self.solution_embedding or not other_snapshot.solution_embedding:
            raise ValueError( "Both snapshots must have a solution summary embedding to compare." )

        return np.dot( self.solution_embedding, other_snapshot.solution_embedding )

    def get_code_similarity( self, other_snapshot ):

        if not self.code_embedding or not other_snapshot.code_embedding:
            raise ValueError( "Both snapshots must have a code embedding to compare." )

        return np.dot( self.code_embedding, other_snapshot.code_embedding )

    def to_json( self ):

        return json.dumps( self.__dict__ )

    def write_to_file( self ):

        # Get the project root directory
        project_root = du.get_project_root()
        # Define the directory where the file will be saved
        directory = f"{project_root}{self.solution_directory}"

        if self.solution_file is None:

            print( "NO solution_file value provided (Must be a new object). Generating a unique file name..." )
            # Generate filename based on first 64 characters of the problem
            filename_base = self.problem[ :64 ]
            # Replace any character that is not alphanumeric or underscore with underscore
            filename_base = "".join( c if c.isalnum() else "-" for c in filename_base )
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
            f.write( self.to_json() )

    @classmethod
    def from_json_file( cls, filename ):

        with open( filename, 'r' ) as f:
            data = json.load( f )
        return cls( **data )


# Add main method
if __name__ == "__main__":

    # today     = SolutionSnapshot( problem="what day is today" )
    # tomorrow  = SolutionSnapshot( problem="what day is tomorrow" )
    # blah      = SolutionSnapshot( problem="i feel so blah today" )
    # color     = SolutionSnapshot( problem="what color is the sky" )
    # date      = SolutionSnapshot( problem="what is today's date" )
    #
    # snapshots = [ today, tomorrow, blah, color, date ]
    #
    # for snapshot in snapshots:
    #
    #     score = today.get_problem_similarity( snapshot )
    #     print( f"Score: [{score}] for [{snapshot.problem}] == [{today.problem}]" )
    #     snapshot.write_to_file()
        
    # foo = SolutionSnapshot.from_json_file( du.get_project_root() + "/src/conf/long-term-memory/solutions/what-day-is-today-0.json" )
    # print( foo.to_json() )
    pass
    