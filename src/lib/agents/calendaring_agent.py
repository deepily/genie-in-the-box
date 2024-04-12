import json

from lib.agents.agent_base import AgentBase
# from lib.agents.llm import Llm


class CalendaringAgent( AgentBase ):
    
    def __init__( self, question="", last_question_asked="", routing_command="agent router go to calendaring", push_counter=-1, debug=False, verbose=False, auto_debug=False, inject_bugs=False ):
        
        super().__init__( df_path_key="path_to_events_df_wo_root", question=question, last_question_asked=last_question_asked, routing_command=routing_command, push_counter=push_counter, debug=debug, verbose=verbose, auto_debug=auto_debug, inject_bugs=inject_bugs )

        self.prompt       = self._get_prompt()
        
        self.xml_response_tag_names = [ "question", "thoughts", "code", "example", "returns", "explanation" ]
        
    def _get_prompt( self ):
        
        column_names, unique_event_types, head = self._get_metadata()
        
        return self.prompt_template.format( question=self.last_question_asked, column_names=column_names, unique_event_types=unique_event_types, head=head )
    
    def _get_metadata( self ):
        
        column_names = self.df.columns.tolist()
        unique_event_types = self.df[ "event_type" ].unique().tolist()
        
        head = self.df.head( 2 ).to_xml( index=False )
        head = head + self.df.tail( 2 ).to_xml( index=False )
        head = head.replace( "data>", "events>" ).replace( "<?xml version='1.0' encoding='utf-8'?>", "" )
        
        return column_names, unique_event_types, head
        
    def restore_from_serialized_state( self, file_path ):
        
        print( "WARNING: CalendaringAgent.restore_from_serialized_state( file_path=" + file_path + " ) NOT implemented yet." )
    
# Add main method
if __name__ == "__main__":
    
    running_job = CalendaringAgent( question="What did we talk about yesterday?", debug=True, auto_debug=True )
    # print( agent.prompt )
    response_dict = running_job.run_prompt()
    # Print dictionary as Jason string
    print( json.dumps( response_dict, indent=4 ) )
    
    if running_job.is_code_runnable():
        
        code_response_dict = running_job.run_code()
        print( json.dumps( code_response_dict, indent=4 ) )
        
        answer = running_job.format_output()
        print( answer )
        
    else:
        print( "Code not runnable?!?" )
        
    if running_job.code_ran_to_completion() and running_job.formatter_ran_to_completion():
        print( "Job complete..." )
    else:
        print( "Job FAILED?" )
