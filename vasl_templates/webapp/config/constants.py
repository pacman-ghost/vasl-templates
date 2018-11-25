""" Application constants. """

import sys
import os

APP_NAME = "VASL Templates"
APP_VERSION = "v0.5" # nb: also update setup.py
APP_DESCRIPTION = "Generate HTML for use in VASL scenarios."

if getattr( sys, "frozen", False ):
    IS_FROZEN = True
    BASE_DIR = os.path.split( sys.executable )[0]
else:
    IS_FROZEN = False
    BASE_DIR = os.path.abspath( os.path.join( os.path.split(__file__)[0], ".." ) )
DATA_DIR = os.path.join( BASE_DIR, "data" )
