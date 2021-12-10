""" Main webapp handlers. """

import os
import threading
import concurrent
import socket
import json
import uuid
from datetime import datetime, timedelta
import re
import logging

from flask import request, render_template, jsonify, send_file, redirect, url_for, abort

from vasl_templates.webapp import app, shutdown_event
from vasl_templates.webapp.vassal import VassalShim
from vasl_templates.webapp.utils import MsgStore, get_java_version, parse_int
import vasl_templates.webapp.config.constants
from vasl_templates.webapp.config.constants import BASE_DIR, DATA_DIR, IS_FROZEN
from vasl_templates.webapp import globvars
from vasl_templates.webapp.lfa import DEFAULT_LFA_DICE_HOTNESS_WEIGHTS, DEFAULT_LFA_DICE_HOTNESS_THRESHOLDS
from vasl_templates.utils import get_build_info

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
    for key in [ "APP_NAME", "APP_VERSION", "APP_DESCRIPTION", "APP_HOME_URL" ]:
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
        with open( fname, "r", encoding="utf-8" ) as fp:
            try:
                vals[ "SCENARIOS_CONFIG" ] = json.load( fp )
            except json.decoder.JSONDecodeError:
                msg = "Couldn't load the ASL Scenario Archive config."
                logging.error( "%s", msg )
                startup_msg_store.error( msg )

    return jsonify( vals )

# ---------------------------------------------------------------------

@app.route( "/program-info" )
def get_program_info():
    """Get the program info."""

    # NOTE: We can't convert to local time, since the time zone inside a Docker container
    # may not be the same as on the host (or where the client is). It's possible to make it so,
    # but messy, so to keep things simple, we get the client to pass in the timezone offset.
    tz_offset = parse_int( request.args.get( "tz_offset", 0 ) )
    def to_localtime( tstamp ):
        """Convert a timestamp to local time."""
        return tstamp + timedelta( minutes=tz_offset )

    # set the basic details
    params = {
        "APP_VERSION": vasl_templates.webapp.config.constants.APP_VERSION,
        "VASSAL_VERSION": VassalShim.get_version()
    }
    if globvars.vasl_mod:
        params[ "VASL_VERSION" ] = globvars.vasl_mod.vasl_version
    for key in [ "VASSAL_DIR", "VASL_MOD", "VASL_EXTNS_DIR", "BOARDS_DIR",
                 "JAVA_PATH", "WEBDRIVER_PATH", "CHAPTER_H_NOTES_DIR", "USER_FILES_DIR" ]:
        params[ key ] = app.config.get( key )
    params[ "JAVA_VERSION" ] = get_java_version()

    def parse_timestamp( val ):
        """Parse a timestamp."""
        if not val:
            return None
        # FUDGE! Adjust the timezone offset from "HH:MM" to "HHMM".
        val = re.sub( r"(\d{2}):(\d{2})$", r"\1\2", val )
        try:
            val = datetime.strptime( val, "%Y-%m-%d %H:%M:%S %z" )
        except ValueError:
            return None
        return to_localtime( val )

    def replace_mountpoint( key ):
        """Replace a mount point with its corresponding target (on the host)."""
        params[ key ] = os.environ.get( "{}_TARGET".format( key ) )

    # check if we are running the desktop application
    if IS_FROZEN:
        # yup - return information about the build
        build_info = get_build_info()
        if build_info:
            params[ "BUILD_TIMESTAMP" ] = datetime.strftime(
                to_localtime( datetime.utcfromtimestamp( build_info["timestamp"] ) ),
                "%H:%M (%d %b %Y)"
            )
            params[ "BUILD_GIT_INFO" ] = build_info[ "git_info" ]

    # check if we are running inside a Docker container
    if app.config.get( "IS_CONTAINER" ):
        # yup - return related information
        params[ "BUILD_GIT_INFO" ] = os.environ.get( "BUILD_GIT_INFO" )
        params[ "DOCKER_IMAGE_NAME" ] = os.environ.get( "DOCKER_IMAGE_NAME" )
        params[ "DOCKER_IMAGE_TIMESTAMP" ] = datetime.strftime(
            parse_timestamp( os.environ.get( "DOCKER_IMAGE_TIMESTAMP" ) ),
            "%H:%M %d %b %Y"
        )
        params[ "DOCKER_CONTAINER_NAME" ] = os.environ.get( "DOCKER_CONTAINER_NAME" )
        with open( "/proc/self/cgroup", "r", encoding="utf-8" ) as fp:
            buf = fp.read()
        mo = re.search( r"^\d+:name=.+/docker/([0-9a-f]{12})", buf, re.MULTILINE )
        # NOTE: Reading cgroup stopped working when we upgraded to Fedora 33, but still works
        # on Centos 8 (but reading the host name gives the physical host's name under Centos :-/).
        # NOTE: os.uname() is not available on Windows. This isn't really a problem (since
        # we're running on Linux inside a container), but pylint is complaining :-/
        params[ "DOCKER_CONTAINER_ID" ] = mo.group(1) if mo else socket.gethostname()
        # replace Docker mount points with their targets on the host
        for key in [ "VASSAL_DIR", "VASL_MOD", "VASL_EXTNS_DIR", "BOARDS_DIR",
                     "CHAPTER_H_NOTES_DIR", "USER_FILES_DIR" ]:
            replace_mountpoint( key )

    # check the scenario index downloads
    def check_df( df ): #pylint: disable=missing-docstring
        with df:
            if not os.path.isfile( df.cache_fname ):
                return
            mtime = datetime.utcfromtimestamp( os.path.getmtime( df.cache_fname ) )
            key = "LAST_{}_SCENARIO_INDEX_DOWNLOAD_TIME".format( df.key )
            params[ key ] = datetime.strftime(to_localtime(mtime), "%H:%M (%d %b %Y)" )
            generated_at = parse_timestamp( getattr( df, "generated_at", None ) )
            if generated_at:
                key =  "LAST_{}_SCENARIO_INDEX_GENERATED_AT".format( df.key )
                params[ key ] = datetime.strftime( generated_at, "%H:%M %d %b %Y" )
    from vasl_templates.webapp.scenarios import _asa_scenarios, _roar_scenarios
    check_df( _asa_scenarios )
    check_df( _roar_scenarios )

    return render_template( "program-info-content.html", **params )

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
    with open( fname, "r", encoding="utf-8" ) as fp:
        return jsonify( json.load( fp ) )

# ---------------------------------------------------------------------

_control_tests_port_no = None

@app.route( "/control-tests" )
def get_control_tests():
    """Return information about the remote test control service."""

    def get_port():
        """Get the configured gRPC service port."""
        # NOTE: The Docker container configures this setting via an environment variable.
        # NOTE: It would be nice to default this to -1, so that pytest will work out-of-the-box,
        # without the user having to do anything, but since this endpoint can be used to
        # mess with the server, we don't want it active by default.
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

@app.route( "/favicon.ico" )
def get_favicon():
    """Get the license."""
    # FUDGE! We specify the favicon in the main page (in a <link> tag), but the additional support pages
    # don't have this, which results in a spurious and annoying 404 warning message in the console,
    # so we explicitly provide this endpoint :-/
    # NOTE: The icon file is a little on the chunky side (since it contains a lot of variants) but we don't
    # want to just remove them, since this file is also used as the app icon for the desktop icon.
    # We could strip it down here, but that's overkill :-/
    return app.send_static_file( "images/app.ico" )

# ---------------------------------------------------------------------

@app.route( "/ping" )
def ping():
    """Let the caller know we're alive."""
    return "pong: {}".format( INSTANCE_ID )
