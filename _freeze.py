#!/usr/bin/env python3
""" Compile the application and create a release. """

import sys
import os
import shutil
import glob
import getopt
from cx_Freeze import setup, Executable

from vasl_templates.webapp.config.constants import APP_NAME, APP_VERSION, APP_DESCRIPTION

BASE_DIR = os.path.split( os.path.abspath(__file__) )[ 0 ]
BUILD_DIR = os.path.join( BASE_DIR, "build" )

MAIN_ENTRY_POINT = "vasl_templates/main.py"
APP_ICON = os.path.join( BASE_DIR, "vasl_templates/webapp/static/images/app.ico" )

TARGET_NAMES = {
    "win32": "vasl-templates.exe",
}
DEFAULT_TARGET_NAME = "vasl-templates"

# ---------------------------------------------------------------------

def get_extra_files():
    """Get the extra files to include in the release."""
    def globfiles( fspec ): #pylint: disable=missing-docstring,unused-variable
        fnames = glob.glob( fspec )
        return zip( fnames, fnames )
    extra_files = []
    extra_files.append( "LICENSE.txt" )
    return extra_files

# ---------------------------------------------------------------------

# parse the command-line options
output_fname = None
cleanup = True
opts,args = getopt.getopt( sys.argv[1:], "o:", ["output=","noclean"] )
for opt,val in opts:
    if opt in ["-o","--output"]:
        output_fname = val.strip()
    elif opt in ["--noclean"]:
        cleanup = False
    else:
        raise RuntimeError( "Unknown argument: {}".format( opt ) )
if not output_fname:
    raise RuntimeError( "No output file was specified." )

# figure out the format of the release archive
formats = { ".zip": "zip", ".tar.gz": "gztar", ".tar.bz": "bztar", ".tar": "tar" }
output_fmt = None
for extn,fmt in formats.items():
    if output_fname.endswith( extn ):
        output_fmt = fmt
        output_fname2 = output_fname[:-len(extn)]
        break
if not output_fmt:
    raise RuntimeError( "Unknown release archive format: {}".format( os.path.split(output_fname)[1] ) )

# initialize the build options
build_options = {
    "packages": [ "os", "asyncio", "jinja2" ],
    "excludes": [ "tkinter" ],
    "include_files": get_extra_files(),
}

# freeze the application
# NOTE: It would be nice to be able to use py2exe to compile this for Windows (since it produces
# a single EXE instead of the morass of files cx-freeze generates) but py2exe only works up to
# Python 3.4, since the byte code format changed after that.
target = Executable(
    MAIN_ENTRY_POINT,
    base = "Win32GUI" if sys.platform == "win32" else None,
    targetName = TARGET_NAMES.get( sys.platform, DEFAULT_TARGET_NAME ),
    icon = APP_ICON
)
if os.path.isdir( BUILD_DIR ):
    shutil.rmtree( BUILD_DIR )
os.chdir( BASE_DIR )
del sys.argv[1:]
sys.argv.append( "build" )
# nb: cx-freeze doesn't report compile errors or anything like that :-/
setup(
    name = APP_NAME,
    version = APP_VERSION,
    description = APP_DESCRIPTION,
    options = {
        "build_exe": build_options
    },
    executables = [ target ]
)
print()

# locate the release files
files = os.listdir( BUILD_DIR )
if len(files) != 1:
    raise RuntimeError( "Unexpected freeze output." )
dname = os.path.join( BUILD_DIR, files[0] )
os.chdir( dname )

# remove some unwanted files
for fname in ["debug.cfg","logging.cfg"]:
    fname = os.path.join( "lib/vasl_templates/webapp/config", fname )
    if os.path.isfile( fname ):
        os.unlink( fname )

# create the release archive
print( "Generating release archive: {}".format( output_fname ) )
shutil.make_archive( output_fname2, output_fmt )
file_size = os.path.getsize( output_fname )
print( "- Done: {0:.1f} MB".format( float(file_size) / 1024 / 1024 ) )

# clean up
if cleanup:
    os.chdir( BASE_DIR ) # so we can delete the build directory :-/
    shutil.rmtree( BUILD_DIR )
