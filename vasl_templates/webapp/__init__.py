""" Initialize the package. """

import os
import configparser
import logging
import logging.config

from flask import Flask
import yaml

from vasl_templates.webapp.config.constants import APP_NAME, APP_VERSION, BASE_DIR

# ---------------------------------------------------------------------

def load_debug_config( fname ):
    """Configure the application."""
    config_parser.read( fname )
    app.config.update( dict( config_parser.items( "Debug" ) ) )

# ---------------------------------------------------------------------

# initialize Flask
app = Flask( __name__ )

# load the application configuration
config_dir = os.path.join( BASE_DIR, "config" )
config_parser = configparser.ConfigParser()
config_parser.optionxform = str # preserve case for the keys :-/
config_parser.read( os.path.join( config_dir, "app.cfg" ) )
app.config.update( dict( config_parser.items( "System" ) ) )

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

# ---------------------------------------------------------------------

@app.context_processor
def inject_template_params():
    """Inject template parameters into Jinja2."""
    return {
        "APP_NAME": APP_NAME,
        "APP_VERSION": APP_VERSION,
    }
