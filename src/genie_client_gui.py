import os
import sys
import tkinter
import tkinter as tk
import tkinter.font as tkf
from threading import Thread
from tkinter import ttk, ACTIVE, DISABLED

import genie_client as gc
import util

class GenieGui:
    
    def __init__( self, default_mode="transcription", record_once_on_startup=False, runtime_context="docker", write_method="flask", recording_timeout=30, debug=False ):
        
        # TODO: Move configuration values into the same kind of format that we used in AMPE
        self.last_text_with_focus = None
        self.debug = debug

        self.last_key = ""
        
        # Instantiate headless client object
        self.genie_client = gc.GenieClient(
            calling_gui=self, startup_mode=default_mode, runtime_context=runtime_context, write_method=write_method, recording_timeout=recording_timeout, debug=debug
        )
        self.record_once_on_startup = record_once_on_startup
        self.default_mode = default_mode
        
        # Kludgey flag to get around mainloop error.
        self.record_once_on_startup_finished = False
        
        # Start Tkinter and set Title
        self.geometry_bar = "666x60"
        self.geometry_editor = "812x1048"

        self.main = tkinter.Tk()
        self.collections = [ ]
        self.main.geometry( self.geometry_bar )
        self.main.title( "Genie in The Box" )

        self.font_size = 18
        self.font_obj = tkf.Font( size=self.font_size )

        # Set Frames
        self.top_level_buttons = tkinter.Frame( self.main, padx=5, pady=5 )
        
        # Pack Frame
        self.top_level_buttons.pack( fill=tk.BOTH )
        
        # Start and Stop buttons
        self.btn_start = tkinter.Button(
            self.top_level_buttons, width=10, padx=10, pady=5, text="Start", font=self.font_obj, command=lambda: self.start_processing()
        )
        self.btn_start.grid( row=0, column=0, padx=5, pady=5 )
        self.btn_stop = tkinter.Button(
            self.top_level_buttons, width=10, padx=10, pady=5, text="Stop", font=self.font_obj, command=lambda: self.stop_processing()
        )
        self.btn_stop.config( state=DISABLED )
        self.btn_stop.grid( row=0, column=1, columnspan=1, padx=5, pady=5 )

        self.selected_mode = tk.StringVar()
        self.cmb_mode = ttk.Combobox( self.top_level_buttons, width=25, height=15, font=self.font_obj, state="readonly", textvariable=self.selected_mode )
        
        self.cmb_mode[ "values" ] = self.genie_client.get_titles()
        self.cmb_mode.current( self.genie_client.default_mode_index )
        self.cmb_mode.bind( "<<ComboboxSelected>>", lambda event: self.set_ready_to_start() )
        self.cmb_mode.grid( row=0, column=2, columnspan=1, padx=5, pady=5 )

        self.editor = tkinter.Frame( self.main, padx=5, pady=5 )
        self.editor.pack( fill=tk.BOTH, expand=True )

        toggle_text = " Clicking toggles transcription"
        self.lbl_prompt = tk.Label( self.editor, text="Prompt (Ctl + p)" + toggle_text, font=self.font_obj, width=65, height=1, anchor="w" )
        self.lbl_prompt.grid( row=0, rowspan=1, column=0, columnspan=10, padx=5, pady=5 )

        self.txt_prompt = tk.Text( self.editor, font=self.font_obj, width=70, height=10, wrap=tk.WORD, borderwidth=1 )
        self.txt_prompt.grid( row=1, rowspan=1, column=0, columnspan=10, padx=5, pady=5 )

        self.lbl_content = tk.Label( self.editor, text="Input (Ctl + i)" + toggle_text, font=self.font_obj, width=65, height=1, anchor="w" )
        self.lbl_content.grid( row=2, rowspan=1, column=0, columnspan=10, padx=5, pady=5 )

        self.txt_content = tk.Text( self.editor, font=self.font_obj, width=70, height=14, wrap=tk.WORD, borderwidth=1 )
        self.txt_content.grid( row=4, rowspan=1, column=0, columnspan=10, padx=5, pady=5 )

        self.lbl_response = tk.Label( self.editor, text="Response (Ctl + r)" + toggle_text, font=self.font_obj, width=65, height=1, anchor="w" )
        self.lbl_response.grid( row=5, rowspan=1, column=0, columnspan=10, padx=5, pady=5 )

        self.txt_response = tk.Text( self.editor, font=self.font_obj, width=70, height=14, wrap=tk.WORD, borderwidth=1 )
        self.txt_response.grid( row=6, rowspan=1, column=0, columnspan=10, padx=5, pady=5 )

        # Create an editor button bar containing Cut, Copy, Paste, Space and Backspace options.
        # self.editor_buttons = tkinter.Frame( self.editor, padx=0, pady=0, border=2 )
        # self.editor_buttons.pack( fill=tk.BOTH, expand=True )

        self.btn_cut = tkinter.Button(
            self.editor, width=4, padx=0, pady=0, text="Cut", font=self.font_obj, command=lambda: self.do_edit( "cut" )
        )
        self.btn_cut.grid( row=3, column=0, padx=0, pady=0 )
        self.btn_copy = tkinter.Button(
            self.editor, width=4, padx=0, pady=0, text="Copy", font=self.font_obj, command=lambda: self.do_edit( "copy" )
        )
        self.btn_copy.grid( row=3, column=1, padx=0, pady=0 )
        self.btn_paste = tkinter.Button(
            self.editor, width=4, padx=0, pady=0, text="Paste", font=self.font_obj, command=lambda: self.do_edit( "paste" )
        )
        self.btn_paste.grid( row=3, column=2, padx=0, pady=0 )
        self.btn_delete = tkinter.Button(
            self.editor, width=4, padx=0, pady=0, text="Del", font=self.font_obj, command=lambda: self.do_edit( "delete" )
        )
        self.btn_delete.grid( row=3, column=3, padx=0, pady=0 )
        self.btn_space = tkinter.Button(
            self.editor, width=4, padx=0, pady=0, text="Space", font=self.font_obj, command=lambda: self.do_edit( "space" )
        )
        self.btn_space.grid( row=3, column=4, padx=0, pady=0 )
        # self.editor_buttons.pack( fill=tk.BOTH, expand=True )

        # Bind keys
        # self.main.bind( "<KeyPress>", self.key_event )
        self.main.bind( "<KeyRelease>", self.key_event )
        # Track focus events for all widgets, specifically, editable text areas.
        self.main.bind( "<FocusIn>", self.handle_focus )

        # bind click events to labels.
        self.lbl_prompt.bind( "<Button-1>", lambda event: self._do_conditional_transcription_toggle() )
        self.lbl_content.bind( "<Button-1>", lambda event: self._do_conditional_transcription_toggle() )
        self.lbl_response.bind( "<Button-1>", lambda event: self._do_conditional_transcription_toggle() )

        self.btn_start.focus_set()

        self.set_ready_to_start()
        
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

    def handle_focus( self, event ):

        if event.widget == self.txt_content:
            print( "Content has focus" )
            self.last_text_with_focus = self.txt_content
        elif event.widget == self.txt_prompt:
            print( "Prompt has focus" )
            self.last_text_with_focus = self.txt_prompt
        elif event.widget == self.txt_response:
            print( "Response has focus" )
            self.last_text_with_focus = self.txt_response
        else:
            print( "Something else has focus:", event.widget )
            # self.widget_with_focus = None
    def key_event( self, event ):
        
        print( "key_event [{}] keysym [{}]".format( event, event.keysym ) )

        if self.last_key == "Up" and event.keysym == "Meta_L":
            print( "Meta + Up" )
            self.font_size += 1
            print( "font_size:", self.font_size )
        elif self.last_key == "Down" and event.keysym == "Meta_L":
            print( "Meta + Down" )
            self.font_size -= 1
            print( "font_size:", self.font_size )
        elif self.last_key == "p" and event.keysym == "Control_L":

            print( "Control + P" )
            self.txt_prompt.focus_set()

        elif self.last_key == "i" and event.keysym == "Control_L":

            print( "Control + I" )
            self.txt_content.focus_set()

        elif self.last_key == "r" and event.keysym == "Control_L":

            print( "Control + R" )
            self.txt_response.focus_set()

        elif self.last_key == "t" and event.keysym == "Control_L":

            print( "Control + T" )
            self._do_conditional_transcription_toggle()
            # if not self.genie_client.is_recording():
            #
            #     ranges = self.last_text_with_focus.tag_ranges( tk.SEL )
            #     if ranges:
            #         print( 'SELECTED Text is %r' % self.last_text_with_focus.get( *ranges ) )
            #         print( "ranges:", ranges )
            #         self.last_text_with_focus.delete( *ranges )
            #     else:
            #         print( 'NO Selected Text' )
            #
            #     self.start_processing()
            #
            #     transcription = self.genie_client.get_from_clipboard()
            #
            #     self.last_text_with_focus.insert( tk.INSERT, transcription )

        # elif self.last_key == "v" and event.keysym == "Control_L":
        #
        #     print( "Control + V (paste)" )
        #     self.do_conditional_paste_from_clipboard( self )

        elif ( event.keysym == "Escape" ) and (
            self.genie_client.is_recording() or
            self.genie_client.is_playing() ):

            self.stop_processing()

        elif ( event.keysym == "Escape" ) and not (
            self.genie_client.is_recording() or
            self.genie_client.is_playing() ):

            print( "Quitting... (Don't forget to check for stream right completion before destroying window?)" )
            self.main.destroy()

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

    def _do_conditional_transcription_toggle( self ):

        if not self.genie_client.is_recording():

            ranges = self.last_text_with_focus.tag_ranges( tk.SEL )
            if ranges:
                print( 'SELECTED Text is %r' % self.last_text_with_focus.get( *ranges ) )
                print( "ranges:", ranges )
                self.last_text_with_focus.delete( *ranges )
            else:
                print( 'NO Selected Text' )

            self.start_processing()

            # blocks until finished processing
            transcription = self.genie_client.get_from_clipboard()
            self.last_text_with_focus.insert( tk.INSERT, transcription )

        else:

            self.stop_processing()

        self.last_text_with_focus.focus_set()

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

    def set_ready_to_start( self ):

        print( "Mode set to [{}]".format( self.selected_mode.get() ) )
        self.btn_start.config( state=ACTIVE )
        self.btn_start.focus_set()
        self.btn_stop.config( state=DISABLED )

        # Add Hock, Switch to display or hide interactive code editor.
        key = self.genie_client.keys_dict[ self.selected_mode.get() ]
        print( "key [{}]".format( key ) )

        if key == "ai_interactive_editor_prose" or key == "ai_interactive_editor_prose_run":
            self.show_interactive_code_editor( True, key )
        else:
            self.show_interactive_code_editor( False, key )

    def show_interactive_code_editor( self, show, key ):

        print( "show_interactive_code_editor() called w/ mode key [{}]...".format( key ) )
        if show:
            print( "Showing interactive editor..." )
            self.editor.pack()
            self.txt_prompt.focus_set()
            self.main.geometry( self.geometry_editor )
        else:
            print( "Hiding interactive editor..." )
            self.editor.forget()
            self.btn_start.focus_set()
            self.main.geometry( self.geometry_bar )

    def start_processing( self ):

        print( "start_processing() called..." )

        self.cmb_mode.config( state=DISABLED )
        self.btn_start.config( state=DISABLED )
        self.btn_stop.config( state=ACTIVE )
        self.btn_stop.focus_set()
        self.main.update()

        # print( self.editor )
        # prompt = self.txt_prompt.get( "1.0", "end" )
        # content = self.txt_content.get( "1.0", "end" )
        # print( "Prompt: \n\n{}".format( prompt ), end="\n\n" )
        # print( "Content: \n\n{}".format( content ), end="\n\n" )

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
    
        print( "stop_processing() called..." )
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
    # Watch out where the Huskies go. Don't you eat the yellow snow!
    # gg.genie_client.do_gpt_prose_explanation_from_clipboard()

    # gg.genie_client.do_gpt_prose_explanation_from_clipboard()
