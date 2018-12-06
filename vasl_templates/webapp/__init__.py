""" Initialize the package. """

import sys
import os
import configparser
import logging
import logging.config

from flask import Flask
import yaml

from vasl_templates.webapp.config.constants import APP_NAME, APP_VERSION, BASE_DIR

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

# initialize Flask
app = Flask( __name__ )

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
        logging.config.dictConfig( yaml.safe_load( fp ) )
else:
    # stop Flask from logging every request :-/
    logging.getLogger( "werkzeug" ).setLevel( logging.WARNING )

# load the application
import vasl_templates.webapp.main #pylint: disable=cyclic-import
import vasl_templates.webapp.vo #pylint: disable=cyclic-import
import vasl_templates.webapp.snippets #pylint: disable=cyclic-import
import vasl_templates.webapp.files #pylint: disable=cyclic-import
import vasl_templates.webapp.vassal #pylint: disable=cyclic-import
if app.config.get( "ENABLE_REMOTE_TEST_CONTROL" ):
    print( "*** WARNING: Remote test control enabled! ***" )
    import vasl_templates.webapp.testing #pylint: disable=cyclic-import

# ---------------------------------------------------------------------

@app.context_processor
def inject_template_params():
    """Inject template parameters into Jinja2."""
    return {
        "APP_NAME": APP_NAME,
        "APP_VERSION": APP_VERSION,
    }
