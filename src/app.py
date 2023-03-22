import os

from flask import Flask, request, render_template
import whisper
import base64

import genie_client as gc

app = Flask( __name__ )

@app.route( "/" )
def root():

    return "Hello whisper flask server!"


# @app.route( "/recorder.html" )
# def blank():
#
#     return render_template( "recorder.html" )
#
# @app.route( "/recorder.js" )
# def recorder():
#
#     return render_template( "recorder.js" )
#
# @app.route( "/uploader.html" )
# def uploader_html():
#
#     return render_template( "uploader.html" )
#
#
# @app.route( "/upload-and-transcribe.html" )
# def upload_and_transcribe_html():
#     return render_template( "upload-and-transcribe.html" )

@app.route( "/api/ask-ai-text" )
def ask_ai_text():

    question = request.args.get( "question" )

    print( "Asking AI [{}]...".format( question ) )
    result = genie_client.ask_chat_gpt_text( question, preamble="What does this mean?" ).strip()
    print( "Result: [{}]".format( result ) )

    return result

@app.route( "/api/upload-and-transcribe", methods=[ "POST" ] )
def upload_and_transcribe_file():

    print( type( request.data ) )
    print( len( request.data ) )
    print( request.data[ 0:32 ] )

    decoded_audio = base64.b64decode( request.data )
    print( type( decoded_audio ) )
    print( len( decoded_audio ) )
    print( decoded_audio[ 0:32] )

    path = gc.local_path.format( "recording.mp3" )

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

    print( "Result: [{}]".format( result[ "text" ].strip() ) )
    print( result[ "text" ].strip() )

    return result[ "text" ].strip()

@app.route( "/api/upload", methods=[ "POST" ] )
def upload_file():

    runtime_context = request.args.get( "runtime_context" )
    print( "/api/upload?runtime_context={}".format( runtime_context ) )

    file = request.files[ "file" ]
    # if runtime_context == "local":
    #     path = gc.local_path.format( file.filename )
    # else:
    path = gc.docker_path.format( file.filename )

    print( "Saving file [{}] to [{}]...".format( file.filename, path ), end="" )
    file.save( path )
    print( " Done!" )

    return path


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
genie_client = gc.GenieClient()

if __name__ == "__main__":

   app.run( debug=True )