import os
import subprocess
import time
import json

from flask import Flask, request, render_template, make_response, send_file
from flask_cors import CORS

from duckduckgo_search import ddg

import whisper
import base64

import genie_client as gc
import multi_modal_munger as mmm
import util_stopwatch as sw

app = Flask( __name__ )

# Props to StackOverflow for this workaround:https://stackoverflow.com/questions/25594893/how-to-enable-cors-in-flask
CORS( app )

@app.route( "/" )
def root():

    return "Genie in the box flask server, ready to reload dynamically!"


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

    print( "Transcribing {}...".format( path ) )
    result = model.transcribe( path )
    print( "Done!", end="\n\n" )

    result = result[ "text" ].strip()

    print( "Result: [{}]".format( result ) )
    
    munger = mmm.MultiModalMunger( result, prefix=prefix, prompt_key=prompt_key )

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
        
        print( "Fetching AI results for [{}]...".format( munger.transcription ) )
        results = ddg( munger.transcription, region='wt-wt', safesearch='Off', time='y', max_results=20 )
        print( results )
        munger.results = results
        
    return munger.get_json()

@app.route( "/api/run-raw-prompt-text" )
def run_raw_prompt_text():
    
    prompt_and_content = request.args.get( "prompt_and_content" )
    prompt_feedback    = request.args.get( "prompt_verbose", default="verbose" )
    
    print( "Running prompt [{}]...".format( prompt_and_content ) )
    
    return genie_client.ask_chat_gpt_using_raw_prompt_and_content( prompt_and_content ).replace( "```", "" )
    
    
    
@app.route( "/api/upload-and-transcribe-wav", methods=[ "POST" ] )
def upload_and_transcribe_wav_file():

    file      = request.files[ "file" ]
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

    return transcribed_text

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

print( os.getenv( "OPENAI_API_KEY" ) )
# genie_client = gc.GenieClient( tts_address="127.0.0.1:5000", runtime_context="local", tts_output_path="/Users/rruiz/Projects/projects-sshfs/io/text-to-vox.wav" )
genie_client = gc.GenieClient()

if __name__ == "__main__":

   app.run( debug=True )