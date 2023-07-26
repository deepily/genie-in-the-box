import os
import subprocess
import sys

import pexpect


def run_command ( cmd ):

    process = subprocess.Popen( cmd, shell=False, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True )

    # Poll process.stdout to show stdout live
    while True:
        output = process.stdout.readline()
        if process.poll() is not None:
            break
        if output:
            print( output.strip() )

    rc = process.poll()

    print( "rc: {}".format( rc ) )
    if rc != 0:
        raise subprocess.CalledProcessError( process.returncode, process.args )

if __name__ == "__main__":

    # for name, value in os.environ.items():
    #     print( "{0}: {1}".format( name, value ) )
    #
    # cmd = [ "ls", "-alh" ]
    cmd = [ "cat", "/Users/rruiz/.bash_aliases" ]
    # cmd = [ "nano", "/Users/rruiz/.bash_aliases" ]
    # cmd = [ "git", "status" ]
    # cmd = [ "/Volumes/projects/genie-in-the-box/run-genie-gui.sh", "record_once_on_startup=True" ]
    # cmd = [ "ssh", "rruiz@162.198.0.19" ]

    run_command( cmd )
    print( os.getcwd() )
    # # child = pexpect.spawn( "ssh rruiz@162.198.0.19" )
    # child = pexpect.spawn( "nano /home/rruiz/.bash_aliases" )
    # # child.expect( "*" )
    # # child.sendline( "ls -alh ~" )
    # print( child.before )
    # child.interact()
    sys.exit( 0 )


# import os
# import sys
#
# import util
# import genie_client as gc
# import genie_client_gui as gcg
#
# class GenieCliClient:
#
#     def __init__( self, startup_mode, copy_transx_to_clipboard=False, recording_timeout=3 ):
#
#         self.startup_mode                  = startup_mode
#         self.recording_timeout             = recording_timeout
#         self.copy_transx_to_clipboard      = copy_transx_to_clipboard
#         # self.genie_client                  = gc.GenieClient( startup_mode=startup_mode, recording_timeout=recording_timeout, copy_transx_to_clipboard=copy_transx_to_clipboard )
#         self.clipboard_contents_at_startup = ""
#
#     def get_input_from_cli( self ):
#
#         # Grab the contents of the clipboard before we do anything else.
#         self.clipboard_contents_at_startup = self.genie_client.get_from_clipboard()
#
#         print( "Listening", end="" )
#
#         transcription = self.genie_client.do_transcribe_and_clean_python()
#
#         print( "You said [{}]".format( transcription ) )
#         # command = input( "You said [{}]".format( transcription ) )
#         # print( "Final string: [{}]".format( command ) )
#         #
#         # return command
#
# if __name__ == "__main__":
#
#     print( "Starting GenieCliClient in [{}]...".format( os.getcwd() ) )
#     cli_args = util.get_name_value_pairs( sys.argv )
#
#     # runtime_context = cli_args.get( "runtime_context", "docker" )
#     # write_method = cli_args.get( "write_method", "flask" )
#     default_mode             = cli_args.get( "default_mode", "transcribe_and_clean_python" )
#     recording_timeout        = int( cli_args.get( "recording_timeout", 3 ) )
#     copy_transx_to_clipboard = cli_args.get( "copy_transx_to_clipboard", "True" ) == "True"
#
#     print( "     default_mode: [{}]".format( default_mode ) )
#     print( "recording_timeout: [{}]".format( recording_timeout ) )
#
#     gcc = GenieCliClient(
#         startup_mode=default_mode,
#         recording_timeout=recording_timeout,
#         copy_transx_to_clipboard=copy_transx_to_clipboard
#     )
#     foo = gcc.get_input_from_cli()
