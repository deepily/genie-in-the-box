import os
import subprocess
import time

from flask import Flask, request, render_template, make_response, send_file
from flask_cors import CORS

import whisper
import base64

import genie_client as gc
import multi_modal_transcriber as mmt

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

@app.route( "/api/upload-and-transcribe-mp3", methods=[ "POST" ] )
def upload_and_transcribe_mp3_file():

    # print( type( request.data ) )
    # print( len( request.data ) )
    # print( request.data[ 0:32 ] )

    decoded_audio = base64.b64decode( request.data )
    # print( type( decoded_audio ) )
    # print( len( decoded_audio ) )
    # print( decoded_audio[ 0:32] )

    path = gc.docker_path.format( "recording.mp3" )

    print( "Saving file recorded audio bytes to [{}]...".format( path ), end="" )
    with open( path, "wb" ) as f:
        f.write( decoded_audio )
    print( " Done!" )

    print( "Skipping *.mp3 -> *.wav conversion, we don't need it!" )
    # sound = AudioSegment.from_mp3( path )
    # sound.export( path.replace( ".mp3", ".wav" ), format="wav" )
    # subprocess.call( [ "ffmpeg", "-y", "-i", "-hide_banner", "-loglevel panic", path, path.replace( ".mp3", ".wav" ) ] )
    # print( "Transcribing {}...".format( path ), end="" )
    # result = model.transcribe( path )
    # print( "Done!", end="\n\n" )
    #
    # print( "Result: [{}]".format( result[ "text" ] ) )
    # print( result[ "text" ] )
    #
    # return path.replace( ".mp3", ".wav" )

    print( "Transcribing {}...".format( path ) )
    result = model.transcribe( path )
    print( "Done!", end="\n\n" )

    result = result[ "text" ].strip()

    print( "Result: [{}]".format( result ) )
    
    munger = mmt.MultiModalTranscriber( result )

    return munger.get_json()

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

@app.route( "/api/upload", methods=[ "POST" ] )
def upload_file():

    bar = "#" * 80
    print( bar )
    print( "# This endpoint has been deprecated. Please update your code." )
    print( bar )
    #
    # file = request.files[ "file" ]
    # path = gc.docker_path.format( file.filename )
    #
    # print( "Saving file [{}] to [{}]...".format( file.filename, path ), end="" )
    # file.save( path )
    # print( " Done!" )
    #
    # return path


@app.route( "/api/vox2text" )
def vox_2_text():

    path = request.args.get( "path" )

    print( "Transcribing {}...".format( path ) )
    result = model.transcribe( path )
    print( "Done!", end="\n\n" )

    print( "Result: [{}]".format( result[ "text" ] ) )
    print( result[ "text" ] )

    return result[ "text" ].strip()

# This is something that the HTML client can access on its own. comma no need to start mixing in max and functionality
# across servers.
# @app.route( "/api/text2vox" )
# def text_2_vox():
#
#     text = request.args.get( "text" )
#
#     path_wav = genie_client.tts_wav_path
#     tts_address = genie_client.tts_address
#     genie_client.get_tts_file( tts_address, text, path_wav )
#
#     # convert to mp3
#     path_mp3 = path_wav.replace( ".wav", ".mp3" )
#     print( "Converting [{}] to [{}]...".format( path_wav, path_mp3 ) )
#     response = subprocess.call( [ "ffmpeg", "-y", "-i", path_wav, path_mp3 ] )
#     print( "response: {}".format( response ) )
#
#     return send_file( path_mp3, mimetype="audio/mpeg", as_attachment=False )

print( "Loading whisper engine... ", end="" )
model = whisper.load_model( "base.en" )
print( "Done!" )

print( os.getenv( "OPENAI_API_KEY" ) )
# genie_client = gc.GenieClient( tts_address="127.0.0.1:5000", runtime_context="local", tts_output_path="/Users/rruiz/Projects/projects-sshfs/io/text-to-vox.wav" )
genie_client = gc.GenieClient()

if __name__ == "__main__":

   app.run( debug=True )