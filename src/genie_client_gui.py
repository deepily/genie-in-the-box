import os
import sys
import tkinter
import tkinter as tk
from threading import Thread
from tkinter import ttk, ACTIVE, DISABLED

import genie_client as gc
import util

class GenieGui:
    
    def __init__( self, default_mode="transcription", record_once_on_startup=False, runtime_context="docker", write_method="flask", recording_timeout=30, debug=False ):
        
        # TODO: Move configuration values into the same kind of format that we used in AMPE
        self.debug = debug
        
        # Instantiate headless client object
        self.genie_client = gc.GenieClient(
            calling_gui=self, startup_mode=default_mode, runtime_context=runtime_context, write_method=write_method, recording_timeout=recording_timeout, debug=debug
        )
        self.record_once_on_startup = record_once_on_startup
        self.default_mode = default_mode
        
        # Kludgey flag to get around mainloop error.
        self.record_once_on_startup_finished = False
        
        # Start Tkinter and set Title
        self.main = tkinter.Tk()
        self.collections = [ ]
        self.main.geometry( "575x55" )
        self.main.title( "Genie in The Box" )
        
        # Set Frames
        self.buttons = tkinter.Frame( self.main, padx=5, pady=5 )
        
        # Pack Frame
        self.buttons.pack( fill=tk.BOTH )
        
        # Start and Stop buttons
        self.btn_start = tkinter.Button(
            self.buttons, width=10, padx=10, pady=5, text="Start", command=lambda: self.start_processing()
        )
        self.btn_start.grid( row=0, column=0, padx=5, pady=5 )
        self.btn_stop = tkinter.Button(
            self.buttons, width=10, padx=10, pady=5, text="Stop", command=lambda: self.stop_processing()
        )
        self.btn_stop.config( state=DISABLED )
        self.btn_stop.grid( row=0, column=1, columnspan=1, padx=5, pady=5 )

        self.selected_mode = tk.StringVar()
        self.cmb_mode = ttk.Combobox( self.buttons, width=25, height=10, state="readonly", textvariable=self.selected_mode )
        
        self.cmb_mode[ "values" ] = self.genie_client.get_titles()
        self.cmb_mode.current( self.genie_client.default_mode_index )
        self.cmb_mode.bind( "<<ComboboxSelected>>", lambda event: self.set_ready_to_start() )
        self.cmb_mode.grid( row=0, column=2, columnspan=1, padx=5, pady=5 )
        
        # Bind keys
        self.main.bind( "<KeyRelease>", self.key_event )
        
        self.btn_start.focus_set()
        
        # force GUI to update periodically?
        def update():
            
            self.main.update()
            self.main.after( 100, update )

        update()

        # Start & block while in the mainloop
        if self.record_once_on_startup:
            print( "self.record_once_on_startup is True, blocking main thread while this runs." )
            self.start_processing()
            self.main.destroy()
        else:
            tkinter.mainloop()

    def key_event( self, event ):
        
        if self.debug: print( "key pressed [{}]".format( event.keysym ) )
        
        if ( event.keysym == "Escape" ) and (
            self.genie_client.is_recording() or
            self.genie_client.is_playing() ):
            
            self.stop_processing()
            
        elif ( event.keysym == "Escape" ) and not (
            self.genie_client.is_recording() or
            self.genie_client.is_playing() ):
            
            print( "Quitting... (Don't forget to check for stream right completion before destroying window?)" )
            self.main.destroy()
    
    def set_ready_to_start( self ):
        
        print( "Mode set to [{}]".format( self.selected_mode.get() ) )
        self.btn_start.config( state=ACTIVE )
        self.btn_start.focus_set()
        self.btn_stop.config( state=DISABLED )
        
    def start_processing( self ):
    
        self.cmb_mode.config( state=DISABLED )
        self.btn_start.config( state=DISABLED )
        self.btn_stop.config( state=ACTIVE )
        self.btn_stop.focus_set()
        self.main.update()

        processing_thread = Thread( target=self._start_processing_thread(), args=() )
        processing_thread.start()
        
    def _start_processing_thread( self ):
    
        print( "Processing. on a separate thread in [{}] mode...".format( self.selected_mode.get() ), end="" )
    
        # branch on mode_title
        mode_title = self.selected_mode.get()
        
        self.genie_client.process_by_mode_title( mode_title )
            
        self.stop_processing()

        # Set flag for early bailout.
        if self.record_once_on_startup:
            self.record_once_on_startup_finished = True
            
    def stop_processing( self ):
    
        # print( "stop_processing() called..." )
        self.cmb_mode.config( state=ACTIVE )
        self.btn_start.config( state=ACTIVE )
        self.btn_start.focus_set()
        self.btn_stop.config( state=DISABLED )
        self.main.update()
        
        if self.genie_client.is_recording():
            self.genie_client.stop_recording()
        if self.genie_client.is_playing():
            self.genie_client.stop_playing()
        
# Create main function to run the program.
if __name__ == "__main__":
    
    # def foo():
    #     print( "foo" )
    #
    # "foo"
    
    print( "Starting GenieClient in [{}]...".format( os.getcwd() ) )
    cli_args = util.get_name_value_pairs( sys.argv )

    runtime_context        = cli_args.get( "runtime_context", "docker" )
    write_method           = cli_args.get( "write_method", "flask" )
    default_mode           = cli_args.get( "default_mode", "transcribe" )
    recording_timeout      = int( cli_args.get( "recording_timeout", 30 ) )
    record_once_on_startup = cli_args.get( "record_once_on_startup", "False" ) == "True"

    gg = GenieGui(
        default_mode=default_mode,
        runtime_context=runtime_context,
        write_method=write_method,
        recording_timeout=recording_timeout,
        record_once_on_startup=record_once_on_startup
    )
    
    