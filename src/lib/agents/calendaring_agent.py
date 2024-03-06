import json

from lib.agents.agent_base import AgentBase
# from lib.agents.llm import Llm


class CalendaringAgent( AgentBase ):
    
    def __init__( self, question=None, push_counter=-1, debug=False, verbose=False, auto_debug=False, inject_bugs=False ):
        
        super().__init__( df_path_key="path_to_events_df_wo_root", question=question, routing_command="agent router go to calendar", push_counter=push_counter, debug=debug, verbose=verbose, auto_debug=auto_debug, inject_bugs=inject_bugs )

        self.prompt       = self._get_prompt()
        
        self.xml_response_tag_names = [ "question", "thoughts", "code", "example", "returns", "explanation" ]
        
    def _get_prompt( self ):
        
        column_names, unique_event_types, head = self._get_metadata()
        
        return self.prompt_template.format( question=self.question, column_names=column_names, unique_event_types=unique_event_types, head=head )
    
    def _get_metadata( self ):
        
        column_names = self.df.columns.tolist()
        unique_event_types = self.df[ "event_type" ].unique().tolist()
        
        head = self.df.head( 2 ).to_xml( index=False )
        head = head + self.df.tail( 2 ).to_xml( index=False )
        head = head.replace( "data>", "events>" ).replace( "<?xml version='1.0' encoding='utf-8'?>", "" )
        
        return column_names, unique_event_types, head
        
    
# Add main method
if __name__ == "__main__":
    
    agent = CalendaringAgent( question="What concerts do I have this week?", debug=True, auto_debug=True )
    # print( agent.prompt )
    response_dict = agent.run_prompt()
    # Print dictionary as Jason string
    print( json.dumps( response_dict, indent=4 ) )
    
    code_response_dict = agent.run_code()
    print( json.dumps( code_response_dict, indent=4 ) )
    
    answer = agent.format_output()
    print( answer )