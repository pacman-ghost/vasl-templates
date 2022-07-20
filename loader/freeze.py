#!/usr/bin/env python3
""" Freeze the vasl-templates loader program.

This script is called by the main freeze script.
"""

import sys
import os
import shutil
import tempfile
import getopt

from PyInstaller.__main__ import run as run_pyinstaller
from PIL import Image

APP_ICON = os.path.join(
    os.path.abspath( os.path.dirname( __file__ ) ),
    "../vasl_templates/webapp/static/images/app.ico"
)

# ---------------------------------------------------------------------

def main( args ):
    """Main processing."""

    # parse the command-line options
    output_fname = "./loader"
    work_dir = os.path.join( tempfile.gettempdir(), "freeze-loader" )
    cleanup = True
    opts,args = getopt.getopt( args, "o:w:", ["output=","work=","no-clean"] )
    for opt, val in opts:
        if opt in ["-o","--output"]:
            output_fname = val.strip()
        elif opt in ["-w","--work"]:
            work_dir = val.strip()
        elif opt in ["--no-clean"]:
            cleanup = False
        else:
            raise RuntimeError( "Unknown argument: {}".format( opt ) )

    # freeze the loader program
    freeze_loader( output_fname, work_dir, cleanup )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def freeze_loader( output_fname, work_dir, cleanup ):
    """Freeze the loader program."""

    with tempfile.TemporaryDirectory() as dist_dir:

        # initialize
        base_dir = os.path.abspath( os.path.dirname( __file__ ) )
        assets_dir = os.path.join( base_dir, "assets" )

        # convert the app icon to an image
        if not os.path.isdir( work_dir ):
            os.makedirs( work_dir )
        app_icon_fname = os.path.join( work_dir, "app-icon.png" )
        _convert_app_icon( app_icon_fname )

        # initialize
        app_name = "loader"
        args = [
            "--distpath", dist_dir,
            "--workpath", work_dir,
            "--specpath", work_dir,
            "--onefile",
            "--name", app_name,
        ]
        args.extend( [
            "--add-data", app_icon_fname + os.pathsep + "assets/",
            "--add-data", os.path.join(assets_dir,"loading.gif") + os.pathsep + "assets/"
        ] )
        if sys.platform == "win32":
            args.append( "--noconsole" )
            args.extend( [ "--icon", APP_ICON ] )
        args.append( os.path.join( base_dir, "main.py" ) )

        # freeze the program
        run_pyinstaller( args )

        # save the generated artifact
        fname = app_name+".exe" if sys.platform == "win32" else app_name
        shutil.move(
            os.path.join( dist_dir, fname ),
            output_fname
        )

        # clean up
        if cleanup:
            shutil.rmtree( work_dir )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _convert_app_icon( save_fname ):
    """Convert the app icon to an image."""
    # NOTE: Tkinter's PhotoImage doesn't handle .ico files, so we convert the app icon
    # to an image, then insert it into the PyInstaller-generated executable (so that
    # we don't have to bundle Pillow into the release).
    img = Image.open( APP_ICON )
    img = img.convert( "RGBA" ).resize( (48, 48) )
    img.save( save_fname, "png" )

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main( sys.argv[1:] )
