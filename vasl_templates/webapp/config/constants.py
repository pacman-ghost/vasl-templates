""" Application constants. """

import os

APP_NAME = "VASL Templates"
APP_VERSION = "v0.3" # nb: also update setup.py
APP_DESCRIPTION = "Generate HTML for use in VASL scenarios."

BASE_DIR = os.path.abspath( os.path.join( os.path.split(__file__)[0], ".." ) )
DATA_DIR = os.path.join( BASE_DIR, "data" )
