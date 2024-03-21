import json
import os
import time

from threading         import Lock

# from duckduckgo_search import ddg

import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

import base64
import flask

from flask_cors import CORS

import requests
from flask          import Flask, request, make_response, send_file
from flask_socketio import SocketIO
from openai         import OpenAI
from awq            import AutoAWQForCausalLM
from transformers   import AutoTokenizer

from lib.clients import genie_client as gc
from lib.app import multimodal_munger as mmm

import lib.utils.util              as du
import lib.utils.util_stopwatch    as sw
import lib.utils.util_xml          as dux

from lib.memory.solution_snapshot_mgr import SolutionSnapshotManager
from lib.app.fifo_queue               import FifoQueue
from lib.app.running_fifo_queue       import RunningFifoQueue
from lib.app.todo_fifo_queue          import TodoFifoQueue
from lib.app.configuration_manager    import ConfigurationManager

from ephemera.prompts.xml_fine_tuning_prompt_generator import XmlFineTuningPromptGenerator

"""
Instantiate configuration manager
"""
# grab the results of runtime environment export like this one:
# export GIB_FLASK_CLI_ARGS="config_path=/src/conf/gib-app.ini splainer_path=/src/conf/gib-app-splainer.ini config_block_id=Genie+in+the+Box:+Development" ...
# ...and convert it from a string to a list and finally, a dictionary
cli_args         = os.environ[ "GIB_CONFIG_MGR_CLI_ARGS" ].split( " " )
cli_args         = du.get_name_value_pairs( cli_args )

app_debug        = cli_args.get( "debug",   "False" ) == "True"
app_verbose      = cli_args.get( "verbose", "False" ) == "True"
app_silent       = cli_args.get( "silent",  "True"  ) == "True"

config_mgr       = None
config_block_id  = cli_args[ "config_block_id" ]
config_path      = du.get_project_root() + cli_args[ "config_path" ]
splainer_path    = du.get_project_root() + cli_args[ "splainer_path" ]

app_config_server_name        = None
path_to_snapshots_dir_wo_root = None
tts_local_url_template        = None
# path_to_events_df_wo_root     = None

def init_configuration( refresh=False ):

    
    global app_debug
    global app_verbose
    global app_silent
    global config_mgr
    global config_block_id
    
    config_mgr = ConfigurationManager( config_path=config_path, splainer_path=splainer_path, config_block_id=config_block_id, debug=app_debug, verbose=app_verbose, silent=app_silent )
    
    # We need to force a refresh, otherwise the configuration mgr singleton will not be updated
    if refresh:
        du.print_banner( "Refreshing configuration manager..." )
        config_mgr.init( config_path=config_path, splainer_path=splainer_path, config_block_id=config_block_id, debug=app_debug, verbose=app_verbose, silent=app_silent )
    
    config_mgr.print_configuration( brackets=True )
    
    # Running flask version 2.1.3
    print( f"Running flask version {flask.__version__}", end="\n\n" )
    
    global app_config_server_name
    global path_to_snapshots_dir_wo_root
    global tts_local_url_template
    # global path_to_events_df_wo_root
    
    app_debug                          = config_mgr.get( "app_debug",   default=False, return_type="boolean" )
    app_verbose                        = config_mgr.get( "app_verbose", default=False, return_type="boolean" )
    app_silent                         = config_mgr.get( "app_silent",  default=False, return_type="boolean" )
    
    app_config_server_name             = config_mgr.get( "app_config_server_name" )
    path_to_snapshots_dir_wo_root      = config_mgr.get( "path_to_snapshots_dir_wo_root" )
    tts_local_url_template             = config_mgr.get( "tts_local_url_template" )
    # path_to_events_df_wo_root          = config_mgr.get( "path_to_events_df_wo_root" )
    
init_configuration()

cmd_prompt_template = None
cmd_model           = None
cmd_tokenizer       = None
whisper_pipeline    = None
clock_thread        = None
run_thread          = None
thread_lock         = Lock()

# Track the number of jobs we've pushed into the queue
push_count       = 1
# Track the number of client connections
connection_count = 0

app = Flask( __name__ )
# Props to StackOverflow for this workaround:https://stackoverflow.com/questions/25594893/how-to-enable-cors-in-flask
CORS( app )
socketio = SocketIO( app, cors_allowed_origins='*' )
app.config[ 'SERVER_NAME' ] = app_config_server_name

path_to_snapshots = du.get_project_root() + path_to_snapshots_dir_wo_root
snapshot_mgr = SolutionSnapshotManager( path_to_snapshots, debug=app_debug, verbose=app_verbose )

"""
Globally visible queue objects
"""
jobs_todo_queue = TodoFifoQueue( socketio, snapshot_mgr, app, config_mgr, debug=app_debug, verbose=app_verbose, silent=app_silent )
jobs_done_queue = FifoQueue()
jobs_dead_queue = FifoQueue()
jobs_run_queue  = RunningFifoQueue( app, socketio, snapshot_mgr, jobs_todo_queue, jobs_done_queue, jobs_dead_queue, config_mgr=config_mgr )

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
    
def get_tts_url( tts_text ):
    
    tts_url = tts_local_url_template.format( tts_text=tts_text )
    tts_url = tts_url.replace( " ", "%20" )

    return tts_url

def get_tts_audio_file( tts_text ):
    
    du.print_banner( f"TTS text [{tts_text}] )", prepend_nl=True )
    tts_generation_strategy = config_mgr.get( "tts_generation_strategy", default="local" )
    
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

# create an endpoint that refreshes the contents of the config manager and reloads the solution snapshot manager
@app.route( '/api/init', methods=[ 'GET' ] )
def init():
    
    init_configuration( refresh=True )
    snapshot_mgr.load_snapshots()
    
    return f"¡Success!"

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


@app.route( "/api/proofread-sql" )
def proofread_sql():
    
    question = request.args.get( "question" )
    
    # timer = sw.Stopwatch()
    # # preamble = "You are an expert Database administrator, or DBA. You will receive two sentences, both of which are voice to text transcriptions. As such, they will contain numerous add spelling and word choices. Correct all syntactic and spelling errors to create a syntactically valid SQL command. Use the first sentence as the plain English context for the second sentence, which is the approximated SQL command."
    # preamble = "You are a helpful expert Database administrator, or DBA."
    # prompt_template = du.get_file_as_string( du.get_project_root() + "/src/conf/prompts/sql-proofreading-template.txt" )
    # sql_prompt      = prompt_template.format( voice_command=question )
    # result = genie_client.ask_chat_gpt_text( sql_prompt, preamble=preamble )
    # print( result )
    # timer.print( "Proofread SQL", use_millis=True )
    prompt_template = du.get_file_as_string( du.get_project_root() + "/src/conf/prompts/sql-proofreading-template.txt" )
    sql_prompt      = prompt_template.format( voice_command=question )
    
    for line in sql_prompt.split( "\n" ): print( line )
    
    tgi_url = config_mgr.get( "tgi_server_codegen_url" )
    du.print_banner( f"proofread_sql tgi_url: [{tgi_url}]" )
    
    xml_ftp_generator = XmlFineTuningPromptGenerator( tgi_url=tgi_url, debug=False, silent=True, init_prompt_templates=False )
    response = xml_ftp_generator.query_llm_tgi( sql_prompt, model_name="Phind-CodeLlama-34B-v2", max_new_tokens=1024, temperature=0.25, top_k=10, top_p=0.9, silent=False )
    print( response )
    response = dux.strip_all_white_space( response )
    print( response )
    sql = dux.get_value_by_xml_tag_name( response, "sql" )
    
    response = make_response( sql )
    # response = make_response( result )
    response.headers.add( "Access-Control-Allow-Origin", "*" )
    
    return response

@app.route( "/api/proofread-python" )
def proofread_python():
    
    question = request.args.get( "question" )
    
    # timer = sw.Stopwatch()
    # preamble = "You are an expert Database administrator, or DBA. You will receive two sentences, both of which are voice to text transcriptions. As such, they will contain numerous add spelling and word choices. Correct all syntactic and spelling errors to create a syntactically valid SQL command. Use the first sentence as the plain English context for the second sentence, which is the approximated SQL command."
    # result = genie_client.ask_chat_gpt_text( question, preamble=preamble )
    # print( result )
    # timer.print( "Proofread SQL", use_millis=True )
    prompt_template = du.get_file_as_string( du.get_project_root() + "/src/conf/prompts/python-proofreading-template.txt" )
    sql_prompt      = prompt_template.format( voice_command=question )
    
    tgi_url = config_mgr.get( "tgi_server_codegen_url" )
    du.print_banner( f"proofread_python tgi_url: [{tgi_url}]" )
    
    xml_ftp_generator = XmlFineTuningPromptGenerator( tgi_url=tgi_url, debug=False, silent=True, init_prompt_templates=False )
    response = xml_ftp_generator.query_llm_tgi( sql_prompt, model_name="Phind-CodeLlama-34B-v2", max_new_tokens=1024, temperature=0.25, top_k=10, top_p=0.9, silent=False )
    print( response )
    response = dux.strip_all_white_space( response )
    print( response )
    python = dux.get_value_by_xml_tag_name( response, "python" )
    
    response = make_response( python )
    response.headers.add( "Access-Control-Allow-Origin", "*" )
    
    return response
@app.route( "/api/upload-and-transcribe-mp3", methods=[ "POST" ] )
def upload_and_transcribe_mp3_file():
    
    print( "upload_and_transcribe_mp3_file() called" )
    
    load_stt_model_once()
    load_commands_llm_once()
    
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
        
    munger = mmm.MultiModalMunger(
        result, prefix=prefix, prompt_key=prompt_key, debug=app_debug, verbose=app_verbose, last_response=last_response,
        cmd_llm_in_memory=cmd_model,
        cmd_llm_tokenizer=cmd_tokenizer,
        cmd_prompt_template=cmd_prompt_template,
        cmd_llm_name=config_mgr.get( "vox_command_llm_name" ),
        cmd_llm_device=config_mgr.get( "vox_command_llm_device_map", default="cuda:0" )
    )

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
    
    # elif munger.is_ddg_search():
#         du.print_banner( "DDG search detected & ABORTED", prepend_nl=True, expletive=True, chunk="b0rk3d! " )
#         print( "Investigate why DGG Throws the following Stacktrace:" )
#         print( """File "/usr/local/lib/python3.11/site-packages/flask/cli.py", line 214, in locate_app
#     __import__(module_name)
#   File "/var/genie-in-the-box/src/app.py", line 7, in <module>
#     from duckduckgo_search import ddg
#   File "/usr/local/lib/python3.11/site-packages/duckduckgo_search/__init__.py", line 11, in <module>
#     from .compat import (
#   File "/usr/local/lib/python3.11/site-packages/duckduckgo_search/compat.py", line 4, in <module>
#     from .duckduckgo_search import DDGS
#   File "/usr/local/lib/python3.11/site-packages/duckduckgo_search/duckduckgo_search.py", line 9, in <module>
#     from curl_cffi import requests
#   File "/usr/local/lib/python3.11/site-packages/curl_cffi/requests/__init__.py", line 29, in <module>
#     from .session import AsyncSession, BrowserType, Session
#   File "/usr/local/lib/python3.11/site-packages/curl_cffi/requests/session.py", line 30, in <module>
#     import eventlet.tpool
#   File "/usr/local/lib/python3.11/site-packages/eventlet/__init__.py", line 17, in <module>
#     from eventlet import convenience
#   File "/usr/local/lib/python3.11/site-packages/eventlet/convenience.py", line 7, in <module>
#     from eventlet.green import socket
#   File "/usr/local/lib/python3.11/site-packages/eventlet/green/socket.py", line 4, in <module>
#     __import__('eventlet.green._socket_nodns')
#   File "/usr/local/lib/python3.11/site-packages/eventlet/green/_socket_nodns.py", line 11, in <module>
#     from eventlet import greenio
#   File "/usr/local/lib/python3.11/site-packages/eventlet/greenio/__init__.py", line 3, in <module>
#     from eventlet.greenio.base import *  # noqa
#     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "/usr/local/lib/python3.11/site-packages/eventlet/greenio/base.py", line 32, in <module>
#     socket_timeout = eventlet.timeout.wrap_is_timeout(socket.timeout)
#                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File "/usr/local/lib/python3.11/site-packages/eventlet/timeout.py", line 166, in wrap_is_timeout
#     base.is_timeout = property(lambda _: True)
#     ^^^^^^^^^^^^^^^
# TypeError: cannot set 'is_timeout' attribute of immutable type 'TimeoutError'""" )
#         munger.results = "DDG search detected & ABORTED"
#         print( "Fetching AI data for [{}]...".format( munger.transcription ) )
#         results = ddg( munger.transcription, region="wt-wt", safesearch="Off", time="y", max_results=20 )
#         print( results )
#         munger.results = results
        
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

@app.route( "/api/get-transcription-to-command" )
def get_transcription_to_command():
    
    transcription = request.args.get( "transcription" )
    
    print( f"Fetching command for [{transcription}]..." )
    timer    = sw.Stopwatch()
    response = genie_client.get_command_for_transcription( transcription ).strip()
    timer.print( "Done!" )
    
    return response

@app.route( "/api/upload-and-transcribe-wav", methods=[ "POST" ] )
def upload_and_transcribe_wav_file():
    
    print( "upload_and_transcribe_wav_file() called" )
    load_stt_model_once()
    
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

def load_stt_model():
    
    torch_dtype   = torch.float16 if torch.cuda.is_available() else torch.float32
    stt_device_id = config_mgr.get( "stt_device_id", default="cuda:0" )
    stt_model_id  = config_mgr.get( "stt_model_id" )
    
    model = AutoModelForSpeechSeq2Seq.from_pretrained(
        stt_model_id, torch_dtype=torch_dtype, low_cpu_mem_usage=True, use_safetensors=True, use_flash_attention_2=True, local_files_only=True
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
    
def load_stt_model_once():

    global whisper_pipeline
    if whisper_pipeline is None:
        print( "Loading distill whisper engine... ", end="" )
        whisper_pipeline = load_stt_model()
        print( "Done!" )
    else:
        if app_debug: print( "Distill whisper engine already loaded" )
        
def load_commands_llm():

    path_to_llm = du.get_project_root() + config_mgr.get( "vox_command_llm_path_wo_root" )
    device_map  = config_mgr.get( "vox_command_llm_device_map", default="cuda:0" )

    print( f"Current working directory [{os.getcwd()}]" )
    print( f"Loading commands model from [{path_to_llm}]..." )

    model_aqw     = AutoAWQForCausalLM.from_pretrained( path_to_llm, device_map=device_map, safetensors=True )
    tokenizer_awq = AutoTokenizer.from_pretrained( path_to_llm, use_fast=True )

    return model_aqw, tokenizer_awq

@app.route( "/api/load-commands-llm" )
def load_commands_llm_once():

    global cmd_model
    global cmd_tokenizer
    global cmd_prompt_template
    global jobs_todo_queue

    if cmd_model is None:
        cmd_model, cmd_tokenizer = load_commands_llm()
        prompt_path              = du.get_project_root() + config_mgr.get( "vox_command_prompt_path_wo_root" )
        cmd_prompt_template      = du.get_file_as_string( prompt_path )
        jobs_todo_queue.set_llm( cmd_model, cmd_tokenizer)
        
        return "Commands LLM and prompt loaded"
    else:
        msg = "Commands LLM and prompt ALREADY loaded"
        print( msg )
        return msg

genie_client = gc.GenieClient()

if __name__ == "__main__":
    
    # how do we pass the equivalent of command line parameters into the flask app?
    # 1. use environment variables
    # 2. use a config file
    # 3. use command line parameters
    # 4. use a combination of the above
    
    app.run( debug=True )
