import os
import json

import lib.utils.util as du

from agent_base                   import AgentBase
from lib.memory.solution_snapshot import SolutionSnapshot
from llm   import Llm

# from incremental_calendaring_agent import IncrementalCalendaringAgent
class TodoListAgent( AgentBase ):
    def __init__( self, question=None, debug=False, verbose=False, auto_debug=False, inject_bugs=False ):
        
        super().__init__( df_path_key="path_to_todolist_df_wo_root", question=question, routing_command="agent router go to todo list", debug=debug, verbose=verbose, auto_debug=auto_debug, inject_bugs=inject_bugs )
        
        self.prompt = self._get_prompt()
        self.xml_response_tag_names = [ "question", "thoughts", "code", "example", "returns", "explanation" ]
    
    def _get_prompt( self ):
        
        column_names, list_names, head = self._get_df_metadata()
        
        return self.prompt_template.format( question=self.question, column_names=column_names, list_names=list_names, head=head )
    
    def _get_df_metadata( self ):
        
        head = self.df.head( 2 ).to_xml( index=False )
        head = head.replace( "<?xml version='1.0' encoding='utf-8'?>", "" )
        head = head.replace( "data>", "todo>" )
        
        head = head + self.df.tail( 2 ).to_xml( index=False )
        head = head.replace( "<?xml version='1.0' encoding='utf-8'?>", "" )
        head = head.replace( "data>", "todo>" )
        
        column_names = self.df.columns.tolist()
        list_names   = self.df.list_name.unique().tolist()
        
        return column_names, list_names, head
    
    def run_prompt( self, model_name=None, temperature=0.5, top_p=0.25, top_k=10, max_new_tokens=1024 ):
        
        results = super().run_prompt( model_name=model_name, temperature=temperature, top_p=top_p, top_k=top_k, max_new_tokens=max_new_tokens )
        self.serialize_to_json( "prompt" )
        
        return results
        
    def run_code( self, auto_debug=None, inject_bugs=None ):
        
        results = super().run_code( auto_debug=auto_debug, inject_bugs=inject_bugs )
        self.serialize_to_json( "code" )
        
        return results
    
    @staticmethod
    def restore_from_serialized_state( file_path ):
        
        print( f"Restoring from {file_path}..." )
        
        # Read the file and parse JSON
        with open( file_path, 'r' ) as file:
            data = json.load( file )
        
        # Create a new object instance with the parsed data
        restored_agent = TodoListAgent(
            data[ "question" ], debug=data[ "debug" ], verbose=data[ "verbose" ], auto_debug=data[ "auto_debug" ], inject_bugs=data[ "inject_bugs" ]
        )
        # Set the remaining attributes from the parsed data, skipping the ones that we've already set
        keys_to_skip = [ "question", "debug", "verbose", "auto_debug", "inject_bugs"]
        for k, v in data.items():
            if k not in keys_to_skip:
                setattr( restored_agent, k, v )
            else:
                print( f"Skipping key [{k}], it's already been set" )
        
        return restored_agent
    
if __name__ == "__main__":
    
    question = "What's on my to do list for today?"
    
    # todolist_agent = TodoListAgent( question=question, debug=True, verbose=False, auto_debug=True, inject_bugs=False )
    todolist_agent = TodoListAgent.restore_from_serialized_state( du.get_project_root() + "/io/log/todo-list-code-whats-on-my-to-do-list-for-today-2024-3-5-12-51-55.json" )
    # todolist_agent.run_prompt()
    
    # results = todolist_agent.run_code()
    # du.print_list( results )
    
    todolist_agent.debug   = True
    todolist_agent.verbose = True
    answer = todolist_agent.format_output()
    print( answer )
    