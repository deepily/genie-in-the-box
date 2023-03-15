from flask import Flask, request, render_template
import whisper

import genie_client as gc

app = Flask( __name__ )

@app.route("/")
def root():
    
    return "Hello whisper flask server!"

@app.route( '/uploader.html' )
def uploader_html():
    return render_template( 'uploader.html' )

@app.route( '/api/upload', methods=[ 'POST' ] )
def upload_file():
    
    runtime_context = request.args.get( "runtime_context" )
    print( "/api/upload?runtime_context={}".format( runtime_context ) )

    file = request.files[ 'file' ]
    if runtime_context == "docker":
        path = gc.docker_path.format( file.filename )
    else:
        path = gc.local_path.format( file.filename )

    print( "Saving file [{}] to [{}]...".format( file.filename, path ), end="" )
    file.save( path )
    print( " Done!" )
    
    return path

@app.route("/api/vox2text" )
def vox_2_text():

    path = request.args.get( 'path' )

    print( "Transcribing {}...".format( path ) )
    result = model.transcribe( path )
    print( "Done!", end="\n\n" )

    print( "Result: [{}]".format( result[ "text" ] ) )
    print( result[ "text" ] )

    return result[ "text" ].strip()

print( "Loading whisper engine... ", end="" )
model = whisper.load_model( "base.en" )
print( "Done!" )

if __name__ == '__main__':
   
   app.run( debug=True )