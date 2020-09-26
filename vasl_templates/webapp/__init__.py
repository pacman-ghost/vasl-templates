""" Initialize the package. """

import sys
import os
import signal
import threading
import configparser
import logging
import logging.config

from flask import Flask
import yaml

from vasl_templates.webapp.config.constants import BASE_DIR

# ---------------------------------------------------------------------

def _on_startup():
    """Do startup initialization."""

    # start downloading files
    # NOTE: We used to do this in the mainline code of __init__, so that we didn't have to wait
    # for the first request before starting the download (useful if we are running as a standalone server).
    # However, this means that the downloads start whenever we import this module e.g. for a stand-alone
    # command-line tool :-/
    from vasl_templates.webapp.downloads import DownloadedFile
    threading.Thread( daemon=True,
        target = DownloadedFile.download_files
    ).start()

    # load the default template_pack
    from vasl_templates.webapp.snippets import load_default_template_pack
    load_default_template_pack()

    # configure the VASL module
    # NOTE: The Docker container configures this setting via an environment variable.
    fname = app.config.get( "VASL_MOD", os.environ.get("VASL_MOD") )
    if fname:
        from vasl_templates.webapp.vasl_mod import set_vasl_mod #pylint: disable=cyclic-import
        from vasl_templates.webapp.main import startup_msg_store #pylint: disable=cyclic-import
        set_vasl_mod( fname, startup_msg_store )

    # load the vehicle/ordnance listings
    from vasl_templates.webapp.vo import load_vo_listings #pylint: disable=cyclic-import
    from vasl_templates.webapp.main import startup_msg_store #pylint: disable=cyclic-import
    load_vo_listings( startup_msg_store )

    # load the vehicle/ordnance notes
    from vasl_templates.webapp.vo_notes import load_vo_notes #pylint: disable=cyclic-import
    load_vo_notes( startup_msg_store )

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

# ---------------------------------------------------------------------

def _on_sigint( signum, stack ): #pylint: disable=unused-argument
    """Clean up after a SIGINT."""
    from vasl_templates.webapp import globvars #pylint: disable=cyclic-import
    for handler in globvars.cleanup_handlers:
        handler()
    raise SystemExit()

# ---------------------------------------------------------------------

# initialize Flask
app = Flask( __name__ )

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

# initialize logging
_fname = os.path.join( config_dir, "logging.yaml" )
if os.path.isfile( _fname ):
    with open( _fname, "r" ) as fp:
        try:
            logging.config.dictConfig( yaml.safe_load( fp ) )
        except Exception as ex: #pylint: disable=broad-except
            logging.error( "Can't load the logging config: %s", ex )
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
if app.config.get( "ENABLE_REMOTE_TEST_CONTROL" ):
    print( "*** WARNING: Remote test control enabled! ***" )
    import vasl_templates.webapp.testing #pylint: disable=cyclic-import

# install our signal handler (must be done in the main thread)
signal.signal( signal.SIGINT, _on_sigint )

# register startup initialization
app.before_first_request( _on_startup )
