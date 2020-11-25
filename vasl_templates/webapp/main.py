""" Main webapp handlers. """

import os
import threading
import concurrent
import json
import uuid
import logging

from flask import request, render_template, jsonify, send_file, redirect, url_for, abort

from vasl_templates.webapp import app, shutdown_event
from vasl_templates.webapp.utils import MsgStore, parse_int
import vasl_templates.webapp.config.constants
from vasl_templates.webapp.config.constants import BASE_DIR, DATA_DIR
from vasl_templates.webapp import globvars
from vasl_templates.webapp.lfa import DEFAULT_LFA_DICE_HOTNESS_WEIGHTS, DEFAULT_LFA_DICE_HOTNESS_THRESHOLDS

# NOTE: This is used to stop multiple instances of the program from running (see main.py in the desktop app).
INSTANCE_ID = uuid.uuid4().hex

startup_msg_store = MsgStore() # store messages generated during startup
_check_versions = True

# ---------------------------------------------------------------------

@app.route( "/" )
def main():
    """Return the main page."""
    return render_template( "index.html" )

# ---------------------------------------------------------------------

@app.route( "/startup-msgs" )
def get_startup_msgs():
    """Return any messages generated during startup."""

    global _check_versions
    if _check_versions:
        _check_versions = False
        # check the VASSAL version
        from vasl_templates.webapp.vassal import VassalShim
        try:
            VassalShim.check_vassal_version( startup_msg_store )
        except Exception as ex: #pylint: disable=broad-except
            msg = "Can't get the VASSAL version: {}".format( ex )
            logging.error( "%s", msg )
            startup_msg_store.error( msg )

    # collect all the startup messages
    startup_msgs = {}
    for msg_type in ("info","warning","error"):
        msgs = startup_msg_store.get_msgs( msg_type )
        if msgs:
            startup_msgs[ msg_type ] = msgs

    # NOTE: Because we don't clear the collected messages here, if the web page is refreshed, or loaded
    # via another browser instance, the user will see the same messages again, which, depending on
    # the exact nature of those messages, could look odd, but is probably what we want.
    return jsonify( startup_msgs )

# ---------------------------------------------------------------------

_APP_CONFIG_DEFAULTS = { # Bodhgaya, India (APR/19)
    "THEATERS": [ "ETO", "DTO", "PTO", "Korea", "Burma", "other" ],
    # NOTE: We use HTTP for static images, since VASSAL is already insanely slow loading images (done in serial?),
    # so I don't even want to think about what it might be doing during a TLS handshake... :-/
    "ONLINE_IMAGES_URL_BASE": "http://vasl-templates.org/services/static-images",
    # NOTE: We would rather use https://github.com/vasl-developers/vasl/raw/develop/dist/images/ in the template,
    # but VASSAL is already so slow to load images, and doing everything twice would make it that much worse :-/
    "ONLINE_COUNTER_IMAGES_URL_TEMPLATE": "https://raw.githubusercontent.com/vasl-developers/vasl/develop/dist/images/{{PATH}}", #pylint: disable=line-too-long
    "ONLINE_EXTN_COUNTER_IMAGES_URL_TEMPLATE": "http://vasl-templates.org/services/counter/{{EXTN_ID}}/{{PATH}}",
    "ASA_UPLOAD_URL": "https://aslscenarioarchive.com/rest/update/{ID}?user={USER}&token={TOKEN}",
}

@app.route( "/app-config" )
def get_app_config():
    """Get the application config."""

    def get_json_val( key, default ):
        """Get a JSON value from the app config."""
        try:
            val = app.config.get( key, default )
            return val if isinstance(val,dict) else json.loads(val)
        except json.decoder.JSONDecodeError:
            msg = "Couldn't parse app config setting: {}".format( key )
            logging.error( "%s", msg )
            startup_msg_store.error( msg )
            return default

    # include the basic app config
    vals = {
        key: app.config.get( key, default )
        for key,default in _APP_CONFIG_DEFAULTS.items()
    }
    if isinstance( vals["THEATERS"], str ):
        vals["THEATERS"] = vals["THEATERS"].split()
    for key in ["APP_NAME","APP_VERSION","APP_DESCRIPTION","APP_HOME_URL"]:
        vals[ key ] = getattr( vasl_templates.webapp.config.constants, key )

    # include the ASL Scenario Archive config
    for key in ["ASA_MAX_VASL_SETUP_SIZE","ASA_MAX_SCREENSHOT_SIZE"]:
        vals[ key ] = app.config[ key ]

    # include the dice hotness config
    vals[ "LFA_DICE_HOTNESS_WEIGHTS" ] = get_json_val(
        "LFA_DICE_HOTNESS_WEIGHTS", DEFAULT_LFA_DICE_HOTNESS_WEIGHTS
    )
    vals[ "LFA_DICE_HOTNESS_THRESHOLDS" ] = get_json_val(
        "LFA_DICE_HOTNESS_THRESHOLDS", DEFAULT_LFA_DICE_HOTNESS_THRESHOLDS
    )
    vals[ "DISABLE_LFA_HOTNESS_FADEIN" ] = app.config.get( "DISABLE_LFA_HOTNESS_FADEIN" )

    # NOTE: We allow the front-end to generate snippets that point to an alternative webapp server (so that
    # VASSAL can get images, etc. from a Docker container rather than the desktop app). However, since it's
    # unlikely anyone else will want this option, we implement it as a debug setting, rather than exposing it
    # as an option in the UI.
    alt_webapp_base_url = app.config.get( "ALTERNATE_WEBAPP_BASE_URL" )
    if alt_webapp_base_url:
        vals[ "ALTERNATE_WEBAPP_BASE_URL" ] = alt_webapp_base_url

    # include information about VASSAL and VASL
    from vasl_templates.webapp.vassal import VassalShim
    try:
        vals[ "VASSAL_VERSION" ] = VassalShim.get_version()
    except Exception as ex: #pylint: disable=broad-except
        logging.error( "Can't check the VASSAL version: %s", str(ex) )
    if globvars.vasl_mod:
        vals["VASL_VERSION"] = globvars.vasl_mod.vasl_version

    # include information about VASL extensions
    if globvars.vasl_mod and globvars.vasl_mod.extns:
        vals["VASL_EXTENSIONS"] = {}
        for extn in globvars.vasl_mod.extns:
            extn_info = {}
            for key in ("version","displayName","displayNameAbbrev"):
                if key in extn[1]:
                    extn_info[ key ] = extn[1][ key ]
                vals["VASL_EXTENSIONS"][ extn[1]["extensionId"] ] = extn_info

    # include the ASL Scenario Archive config data
    for key in ["ASA_SCENARIO_URL","ASA_PUBLICATION_URL","ASA_PUBLISHER_URL"]:
        vals[ key ] = app.config[ key ]
    for key in ["BALANCE_GRAPH_THRESHOLD"]:
        vals[ key ] = app.config.get( key )
    fname = os.path.join( DATA_DIR, "asl-scenario-archive.json" )
    if os.path.isfile( fname ):
        with open( fname, "r" ) as fp:
            try:
                vals[ "SCENARIOS_CONFIG" ] = json.load( fp )
            except json.decoder.JSONDecodeError as ex:
                msg = "Couldn't load the ASL Scenario Archive config."
                logging.error( "%s", msg )
                startup_msg_store.error( msg )

    return jsonify( vals )

# ---------------------------------------------------------------------

@app.route( "/help" )
def show_help():
    """Show the help page."""
    url = url_for( "static", filename="help/index.html" )
    if request.args:
        args = [ "{}={}".format( arg, request.args[arg] ) for arg in request.args ]
        url += "?{}".format( "&".join( args ) )
    return redirect( url, code=302 )

# ---------------------------------------------------------------------

@app.route( "/license" )
def get_license():
    """Get the license."""

    # locate the license file
    dname = BASE_DIR
    fname = os.path.join( dname, "../../LICENSE.txt" ) # nb: if we're running from source
    if not os.path.isfile( fname ):
        fname = os.path.join( dname, "LICENSE.txt" ) # nb: if we're running as a compiled binary
    if not os.path.isfile( fname ):
        # FUDGE! If we've been pip install'ed walk up the directory tree, looking for the license file :-/
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

_control_tests_port_no = None

@app.route( "/control-tests" )
def get_control_tests():
    """Return information about the remote test control service."""

    def get_port():
        """Get the configured gRPC service port."""
        # NOTE: The Docker container configures this setting via an environment variable.
        return app.config.get( "CONTROL_TESTS_PORT", os.environ.get("CONTROL_TESTS_PORT") )

    # check if the test control service should be made available
    port_no = get_port()
    if not port_no:
        abort( 404 )

    # check if we've already started the service
    if not _control_tests_port_no:

        # nope - make it so
        print( "*** WARNING: Remote test control enabled! ***" )
        started_event = threading.Event()
        def run_service(): #pylint: disable=missing-docstring
            import grpc
            server = grpc.server( concurrent.futures.ThreadPoolExecutor( max_workers=1 ) )
            from vasl_templates.webapp.tests.proto.generated.control_tests_pb2_grpc \
                import add_ControlTestsServicer_to_server
            from vasl_templates.webapp.tests.control_tests_servicer import ControlTestsServicer #pylint: disable=cyclic-import
            servicer = ControlTestsServicer( app )
            add_ControlTestsServicer_to_server( servicer, server )
            port_no = parse_int( get_port(), -1 ) # nb: have to get this again?!
            if port_no <= 0:
                # NOTE: Requesting port 0 tells grpc to use any free port, which is usually OK, unless
                # we're running inside a Docker container, in which case it needs to be pre-defined,
                # so that the port can be mapped to an external port when the container is started.
                port_no = 0
            port_no = server.add_insecure_port( "[::]:{}".format( port_no ) )
            logging.getLogger( "control_tests" ).debug(
                "Started the gRPC test control service: port=%s", str(port_no)
            )
            server.start()
            global _control_tests_port_no
            _control_tests_port_no = port_no
            started_event.set()
            shutdown_event.wait()
            server.stop( None )
            server.wait_for_termination()
        thread = threading.Thread( target=run_service, daemon=True )
        thread.start()

        # wait for the service to start (since the caller will probably try to connect
        # to it as soon as we return a response).
        started_event.wait( timeout=10 )

        # wait for the gRPC server to end cleanly when we shutdown
        def cleanup(): #pylint: disable=missing-docstring
            thread.join()
        globvars.cleanup_handlers.append( cleanup )

    # return the service info to the caller
    return jsonify( { "port": _control_tests_port_no } )

# ---------------------------------------------------------------------

@app.route( "/ping" )
def ping():
    """Let the caller know we're alive."""
    return "pong: {}".format( INSTANCE_ID )
