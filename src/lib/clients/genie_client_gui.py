import os
import sys
import tkinter
import tkinter as tk
import tkinter.font as tkf
from threading import Thread
from tkinter import ttk, ACTIVE, DISABLED

sys.path.append( os.getcwd() )

import lib.clients.genie_client as gc
import lib.utils.util as du

class GenieGui:
    
    def __init__( self, startup_mode="transcribe_and_clean_prose", copy_transx_to_clipboard=True, record_once_on_startup=False, runtime_context="docker", write_method="flask", recording_timeout=30, debug=False ):
        
        self.finished_transcription = None
        
        # TODO: Move configuration values into the same kind of format that we used in AMPE
        self.last_text_with_focus = None
        self.debug = debug

        self.last_key = ""
        
        self.copy_transx_to_clipboard = copy_transx_to_clipboard
        self.record_once_on_startup = record_once_on_startup
        self.startup_mode = startup_mode
        
        # Kludgey flag to get around mainloop error.
        self.record_once_on_startup_finished = False
        
        # Start Tkinter and set Title
        self.geometry_bar = "666x70"
        # self.geometry_editor = "854x1048"

        self.main = tkinter.Tk()
        self.collections = [ ]
        self.main.geometry( self.geometry_bar )
        self.main.title( "Genie in The Box" )

        # Now that we have a GUI object to point to, instantiate headless client object
        self.genie_client = gc.GenieClient( calling_gui=self.main, startup_mode=startup_mode,
                                            copy_transx_to_clipboard=copy_transx_to_clipboard,
                                            runtime_context=runtime_context, write_method=write_method, debug=debug,
                                            recording_timeout=recording_timeout
                                            )
        self.font_size = 18
        self.font_obj_big = tkf.Font( size=self.font_size )
        self.font_obj_mid = tkf.Font( size=int( self.font_size * .75 ) )

        # Set Frames
        self.top_level_buttons = tkinter.Frame( self.main, padx=10, pady=5 )
        
        # Pack Frame
        self.top_level_buttons.pack( fill=tk.BOTH )
        
        # Start and Stop buttons
        self.btn_start = tkinter.Button(
            self.top_level_buttons, width=10, padx=0, pady=5, text="Start", font=self.font_obj_big, command=lambda: self.start_processing()
        )
        self.btn_start.grid( row=0, column=0, padx=0, pady=5 )
        self.btn_stop = tkinter.Button(
            self.top_level_buttons, width=10, padx=0, pady=5, text="Stop", font=self.font_obj_big, command=lambda: self.stop_processing()
        )
        self.btn_stop.config( state=DISABLED )
        self.btn_stop.grid( row=0, column=1, columnspan=1, padx=0, pady=5 )

        # Mode selection
        self.selected_mode = tk.StringVar()
        self.cmb_mode = ttk.Combobox( self.top_level_buttons, width=22, height=20, font=self.font_obj_big, state="readonly", textvariable=self.selected_mode )
        
        self.cmb_mode[ "values" ] = self.genie_client.get_titles()
        self.cmb_mode.current( self.genie_client.default_mode_index )
        self.cmb_mode.bind( "<<ComboboxSelected>>", lambda event: self.set_ready_to_start() )
        self.cmb_mode.grid( row=0, column=2, columnspan=1, padx=5, pady=5 )

        # Bind keys
        # self.main.bind( "<KeyPress>", self.key_event )
        self.main.bind( "<KeyRelease>", self.key_event )
        
        # This is superfluous. It's already called in the next method.
        self.set_ready_to_start()
        # self.update_prompt()

        # force GUI to update periodically?
        def update():
            
            self.main.update()
            self.main.after( 100, update )

        update()

        # Start & block while in the mainloop
        if self.record_once_on_startup:
            if self.debug: print( "self.record_once_on_startup is True, blocking main thread while this runs." )
            self.start_processing()
            # self.main.destroy()
        else:
            tkinter.mainloop()

    def key_event( self, event ):
        
        if self.debug: print( "key_event [{}] keysym [{}]".format( event, event.keysym ) )
        
        # if self.last_key == "Up" and event.keysym == "Meta_L":
        #     print( "Meta + Up" )
        #     self.font_size += 1
        #     print( "font_size:", self.font_size )
        # elif self.last_key == "Down" and event.keysym == "Meta_L":
        #     print( "Meta + Down" )
        #     self.font_size -= 1
        #     print( "font_size:", self.font_size )
        # elif self.last_key == "p" and event.keysym == "Control_L":
        #
        #     print( "Control + P" )
        #     self.txt_prompt.focus_set()
        #
        # elif self.last_key == "i" and event.keysym == "Control_L":
        #
        #     print( "Control + I" )
        #     self.txt_content.focus_set()
        #
        # elif self.last_key == "r" and event.keysym == "Control_L":
        #
        #     print( "Control + R" )
        #     self.txt_response.focus_set()
        #
        # elif self.last_key == "t" and event.keysym == "Control_L":
        #
        #     print( "Control + T" )
        #     self._do_conditional_transcription_toggle()
        #
        # el
        if ( event.keysym == "Escape" or event.keysym == "BackSpace" ) and (
            self.genie_client.is_recording() or
            self.genie_client.is_playing() ):

            self.stop_processing()

        elif ( event.keysym == "Escape" or event.keysym == "BackSpace" ) and not (
            self.genie_client.is_recording() or
            self.genie_client.is_playing() ):

            if self.debug: print( "Quitting... (Don't forget to check for stream right completion before destroying window?)" )
            # self.main.destroy()
            self.main.quit()
        self.last_key = event.keysym

    def _do_conditional_paste_from_clipboard( self ):

        if not self.genie_client.is_recording():

            ranges = self.last_text_with_focus.tag_ranges( tk.SEL )
            if ranges:
                print( 'SELECTED Text is %r' % self.last_text_with_focus.get( *ranges ) )
                print( "ranges:", ranges )
                self.last_text_with_focus.delete( *ranges )
            else:
                print( 'NO Selected Text to delete' )

            self.last_text_with_focus.insert( tk.INSERT, self.genie_client.get_from_clipboard() )

        else:
            print( "Can't paste while recording!" )

    def _do_conditional_cut_copy_delete( self, delete_selected_text=True, copy_to_clipboard=True ):

        """
        Cut selected text, if any exists, and copy to clipboard if copy_to_clipboard is True
        :param copy_to_clipboard:
        :return:
        """
        if not self.genie_client.is_recording():

            ranges = self.last_text_with_focus.tag_ranges( tk.SEL )
            if ranges:

                # Get a copy of the selected text before doing anything else.
                selected_text = self.last_text_with_focus.get( *ranges )
                print( "ranges:", ranges )
                print( 'SELECTED Text [{}]'.format( selected_text ) )

                if delete_selected_text: self.last_text_with_focus.delete( *ranges )

                if copy_to_clipboard: self.genie_client.copy_to_clipboard( selected_text )
            else:
                print( "Nothing selected to cut, copy or delete." )
        else:
            print( "Can't cut/copy/delete while recording!" )
            

    def do_edit( self, action ):

        print( "do_edit() called w/ action [{}]".format( action ) )
        if action == "paste":
            self._do_conditional_paste_from_clipboard()
        elif action == "cut":
            self._do_conditional_cut_copy_delete( delete_selected_text=True, copy_to_clipboard=True )
        elif action == "copy":
            self._do_conditional_cut_copy_delete( delete_selected_text=False, copy_to_clipboard=True )
        elif action == "delete":
            self._do_conditional_cut_copy_delete( delete_selected_text=True, copy_to_clipboard=False )
        elif action == "space":
            self.last_text_with_focus.insert( tk.INSERT, " " )
        elif action == "clear":
            self.last_text_with_focus.delete( 1.0, tk.END )

    def set_ready_to_start( self ):

        if self.debug: print( "Mode set to [{}]".format( self.selected_mode.get() ) )
        self.btn_start.config( state=ACTIVE )
        self.btn_start.focus_set()
        self.btn_stop.config( state=DISABLED )

        # Add Hock, Switch to display or hide interactive code editor.
        key = self.genie_client.keys_dict[ self.selected_mode.get() ]
        if self.debug: print( "key [{}]".format( key ) )

    def start_processing( self ):

        if self.debug: print( "start_processing() called..." )

        self.cmb_mode.config( state=DISABLED )
        self.btn_start.config( state=DISABLED )
        self.btn_stop.config( state=ACTIVE )
        self.btn_stop.focus_set()
        self.main.update()

        processing_thread = Thread( target=self._start_processing_thread(), args=() )
        processing_thread.start()
        
    def _start_processing_thread( self ):
    
        if self.debug: print( "Processing. on a separate thread in [{}] mode...".format( self.selected_mode.get() ), end="" )
    
        # branch on mode_title
        mode_title = self.selected_mode.get()
        
        self.finished_transcription = self.genie_client.process_by_mode_title( mode_title )
            
        self.stop_processing()

        # Set flag for early bailout.
        if self.record_once_on_startup:
            self.record_once_on_startup_finished = True
            
    def stop_processing( self ):
    
        if self.debug: print( "stop_processing() called..." )
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
    
    # print( "Starting GenieClient in [{}]...".format( os.getcwd() ) )
    cli_args = du.get_name_value_pairs( sys.argv )

    # startup_mode           = cli_args.get( "startup_mode", "transcribe_and_clean_prose" )
    startup_mode             = cli_args.get( "startup_mode", "transcribe" )
    # startup_mode           = cli_args.get( "startup_mode", "transcribe_and_clean_python" )
    recording_timeout      = int( cli_args.get( "recording_timeout", 30 ) )
    record_once_on_startup = cli_args.get( "record_once_on_startup", "False" ) == "True"

    # and now for something completely different !
    gg = GenieGui(
        startup_mode=startup_mode,
        recording_timeout=recording_timeout,
        record_once_on_startup=record_once_on_startup,
        debug=False
    )
    # print( "gg.finished_transcription [{}]".format( gg.finished_transcription ) )
    # exit and push transcription to the console
    sys.exit( gg.finished_transcription )
    # sys.exit( 0 )
