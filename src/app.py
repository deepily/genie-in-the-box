import json
import os
import pprint
import time

from threading         import Lock

from duckduckgo_search import ddg

import whisper
import base64

# from flask import
from flask_cors import CORS

# Dependencies for socket I/O prototyping
import requests
from flask          import Flask, request, make_response, send_file, url_for
from flask_socketio import SocketIO

# print( "os.getcwd() [{}]".format( os.getcwd() ) )
# print( "GENIE_IN_THE_BOX_ROOT [{}]".format( os.getenv( "GENIE_IN_THE_BOX_ROOT" ) ) )
# print( "Flask version [{}]".format( flask.__version__ ) )

import genie_client       as gc
import multimodal_munger  as mmm
import calendaring_agent  as ca

import lib.util             as du
import lib.util_stopwatch   as sw
import lib.util_code_runner as ulc


from genie_client         import GPT_3_5
from genie_client         import GPT_4

from solution_snapshot import SolutionSnapshot
from calendaring_agent import CalendaringAgent

from solution_snapshot_mgr import SolutionSnapshotManager
from fifo_queue            import FifoQueue

"""
Globally visible queue object
"""
jobs_todo_queue = FifoQueue()
jobs_done_queue = FifoQueue()
jobs_run_queue  = FifoQueue()

"""
Background Threads
"""
clock_thread = None
run_thread   = None
thread_lock  = Lock()
# Track the number of jobs we've pushed into the queue
push_count  = 1
# Track the number of client connections
connection_count   = 0

# TODO: find a way to get this address dynamically
tts_url_template = "http://192.168.0.188:5002/api/tts?text={tts_text}"

app = Flask( __name__ )
# Props to StackOverflow for this workaround:https://stackoverflow.com/questions/25594893/how-to-enable-cors-in-flask
CORS( app )
socketio = SocketIO( app, cors_allowed_origins='*' )
app.config['SERVER_NAME'] = '127.0.0.1:7999'

path_to_snapshots = os.path.join( du.get_project_root(), "src/conf/long-term-memory/solutions/" )
print( "path_to_snapshots [{}]".format( path_to_snapshots ) )
snapshot_mgr = SolutionSnapshotManager( path_to_snapshots, debug=True, verbose=True )

EVENTS_DF_PATH = "/src/conf/long-term-memory/events.csv"

"""
Track the todo Q
"""
def enter_clock_loop():
    
    print( "Tracking job TODO queue..." )
    while True:
        
        socketio.emit( 'time_update', { "date": du.get_current_datetime() } )
        socketio.sleep( 1 )

def enter_running_loop():
    
    print( "Starting job run loop..." )
    while True:
        
        if not jobs_todo_queue.is_empty():
            
            print( "Jobs running @ " + du.get_current_datetime() )
            run_timer = sw.Stopwatch( "Starting run timer..." )
            
            print( "popping one job from todo Q" )
            job = jobs_todo_queue.pop()
            socketio.emit( 'todo_update', { 'value': jobs_todo_queue.size() } )
            
            jobs_run_queue.push( job )
            socketio.emit( 'run_update', { 'value': jobs_run_queue.size() } )
            
            # Point to the head of the queue without popping it
            running_job = jobs_run_queue.head()
            
            if type( running_job ) == CalendaringAgent:
                
                # Limit the length to 64 characters
                msg = f"Running CalendaringAgent for [{running_job.question[ :64 ]}]..."
                du.print_banner( msg=msg, prepend_nl=True )
                
                agent_timer = sw.Stopwatch( msg=msg )
                response_dict    = running_job.run_prompt()
                code_response    = running_job.run_code()
                formatted_output = running_job.format_output()
                agent_timer.print( "Done!", use_millis=True )
                
                du.print_banner( f"Job [{running_job.question}] complete...", prepend_nl=True, end="\n" )
                
                if code_response[ "response_code" ] == "0":
                    
                    # If we've arrived at this point, then we've successfully run the agentic part of this job,
                    # But we still need to recast the agent object as a solution snapshot
                    running_job = SolutionSnapshot.create_solution_snapshot( running_job )
                    
                    running_job.update_runtime_stats( agent_timer )
                    print( f"Writing job [{running_job.question}] to file..." )
                    running_job.write_to_file()
                    print( f"Writing job [{running_job.question}] to file... Done!" )
                    
                    du.print_banner( "running_job.runtime_stats", prepend_nl=True )
                    pprint.pprint( running_job.runtime_stats )
                else:
                    du.print_banner( f"Error running [{running_job.question[ :64 ]}]", prepend_nl=True )
                    print( code_response[ "output" ] )
                    
                
            else:
                msg = f"Executing SolutionSnapshot code for [{running_job.question[ :64 ]}]..."
                du.print_banner( msg=msg, prepend_nl=True )
                timer = sw.Stopwatch( msg=msg )
                results = ulc.assemble_and_run_solution( running_job.code, path=EVENTS_DF_PATH, debug=False )
                timer.print( "Done!", use_millis=True )
                du.print_banner( f"Results for [{running_job.question}]", prepend_nl=True, end="\n" )
                
                if results[ "return_code" ] != 0:
                    print( results[ "output" ] )
                    running_job.answer = results[ "output" ]
                else:
                    response = results[ "output" ]
                    running_job.answer = response
                    
                    for line in response.split( "\n" ): print( "* " + line )
                    print()
                    
                    msg = "Calling GPT to reformat the job.answer..."
                    timer = sw.Stopwatch( msg )
                    preamble = get_preamble( running_job.last_question_asked, running_job.answer )
                    running_job.answer_conversational = genie_client.ask_chat_gpt_text( query=running_job.answer, preamble=preamble, model=GPT_3_5 )
                    timer.print( "Done!", use_millis=True )
                    
                    # Arrive if we've arrived at this point, then we've successfully run the job
                    run_timer.print( "Full run complete ", use_millis=True )
                    running_job.update_runtime_stats( run_timer )
                    du.print_banner( f"Job [{running_job.question}] complete!", prepend_nl=True, end="\n" )
                    print( f"Writing job [{running_job.question}] to file..." )
                    running_job.write_to_file()
                    print( f"Writing job [{running_job.question}] to file... Done!" )
                    du.print_banner( "running_job.runtime_stats", prepend_nl=True )
                    pprint.pprint( running_job.runtime_stats )
                
            jobs_run_queue.pop()
            socketio.emit( 'run_update', { 'value': jobs_run_queue.size() } )
            jobs_done_queue.push( running_job )
            socketio.emit( 'done_update', { 'value': jobs_done_queue.size() } )
            
            with app.app_context():
                # url = url_for( 'get_tts_audio' ) + f"?tts_text=1 job finished. {running_job.last_question_asked}? {running_job.answer_conversational}"
                url = url_for( 'get_tts_audio' ) + f"?tts_text={running_job.answer_conversational}"
                
            print( f"Emitting DONE url [{url}]..." )
            socketio.emit( 'audio_update', { 'audioURL': url } )
        
        else:
            # print( "No jobs to pop from todo Q " )
            socketio.sleep( 1 )
        
def get_preamble( question, answer ):

    preamble = f"""
    I'm going to provide you with a question and answer pair like this:

    Q: <question>
    A: <answer>
    
    Rephrase the terse answer in a conversational manner that matches the tone of the question.
    Your rephrasing of the terse answer must only answer the question and no more.
    Do not include the question in your answer.
    
    Q: {question}
    A: {answer}"""
    
    return preamble
    
@app.route( "/" )
def root():
    return "Genie in the box flask server root"

"""
Serve static files
"""
@app.route( "/static/<filename>" )
def serve_static( filename ):
    
    return app.send_static_file( filename )


@app.route( "/push", methods=[ "GET" ] )
def push():
    
    question = request.args.get( 'question' )
    
    return push_job_to_todo_queue( question )

def push_job_to_todo_queue( question ):
    
    global push_count
    push_count += 1
    
    du.print_banner( f"Question: [{question}]", prepend_nl=True )
    similar_snapshots = snapshot_mgr.get_snapshots_by_question( question )
    print()
    
    if len( similar_snapshots ) > 0:
        
        # Get the best match: best[ 0 ] is the score, best[ 1 ] is the snapshot
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
        job.add_synonymous_question( question, best_score )
        
        # Update date & count so that we can create id_hash
        job.run_date     = du.get_current_datetime()
        job.push_counter = push_count
        job.id_hash      = SolutionSnapshot.generate_id_hash( job.push_counter, job.run_date )
        
        print()
        
        # Only notify the poster if there are jobs ahead of them in the todo Q
        if jobs_todo_queue.size() != 0:
            # Generate plurality suffix
            suffix = "s" if jobs_todo_queue.size() > 1 else ""
            with app.app_context():
                url = url_for( 'get_tts_audio' ) + f"?tts_text={jobs_todo_queue.size()} job{suffix} before this one"
            print( f"Emitting TODO url [{url}]..." )
            socketio.emit( 'audio_update', { 'audioURL': url } )
        else:
            print( "No jobs ahead of this one in the todo Q" )
        
        jobs_todo_queue.push( job )
        socketio.emit( 'todo_update', { 'value': jobs_todo_queue.size() } )
        
        return f'Job added to queue. Queue size [{jobs_todo_queue.size()}]'
    
    else:
        
        calendaring_agent = CalendaringAgent( EVENTS_DF_PATH, question=question, push_counter=push_count, debug=True, verbose=True )
        jobs_todo_queue.push( calendaring_agent )
        socketio.emit( 'audio_update', { 'audioURL': url_for( 'get_tts_audio' ) + "?tts_text=Working on it!" } )
        socketio.emit( 'todo_update', { 'value': jobs_todo_queue.size() } )
        
        return f'No similar snapshots found, adding NEW CalendaringAgent to TODO queue. Queue size [{jobs_todo_queue.size()}]'

# Rethink how/why we're killing/popping jobs in the todo queue
# @app.route( "/pop", methods=[ "GET" ] )
# def pop():
#
#     popped_job = jobs_todo_queue.pop()
#     return f'Job [{popped_job}] popped from queue. queue size [{jobs_todo_queue.size()}]'

def get_tts_url( tts_text ):
    
    # ¡OJO! This is a hack to get around the fact that the docker container can't see the host machine's IPv6 address
    # TODO: find a way to get the ip6 address dynamically
    tts_url = tts_url_template.format( tts_text=tts_text )
    tts_url = tts_url.replace( " ", "%20" )

    return tts_url

def get_audio_file( tts_text ):
    
    tts_url = get_tts_url( tts_text )
    
    du.print_banner( f"Fetching [{tts_url}]" )
    response = requests.get( tts_url )
    path = du.get_project_root() + "/io/tts.wav"
    
    # Check if the request was successful
    if response.status_code == 200:
        
        # Write the content of the response to a file
        with open( path, "wb" ) as audio_file:
            audio_file.write( response.content )
    else:
        print( f"Failed to get UPDATED audio file: {response.status_code}" )
        path = du.get_project_root() + "/io/failed-to-fetch-tts-file.wav"
    
    return send_file( path, mimetype="audio/wav" )

@app.route( "/get_tts_audio", methods=[ "GET" ] )
def get_tts_audio():
    
    tts_text = request.args.get( "tts_text" )

    return get_audio_file( tts_text )

def generate_html_list( fifo_queue, descending=False, add_play_button=False ):
    
    html_list = [ ]
    for job in fifo_queue.queue_list:
        html_list.append( job.get_html() )
    
    if descending: html_list.reverse()
    
    return html_list


@app.route( '/get_queue/<queue_name>', methods=[ 'GET' ] )
def get_queue( queue_name ):
    
    if queue_name == "todo":
        jobs = generate_html_list( jobs_todo_queue, descending=True )
    elif queue_name == "done":
        jobs = generate_html_list( jobs_done_queue, descending=True )
    elif queue_name == "run":
        jobs = generate_html_list( jobs_run_queue )
    else:
        return json.dumps( { "error": "Invalid queue name. Please specify either 'todo' or 'done'." } )
    
    return json.dumps( { f"{queue_name}_jobs": jobs } )


@app.route( '/get_answer/<string:id_hash>', methods=[ 'GET' ] )
def get_answer( id_hash ):
    
    answer_conversational = jobs_done_queue.get_by_id_hash( id_hash ).answer_conversational
    
    return get_audio_file( answer_conversational)

"""
Decorator for connect
"""
@socketio.on( "connect" )
def connect():
    
    global connection_count
    connection_count += 1
    print( f"[{connection_count}] Clients connected" )
    
    global clock_thread
    global run_thread
    
    with thread_lock:
        if clock_thread is None:
            clock_thread = socketio.start_background_task( enter_clock_loop )
            run_thread   = socketio.start_background_task( enter_running_loop )

"""
Decorator for disconnect
"""
@socketio.on( "disconnect" )
def disconnect():
    
    global connection_count
    connection_count -= 1
    # sanity check size
    if connection_count < 0: connection_count = 0
    
    print( f"Client [{request.sid}] disconnected" )
    print( f"[{connection_count}] Clients connected" )
    

@app.route( "/api/ask-ai-text" )
def ask_ai_text():
    
    question = request.args.get( "question" )
    
    print( "Calling ask_chat_gpt_text() [{}]...".format( question ) )
    result = genie_client.ask_chat_gpt_text( question, preamble="What does this mean?" ).strip()
    print( "Result: [{}]".format( result ) )
    
    response = make_response( result )
    response.headers.add( "Access-Control-Allow-Origin", "*" )
    
    return response


@app.route( "/api/proofread" )
def proofread():
    
    question = request.args.get( "question" )
    
    timer = sw.Stopwatch()
    preamble = "You are an expert proofreader. Correct grammar. Correct tense. Correct spelling. Correct contractions. Correct punctuation. Correct capitalization. Correct word choice. Correct sentence structure. Correct paragraph structure. Correct paragraph length. Correct paragraph flow. Correct paragraph topic. Correct paragraph tone. Correct paragraph style. Correct paragraph voice. Correct paragraph mood. Correct paragraph theme."
    result = genie_client.ask_chat_gpt_text( question, preamble=preamble )
    print( result )
    timer.print( "Proofread", use_millis=True )
    
    response = make_response( result )
    response.headers.add( "Access-Control-Allow-Origin", "*" )
    
    return response

@app.route( "/api/upload-and-transcribe-mp3", methods=[ "POST" ] )
def upload_and_transcribe_mp3_file():
    
    print( "upload_and_transcribe_mp3_file() called" )
    
    prefix = request.args.get( "prefix" )
    prompt_key = request.args.get( "prompt_key", default="generic" )
    prompt_feedback = request.args.get( "prompt_verbose", default="verbose" )
    print( "    prefix: [{}]".format( prefix ) )
    print( "prompt_key: [{}]".format( prompt_key ) )
    
    decoded_audio = base64.b64decode( request.data )
    
    path = gc.docker_path.format( "recording.mp3" )
    
    print( "Saving file recorded audio bytes to [{}]...".format( path ), end="" )
    with open( path, "wb" ) as f:
        f.write( decoded_audio )
    print( " Done!" )
    
    timer = sw.Stopwatch( "Transcribing {}...".format( path ) )
    result = model.transcribe( path )
    timer.print( "Done!", use_millis=True, end="\n\n" )
    
    result = result[ "text" ].strip()
    
    print( "Result: [{}]".format( result ) )
    
    # Fetch last response processed... ¡OJO! This is pretty kludgey, but it works for now. TODO: Do better!
    if os.path.isfile( du.get_project_root() + "/io/last_response.json" ):
        with open( du.get_project_root() + "/io/last_response.json" ) as json_file:
            last_response = json.load( json_file )
    else:
        last_response = None
        
    munger = mmm.MultiModalMunger( result, prefix=prefix, prompt_key=prompt_key, debug=True, verbose=False, last_response=last_response )
    
    if munger.is_text_proofread():
        
        print( "Proofreading text... ", end="" )
        timer = sw.Stopwatch()
        
        if prompt_feedback.lower() == "verbose":
            prompt_feedback = "DO"
        else:
            prompt_feedback = "DO NOT"
        
        preamble = munger.prompt.format( prompt_feedback=prompt_feedback )
        response = genie_client.ask_chat_gpt_text( "```" + munger.transcription + "```", preamble=preamble )
        timer.print( "Done!" )
        
        munger.transcription = response
        munger.results = response
    
    elif munger.is_ddg_search():
        
        print( "Fetching AI data for [{}]...".format( munger.transcription ) )
        results = ddg( munger.transcription, region="wt-wt", safesearch="Off", time="y", max_results=20 )
        print( results )
        munger.results = results
        
    elif munger.is_agent():
        
        print( "Posting [{}] to the agent's todo queue...".format( munger.transcription ) )
        munger.results = push_job_to_todo_queue( munger.transcription )
    
    # Write JSON string to file system.
    last_response = munger.get_jsons()
    du.write_string_to_file( du.get_project_root() + "/io/last_response.json", last_response )

    return last_response


@app.route( "/api/run-raw-prompt-text" )
def run_raw_prompt_text():
    
    for key in request.__dict__:
        # print( "key [{}] value [{}]".format( key, request.__dict__[ key ] ), end="\n\n" )
        print( "key [{}]".format( key ) )
    print()
    print( "request.args: [{}]".format( request.args ) )
    print( "request.data: [{}]".format( request.data ) )
    print( "query_string: [{}]".format( request.query_string ) )
    
    prompt_and_content = request.args.get( "prompt_and_content" )
    # prompt_feedback = request.args.get( "prompt_verbose", default="verbose" )
    
    print( "Running prompt [{}]...".format( prompt_and_content ) )
    
    timer = sw.Stopwatch()
    response = genie_client.ask_chat_gpt_using_raw_prompt_and_content( prompt_and_content ).replace( "```", "" ).strip()
    timer.print( "Done!" )
    
    return response


@app.route( "/api/upload-and-transcribe-wav", methods=[ "POST" ] )
def upload_and_transcribe_wav_file():
    
    # Get prefix for multimodal munger
    prefix = request.args.get( "prefix" )
    
    file = request.files[ "file" ]
    timestamp = str( time.time() ).replace( ".", "-" )
    temp_file = "/tmp/{}-{}".format( timestamp, file.filename )
    
    print( "Saving file [{}] to [{}]...".format( file.filename, temp_file ), end="" )
    file.save( temp_file )
    print( " Done!" )
    
    print( "Transcribing {}...".format( temp_file ) )
    result = model.transcribe( temp_file )
    print( "Done!", end="\n\n" )
    
    transcribed_text = result[ "text" ].strip()
    print( "transcribed_text: [{}]".format( transcribed_text ) )
    
    print( "Deleting temp file [{}]...".format( temp_file ), end="" )
    os.remove( temp_file )
    print( " Done!" )
    
    munger = mmm.MultiModalMunger( transcribed_text, prefix=prefix, debug=True, verbose=False )
    
    return munger.transcription

@app.route( "/api/vox2text" )
def vox_2_text():
    path = request.args.get( "path" )
    
    print( "Transcribing {}...".format( path ) )
    result = model.transcribe( path )
    print( "Done!", end="\n\n" )
    
    print( "Result: [{}]".format( result[ "text" ] ) )
    print( result[ "text" ] )
    
    return result[ "text" ].strip()

print( "Loading whisper engine... ", end="" )
model = whisper.load_model( "base.en" )
print( "Done!" )

print( os.getenv( "FALSE_POSITIVE_API_KEY" ) )
genie_client = gc.GenieClient()

if __name__ == "__main__":
    
    app.run( debug=True )
