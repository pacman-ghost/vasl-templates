#!/usr/bin/env python3
""" Run the webapp server. """

import os
import threading
import urllib.request
import time
import glob

# ---------------------------------------------------------------------

# monitor extra files for changes
extra_files = []
for fspec in ["config","static","templates"] :
    fspec = os.path.abspath( os.path.join( os.path.dirname(__file__), fspec ) )
    if os.path.isdir( fspec ):
        files = [ os.path.join(fspec,f) for f in os.listdir(fspec) ]
        files = [ f for f in files if os.path.isfile(f) and os.path.splitext(f)[1] not in [".swp"] ]
    else:
        files = glob.glob( fspec )
    extra_files.extend( files )

# initialize
from vasl_templates.webapp import app
host = app.config.get( "FLASK_HOST", "localhost" )
port = app.config["FLASK_PORT_NO"]
debug = app.config.get( "FLASK_DEBUG", False )

def start_server():
    """Force the server to do "first request" initialization."""
    # NOTE: This is not needed when running the desktop app (since it will request the home page),
    # but if we're running just the server (i.e. from the console, or a Docker container), then
    # sending a request, any request, will trigger the "first request" initialization (in particular,
    # the download thread).
    time.sleep( 5 )
    url = "http://{}:{}/ping".format( host, port )
    _ = urllib.request.urlopen( url )
threading.Thread( target=start_server, daemon=True ).start()

# run the server
app.run( host=host, port=port, debug=debug,
    extra_files = extra_files
)
