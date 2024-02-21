from lib.utils import util as du

from lib.app.configuration_manager import ConfigurationManager

from lib.agents.llm import Llm

class RawOutputFormatter:
    
    def __init__(self, question, raw_output, routing_command, debug=False, verbose=False ):
        
        self.debug       = debug
        self.verbose     = verbose
        
        self.question    = question
        self.raw_output  = raw_output
        
        self.config_mgr  = ConfigurationManager( env_var_name="GIB_CONFIG_MGR_CLI_ARGS", debug=self.debug, verbose=self.verbose, silent=True )

        self.routing_command_paths = {
            "agent router go to date and time": self.config_mgr.get( "raw_output_formatter_date_and_time" ),
            "agent router go to calendar"     : self.config_mgr.get( "raw_output_formatter_calendaring" ),
            "agent router go to weather"      : self.config_mgr.get( "raw_output_formatter_weather" ),
            "agent router go to todo list"    : self.config_mgr.get( "raw_output_formatter_todo_list" )
        }
        self.llms                  = {
            "agent router go to date and time": self.config_mgr.get( "formatter_llm_for_date_and_time" ),
            "agent router go to calendar"     : self.config_mgr.get( "formatter_llm_for_calendaring" ),
            "agent router go to weather"      : self.config_mgr.get( "formatter_llm_for_weather" ),
            "agent router go to todo list"    : self.config_mgr.get( "formatter_llm_for_todo_list" )
        }
        self.routing_command       = routing_command
        self.formatting_template   = du.get_file_as_string( du.get_project_root() + self.routing_command_paths.get( routing_command ) )
        self.prompt                = self._get_prompt()
        
        default_url                = self.config_mgr.get( "tgi_server_codegen_url", default=None )
        self.llm                   = Llm( self.llms[ routing_command ], self.prompt, default_url=default_url, debug=self.debug, verbose=self.verbose )
    
    def format_output( self ):
        
        return self.llm.query_llm()
    
    def _get_prompt( self ):
        
        # ¡OJO! This is a pretty simple case, but there will be formatting types that will require more sophisticated formatting
        return self.formatting_template.format( question=self.question, raw_output=self.raw_output )
    
if __name__ == "__main__":
    
    # routing_command = "agent router go to date and time"
    routing_command = "agent router go to calendar"
    # question        = "What time is it now?"
    # question        = "What day is today?"
    # question        = "Is it daytime or nighttime?"
    # question        = "Is today Tuesday, February 20, 2024?"
    # question        = "Is today Tuesday?"
    # question        = "Is today Tuesday or Wednesday?"
    # question        = "Is it time to go to bed yet?"
    # question        = "What time is it now?"
    # question        = "Is it daylight savings time?"
    # raw_output      = "8:57PM EDT, Monday, February 19, 2024"
    
    question        = "Who has birthdays this week?"
    raw_output      = """
    <data>
  <row>
    <index>57</index>
    <start_date>2024-02-20 00:00:00</start_date>
    <end_date>2024-02-20 00:00:00</end_date>
    <start_time>00:00</start_time>
    <end_time>23:59</end_time>
    <event_type>birthday</event_type>
    <recurrent>True</recurrent>
    <recurrence_interval>2 month</recurrence_interval>
    <priority_level>medium</priority_level>
    <name>Tom Ruiz</name>
    <relationship>brother</relationship>
    <description_who_what_where>Tom Ruiz's birthday party at their favorite bar</description_who_what_where>
  </row>
  <row>
    <index>71</index>
    <start_date>2024-02-23 00:00:00</start_date>
    <end_date>2024-02-23 00:00:00</end_date>
    <start_time>00:00</start_time>
    <end_time>23:59</end_time>
    <event_type>birthday</event_type>
    <recurrent>True</recurrent>
    <recurrence_interval>4 day</recurrence_interval>
    <priority_level>high</priority_level>
    <name>Alice</name>
    <relationship>aunt</relationship>
    <description_who_what_where>Alice's birthday party at their favorite bar</description_who_what_where>
  </row>
</data>
    """
    formatter = RawOutputFormatter( question, raw_output, routing_command, debug=False, verbose=False)
    print( formatter.format_output() )