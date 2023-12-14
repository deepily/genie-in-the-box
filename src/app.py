import json
import os
import pprint
import time
import traceback

from threading         import Lock

from duckduckgo_search import ddg

# import whisper
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

import base64

# from flask import
from flask_cors import CORS

# Dependencies for socket I/O prototyping
import requests
from flask          import Flask, request, make_response, send_file, url_for
from flask_socketio import SocketIO
from openai         import OpenAI

from lib.clients import genie_client as gc
from lib.app import multimodal_munger as mmm

import lib.utils.util as du
import lib.utils.util_stopwatch as sw
import lib.utils.util_code_runner as ulc


# from lib.clients.genie_client import GPT_3_5
#
# from lib.memory.solution_snapshot import SolutionSnapshot
# from lib.agents.calendaring_agent import CalendaringAgent

from lib.memory.solution_snapshot_mgr import SolutionSnapshotManager
from lib.app.fifo_queue               import FifoQueue
from lib.app.running_fifo_queue       import RunningFifoQueue
from lib.app.todo_fifo_queue          import TodoFifoQueue
from lib.app.configuration_manager    import ConfigurationManager

"""
Instantiate configuration manager
"""
config_path     = du.get_project_root() + "/src/conf/gib-app.ini"
config_block_id = "Genie in the Box: Development"
config_mgr      = ConfigurationManager( config_path, config_block_id=config_block_id, debug=False, verbose=False, silent=False )

config_mgr.print_configuration( brackets=True )

app_debug                          = config_mgr.get_config( "app_debug",   default=False, return_type="boolean" )
app_verbose                        = config_mgr.get_config( "app_verbose", default=False, return_type="boolean" )
app_config_server_name             = config_mgr.get_config( "app_config_server_name" )
path_to_events_df_wo_root          = config_mgr.get_config( "path_to_events_df_wo_root" )
path_to_snapshots_dir_wo_root      = config_mgr.get_config( "path_to_snapshots_dir_wo_root" )
tts_url_template                   = config_mgr.get_config( "tts_url_template" )

whisper_pipeline = None

clock_thread = None
run_thread   = None
thread_lock  = Lock()

# Track the number of jobs we've pushed into the queue
push_count  = 1
# Track the number of client connections
connection_count   = 0


app = Flask( __name__ )
# Props to StackOverflow for this workaround:https://stackoverflow.com/questions/25594893/how-to-enable-cors-in-flask
CORS( app )
socketio = SocketIO( app, cors_allowed_origins='*' )
app.config[ 'SERVER_NAME' ] = app_config_server_name

path_to_snapshots = du.get_project_root() + path_to_snapshots_dir_wo_root
# du.print_banner( f"path_to_snapshots [{path_to_snapshots}]" )
snapshot_mgr = SolutionSnapshotManager( path_to_snapshots, debug=app_debug, verbose=app_verbose )

"""
Globally visible queue objects
"""
jobs_todo_queue = TodoFifoQueue( socketio, snapshot_mgr, app, path_to_events_df_wo_root )
jobs_done_queue = FifoQueue()
jobs_dead_queue = FifoQueue()
jobs_run_queue  = RunningFifoQueue( app, socketio, snapshot_mgr, jobs_todo_queue, jobs_done_queue, jobs_dead_queue )

def enter_clock_loop():
    
    print( "enter_clock_loop..." )
    while True:
        
        socketio.emit( 'time_update', { "date": du.get_current_datetime() } )
        socketio.sleep( 1 )


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
    
    return jobs_todo_queue.push_job( question )
    
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

def get_tts_audio_file( tts_text ):
    
    du.print_banner( f"TTS text [{tts_text}] )", prepend_nl=True )
    tts_generation_strategy = config_mgr.get_config( "tts_generation_strategy", default="local" )
    
    if tts_generation_strategy == "openai":
        
        client   = OpenAI( api_key=du.get_api_key( "openai" ) )
        path     = du.get_project_root() + "/io/openai-speech.mp3"
        mimetype = "audio/mpeg"
        
        # ¡OJO! this too could benefit from runtime configurable parameters
        response = client.audio.speech.create(
            model="tts-1",
            voice="alloy",
            speed=1.125,
            input=tts_text
        )
        response.stream_to_file( path )
    
    else:
        
        print( f"Fetching audio file from local service...", end="" )
        mimetype = "audio/wav"
        tts_url  = get_tts_url( tts_text )
        response = requests.get( tts_url )
        path     = du.get_project_root() + "/io/tts.wav"

        # Check if the request was successful
        if response.status_code == 200:

            # Write the content of the response to a file
            with open( path, "wb" ) as audio_file:
                audio_file.write( response.content )
            print( f"Fetching audio file... Done!" )
        else:
            print( f"Failed to get UPDATED audio file: {response.status_code}" )
            path = du.get_project_root() + "/io/failed-to-fetch-tts-file.wav"
    
    return send_file( path, mimetype=mimetype )

@app.route( "/get_tts_audio", methods=[ "GET" ] )
def get_tts_audio():
    
    tts_text = request.args.get( "tts_text" )

    return get_tts_audio_file( tts_text )

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
    elif queue_name == "run":
        jobs = generate_html_list( jobs_run_queue )
    elif queue_name == "dead":
        jobs = generate_html_list( jobs_dead_queue, descending=True )
    elif queue_name == "done":
        jobs = generate_html_list( jobs_done_queue, descending=True )

    else:
        return json.dumps( { "error": "Invalid queue name. Please specify either 'todo' or 'done'." } )
    
    return json.dumps( { f"{queue_name}_jobs": jobs } )


@app.route( '/get-answer/<string:id_hash>', methods=[ 'GET' ] )
def get_answer( id_hash ):
    
    answer_conversational = jobs_done_queue.get_by_id_hash( id_hash ).answer_conversational
    
    return get_tts_audio_file( answer_conversational )


@app.route( '/delete-snapshot/<string:id_hash>', methods=[ 'GET' ] )
def delete_snapshot( id_hash ):
    
    # Fetch the object so that we can delete it from the file system too
    to_be_deleted = jobs_done_queue.get_by_id_hash( id_hash )
    # to_be_deleted.delete_file()
    
    jobs_done_queue.delete_by_id_hash( id_hash )
    
    snapshot_mgr.delete_snapshot( to_be_deleted.question, delete_file=True )
    
    socketio.emit( 'done_update', { 'value': jobs_done_queue.size() } )
    socketio.emit( 'notification_sound_update', { 'soundFile': '/static/gentle-gong.mp3' } )
    
    return f"Deleted snapshot [{id_hash}]"

# create an endpoint that refreshes the contents of the solution snapshot manager
@app.route( '/reload-snapshots', methods=[ 'GET' ] )
def reload_snapshots():
    
    snapshot_mgr.load_snapshots()
    
    return f"Snapshot manager refreshed"

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
            run_thread   = socketio.start_background_task( jobs_run_queue.enter_running_loop )

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
    
    load_model_once()
    
    prefix          = request.args.get( "prefix" )
    prompt_key      = request.args.get( "prompt_key",     default="generic" )
    prompt_feedback = request.args.get( "prompt_verbose", default="verbose" )
    
    print( "    prefix: [{}]".format( prefix ) )
    print( "prompt_key: [{}]".format( prompt_key ) )
    
    decoded_audio = base64.b64decode( request.data )
    
    path = gc.docker_path.format( "recording.mp3" )
    
    print( "Saving file recorded audio bytes to [{}]...".format( path ), end="" )
    with open( path, "wb" ) as f:
        f.write( decoded_audio )
    print( " Done!" )
    
    timer  = sw.Stopwatch( f"Transcribing {path}..." )
    result = whisper_pipeline( path )
    timer.print( "Done!", use_millis=True, end="\n\n" )
    
    result = result[ "text" ].strip()
    
    print( "Result: [{}]".format( result ) )
    
    # Fetch last response processed... ¡OJO! This is pretty kludgey, but it works for now. TODO: Do better!
    last_response_path = "/io/last_response.json"
    if os.path.isfile( du.get_project_root() + last_response_path ):
        with open( du.get_project_root() + last_response_path ) as json_file:
            last_response = json.load( json_file )
    else:
        last_response = None
        
    munger = mmm.MultiModalMunger( result, prefix=prefix, prompt_key=prompt_key, debug=app_debug, verbose=app_verbose, last_response=last_response )
    
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
        munger.results = jobs_todo_queue.push_job( munger.transcription )
        
    # Write JSON string to file system.
    last_response = munger.get_jsons()
    du.write_string_to_file( du.get_project_root() + last_response_path, last_response )

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
    
    print( "upload_and_transcribe_wav_file() called" )
    load_model_once()
    
    # Get prefix for multimodal munger
    prefix = request.args.get( "prefix" )
    
    file = request.files[ "file" ]
    timestamp = str( time.time() ).replace( ".", "-" )
    temp_file = "/tmp/{}-{}".format( timestamp, file.filename )
    
    print( "Saving file [{}] to [{}]...".format( file.filename, temp_file ), end="" )
    file.save( temp_file )
    print( " Done!" )
    
    timer = sw.Stopwatch( msg=f"Transcribing {temp_file}..." )
    # result = model.transcribe( temp_file )
    result = whisper_pipeline( temp_file )
    timer.print( "Done!", use_millis=True, end="\n\n" )
    
    transcribed_text = result[ "text" ].strip()
    print( "transcribed_text: [{}]".format( transcribed_text ) )
    
    print( "Deleting temp file [{}]...".format( temp_file ), end="" )
    os.remove( temp_file )
    print( " Done!" )
    
    munger = mmm.MultiModalMunger( transcribed_text, prefix=prefix, debug=app_debug, verbose=app_verbose )
    
    return munger.transcription


# @app.route( "/api/load-model" )
# def load_model():
#
#     size = request.args.get( "size", default="base.en" )
#     if size not in [ "base.en", "small.en", "medium.en", "large" ]:
#         size = "base.en"
#
#     print( f"Model [{size}] requested. Loading..." )
#     global model, model_size
#     model_size = size
#     model      = whisper.load_model( model_size )
#     print( f"Model [{size}] requested. Loading... Done!" )
#
#     return f"Model [{size}] loaded"

# @app.route( "/api/get-model-size" )
# def get_model_size():
#
#     return model_size

# print( "Loading whisper engine... ", end="" )
# model_size  = "small.en"
# model = whisper.load_model( model_size )
# print( "Done!" )

def load_model():
    
    torch_dtype   = torch.bfloat16
    stt_device_id = config_mgr.get_config( "stt_device_id", default="cuda:0" )
    stt_model_id  = config_mgr.get_config( "stt_model_id" )
    
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        stt_model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True, use_flash_attention_2=True
    )
    model.to( stt_device_id )
    
    processor = AutoProcessor.from_pretrained( stt_model_id )
    
    pipe = pipeline(
        "automatic-speech-recognition",
        model=model,
        tokenizer=processor.tokenizer,
        feature_extractor=processor.feature_extractor,
        max_new_tokens=128,
        torch_dtype=torch_dtype,
        device=stt_device_id,
    )
    return pipe
    
def load_model_once():

    global whisper_pipeline
    if whisper_pipeline is None:
        print( "Loading distill whisper engine... ", end="" )
        whisper_pipeline = load_model()
        print( "Done!" )
    else:
        print( "Distill whisper engine already loaded" )
        
print( os.getenv( "FALSE_POSITIVE_API_KEY" ) )
genie_client = gc.GenieClient()

if __name__ == "__main__":
    
    app.run( debug=True )
