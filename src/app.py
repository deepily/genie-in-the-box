import json
import os
import time
from subprocess import PIPE, run

import lib.util as du
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

app = Flask( __name__ )

# Props to StackOverflow for this workaround:https://stackoverflow.com/questions/25594893/how-to-enable-cors-in-flask
CORS( app )

# print( "Flask version [{}]".format( flask.__version__ ) )

job_queue = FifoQueue()

"""
Background Thread
"""
thread = None
thread_lock = Lock()

app = Flask( __name__ )
socketio = SocketIO( app, cors_allowed_origins='*' )

app.config[ 'SERVER_NAME' ] = '127.0.0.1:7999'

"""
Get current date time
"""
def get_current_datetime():
    
    now = datetime.now()
    return now.strftime( "%m/%d/%Y %H:%M:%S" )

"""
Simulate jobs waiting to be processed
"""
def background_thread():
    print( "Tracking job queue size..." )
    while True:
        print( get_current_datetime() )
        if job_queue.has_changed():
            print( "Q size has changed" )
            socketio.emit( 'time_update', { 'value': job_queue.size(), "date": get_current_datetime() } )
            with app.app_context():
                url = url_for( 'get_audio' ) + f"?tts_text={job_queue.size()} jobs waiting"
            print( f"Emitting url [{url}]..." )
            socketio.emit( 'audio_file', { 'audioURL': url } )
        else:
            socketio.emit( 'no_change', { 'value': job_queue.size(), "date": get_current_datetime() } )
        
        socketio.sleep( 4 )
@app.route( "/" )
def root():
    return "Genie in the box flask server root"

"""
Serve static files
"""
@app.route( '/static/<filename>' )
def serve_static( filename ):
    return app.send_static_file( filename )


@app.route( '/push', methods=[ 'GET' ] )
def push():
    job_name = request.args.get( 'job_name' )
    print( job_name )
    job_name = f'{job_queue.get_push_count() + 1}th job: {job_name}'
    
    job_queue.push( job_name )
    return f'Job [{job_name}] added to stack. Stack size [{job_queue.size()}]'


@app.route( '/pop', methods=[ 'GET' ] )
def pop():
    popped_job = job_queue.pop()
    return f'Job [{popped_job}] popped from stack. Stack size [{job_queue.size()}]'


@app.route( '/get_audio', methods=[ 'GET' ] )
def get_audio():
    
    tts_text = request.args.get( 'tts_text' )
    # ¡OJO! This is a hack to get around the fact that the docker container can't see the host machine's IP address
    # TODO: find a way to get the ip6 address dynamically
    tts_url = "http://172.17.0.1:5002/api/tts?text=" + tts_text
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
    # return send_file( path, mimetype='audio/wav' )
    
    # Check if the request was successful
    if response.status_code == 200:
        # Write the content of the response to a file
        with open( path, 'wb' ) as audio_file:
            audio_file.write( response.content )
    else:
        print( f"Failed to get UPDATED audio file: {response.status_code}" )
        path = du.get_project_root() + "/io/failed-to-fetch-tts-file.wav"
    
    return send_file( path, mimetype='audio/wav' )


"""
Decorator for connect
"""
@socketio.on( 'connect' )
def connect():
    
    print( 'Client connected' )
    global thread
    with thread_lock:
        if thread is None:
            thread = socketio.start_background_task( background_thread )


"""
Decorator for disconnect
"""
@socketio.on( 'disconnect' )
def disconnect():
    
    print( 'Client disconnected', request.sid )
    
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
        results = ddg( munger.transcription, region='wt-wt', safesearch='Off', time='y', max_results=20 )
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
