import re

from flask import url_for

from lib.agents.date_and_time_agent            import DateAndTimeAgent
from lib.agents.receptionist_agent import ReceptionistAgent
from lib.app.fifo_queue                        import FifoQueue
from lib.agents.todo_list_agent                import TodoListAgent
from lib.agents.calendaring_agent              import CalendaringAgent

# from lib.agents.agent_function_mapping        import FunctionMappingAgent

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
        
        # Salutations to be stripped by a brute force method until the router parses them off for us
        self.salutations = [ "computer", "little", "buddy", "pal", "ai", "jarvis", "alexa", "siri", "hal", "einstein",
            "jeeves", "alfred", "watson", "samwise", "sam", "hawkeye", "oye", "hey", "there", "you", "yo",
            "hi", "hello", "hola", "good", "morning", "afternoon", "evening", "night", "buenas", "buenos", "buen", "tardes",
            "noches", "dias", "día", "tarde", "greetings", "my", "dear", "dearest", "esteemed", "assistant", "receptionist", "friend"
        ]
        
    def set_llm( self, cmd_llm_in_memory, cmd_llm_tokenizer ):
        
        self.cmd_llm_in_memory = cmd_llm_in_memory
        self.cmd_llm_tokenizer = cmd_llm_tokenizer
    
    def parse_salutations( self, transcription ):
        
        # from lib.utils.util_stopwatch import Stopwatch
        # timer = Stopwatch( "parse_salutations()" )
        
        # Normalize the transcription by removing extra spaces after punctuation
        # From: https://chat.openai.com/share/5783e1d5-c9ce-4503-9338-270a4c9095b2
        words = transcription.split()
        prefix_holder = [ ]
        
        # Find the index where salutations stop
        index = 0
        for word in words:
            if word.strip( ',.:;!?' ).lower() in self.salutations:
                prefix_holder.append( word )
                index += 1
            else:
                break
        
        # Get the remaining string after salutations
        remaining_string = ' '.join( words[ index: ] )
        
        return ' '.join( prefix_holder ), remaining_string
    
    
    def push_job( self, question ):
        
        self.push_counter += 1
        salutations, question = self.parse_salutations( question )
        
        du.print_banner( f"push_job( '{salutations}: {question}' )", prepend_nl=True )
        threshold = self.config_mgr.get( "snapshot_similiarity_threshold", default=90.0, return_type="float" )
        print( f"push_job(): Using snapshot similarity threshold of [{threshold}]" )
        
        # We're searching for similar snapshots without any salutations prepended to the question.
        similar_snapshots = self.snapshot_mgr.get_snapshots_by_question( question, threshold=threshold )
        print()
        
        # if we've got a similar snapshot then go ahead and push it onto the queue
        if len( similar_snapshots ) > 0:
        
            best_snapshot = similar_snapshots[ 0 ][ 1 ]
            best_score    = similar_snapshots[ 0 ][ 0 ]
            
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
            job.add_synonymous_question( question, salutation=salutations, score=best_score )
            
            job.run_date     = du.get_current_datetime()
            job.push_counter = self.push_counter
            job.id_hash      = SolutionSnapshot.generate_id_hash( job.push_counter, job.run_date )
            
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
            
            print( "No similar snapshots found, calling routing LLM..." )
            
            # Note the distinction between salutation and the question: all agents except the receptionist get the question only.
            # The receptionist gets the salutation plus the question to help it decide how it will respond.
            salutation_plus_question = salutations + " " + question
            salutation_plus_question.strip()

            # We're going to give the routing function maximum information, hence including the salutation with the question
            # ¡OJO! I know this is a tad adhoc-ish, but it's what we want... for the moment at least
            command, args = self._get_routing_command( salutation_plus_question )
            
            starting_a_new_job = "Starting a new {agent_type} job, I'll be right back."
            ding_for_new_job   = False
            # if command == "none":
            #     msg = "Hmm... I'm not certain what to do with that question, Could you rephrase and try again?"
            if command == "agent router go to calendar":
                agent = CalendaringAgent( question=question, push_counter=self.push_counter, debug=True, verbose=False, auto_debug=self.auto_debug, inject_bugs=self.inject_bugs )
                self.push( agent )
                msg = starting_a_new_job.format( agent_type="calendaring" )
                ding_for_new_job = True
            elif command == "agent router go to todo list":
                agent = TodoListAgent( question=question, push_counter=self.push_counter, debug=True, verbose=False, auto_debug=self.auto_debug, inject_bugs=self.inject_bugs )
                self.push( agent )
                msg = starting_a_new_job.format( agent_type="todo list")
                ding_for_new_job = True
            elif command == "agent router go to date and time":
                agent = DateAndTimeAgent( question=question, push_counter=self.push_counter, debug=True, verbose=False, auto_debug=self.auto_debug, inject_bugs=self.inject_bugs )
                self.push( agent )
                msg = starting_a_new_job.format( agent_type="date and time")
                ding_for_new_job = True
            elif command == "agent router go to receptionist" or command == "none":
                agent = ReceptionistAgent( question=salutation_plus_question, push_counter=self.push_counter, debug=True, verbose=False, auto_debug=self.auto_debug, inject_bugs=self.inject_bugs )
                self.push( agent )
                msg = "Hmm... Let me think about that..."
                
            else:
                msg = "TO DO: Implement command " + command
            
            if ding_for_new_job: self.socketio.emit( 'notification_sound_update', { 'soundFile': '/static/gentle-gong.mp3' } )
            
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
    
# Add me
if __name__ == "__main__":
    
    queue = TodoFifoQueue( None, None, None )
    input_string = "Good morning, my dearest receptionist. How are you feeling today?"
    # input_string = "Greetings little buddy! What's your name?"
    salutations, question = queue.parse_salutations( input_string )
    print( salutations )
    print( question )