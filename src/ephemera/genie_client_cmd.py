import os
import sys
import subprocess

import util

import genie_client as gc
import genie_client_gui as gcg

class GenieCmdClient:

    def __init__( self, record_once_on_startup=False, startup_mode="transcribe_and_clean_python", copy_transx_to_clipboard=False, recording_timeout=3, debug=False ):

        self.debug                         = debug
        self.startup_mode                  = startup_mode
        self.recording_timeout             = recording_timeout
        self.copy_transx_to_clipboard      = copy_transx_to_clipboard
        self.record_once_on_startup        = record_once_on_startup
        # self.genie_client                  = gc.GenieClient( startup_mode=startup_mode, recording_timeout=recording_timeout, copy_transx_to_clipboard=copy_transx_to_clipboard )
        self.clipboard_contents_at_startup = ""

        

    def run_command ( self, cmd ):

        cmd = cmd.split( " " )
        print( "cmd: {}".format( cmd ) )
        process = subprocess.Popen( cmd, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True )

        # Poll process.stdout to show stdout live
        while True:
            output = process.stdout.readline()
            if process.poll() is not None:
                break
            if output:
                print( output.strip() )

        rc = process.poll()

        if self.debug: print( "rc: {}".format( rc ) )
        if rc != 0:
            raise subprocess.CalledProcessError( process.returncode, process.args )

    def get_transcription( self ):

        genie_client = gc.GenieClient( startup_mode=self.startup_mode, recording_timeout=self.recording_timeout, copy_transx_to_clipboard=self.copy_transx_to_clipboard, debug=self.debug )
        # genie_gui  = gcg.GenieGui( record_once_on_startup=self.record_once_on_startup, default_mode=self.startup_mode, recording_timeout=self.recording_timeout, copy_transx_to_clipboard=self.copy_transx_to_clipboard, debug=self.debug )
        transcription = genie_client.do_transcribe_and_clean_python()

        return transcription
        # return genie_client.get_from_clipboard()

if __name__ == "__main__":

    debug = True
    cwd = os.getcwd()
    print( cwd )
    cmd_dict = util.get_file_as_dictionary( cwd + "/conf/cli-commands.map", debug=debug )
    if debug: print( cmd_dict )

    cli_args = util.get_name_value_pairs( sys.argv )

    # runtime_context = cli_args.get( "runtime_context", "docker" )
    # write_method = cli_args.get( "write_method", "flask" )
    startup_mode             = cli_args.get( "startup_mode", "transcribe_and_clean_python" )
    record_once_on_startup   = cli_args.get( "record_once_on_startup", "True" ) == "True"
    copy_transx_to_clipboard = cli_args.get( "copy_transx_to_clipboard", "True" ) == "True"
    recording_timeout        = int( cli_args.get( "recording_timeout", 4 ) )

    if debug: print( "     startup_mode: [{}]".format( startup_mode ) )
    if debug: print( "recording_timeout: [{}]".format( recording_timeout ) )

    gcc = GenieCmdClient(
        record_once_on_startup=record_once_on_startup,
        startup_mode=startup_mode,
        recording_timeout=recording_timeout,
        copy_transx_to_clipboard=copy_transx_to_clipboard,
        debug=debug
    )
    transcription = gcc.get_transcription()
    if debug: print( "transcription [{}]".format( transcription ) )

    cmd = cmd_dict.get( transcription, None )

    if cmd is None:
        print( "Command not found: [{}]".format( transcription ) )
    else:
        response = input( "Execute cmd [{}] (y/N): ".format( cmd ) )

        if response.lower() == "y":
            gcc.run_command( cmd )
        else:
            print( "Command [{}] not executed ".format( cmd ) )

    #     foo = gcc.get_input_from_cli()
