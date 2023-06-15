import os
import sys
import tkinter
import tkinter as tk
import tkinter.font as tkf
from threading import Thread
from tkinter import ttk, ACTIVE, DISABLED

import genie_client as gc
import lib.util as du


class GenieGui:
    
    def __init__( self, default_mode="transcription", copy_transx_to_clipboard=True, record_once_on_startup=False, runtime_context="docker", write_method="flask", recording_timeout=30, debug=False ):
        
        # TODO: Move configuration values into the same kind of format that we used in AMPE
        self.last_text_with_focus = None
        self.debug = debug

        self.last_key = ""
        
        self.copy_transx_to_clipboard = copy_transx_to_clipboard
        self.record_once_on_startup = record_once_on_startup
        self.default_mode = default_mode
        
        # Kludgey flag to get around mainloop error.
        self.record_once_on_startup_finished = False
        
        # Start Tkinter and set Title
        self.geometry_bar = "666x70"
        self.geometry_editor = "854x1048"

        self.main = tkinter.Tk()
        self.collections = [ ]
        self.main.geometry( self.geometry_bar )
        self.main.title( "Genie in The Box" )

        # Now that we have a GUI object to point to, instantiate headless client object
        self.genie_client = gc.GenieClient(
            calling_gui=self.main, startup_mode=default_mode, copy_transx_to_clipboard=copy_transx_to_clipboard, runtime_context=runtime_context, write_method=write_method, recording_timeout=recording_timeout, debug=debug
        )
        self.font_size = 18
        self.font_obj_big = tkf.Font( size=self.font_size )
        self.font_obj_mid = tkf.Font( size=int( self.font_size * .75 ) )

        # Center the frame?
        # self.main.eval( 'tk::PlaceWindow . center' )

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

        # Prompt selection.
        self.selected_prompt = tk.StringVar()
        self.cmb_prompt = ttk.Combobox( self.top_level_buttons, width=70, height=20, font=self.font_obj_big, state="readonly", textvariable=self.selected_prompt )
        self.cmb_prompt[ "values" ] = self.genie_client.prompt_titles
        self.cmb_prompt.current( 0 )
        self.cmb_prompt.bind( "<<ComboboxSelected>>", lambda event: self.update_prompt() )
        self.cmb_prompt.grid( row=1, column=0, columnspan=10, padx=12, pady=10, sticky="w" )

        self.editor = tkinter.Frame( self.main, padx=10, pady=0 )
        self.editor.pack( fill=tk.BOTH, expand=True )

        toggle_text = " Click HERE to start/stop transcription"
        self.lbl_prompt = tk.Label( self.editor, text="Prompt focus = [Ctl + p]" + toggle_text, font=self.font_obj_big, width=65, height=1, anchor="w" )
        self.lbl_prompt.grid( row=0, rowspan=1, column=0, columnspan=12, padx=10, pady=5 )

        self.txt_prompt = tk.Text( self.editor, font=self.font_obj_big, width=72, height=10, wrap=tk.WORD, borderwidth=1 )
        self.txt_prompt.grid( row=1, rowspan=1, column=0, columnspan=12, padx=10, pady=5 )

        self.lbl_content = tk.Label( self.editor, text="Input focus = [Ctl + i]" + toggle_text, font=self.font_obj_big, width=65, height=1, anchor="w" )
        self.lbl_content.grid( row=2, rowspan=1, column=0, columnspan=12, padx=5, pady=5 )

        self.txt_content = tk.Text( self.editor, font=self.font_obj_big, width=72, height=14, wrap=tk.WORD, borderwidth=1 )
        self.txt_content.grid( row=4, rowspan=1, column=0, columnspan=12, padx=10, pady=5 )

        self.lbl_response = tk.Label( self.editor, text="Response focus = [Ctl + r]" + toggle_text, font=self.font_obj_big, width=65, height=1, anchor="w" )
        self.lbl_response.grid( row=5, rowspan=1, column=0, columnspan=12, padx=10, pady=5 )

        self.txt_response = tk.Text( self.editor, font=self.font_obj_big, width=72, height=14, wrap=tk.WORD, borderwidth=1 )
        self.txt_response.grid( row=6, rowspan=1, column=0, columnspan=12, padx=10, pady=5 )

        # Create an editor button bar containing Cut, Copy, Paste, Space and Backspace options.
        # self.editor_buttons = tkinter.Frame( self.editor, padx=0, pady=0, border=2 )
        # self.editor_buttons.pack( fill=tk.BOTH, expand=True )

        self.btn_cut = tkinter.Button(
            self.editor, width=2, padx=0, pady=0, text="Cut", font=self.font_obj_mid, command=lambda: self.do_edit( "cut" )
        )
        self.btn_cut.grid( row=3, column=0, padx=0, pady=0 )

        self.btn_copy = tkinter.Button(
            self.editor, width=2, padx=0, pady=0, text="Copy", font=self.font_obj_mid, command=lambda: self.do_edit( "copy" )
        )
        self.btn_copy.grid( row=3, column=1, padx=0, pady=0 )

        self.btn_paste = tkinter.Button(
            self.editor, width=2, padx=0, pady=0, text="Paste", font=self.font_obj_mid, command=lambda: self.do_edit( "paste" )
        )
        self.btn_paste.grid( row=3, column=2, padx=0, pady=0 )

        self.btn_delete = tkinter.Button(
            self.editor, width=2, padx=0, pady=0, text="Del", font=self.font_obj_mid, command=lambda: self.do_edit( "delete" )
        )
        self.btn_delete.grid( row=3, column=3, padx=0, pady=0 )

        self.btn_space = tkinter.Button(
            self.editor, width=2, padx=0, pady=0, text="Space", font=self.font_obj_mid, command=lambda: self.do_edit( "space" )
        )
        self.btn_space.grid( row=3, column=4, padx=0, pady=0 )

        self.btn_clear = tkinter.Button(
            self.editor, width=2, padx=0, pady=0, text="Clear", font=self.font_obj_mid, command=lambda: self.do_edit( "clear" )
        )
        self.btn_clear.grid( row=3, column=5, padx=0, pady=0 )

        self.btn_left = tkinter.Button(
            self.editor, width=2, padx=0, pady=0, text="<", font=self.font_obj_mid, command=lambda: self.move_cursor( "left" )
        )
        self.btn_left.grid( row=3, column=6, padx=0, pady=0 )

        self.btn_right = tkinter.Button(
            self.editor, width=2, padx=0, pady=0, text=">", font=self.font_obj_mid, command=lambda: self.move_cursor( "right" )
        )
        self.btn_right.grid( row=3, column=7, padx=0, pady=0 )

        self.btn_up = tkinter.Button(
            self.editor, width=2, padx=0, pady=0, text="Up", font=self.font_obj_mid, command=lambda: self.move_cursor( "up" )
        )
        self.btn_up.grid( row=3, column=8, padx=0, pady=0 )

        self.btn_down = tkinter.Button(
            self.editor, width=2, padx=0, pady=0, text="Down", font=self.font_obj_mid, command=lambda: self.move_cursor( "down" )
        )
        self.btn_down.grid( row=3, column=9, padx=0, pady=0 )

        # Bind keys
        # self.main.bind( "<KeyPress>", self.key_event )
        self.main.bind( "<KeyRelease>", self.key_event )
        # Track focus events for all widgets, specifically, editable text areas.
        self.main.bind( "<FocusIn>", self.handle_focus )

        # bind click events to labels.
        self.lbl_prompt.bind( "<Button-1>", lambda event: self._do_conditional_transcription_toggle() )
        self.lbl_content.bind( "<Button-1>", lambda event: self._do_conditional_transcription_toggle() )
        self.lbl_response.bind( "<Button-1>", lambda event: self._do_conditional_transcription_toggle() )

        # This is superfluous. It's already called in the next method.
        self.set_ready_to_start()
        self.update_prompt()

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

    # Create a method to move the cursor forward and backwards within a text object.
    def move_cursor( self, direction ):

        if self.debug: print( "move_cursor [{}]".format( direction ) )
        position = self.last_text_with_focus.index( tk.INSERT )
        if self.debug: print( "position:", position )

        if direction == "left":
            self.last_text_with_focus.mark_set( tk.INSERT, position + " -1c" )
        elif direction == "right":
            self.last_text_with_focus.mark_set( tk.INSERT, position + " +1c" )
        elif direction == "up":
            self.last_text_with_focus.mark_set( tk.INSERT, position + " -1l" )
        elif direction == "down":
            self.last_text_with_focus.mark_set( tk.INSERT, position + " +1l" )

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

    def key_event( self, event ):
        
        if self.debug: print( "key_event [{}] keysym [{}]".format( event, event.keysym ) )

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

        # This is superfluous. It's already captured in the button bar.
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

        # ¡OJO! This is extremely ad hoc and brittle, WILL break if the mode keys are changed.
        if key == "ai_interactive_editor_prose" or key == "ai_interactive_editor_prose_run":
            self.show_interactive_code_editor( True, key )
        else:
            self.show_interactive_code_editor( False, key )

        # ¡OJO! This is extremely ad hoc and brittle too, WILL break if the mode keys are changed.
        if key == "ai_interactive_editor_prose":
            self.btn_start.config( state=DISABLED )
    def update_prompt( self ):

        if self.debug: print( "update_prompt() called, key [{}]".format( self.selected_prompt.get() ) )
        prompt = self.genie_client.prompts_dict[ self.selected_prompt.get() ]
        if self.debug: print( "prompt [{}]".format( prompt ) )

        self.txt_prompt.delete( "0.0", tk.END )
        self.txt_prompt.insert( tk.INSERT, prompt )

    def show_interactive_code_editor( self, show, key ):

        if self.debug: print( "show_interactive_code_editor() called w/ mode key [{}]...".format( key ) )
        if show:
            if self.debug: print( "Showing interactive editor..." )
            self.editor.pack()
            self.txt_prompt.focus_set()
            self.main.geometry( self.geometry_editor )
        else:
            if self.debug: print( "Hiding interactive editor..." )
            self.editor.forget()
            self.btn_start.focus_set()
            self.main.geometry( self.geometry_bar )

    def start_processing( self ):

        if self.debug: print( "start_processing() called..." )

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
    
        if self.debug: print( "Processing. on a separate thread in [{}] mode...".format( self.selected_mode.get() ), end="" )
    
        # branch on mode_title
        mode_title = self.selected_mode.get()
        
        self.genie_client.process_by_mode_title( mode_title )
            
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
    
    print( "Starting GenieClient in [{}]...".format( os.getcwd() ) )
    cli_args = du.get_name_value_pairs( sys.argv )

    # runtime_context        = cli_args.get( "runtime_context", "docker" )
    # write_method           = cli_args.get( "write_method", "flask" )
    default_mode           = cli_args.get( "default_mode", "transcribe_and_clean_prose" )
    recording_timeout      = int( cli_args.get( "recording_timeout", 30 ) )
    record_once_on_startup = cli_args.get( "record_once_on_startup", "False" ) == "True"

    gg = GenieGui(
        default_mode=default_mode,
        # runtime_context=runtime_context,
        # write_method=write_method,
        recording_timeout=recording_timeout,
        record_once_on_startup=record_once_on_startup,
        debug=False
    )
    # Watch out where the Huskies go. Don't you eat the yellow snow!
    # gg.genie_client.do_gpt_prose_explanation_from_clipboard()

    # gg.genie_client.do_gpt_prose_explanation_from_clipboard()
    
    #
    # sys.exit( 0 )
    
    
