""" Initialize the package. """

import os
import configparser
import json
import logging

from flask import Flask

from vasl_templates.webapp.config.constants import APP_NAME, BASE_DIR

# ---------------------------------------------------------------------

# initialize Flask
app = Flask( __name__ )

# load the application configuration
config_dir = os.path.join( BASE_DIR, "config" )
config_parser = configparser.ConfigParser()
config_parser.optionxform = str # preserve case for the keys :-/
config_parser.read( os.path.join( config_dir, "app.cfg" ) )
app.config.update( dict( config_parser.items( "System" ) ) )
fname = os.path.join( config_dir, "debug.cfg" )
if os.path.isfile( fname ) :
    config_parser.read( fname )
    app.config.update( dict( config_parser.items( "Debug" ) ) )

# initialize logging
fname = os.path.join( config_dir, "logging.cfg" )
if os.path.isfile( fname ):
    import logging.config
    logging.config.dictConfig( json.load( open(fname,"r") ) )

# load the application
import vasl_templates.webapp.main #pylint: disable=cyclic-import
import vasl_templates.webapp.generate #pylint: disable=cyclic-import

# initialize the application
logger = logging.getLogger( "startup" )

# ---------------------------------------------------------------------

@app.context_processor
def inject_template_params():
    """Inject template parameters into Jinja2."""
    return { "APP_NAME": APP_NAME }
