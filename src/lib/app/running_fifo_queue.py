
from lib.app.fifo_queue import FifoQueue
from lib.agents.agent_calendaring import CalendaringAgent
from lib.agents.agent_function_mapping import FunctionMappingAgent
from lib.memory.solution_snapshot import SolutionSnapshot
# from lib.utils.util import print_banner, get_current_datetime, truncate_string
# from lib.utils.util_stopwatch import Stopwatch

import lib.utils.util as du
import lib.utils.util_stopwatch as sw

from flask import url_for
import traceback
import pprint


class RunningFifoQueue( FifoQueue ):
    def __init__( self, app, socketio, snapshot_mgr, jobs_todo_queue, jobs_done_queue, jobs_dead_queue ):
        super().__init__()
        self.app             = app
        self.socketio        = socketio
        self.snapshot_mgr    = snapshot_mgr
        self.jobs_todo_queue = jobs_todo_queue
        self.jobs_done_queue = jobs_done_queue
        self.jobs_dead_queue = jobs_dead_queue
    
    def enter_running_loop( self ):
        
        print( "Starting job run loop..." )
        while True:
            
            if not self.jobs_todo_queue.is_empty():
                
                print( "Jobs running @ " + du.get_current_datetime() )
                run_timer = sw.Stopwatch( "Starting run timer..." )
                
                print( "popping one job from todo Q" )
                job = self.jobs_todo_queue.pop()
                self.socketio.emit( 'todo_update', { 'value': self.jobs_todo_queue.size() } )
                
                self.push( job )
                self.socketio.emit( 'run_update', { 'value': self.size() } )
                
                # Point to the head of the queue without popping it
                running_job = self.head()
                
                # Limit the length of the question string
                truncated_question = du.truncate_string( running_job.question, max_len=64 )
                
                if type( running_job ) == FunctionMappingAgent:
                    running_job = self._handle_function_mapping_agent( running_job, truncated_question )
                    
                if type( running_job ) == CalendaringAgent:
                    running_job = self._handle_calendaring_agent( running_job, truncated_question )
                    
                else:
                    running_job = self._handle_solution_snapshot( running_job, truncated_question, run_timer )
                    
                self.pop()
                self.socketio.emit( 'run_update', { 'value': self.size() } )
                self.jobs_done_queue.push( running_job )
                self.socketio.emit( 'done_update', { 'value': self.jobs_done_queue.size() } )
                
                url = self._get_audio_url( running_job.answer_conversational )
                
                print( f"Emitting DONE url [{url}]...", end="\n\n" )
                self.socketio.emit( 'audio_update', { 'audioURL': url } )
            
            else:
                # print( "No jobs to pop from todo Q " )
                self.socketio.sleep( 1 )

    def _handle_function_mapping_agent( self, running_job, truncated_question ):
        
        self.socketio.emit( 'audio_update', { 'audioURL': self._get_audio_url( "Searching my memory" ) } )
        print( running_job.get_html() )
        msg = f"Running FunctionMappingAgent for [{truncated_question}]..."
        agent_timer = sw.Stopwatch( msg=msg )
        
        response_dict = running_job.run_prompt()
        
        if running_job.is_runnable():
            
            code_response = running_job.run_code()
            
            if code_response[ "return_code" ] != 0:
                
                running_job = self._handle_error_case( code_response, running_job, truncated_question )
            
            else:
                
                du.print_banner( f"Job [{running_job.question}] complete...", prepend_nl=True, end="\n" )
                
                # If we've arrived at this point, then we've successfully run the agentic part of this job
                # recast the agent object as a solution snapshot object and add it to the snapshot manager
                running_job = SolutionSnapshot.create( running_job )
                
                running_job.update_runtime_stats( agent_timer )
                
                # Adding this snapshot to the snapshot manager serializes it to the local filesystem
                print( f"Adding job [{truncated_question}] to snapshot manager..." )
                self.snapshot_mgr.add_snapshot( running_job )
                print( f"Adding job [{truncated_question}] to snapshot manager... Done!" )
                
                du.print_banner( "running_job.runtime_stats", prepend_nl=True )
                pprint.pprint( running_job.runtime_stats )
        else:
            
            print( f"Executing [{truncated_question}] as a open ended calendaring agent job instead..." )
            self.socketio.emit( 'notification_sound_update', { 'soundFile': '/static/gentle-gong.mp3' } )
            running_job = CalendaringAgent( "/src/conf/long-term-memory/events.csv", question=running_job.question, push_counter=running_job.push_counter, debug=True, verbose=True )
            
        return running_job
        
    def _handle_error_case( self, response, running_job, truncated_question ):
        
        du.print_banner( f"Error running code for [{truncated_question}]", prepend_nl=True )
        
        for line in response[ "output" ].split( "\n" ): print( line )
        
        self.pop()
        self.socketio.emit( 'run_update', { 'value': self.size() } )
        
        url = self._get_audio_url( "I'm sorry Dave, I'm afraid I can't do that." )
        self.socketio.emit( 'audio_update', { 'audioURL': url } )
        self.jobs_dead_queue.push( running_job )
        self.socketio.emit( 'dead_update', { 'value': self.jobs_dead_queue.size() } )
        
        return running_job
        
    def _handle_calendaring_agent( self, running_job, truncated_question ):
        
        msg = f"Running CalendaringAgent for [{truncated_question}]..."
        
        code_response = {
            "return_code": -1,
            "output"     : "ERROR: Output not yet generated!?!"
        }
        
        agent_timer = sw.Stopwatch( msg=msg )
        try:
            response_dict    = running_job.run_prompt()
            code_response    = running_job.run_code()
            formatted_output = running_job.format_output()
        
        except Exception as e:
            
            stack_trace = traceback.format_tb( e.__traceback__ )
            running_job = self._handle_error_case( stack_trace, running_job, truncated_question )
            
        agent_timer.print( "Done!", use_millis=True )
        
        du.print_banner( f"Job [{running_job.question}] complete...", prepend_nl=True, end="\n" )
        
        if code_response[ "return_code" ] == 0:
            
            # If we've arrived at this point, then we've successfully run the agentic part of this job
            # recast the agent object as a solution snapshot object and add it to the snapshot manager
            running_job = SolutionSnapshot.create( running_job )
            
            running_job.update_runtime_stats( agent_timer )
            
            # Adding this snapshot to the snapshot manager serializes it to the local filesystem
            print( f"Adding job [{truncated_question}] to snapshot manager..." )
            self.snapshot_mgr.add_snapshot( running_job )
            print( f"Adding job [{truncated_question}] to snapshot manager... Done!" )
            
            du.print_banner( "running_job.runtime_stats", prepend_nl=True )
            pprint.pprint( running_job.runtime_stats )
        
        else:
            
            running_job = self._handle_error_case( code_response, running_job, truncated_question )
            
        return running_job
            
    def _handle_solution_snapshot( self, running_job, truncated_question, run_timer ):
        
        msg = f"Executing SolutionSnapshot code for [{truncated_question}]..."
        du.print_banner( msg=msg, prepend_nl=True )
        timer = sw.Stopwatch( msg=msg )
        _ = running_job.run_code()
        timer.print( "Done!", use_millis=True )
        
        msg = "Calling GPT to reformat the job.answer..."
        timer = sw.Stopwatch( msg )
        _ = running_job.format_output()
        timer.print( "Done!", use_millis=True )
        
        # If we've arrived at this point, then we've successfully run the job
        run_timer.print( "Full run complete ", use_millis=True )
        running_job.update_runtime_stats( run_timer )
        du.print_banner( f"Job [{running_job.question}] complete!", prepend_nl=True, end="\n" )
        print( f"Writing job [{running_job.question}] to file..." )
        running_job.write_current_state_to_file()
        print( f"Writing job [{running_job.question}] to file... Done!" )
        du.print_banner( "running_job.runtime_stats", prepend_nl=True )
        pprint.pprint( running_job.runtime_stats )
        
        return running_job
    
    def _get_audio_url( self, text ):

        with self.app.app_context():
            url = url_for( 'get_tts_audio' ) + f"?tts_text={text}"

        return url