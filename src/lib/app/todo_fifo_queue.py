from flask import url_for

from lib.app.fifo_queue                        import FifoQueue
from lib.agents.todo_list_agent                import TodoListAgent
from lib.agents.calendaring_agent              import CalendaringAgent

# from lib.agents.incremental_calendaring_agent import IncrementalCalendaringAgent
# from lib.agents.agent_function_mapping        import FunctionMappingAgent
# from lib.memory.solution_snapshot_mgr         import SolutionSnapshotManager

from lib.utils import util     as du
from lib.utils import util_xml as dux

import lib.app.util_llm_client  as llm_client

from lib.memory.solution_snapshot import SolutionSnapshot

class TodoFifoQueue( FifoQueue ):
    def __init__( self, socketio, snapshot_mgr, app, config_mgr=None, debug=False, verbose=False, silent=False ):
        
        super().__init__()
        self.debug        = debug
        self.verbose      = verbose
        self.silent       = silent
        
        self.socketio     = socketio
        self.snapshot_mgr = snapshot_mgr
        self.app          = app
        self.push_counter = 0
        self.config_mgr   = config_mgr
        
        self.auto_debug   = False if config_mgr is None else config_mgr.get( "auto_debug",  default=False, return_type="boolean" )
        self.inject_bugs  = False if config_mgr is None else config_mgr.get( "inject_bugs", default=False, return_type="boolean" )
        
        # Set by set_llm() below
        self.cmd_llm_in_memory = None
        self.cmd_llm_tokenizer = None
        
    def set_llm( self, cmd_llm_in_memory, cmd_llm_tokenizer ):
        
        self.cmd_llm_in_memory = cmd_llm_in_memory
        self.cmd_llm_tokenizer = cmd_llm_tokenizer
        
    
    def push_job( self, question ):
        
        self.push_counter += 1
        
        du.print_banner( f"push_job( '{question}' )", prepend_nl=True )
        threshold = self.config_mgr.get( "snapshot_similiarity_threshold", default=90.0, return_type="float" )
        print( f"push_job(): Using snapshot similarity threshold of [{threshold}]" )
        similar_snapshots = self.snapshot_mgr.get_snapshots_by_question( question, threshold=threshold )
        print()
        
        # if we've got a similar snapshot then go ahead and push it onto the queue
        if len( similar_snapshots ) > 0:
            
            best_snapshot = similar_snapshots[ 0 ][ 1 ]
            best_score = similar_snapshots[ 0 ][ 0 ]
            
            lines_of_code = best_snapshot.code
            if len( lines_of_code ) > 0:
                du.print_banner( f"Code for [{best_snapshot.question}]:" )
            else:
                du.print_banner( "Code: NONE found?" )
            for line in lines_of_code:
                print( line )
            if len( lines_of_code ) > 0:
                print()
            
            job = best_snapshot.get_copy()
            print( "Python object ID for copied job: " + str( id( job ) ) )
            job.debug   = self.debug
            job.verbose = self.verbose
            job.add_synonymous_question( question, best_score )
            
            job.run_date = du.get_current_datetime()
            job.push_counter = self.push_counter
            job.id_hash = SolutionSnapshot.generate_id_hash( job.push_counter, job.run_date )
            
            print()
            
            if self.size() != 0:
                suffix = "s" if self.size() > 1 else ""
                with self.app.app_context():
                    url = url_for( 'get_tts_audio' ) + f"?tts_text={self.size()} job{suffix} before this one"
                print( f"Emitting TODO url [{url}]..." )
                self.socketio.emit( 'audio_update', { 'audioURL': url } )
            else:
                print( "No jobs ahead of this one in the todo Q" )
            
            self.push( job )
            self.socketio.emit( 'todo_update', { 'value': self.size() } )
            
            return f'Job added to queue. Queue size [{self.size()}]'
        
        else:
            
            self.socketio.emit( 'notification_sound_update', { 'soundFile': '/static/gentle-gong.mp3' } )
            print( "No similar snapshots found, calling routing LLM..." )
            
            command, args = self._get_routing_command( question )
            
            if command == "none":
                msg = "Hmm... I'm not certain what to do with that question, Could you rephrase and try again?"
            elif command == "agent router go to calendar":
                calendaring_agent = CalendaringAgent( question=question, routing_command=command, push_counter=self.push_counter, debug=True, verbose=False, auto_debug=self.auto_debug, inject_bugs=self.inject_bugs )
                self.push( calendaring_agent )
                msg = f"Starting a new calendaring job, I'll be right back."
            elif command == "agent router go to todo list":
                todo_list_agent = TodoListAgent( question=question, routing_command=command, push_counter=self.push_counter, debug=True, verbose=False, auto_debug=self.auto_debug, inject_bugs=self.inject_bugs )
                self.push( todo_list_agent )
                msg = f"Starting a new todo list job, I'll be right back."
            else:
                msg = "TO DO: Implement command " + command
            
            with self.app.app_context():
                url = url_for( 'get_tts_audio' ) + "?tts_text=" + msg
            print( f"Emitting url [{url}]..." )
            self.socketio.emit( 'audio_update', { 'audioURL': url } )
            
            return msg
            
            # agent = FunctionMappingAgent( question=question, push_counter=self.push_counter, debug=True, verbose=True )
            # self.push( agent )
            # self.socketio.emit( 'todo_update', { 'value': self.size() } )
            #
            # return f'No similar snapshots found, adding NEW FunctionMappingAgent to TODO queue. Queue size [{self.size()}]'

    def _get_routing_command( self, question ):
        
        router_prompt_template = du.get_file_as_string( du.get_project_root() + self.config_mgr.get( "agent_router_prompt_path_wo_root" ) )
        
        response = llm_client.query_llm_in_memory(
            self.cmd_llm_in_memory,
            self.cmd_llm_tokenizer,
            router_prompt_template.format( voice_command=question ),
            model_name=self.config_mgr.get( "vox_command_llm_name" ),
            device=self.config_mgr.get( "vox_command_llm_device_map", default="cuda:0" )
        )
        print( f"LLM response: [{response}]" )
        # Parse results
        command = dux.get_value_by_xml_tag_name( response, "command" )
        args    = dux.get_value_by_xml_tag_name( response, "args" )
        
        return command, args