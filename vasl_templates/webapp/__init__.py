""" Initialize the package. """

import sys
import os
import signal
import threading
import time
import tempfile
import configparser
import logging
import logging.config

from flask import Flask, request
import flask.cli
import yaml

from vasl_templates.webapp.config.constants import BASE_DIR

shutdown_event = threading.Event()
_LOCK_FNAME = os.path.join( tempfile.gettempdir(), "vasl-templates.lock" )

# ---------------------------------------------------------------------

_init_done = False
_init_lock = threading.Lock()

def _on_request():
    """Called before each request."""
    # initialize the webapp on the first request, except for $/control-tests.
    # NOTE: The test suite calls $/control-tests to find out which port the gRPC test control service
    # is running on, which is nice since we don't need to configure both ends with a predefined port.
    # However, we don't want this call to trigger initialization, since the tests will often want to
    # configure the remote webapp before loading the main page.
    if request.path == "/control-tests":
        return
    with _init_lock:
        global _init_done
        if not _init_done or (request.path == "/" and request.args.get("force-reinit")):
            try:
                _init_webapp()
            except Exception as ex: #pylint: disable=broad-except
                from vasl_templates.webapp.main import startup_msg_store #pylint: disable=cyclic-import
                startup_msg_store.error( str(ex) )
            finally:
                # NOTE: It's important to set this, even if initialization failed, so we don't
                # try to initialize again.
                _init_done = True

def _init_webapp():
    """Do startup initialization."""

    # NOTE: While this is generally called only once (before the first request), the test suite
    # can force it be done again, since it wants to reconfigure the server to test different cases.

    # initialize
    from vasl_templates.webapp.main import startup_msg_store #pylint: disable=cyclic-import

    # start downloading files
    # NOTE: We used to do this in the mainline code of __init__, so that we didn't have to wait
    # for the first request before starting the download (useful if we are running as a standalone server).
    # However, this means that the downloads start whenever we import this module e.g. for a stand-alone
    # command-line tool :-/ Instead, we send a dummy request in run_server.py to trigger a call
    # to this function.
    if not _init_done:
        from vasl_templates.webapp.downloads import DownloadedFile
        threading.Thread( daemon=True,
            target = DownloadedFile.download_files
        ).start()

    # load the default template_pack
    from vasl_templates.webapp.snippets import load_default_template_pack
    load_default_template_pack()

    # configure the VASL module
    fname = app.config.get( "VASL_MOD" )
    from vasl_templates.webapp.vasl_mod import set_vasl_mod #pylint: disable=cyclic-import
    set_vasl_mod( fname, startup_msg_store )

    # load the vehicle/ordnance listings
    from vasl_templates.webapp.vo import load_vo_listings #pylint: disable=cyclic-import
    load_vo_listings( startup_msg_store )

    # load the vehicle/ordnance notes
    from vasl_templates.webapp.vo_notes import load_vo_notes #pylint: disable=cyclic-import
    load_vo_notes( startup_msg_store )

    # initialize the vehicle/ordnance notes image cache
    from vasl_templates.webapp import vo_notes as webapp_vo_notes #pylint: disable=reimported
    dname = app.config.get( "VO_NOTES_IMAGE_CACHE_DIR" )
    if dname in ( "disable", "disabled" ):
        webapp_vo_notes._vo_notes_image_cache_dname = None #pylint: disable=protected-access
    elif dname:
        webapp_vo_notes._vo_notes_image_cache_dname = dname #pylint: disable=protected-access
    else:
        webapp_vo_notes._vo_notes_image_cache_dname = os.path.join( #pylint: disable=protected-access
            tempfile.gettempdir(), "vasl-templates", "vo-notes-image-cache"
        )

    # load integration data from asl-rulebook2
    from vasl_templates.webapp.vo_notes import load_asl_rulebook2_vo_note_targets #pylint: disable=cyclic-import
    load_asl_rulebook2_vo_note_targets( startup_msg_store )

# ---------------------------------------------------------------------

def _load_config( fname, section ):
    """Load config settings from a file."""
    if not os.path.isfile( fname ):
        return
    config_parser = configparser.ConfigParser()
    config_parser.optionxform = str # preserve case for the keys :-/
    config_parser.read( fname )
    app.config.update( dict( config_parser.items( section) ) )

def load_debug_config( fname ):
    """Configure the application."""
    _load_config( fname, "Debug" )

def _set_config_from_env( key ):
    """Set an app config setting from an environment variable."""
    val = os.environ.get( key )
    if val:
        app.config[ key ] = val

def _is_flask_child_process():
    """Check if we are the Flask child process."""
    # NOTE: There are actually 3 possible cases:
    #   (*) Flask reloading is enabled:
    #       - we are the parent process (returns False)
    #       - we are the child process (returns True)
    #   (*) Flask reloading is disabled:
    #       - returns False
    return os.environ.get( "WERKZEUG_RUN_MAIN" ) is not None

# ---------------------------------------------------------------------

def _on_sigint( signum, stack ): #pylint: disable=unused-argument
    """Clean up after a SIGINT."""

    # FUDGE! Since we added gRPC test control, we want to shutdown properly and clean things up (e.g. temp files
    # created by the gRPC service), but the Flask reloader complicates what we have to do here horribly :-(
    # Since automatic reloading is a really nice feature to have, we try to handle things.
    # If the Flask app is started with reloading enabled, it launches a child process to actually do the work,
    # that is restarted when any of the monitored files change. It's easy for each process to figure out
    # if it's the parent or child, but they need to synchronize their shutdown. Both processes get the SIGINT,
    # but the parent can't just exit, since that will cause the child process to terminate, even if it hasn't
    # finished shutting down i.e. the parent process needs to wait for the child process to finish shutting down
    # before it can exit itself.
    # Unfortunately, the way the child process is launched (see werkzeug._reloader.restart_with_reloader())
    # means that there is no way for us to know what the child process is (and hence be able to wait for it),
    # so the way the child process tells its parent that it has finished shutting down is via a lock file.

    # NOTE: We always go through the shutdown process, regardless of whether we are the Flask parent or child process,
    # because if Flask reloading is disabled, there will be only one process (that will look like it's the parent),
    # and there doesn't seem to be any way to check if reloading is enabled or not. Note that if reloading is enabled,
    # then doing shutdown in the parent process will be harmless, since it won't have done any real work (it's all done
    # by the child process), and so there won't be anything to clean up.

    # notify everyone that we're shutting down
    shutdown_event.set()

    # call any registered cleanup handlers
    from vasl_templates.webapp import globvars #pylint: disable=cyclic-import
    for handler in globvars.cleanup_handlers:
        handler()

    if _is_flask_child_process():
        # notify the parent process that we're done
        os.unlink( _LOCK_FNAME )
    else:
        # we are the Flask parent process (so we wait for the child process to finish) or Flask reloading
        # is disabled (and the wait below will end immediately, because the lock file was never created).
        # NOTE: If, for whatever reason, the lock file doesn't get deleted, we give up waiting and exit anyway.
        # This means that the child process might not get to finish cleaning up properly, but if it hasn't
        # deleted the lock file, it was probably in trouble anyway.
        for _ in range(0, 20):
            # NOTE: os.path.isfile() and .exists() both return True even after the log file has gone!?!?
            # Is somebody caching something somewhere? :-/
            try:
                with open( _LOCK_FNAME, "rb" ):
                    pass
            except FileNotFoundError:
                break
            time.sleep( 0.1 )
        raise SystemExit()

# ---------------------------------------------------------------------

# disable the Flask startup banner
flask.cli.show_server_banner = lambda *args: None

# initialize Flask
app = Flask( __name__ )
if _is_flask_child_process():
    # we are the Flask child process - create a lock file
    with open( _LOCK_FNAME, "wb" ):
        pass

# set config defaults
# NOTE: These are defined here since they are used by both the back- and front-ends.
app.config[ "ASA_SCENARIO_URL" ] = "https://aslscenarioarchive.com/scenario.php?id={ID}"
app.config[ "ASA_PUBLICATION_URL" ] = "https://aslscenarioarchive.com/viewPub.php?id={ID}"
app.config[ "ASA_PUBLISHER_URL" ] = "https://aslscenarioarchive.com/viewPublisher.php?id={ID}"
app.config[ "ASA_GET_SCENARIO_URL" ] = "https://aslscenarioarchive.com/rest/scenario/list/{ID}"
app.config[ "ASA_MAX_VASL_SETUP_SIZE" ] = 200 # nb: KB
app.config[ "ASA_MAX_SCREENSHOT_SIZE" ] = 200 # nb: KB

# load the application configuration
config_dir = os.path.join( BASE_DIR, "config" )
_fname = os.path.join( config_dir, "app.cfg" )
_load_config( _fname, "System" )

# load any site configuration
_fname = os.path.join( config_dir, "site.cfg" )
_load_config( _fname, "Site Config" )

# load any debug configuration
_fname = os.path.join( config_dir, "debug.cfg" )
if os.path.isfile( _fname ) :
    load_debug_config( _fname )

# load any config from environment variables (e.g. set in the Docker container)
# NOTE: We could add these settings to the container's site.cfg, so that they are always defined, and things
# would work (or not) depending on whether anything had been mapped to the endpoints. For example, if nothing
# had been mapped to /data/vassal/, we would not find a Vengine.jar and it would look like no VASSAL engine
# had been configured). However, requiring things to be explicitly turned on via an environment variable
# lets us issue better error message, such as "VASSAL has not been configured".
_set_config_from_env( "VASSAL_DIR" )
_set_config_from_env( "VASL_MOD" )
_set_config_from_env( "VASL_EXTNS_DIR" )
_set_config_from_env( "BOARDS_DIR" )
_set_config_from_env( "CHAPTER_H_NOTES_DIR" )
_set_config_from_env( "USER_FILES_DIR" )
# NOTE: The Docker container also sets DEFAULT_TEMPLATE_PACK, but we read it directly from
# the environment variable, since it is not something that is stored in app.config.

# initialize logging
_fname = os.path.join( config_dir, "logging.yaml" )
if os.path.isfile( _fname ):
    with open( _fname, "r", encoding="utf-8" ) as fp:
        try:
            logging.config.dictConfig( yaml.safe_load( fp ) )
        except Exception as _ex: #pylint: disable=broad-except
            logging.error( "Can't load the logging config: %s", _ex )
else:
    # stop Flask from logging every request :-/
    logging.getLogger( "werkzeug" ).setLevel( logging.WARNING )

# load the application
import vasl_templates.webapp.main #pylint: disable=cyclic-import
import vasl_templates.webapp.vo #pylint: disable=cyclic-import
import vasl_templates.webapp.snippets #pylint: disable=cyclic-import
import vasl_templates.webapp.files #pylint: disable=cyclic-import
import vasl_templates.webapp.vassal #pylint: disable=cyclic-import
import vasl_templates.webapp.vo_notes #pylint: disable=cyclic-import
import vasl_templates.webapp.nat_caps #pylint: disable=cyclic-import
import vasl_templates.webapp.scenarios #pylint: disable=cyclic-import
import vasl_templates.webapp.downloads #pylint: disable=cyclic-import
import vasl_templates.webapp.lfa #pylint: disable=cyclic-import

# install our signal handler (must be done in the main thread)
signal.signal( signal.SIGINT, _on_sigint )

# register startup initialization
app.before_request( _on_request )
