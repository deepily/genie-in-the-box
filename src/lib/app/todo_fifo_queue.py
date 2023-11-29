from flask import url_for
from lib.app.fifo_queue import FifoQueue
from lib.agents.agent_calendaring import CalendaringAgent
from lib.agents.agent_function_mapping import FunctionMappingAgent
from lib.memory.solution_snapshot_mgr import SolutionSnapshotManager

from lib.utils.util import print_banner, get_current_datetime
from lib.memory.solution_snapshot import SolutionSnapshot


class TodoFifoQueue( FifoQueue ):
    def __init__( self, socketio, snapshot_mgr, app, path_to_events_df ):
        
        super().__init__()
        
        self.socketio = socketio
        self.snapshot_mgr = snapshot_mgr
        self.app = app
        self.push_counter = 0
        self.path_to_events_df = path_to_events_df
    
    def push_job( self, question ):
        
        self.push_counter += 1
        
        print_banner( f"push_job( '{question}' )", prepend_nl=True )
        similar_snapshots = self.snapshot_mgr.get_snapshots_by_question( question, threshold=95.0 )
        print()
        
        # if we've got a similar snapshot then go ahead and push it onto the queue
        if len( similar_snapshots ) > 0:
            
            best_snapshot = similar_snapshots[ 0 ][ 1 ]
            best_score = similar_snapshots[ 0 ][ 0 ]
            
            lines_of_code = best_snapshot.code
            if len( lines_of_code ) > 0:
                print_banner( f"Code for [{best_snapshot.question}]:" )
            else:
                print_banner( "Code: NONE found?" )
            for line in lines_of_code:
                print( line )
            if len( lines_of_code ) > 0:
                print()
            
            job = best_snapshot.get_copy()
            print( "Python object ID for copied job: " + str( id( job ) ) )
            job.add_synonymous_question( question, best_score )
            
            job.run_date = get_current_datetime()
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
            
            msg = f"No similar snapshots found, adding NEW CalendaringAgent to TODO queue. Queue size [{self.size()}]"
            print( msg )
            calendaring_agent = CalendaringAgent( self.path_to_events_df, question=question, push_counter=self.push_counter, debug=True, verbose=False )
            self.push( calendaring_agent )
            return msg
            
            # agent = FunctionMappingAgent( "/src/conf/long-term-memory/events.csv", question=question, push_counter=self.push_counter, debug=True, verbose=True )
            # self.push( agent )
            # self.socketio.emit( 'todo_update', { 'value': self.size() } )
            #
            # return f'No similar snapshots found, adding NEW FunctionMappingAgent to TODO queue. Queue size [{self.size()}]'
