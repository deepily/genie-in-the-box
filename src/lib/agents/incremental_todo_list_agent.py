import lib.utils.util as du

from agent import Agent

from incremental_calendaring_agent import IncrementalCalendaringAgent
class IncrementalTodoListAgent( IncrementalCalendaringAgent ):
    def __init__( self, df_path_key="path_to_todolist_df_wo_root", question="", default_model=Agent.PHIND_34B_v2, push_counter=-1, debug=False, verbose=False, auto_debug=False, inject_bugs=False ):
        
        super().__init__( df_path_key=df_path_key, question=question, default_model=default_model, push_counter=push_counter, debug=debug, verbose=verbose, auto_debug=auto_debug, inject_bugs=inject_bugs )
        
        self.path_to_prompts   = du.get_project_root() + self.config_mgr.get( "path_to_todolist_prompts_wo_root" )
        self.prompt_components = self._initialize_prompt_components()
    
    def _initialize_prompt_components( self ):
        
        head, value_counts = self._get_df_metadata()
        
        step_1 = du.get_file_as_string( self.path_to_prompts + "todo-list-step-1.txt" ).format(
            head=head, value_counts=value_counts, question=self.question
        )
        step_2 = du.get_file_as_string( self.path_to_prompts + "todo-list-step-2.txt" )
        step_3 = du.get_file_as_string( self.path_to_prompts + "todo-list-step-3.txt" )
        step_4 = du.get_file_as_string( self.path_to_prompts + "todo-list-step-4.txt" )
        
        xml_formatting_instructions_step_1 = du.get_file_as_string( self.path_to_prompts + "todo-lists-xml-formatting-instructions-step-1.txt" )
        xml_formatting_instructions_step_2 = du.get_file_as_string( self.path_to_prompts + "todo-lists-xml-formatting-instructions-step-2.txt" )
        xml_formatting_instructions_step_3 = du.get_file_as_string( self.path_to_prompts + "todo-lists-xml-formatting-instructions-step-3.txt" )
        
        steps = [ step_1, step_2, step_3, step_4 ]
        self.step_len = len( steps )
        prompt_components = {
            "steps"                      : steps,
            "responses"                  : [ ],
            "response_tag_names"         : [ [ "thoughts" ], [ "code" ], [ "returns", "example", "explanation" ] ],
            "running_history"            : "",
            "xml_formatting_instructions": [
                xml_formatting_instructions_step_1, xml_formatting_instructions_step_2, xml_formatting_instructions_step_3
            ]
        }
        
        return prompt_components
    
    def _get_df_metadata( self ):
        
        head = self.df.head( 3 ).to_xml( index=False )
        head = head + self.df.tail( 3 ).to_xml( index=False )
        head = head.replace( "data>", "lists>" ).replace( "<?xml version='1.0' encoding='utf-8'?>", "" )
        
        value_counts = self.df.list_name.value_counts()
        
        return head, value_counts
    
    # add main method
if __name__ == "__main__":
    
    question = "What's on my to do list for today?"
    
    todolist_agent = IncrementalTodoListAgent( question=question, debug=False, verbose=False, auto_debug=False, inject_bugs=False )
    todolist_agent.run_prompts()
    