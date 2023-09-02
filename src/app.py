import json
import os
import time
from subprocess import PIPE, run

import lib.util as du
import lib.util_stopwatch as sw
from fifo_queue import FifoQueue

from flask import Flask, request, make_response
from flask_cors import CORS
import flask

from duckduckgo_search import ddg

import whisper
import base64

# Dependencies for socket I/O prototyping
import requests
from flask import Flask, render_template, send_file, url_for
from flask_socketio import SocketIO
from random import random
from threading import Lock
from datetime import datetime

# print( "os.getcwd() [{}]".format( os.getcwd() ) )
# print( "GENIE_IN_THE_BOX_ROOT [{}]".format( os.getenv( "GENIE_IN_THE_BOX_ROOT" ) ) )

import genie_client as gc
import multimodal_munger as mmm
import lib.util_stopwatch as sw
import lib.util_langchain as ul
from solution_snapshot_mgr import SolutionSnapshotManager

# print( "Flask version [{}]".format( flask.__version__ ) )

"""
Globally visible queue object
"""
jobs_todo_queue = FifoQueue()
jobs_done_queue = FifoQueue()
jobs_run_queue  = FifoQueue()

"""
Background Threads
"""
todo_thread = None
done_thread = None
run_thread  = None
thread_lock = Lock()

announcement_delay = 0
connection_count   = 0

app = Flask( __name__ )
# Props to StackOverflow for this workaround:https://stackoverflow.com/questions/25594893/how-to-enable-cors-in-flask
CORS( app )
socketio = SocketIO( app, cors_allowed_origins='*' )
app.config['SERVER_NAME'] = '127.0.0.1:7999'

path_to_snapshots = os.path.join( du.get_project_root(), "src/conf/long-term-memory/solutions/" )
snapshot_mgr = SolutionSnapshotManager( path_to_snapshots, debug=True, verbose=True )

"""
Track the todo Q
"""
def track_todo_thread():
    
    print( "Tracking job TODO queue..." )
    while True:
        
        # print( du.get_current_datetime() )
        socketio.emit( 'time_update', { "date": du.get_current_datetime() } )
        
        if jobs_todo_queue.has_changed():
            
            print( "TODO Q size has changed" )
            socketio.emit( 'todo_update', { 'value': jobs_todo_queue.size() } )
            
            with app.app_context():
                url = url_for( 'get_audio' ) + f"?tts_text={jobs_todo_queue.size()} jobs waiting"
            
            print( f"Emitting TODO url [{url}]..." )
            socketio.emit( 'audio_update', { 'audioURL': url } )
            
            # Add a little bit of sleep time between when this audio event is passed to the client and the done Q audio event is passed
            announcement_delay = 2
        else:
            announcement_delay = 0
            
        socketio.sleep( 2 )

"""
Track the done Q
"""
def track_done_thread():
    
    print( "Tracking job DONE queue..." )
    while True:
        
        print( du.get_current_datetime() )
        socketio.emit( 'time_update', { "date": du.get_current_datetime() } )
        
        if jobs_done_queue.has_changed():
            print( "Done Q size has changed" )
            socketio.emit( 'done_update', { 'value': jobs_done_queue.size() } )
            
            with app.app_context():
                url = url_for( 'get_audio' ) + f"?tts_text={jobs_done_queue.size()} jobs finished"
            
            print( f"Emitting DONE url [{url}]..." )
            socketio.sleep( announcement_delay )
            socketio.emit( 'audio_update', { 'audioURL': url } )
        # else:
        #     socketio.emit('no_change', {'value': jobs_done_queue.size(), "date": uj.get_current_datetime()})
        
        socketio.sleep( 3 )


def track_running_thread():
    
    print( "Simulating job run execution..." )
    while True:
        
        print( "Jobs running @ " + du.get_current_datetime() )
        
        if not jobs_todo_queue.is_empty():
            
            job = jobs_todo_queue.pop()
            jobs_run_queue.push( job )
            
            socketio.emit( 'run_update', { 'value': jobs_run_queue.size() } )
            with app.app_context():
                url = url_for( 'get_audio' ) + f"?tts_text={jobs_run_queue.size()} jobs running"
            
            print( f"Emitting RUN url [{url}]..." )
            socketio.emit( 'audio_update', { 'audioURL': url } )
            
            # Point to the head of the queue without popping it
            running_job = jobs_run_queue.head()
            timer = sw.Stopwatch( f"Executing [{running_job.question}]..." )
            results = ul.assemble_and_run_solution( running_job.code, du.get_project_root() + "/src/conf/long-term-memory/events.csv", debug=True )
            timer.print( "Done!", use_millis=True )
            du.print_banner( "¡TODO: Uncomment job.complete() once access to GPT has been restored!", expletive=True, end="\n" )
            
            du.print_banner( f"Results for [{running_job.question}]", prepend_nl=True, end="\n" )
            if results[ "return_code" ] != 0:
                print( results[ "response" ] )
            else:
                response = results[ "response" ]
                for line in response.split( "\n" ): print( "* " + line )
                print()
            running_job.answer = results[ "response" ]
            
            #
            # job.complete(
            #     "I don't know, beats the hell out of me!",
            #     [ "foo = 31", "bar = 17", "total = foo + bar", "total" ],
            #     "I did this and then I did that, and then something else."
            # )
            print( running_job.to_jsons( verbose=False) )
            jobs_done_queue.push( running_job )
            
            # Remove the job at the head of the queue
            jobs_run_queue.pop()
            socketio.emit( 'run_update', { 'value': jobs_run_queue.size() } )
        
        else:
            print( "no jobs to pop from todo Q " )
        
        socketio.sleep( 10 )
        
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
    
    du.print_banner( f"Question: [{question}]", prepend_nl=True )
    similar_snapshots = snapshot_mgr.get_snapshots_by_question( question )
    print()
    
    if len( similar_snapshots ) > 0:
        
        lines_of_code = similar_snapshots[ 0 ][ 1 ].code
        if len( lines_of_code ) > 0:
            du.print_banner( f"Code for [{similar_snapshots[ 0 ][ 1 ].question}]:" )
        else:
            du.print_banner( "Code: NONE found?" )
        for line in lines_of_code:
            print( line )
        if len( lines_of_code ) > 0:
            print()
            
        job = similar_snapshots[ 0 ][ 1 ]
        # print( job.to_json() )
        
        jobs_todo_queue.push( job )
        return f'Job [{question}] added to queue. queue size [{jobs_todo_queue.size()}]'
    
    else:
        
        return f'No similar snapshots found, job [{question}] NOT added to queue. queue size [{jobs_todo_queue.size()}]'


@app.route( "/pop", methods=[ "GET" ] )
def pop():
    
    popped_job = jobs_todo_queue.pop()
    return f'Job [{popped_job}] popped from queue. queue size [{jobs_todo_queue.size()}]'

@app.route( "/get_audio", methods=[ "GET" ] )
def get_audio():
    
    tts_text = request.args.get( "tts_text" )
    # ¡OJO! This is a hack to get around the fact that the docker container can't see the host machine's IP address
    # TODO: find a way to get the ip6 address dynamically
    tts_url = "http://172.17.0.4:5002/api/tts?text=" + tts_text
    tts_url = tts_url.replace( " ", "%20" )
    
    du.print_banner( f"Fetching [{tts_url}]" )
    response = requests.get( tts_url )
    path = du.get_project_root() + "/io/tts.wav"
    
    # commands = [ "wget", "-O", path, tts_url ]
    #
    # results = run( commands, stdout=PIPE, stderr=PIPE, universal_newlines=True )
    #
    # if results.returncode != 0:
    #     print()
    #     response = "ERROR:\n{}".format( results.stderr.strip() )
    #     path = du.get_project_root() + "/io/failed-to-fetch-tts-file.wav"
    #     print( response )
    #
    # return send_file( path, mimetype="audio/wav" )
    
    # Check if the request was successful
    if response.status_code == 200:
        
        # Write the content of the response to a file
        with open( path, "wb" ) as audio_file:
            audio_file.write( response.content )
    else:
        print( f"Failed to get UPDATED audio file: {response.status_code}" )
        path = du.get_project_root() + "/io/failed-to-fetch-tts-file.wav"
    
    return send_file( path, mimetype="audio/wav" )


def generate_html_list( fifo_queue ):
    
    html_list = [ ]
    for job in fifo_queue.queue:
        html_list.append( job.get_html() )
    
    return html_list


@app.route( '/get_queue/<queue_name>', methods=[ 'GET' ] )
def get_queue( queue_name ):
    if queue_name == "todo":
        jobs = generate_html_list( jobs_todo_queue )
    elif queue_name == "done":
        jobs = generate_html_list( jobs_done_queue )
    elif queue_name == "run":
        jobs = generate_html_list( jobs_run_queue )
    else:
        return json.dumps( { "error": "Invalid queue name. Please specify either 'todo' or 'done'." } )
    
    return json.dumps( { f"{queue_name}_jobs": jobs } )

"""
Decorator for connect
"""
@socketio.on( "connect" )
def connect():
    
    global connection_count
    connection_count += 1
    print( f"[{connection_count}] Clients connected" )
    
    global todo_thread
    global done_thread
    global exec_thread
    
    with thread_lock:
        if todo_thread is None:
            todo_thread = socketio.start_background_task( track_todo_thread )
            done_thread = socketio.start_background_task( track_done_thread )
            exec_thread = socketio.start_background_task( track_running_thread )


"""
Decorator for disconnect
"""
@socketio.on( "disconnect" )
def disconnect():
    
    global connection_count
    connection_count -= 1
    # sanity check size
    if connection_count < 0:
        connection_count = 0
        
    print( f"Client [{request.sid}] disconnected" )
    print( f"[{connection_count}] Clients connected" )
    

@app.route( "/api/ask-ai-text" )
def ask_ai_text():
    question = request.args.get( "question" )
    
    print( "Calling ask_chat_gpt_text() [{}]...".format( question ) )
    result = genie_client.ask_chat_gpt_text( question, preamble="What does this mean?" ).strip()
    print( "Result: [{}]".format( result ) )
    
    response = make_response( result )
    response.headers.add( "Access-Control-Allow-Origin", "*" );
    
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
    response.headers.add( "Access-Control-Allow-Origin", "*" );
    
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
    
    print( "Transcribing {}...".format( path ) )
    timer = sw.Stopwatch()
    result = model.transcribe( path )
    timer.print( "Done!", use_millis=True, end="\n\n" )
    
    result = result[ "text" ].strip()
    
    print( "Result: [{}]".format( result ) )
    
    # Fetch last response processed... ¡OJO! This is absolutely NOT thread safe!
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
    
    # Write JSON string to file system.
    last_response = munger.get_json()
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
    prompt_feedback = request.args.get( "prompt_verbose", default="verbose" )
    
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
# genie_client = gc.GenieClient( tts_address="127.0.0.1:5000", runtime_context="local", tts_output_path="/Users/rruiz/Projects/projects-sshfs/io/text-to-vox.wav" )
genie_client = gc.GenieClient()

if __name__ == "__main__":
    app.run( debug=True )
