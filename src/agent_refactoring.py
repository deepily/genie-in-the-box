import os
import json

import lib.util             as du

import solution_snapshot as ss
from agent import CommonAgent
from solution_snapshot_mgr import SolutionSnapshotManager
class RefactoringAgent( CommonAgent ):
    
    def __init__( self, similar_snapshots=[], path_to_solutions="/src/conf/long-term-memory/solutions", debug=False, verbose=False ):
        
        self.debug             = debug
        self.verbose           = verbose
        
        self.path_to_solutions = path_to_solutions
        self.similar_snapshots = similar_snapshots
        self.snippets          = None
        self.snippets_string   = None
        self.system_message    = self._get_system_message()
        self.user_message      = self._get_user_message()
        self.response          = None
        self.response_dict     = None
        self.error             = None
    
    def _preprocess_similar_snapshots( self ):
        
        i = 1
        self.snippets = []
        
        for snapshot in self.similar_snapshots:
            
            # snippet = f"Question {i}: {snapshot[ 1 ].question}"
            # self.snippets.append( snippet )
            
            snippet = "\n".join( snapshot[ 1 ].code )
            snippet = f"Snippet {i} for question `{snapshot[ 1 ].question}`: \n\n{snippet}"
            self.snippets.append( snippet )
            
            if self.debug: print( snippet, end="\n\n" )
            i += 1
    
    def _get_system_message( self ):
        
        self._preprocess_similar_snapshots()
        
        snippet_count = len( self.snippets )
        
        system_message = f"""
        I'm going to show you {snippet_count} Python code snippets that are similar, along with the questions they were created to answer.
        How would you coalesce or refactor them so that you only need to call one function in all {snippet_count} scenarios?
        How would you name the function in a way that clearly explains exactly what the function does?
        Descriptive function names look like: `get_birthday_by_name`, or `get_birthdays_by_day`, `get_events_by_week_and_type`,`get_events_by_day_and_type`, etc.,

        As you generate the Python 3.10 code needed to answer this question, I want you to:

        1) Think: Before you do anything, think out loud about what I'm asking you to do, including the steps that you will need to take to solve this problem.
        Be critical of your thought process! How will you handle the edge cases? For example, what will you do if your query does not return a result?
        2) Code: Generate a verbatim list of code that you used to arrive at your answer, one line of code per item on the list. The code must be complete,
        syntactically correct, and capable of running to completion. You must allow for the possibility that your query may not return a result.
        3) Return: Report on the object type returned by your last line of code. Use one word to represent the object type.
        4) Generate examples: Generate a dictionary containing the code examples needed to call the function you created, one line of code per question provided.
        The example function calls must be complete, syntactically correct, and capable of running to completion. Each example must be wrapped in a print statement.
        5) Explain: Briefly and succinctly explain your code in plain English.

        Format: return your response as a JSON object in the following fields:
        {{
            "thoughts": "Your thoughts",
            "code": [],
            "function_name": "The name of your function",
            "returns": "Object type of the variable `solution`",
            "examples": {{}}, a dictionary containing the questions and example code, one line of code per question provided.
            "python_version": "3.10",
            "explanation": "A brief explanation of your code",
            "error": "Verbatim stack trace or description of issues encountered while attempting to carry out this task."
        }}"""
        
        return system_message
    
    def _get_user_message( self ):
        
        snippets_string = "\n\n".join( self.snippets )
        
        user_message = f"""
        {snippets_string}

        Begin!
        """
        
        return user_message
    
    def run_prompt( self ):
        
        prompt_model = CommonAgent.GPT_4
        if self.debug:
            
            count = self._get_token_count( self.system_message, model=prompt_model )
            msg = f"Token count for self.system_message: [{count}]"
            if self.verbose:
                du.print_banner( msg=msg, prepend_nl=True )
                print( self.system_message )
            else:
                print( msg )
            
            count = self._get_token_count( self.user_message, model=prompt_model )
            msg = f"Token count for self.user_message: [{count}]"
            if self.verbose:
                du.print_banner( msg=msg, prepend_nl=True )
                print( self.user_message )
            else:
                print( msg )
                
        self.response      = self._query_gpt( self.system_message, self.user_message, model=prompt_model, debug=self.debug )
        self.response_dict = json.loads( self.response )

        if self.debug and self.verbose: print( json.dumps( self.response_dict, indent=4 ) )

        # Test for no code returned and throw error
        if self.response_dict[ "code" ] == [ ]:
            stem = "No code was returned."
            # Save for debugging by LLM later
            self.error = f"{stem} LLM error: {self.response_dict[ 'error' ]}"
            raise ValueError( stem )
        
        if self.response_dict[ "examples" ] == [ ]:
            self.error = self.response_dict[ "error" ]
            raise ValueError( "No examples were returned, please check the logs" )

        return self.response_dict
    
    def update_code( self, debug=False ):
        
        agent_src_root = du.get_project_root() + "/src/"
        agent_lib_chunk = "lib/autogen/"
        
        code_write_metadata = self._write_code_to_unique_files(
            self.response_dict[ "code" ], agent_src_root, agent_lib_chunk, "util_calendaring_", suffix=".py"
        )
        if debug:
            print( f"File     count: [{code_write_metadata[ 'count' ]}]" )
            print( f"File file_name: [{code_write_metadata[ 'file_name' ]}]" )
            print( f"File repo_path: [{code_write_metadata[ 'repo_path' ]}]" )
            print( f"File   io_path: [{code_write_metadata[ 'io_path' ]}]" )
            print( f"File    abbrev: [{code_write_metadata[ 'abbrev' ]}]" )
            print( f"File    import: [{code_write_metadata[ 'import' ]}]" , end="\n\n" )
        
        response_dict = self._update_example_code( self.response_dict.copy(), code_write_metadata, code_write_metadata )
        
        self._update_snapshot_code( self.similar_snapshots, response_dict, debug=debug )
    
    def _write_code_to_unique_files( self, lines, agent_src_root, agent_lib_chunk, file_name_prefix, suffix=".py" ):
        
        # Get the list of files in the agent_lib_path directory
        files = os.listdir( agent_src_root + agent_lib_chunk )
        
        # Count the number of files with the name {file_name_prefix}{}{suffix}"
        count = sum( 1 for file in files if file.startswith( file_name_prefix ) and file.endswith( suffix ) )
        
        # Format the file name with the count
        file_name = f"{file_name_prefix}{count}{suffix}"
        util_name = f"{file_name_prefix}{count}"
        
        # Write the file to the repo path
        repo_path = os.path.join( agent_src_root, agent_lib_chunk, file_name )
        print( f"Writing file [{repo_path}]... ", end="" )
        du.write_lines_to_file( repo_path, lines )
        # Set the permissions of the file to be world-readable and writable
        os.chmod( repo_path, 0o666 )
        print( "Done!" )
        
        # Write the file to the io/execution path
        io_path = f"{du.get_project_root()}/io/{agent_lib_chunk}{file_name}"
        print( f"Writing file [{io_path}]... ", end="" )
        du.write_lines_to_file( io_path, lines )
        # Set the permissions of the file to be world-readable and writable
        os.chmod( io_path, 0o666 )
        print( "Done!", end="\n\n" )
        
        # Build import 'as' string:
        non_digits = "util_calendaring_2".split( "_" )[ :-1 ]
        first_digits = "".join( [ item[ 0 ] for item in non_digits ] )
        abbrev = f"{first_digits}{count}"
        as_chunk = f"as {abbrev}"
        import_str = f"import {agent_lib_chunk.replace( '/', '.' )}{util_name} {as_chunk}"
        
        results = {
            "file_name": file_name,
            "repo_path": repo_path,
            "io_path"  : io_path,
            "count"    : count,
            "abbrev"   : abbrev,
            "import"   : import_str
        }
        
        return results
    
    def _update_example_code( self, refactoring_response_dict, code_metadata, debug=False ):
        
        function_name = refactoring_response_dict[ "function_name" ]
        
        # Update the examples dictionary so that it contains a list of source code needed to execute the freshly minted function
        for key, value in refactoring_response_dict[ "examples" ].items():
            
            # if debug: print( f"Before: {key}: {value}" )
            if type( value ) is not list:
                value = value.replace( function_name, f"{code_metadata[ 'abbrev' ]}.{function_name}" )
                value = [ code_metadata[ 'import' ], value ]
            # else:
            #     if debug: print( f"No need to update [{value}]" )
            # if debug: print( f" After: {key}: {value}" )
            
            refactoring_response_dict[ "examples" ][ key ] = value
        
        return refactoring_response_dict
    
    def _update_snapshot_code( self, snapshots, refactoring_response_dict, debug=False ):
        
        for snapshot in snapshots:
            
            if debug:
                du.print_banner( f"BEFORE updating `{snapshot[ 1 ].question}`...", prepend_nl=False )
                for line in snapshot[ 1 ].code: print( line )
                print( "\n" )
            
            # Update the code, using the question as the key
            new_code = refactoring_response_dict[ "examples" ][ snapshot[ 1 ].question ]
            snapshot[ 1 ].code = new_code
            snapshot[ 1 ].code_embedding = ss.SolutionSnapshot.generate_embedding( " ".join( new_code ) )
            snapshot[ 1 ].write_to_file()
            
            if debug:
                du.print_banner( f" AFTER updating `{snapshot[ 1 ].question}`...", prepend_nl=False )
                for line in snapshot[ 1 ].code: print( line )
                print( "\n" )

if __name__ == "__main__":
    
    path_to_snapshots = du.get_project_root() + "/src/conf/long-term-memory/solutions/"
    snapshot_mgr      = SolutionSnapshotManager( path_to_snapshots, debug=False )
    exemplar_snapshot = snapshot_mgr.get_snapshots_by_question( "What concerts do I have this week?" )[ 0 ][ 1 ]
    similar_snapshots = snapshot_mgr.get_snapshots_by_code_similarity( exemplar_snapshot, threshold=90.0 )
    
    agent         = RefactoringAgent( similar_snapshots=similar_snapshots, path_to_solutions="/src/conf/long-term-memory/solutions", debug=True, verbose=True )
    response_dict = agent.run_prompt()