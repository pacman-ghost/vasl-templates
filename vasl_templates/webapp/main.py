""" Main webapp handlers. """

import os
import json

from flask import request, render_template, jsonify, send_file, redirect, url_for, abort

from vasl_templates.webapp import app
from vasl_templates.webapp.config.constants import DATA_DIR

# ---------------------------------------------------------------------

@app.route( "/" )
def main():
    """Return the main page."""
    return render_template( "index.html" )

# ---------------------------------------------------------------------

@app.route( "/help" )
def show_help():
    """Show the help page."""
    url = url_for( "static", filename="help/index.html" )
    args = []
    for arg in ("embedded","tab","pyqt"):
        if request.args.get( arg ):
            args.append( "{}={}".format( arg, request.args[arg] ) )
    if args:
        url += "?{}".format( "&".join( args ) )
    return redirect( url, code=302 )

# ---------------------------------------------------------------------

@app.route( "/license" )
def get_license():
    """Get the license."""

    # locate the license file
    dname = os.path.split( __file__ )[0]
    fname = os.path.join( dname, "../../LICENSE.txt" ) # nb: if we're running from source
    if not os.path.isfile( fname ):
        fname = os.path.join( dname, "../../../LICENSE.txt" ) # nb: if we're running as a compiled binary
    if not os.path.isfile( fname ):
        # FUDGE! If we've been pip install'ed walk up the directory tree, looking for the license file :-/
        dname = os.path.split( fname )[0]
        while True:
            # go up a directory
            prev_dname = dname
            dname = os.path.split( dname )[0]
            if dname == prev_dname:
                break
            # check if we can find the license file
            fname = os.path.join( dname, "vasl-templates/LICENSE.txt" )
            if os.path.isfile( fname ):
                break
    if not os.path.isfile( fname ):
        abort( 404 )

    return send_file( fname, "text/plain" )

# ---------------------------------------------------------------------

default_scenario = None

@app.route( "/default-scenario" )
def get_default_scenario():
    """Return the default scenario."""

    # check if a default scenario has been configured
    if default_scenario:
        fname = default_scenario
    else:
        fname = os.path.join( app.config.get("DATA_DIR",DATA_DIR), "default-scenario.json" )

    # return the default scenario
    with open(fname,"r") as fp:
        return jsonify( json.load( fp ) )

# ---------------------------------------------------------------------

@app.route( "/ping" )
def ping():
    """Let the caller know we're alive."""
    return "pong"

# ---------------------------------------------------------------------

@app.route( "/shutdown" )
def shutdown():
    """Shutdown the webapp (for testing porpoises)."""
    request.environ.get( "werkzeug.server.shutdown" )()
    return ""
