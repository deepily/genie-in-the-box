import os
import json

import lib.utils.util as du

from lib.agents.agent_base             import AgentBase
from lib.agents.raw_output_formatter   import RawOutputFormatter
from lib.memory.input_and_output_table import InputAndOutputTable

class ReceptionistAgent( AgentBase ):
    def __init__( self, question=None, push_counter=-1, routing_command=None, debug=False, verbose=False, auto_debug=False, inject_bugs=False ):
        
        super().__init__( question=question, routing_command="agent router go to receptionist", push_counter=push_counter, debug=debug, verbose=verbose )
        
        self.io_tbl                   = InputAndOutputTable( debug=self.debug, verbose=self.verbose)
        self.prompt                   = self._get_prompt()
        self.xml_response_tag_names   = [ "thoughts", "category", "answer" ]
        self.serialize_prompt_to_json = self.config_mgr.get( "agent_receptionist_serialize_prompt_to_json", default=False, return_type="boolean" )
        # self.serialize_code_to_json   = self.config_mgr.get( "agent_receptionist_serialize_code_to_json",   default=False, return_type="boolean" )
    
    def _get_prompt( self ):
        
        date_today, entries = self._get_df_metadata()
        
        return self.prompt_template.format( query=self.question, date_today=date_today, entries=entries )
    
    def _get_df_metadata( self ):
        
        entries    = []
        rows       = self.io_tbl.get_all_qnr()
        for row in rows:
            entries.append( f"<memory-fragment> <date>{row['date']}</date/> <human-queried>{row['input']}</human-queried> <ai-answered>{row['output_final']}</ai-answered> </memory-fragment>" )
            
        entries    = "\n".join( entries )
        date_today = du.get_current_date()
        
        return date_today, entries
    
    def run_prompt( self, model_name=None, temperature=0.5, top_p=0.25, top_k=10, max_new_tokens=1024 ):
        
        results = super().run_prompt( model_name=model_name, temperature=temperature, top_p=top_p, top_k=top_k, max_new_tokens=max_new_tokens )
        
        self.prompt_response_dict = results
        
        self.answer_conversational = self.prompt_response_dict[ "answer" ]
        
        if self.serialize_prompt_to_json: self.serialize_to_json( "prompt" )
        
        return results
    
    def is_code_runnable( self ):
        
        return False
    
    def run_code( self, auto_debug=None, inject_bugs=None ):
        
        print( "NOT Running code, this is a receptionist agent" )
        self.code_response_dict = {
            "return_code": 0,
            "output": "No code to run, this is a receptionist agent"
        }
        return self.code_response_dict
    
    def code_ran_to_completion( self ):
        
        # This is a necessary lie to satisfy the interface
        return True
    
    def format_output( self ):
        
        # Only reformat the output if it's humorous or salacious
        if self.prompt_response_dict[ "category" ] != "benign":
            
            formatter = RawOutputFormatter(
                self.last_question_asked, self.answer_conversational, self.routing_command,
                thoughts=self.prompt_response_dict[ "thoughts" ], debug=self.debug, verbose=self.verbose
            )
            self.answer_conversational = formatter.format_output()
            
        else:
            print( "Not reformatting the output, it's benign")
        
        return self.answer_conversational
   
    
    @staticmethod
    def restore_from_serialized_state( file_path ):
        
        print( f"Restoring from {file_path}..." )
        
        # Read the file and parse JSON
        with open( file_path, 'r' ) as file:
            data = json.load( file )
        
        # Create a new object instance with the parsed data
        restored_agent = ReceptionistAgent(
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
    
    # question = "What have we talked about lately?"
    # question = "What's on my to do list for today?"
    # question = "AI, have I asked you about the weather lately?"
    # question = "What's your name?"
    # question = "How are you today Einstein?"
    # question = "When's the last time I asked you about the weather?"
    # question = "Have I ever called you my gal Friday?"
    # question = "What's the last thing I asked you about?"
    # question = "Good morning dear receptionist, what's today's date?"
    question = "my friend and i think you are pretty cool like really fucking cool!"
    receptionist_agent = ReceptionistAgent( question=question, debug=True, verbose=True )
    # receptionist_agent = ReceptionistAgent.restore_from_serialized_state( du.get_project_root() + "/io/log/todo-list-code-whats-on-my-to-do-list-for-today-2024-3-5-12-51-55.json" )
    receptionist_agent.run_prompt()
    
    response = receptionist_agent.format_output()
    du.print_banner( "Response:", prepend_nl=True )
    print( response )
    
    # results = receptionist_agent.run_code()
    # du.print_list( results )
    #
    # receptionist_agent.debug   = True
    # receptionist_agent.verbose = True
    # answer = receptionist_agent.format_output()
    # print( answer )
    