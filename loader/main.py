""" Load the main vasl-templates program.

vasl-templates can be slow to start (especially on Windows), since it has to unpack the PyInstaller-generated EXE,
then startup Qt. We want to show a splash screen while all this happening, but we can't just put it in vasl-templates,
since it would only happen *after* all the slow stuff has finished :-/ So, we have this stub program that shows
a splash screen, launches the main vasl-templates program, and waits for it to finish starting up.
"""

import sys
import os
import subprocess
import threading
import itertools
import urllib.request
from urllib.error import URLError
import time
import configparser

# NOTE: It's important that this program start up quickly (otherwise it becomes pointless),
# so we use tkinter, instead of PyQt (and also avoid bundling a 2nd copy of PyQt :-/).
import tkinter
import tkinter.messagebox

if getattr( sys, "frozen", False ):
    BASE_DIR = sys._MEIPASS #pylint: disable=no-member,protected-access
else:
    BASE_DIR = os.path.abspath( os.path.dirname( __file__ ) )

STARTUP_TIMEOUT = 60 # how to long to wait for vasl-templates to start (seconds)

main_window = None

# ---------------------------------------------------------------------

def main( args ):
    """Load the main vasl-templates program."""

    # initialize Tkinter
    global main_window
    main_window = tkinter.Tk()
    main_window.option_add( "*Dialog.msg.font", "Helvetica 12" )

    # load the app icon
    # NOTE: This image file doesn't exist in source control, but is created dynamically from
    # the main app icon by the freeze script, and inserted into the PyInstaller-generated executable.
    # We do things this way so that we don't have to bundle Pillow into the release.
    app_icon = tkinter.PhotoImage(
        file = make_asset_path( "app-icon.png" )
    )

    # locate the main vasl-templates executable
    fname = os.path.join( os.path.dirname( sys.executable ), "vasl-templates-main" )
    if sys.platform == "win32":
        fname += ".exe"
    if not os.path.isfile( fname ):
        show_error_msg( "Can't find the main vasl-templates program.", withdraw=True )
        return -1

    # launch the main vasl-templates program
    try:
        proc = subprocess.Popen( itertools.chain( [fname], args ) ) #pylint: disable=consider-using-with
    except Exception as ex: #pylint: disable=broad-except
        show_error_msg( "Can't start vasl-templates:\n\n{}".format( ex ), withdraw=True )
        return -2

    # get the webapp port number
    port = 5010
    fname = os.path.join( os.path.dirname( fname ), "config/app.cfg" )
    if os.path.isfile( fname ):
        config_parser = configparser.ConfigParser()
        config_parser.optionxform = str # preserve case for the keys :-/
        config_parser.read( fname )
        args = dict( config_parser.items( "System" ) )
        port = args.get( "FLASK_PORT_NO", port )

    # create the splash window
    create_window( app_icon )

    # start a background thread to check on the main vasl-templates process
    threading.Thread(
        target = check_startup,
        args = ( proc, port )
    ).start()

    # run the main loop
    main_window.mainloop()

    return 0

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def create_window( app_icon ):
    """Create the splash window."""

    # create the splash window
    main_window.geometry( "275x64" )
    main_window.title( "vasl-templates loader" )
    main_window.overrideredirect( 1 ) # nb: "-type splash" doesn't work on Windows :-/
    main_window.eval( "tk::PlaceWindow . center" )
    main_window.wm_attributes( "-topmost", 1 )
    main_window.tk.call( "wm", "iconphoto", main_window._w, app_icon ) #pylint: disable=protected-access
    main_window.protocol( "WM_DELETE_WINDOW", lambda: None )

    # add the app icon
    label = tkinter.Label( main_window, image=app_icon )
    label.grid( row=0, column=0, rowspan=2, padx=8, pady=8 )

    # add the caption
    label = tkinter.Label( main_window, text="Loading vasl-templates...", font=("Helvetica",12) )
    label.grid( row=0, column=1, padx=5, pady=(8,0) )

    # add the "loading" image (we have to animate it ourself :-/)
    anim_label = tkinter.Label( main_window )
    anim_label.grid( row=1, column=1, sticky=tkinter.N, padx=0, pady=0 )
    fname = make_asset_path( "loading.gif" )
    nframes = 13
    frames = [
        tkinter.PhotoImage( file=fname, format="gif -index {}".format( i ) )
        for i in range(nframes)
    ]
    frame_index = 0
    def next_frame():
        nonlocal frame_index
        frame = frames[ frame_index ]
        frame_index = ( frame_index + 1 ) % nframes
        anim_label.configure( image=frame )
        main_window.after( 75, next_frame )
    main_window.after( 0, next_frame )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def check_startup( proc, port ):
    """Check the startup of the main vasl-templates process."""

    def do_check():

        # check if we've waited for too long
        if time.time() - start_time > STARTUP_TIMEOUT:
            # yup - give up
            raise RuntimeError( "Couldn't start vasl-templates." )

        # check if the main vasl-templates process has gone away
        if proc.poll() is not None:
            raise RuntimeError( "The vasl-templates program ended unexpectedly." )

        # check if the webapp is responding
        url = "http://localhost:{}/ping".format( port )
        try:
            with urllib.request.urlopen( url ) as resp:
                _ = resp.read()
        except URLError:
            # no response - the webapp is probably still starting up
            return False
        except Exception as ex: #pylint: disable=broad-except
            raise RuntimeError( "Couldn't communicate with vasl-templates:\n\n{}".format( ex ) ) from ex

        # the main vasl-templates program has started up and is responsive - our job is done!
        if sys.platform == "win32":
            # FUDGE! There is a short amount of time between the webapp server starting and
            # the main window appearing. We delay here for a bit, to try to synchronize
            # our window fading out with the main vasl-templates window appearing.
            time.sleep( 1 )
        return True

    def on_done( msg ):
        if msg:
            show_error_msg( msg, withdraw=True )
        fade_out( main_window, main_window.quit )

    # run the main loop
    start_time = time.time()
    while True:
        try:
            if do_check():
                on_done( None )
                break
        except Exception as ex: #pylint: disable=broad-except
            on_done( str(ex) )
            return
        time.sleep( 0.25 )

# ---------------------------------------------------------------------

def fade_out( target, on_done ):
    """Fade out the target window."""
    alpha = target.attributes( "-alpha" )
    if alpha > 0:
        alpha -= 0.1
        target.attributes( "-alpha", alpha )
        target.after( 50, lambda: fade_out( target, on_done ) )
    else:
        on_done()

def make_asset_path( fname ):
    """Generate the path to an asset file."""
    return os.path.join( BASE_DIR, "assets", fname )

def show_error_msg( error_msg, withdraw=False ):
    """Show an error dialog."""
    if withdraw:
        main_window.withdraw()
    tkinter.messagebox.showinfo( "vasl-templates loader error", error_msg )

# ---------------------------------------------------------------------

if __name__ == "__main__":
    sys.exit( main( sys.argv[1:] ) )
