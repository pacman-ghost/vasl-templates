"""Provide integration with ROAR."""
# Bodhgaya, India (APR/19)

import os.path
import threading
import json
import time
import datetime
import tempfile
import logging
import urllib.request

from flask import render_template, jsonify

from vasl_templates.webapp import app

_roar_scenario_index = {}
_roar_scenario_index_lock = threading.Lock()

_logger = logging.getLogger( "roar" )

ROAR_SCENARIO_INDEX_URL = "http://vasl-templates.org/services/roar/scenario-index.json"
CACHE_TTL = 6 * 60*60

# ---------------------------------------------------------------------

def init_roar( msg_store ):
    """Initialize ROAR integration."""

    # initialize
    download = True
    cache_fname = os.path.join( tempfile.gettempdir(), "vasl-templates.roar-scenario-index.json" )
    enable_cache = not app.config.get( "DISABLE_ROAR_SCENARIO_INDEX_CACHE" )
    if not enable_cache:
        cache_fname = None

    # check if we have a cached copy of the scenario index
    if enable_cache and os.path.isfile( cache_fname ):
        # yup - load it, so that we have something until we finish downloading a fresh copy
        _logger.info( "Loading cached ROAR scenario index: %s", cache_fname )
        with open( cache_fname, "r" ) as fp:
            _load_roar_scenario_index( fp.read(), "cached", msg_store )
        # check if we should download a fresh copy
        mtime = os.path.getmtime( cache_fname )
        age = int( time.time() - mtime )
        _logger.debug( "Cached scenario index age: %s (ttl=%s) (mtime=%s)",
            datetime.timedelta(seconds=age), datetime.timedelta(seconds=CACHE_TTL),
            time.strftime( "%Y-%m-%d %H:%M:%S", time.gmtime(mtime) )
        )
        if age < CACHE_TTL:
            download = False

    # check if we should download the ROAR scenario index
    if download:
        if app.config.get("DISABLE_ROAR_SCENARIO_INDEX_DOWNLOAD"):
            _logger.warning( "Downloading the ROAR scenario index has been disabled." )
        else:
            # yup - make it so (nb: we do it in a background thread to avoid blocking the startup process)
            # NOTE: This is the only place we do this, so if it fails, the program needs to be restarted to try again.
            # This is not great, but we can live it (e.g. we will generally be using the cached copy).
            threading.Thread( target = _download_roar_scenario_index,
                args = ( cache_fname, msg_store )
            ).start()

def _download_roar_scenario_index( save_fname, msg_store ):
    """Download the ROAR scenario index."""

    # download the ROAR scenario index
    url = app.config.get( "ROAR_SCENARIO_INDEX_URL", "https://vasl-templates.org/services/roar/scenario-index.json" )
    _logger.info( "Downloading ROAR scenario index: %s", url )
    try:
        fp = urllib.request.urlopen( url )
        data = fp.read().decode( "utf-8" )
    except Exception as ex: #pylint: disable=broad-except
        # NOTE: We catch all exceptions, since we don't want an error here to stop us from running :-/
        error_msg = "Can't download ROAR scenario index: {}".format( getattr(ex,"reason",str(ex)) )
        _logger.warning( error_msg )
        if msg_store:
            msg_store.warning( error_msg )
        return
    if not _load_roar_scenario_index( data, "downloaded", msg_store ):
        # NOTE: If we fail to load the scenario index (e.g. because of invalid JSON), we exit here
        # and won't overwrite the cached copy of the file with the bad data.
        return

    # save a copy of the data
    if save_fname:
        _logger.debug( "Saving a copy of the ROAR scenario index: %s", save_fname )
        with open( save_fname, "w" ) as fp:
            fp.write( data )

def _load_roar_scenario_index( data, data_type, msg_store ):
    """Load the ROAR scenario index."""

    # load the ROAR scenario index
    try:
        scenario_index = json.loads( data )
    except Exception as ex: #pylint: disable=broad-except
        # NOTE: We catch all exceptions, since we don't want an error here to stop us from running :-/
        error_msg = "Can't load {} ROAR scenario index: {}".format( data_type, ex )
        _logger.warning( error_msg )
        if msg_store:
            msg_store.warning( error_msg )
        return False
    _logger.debug( "Loaded %s ROAR scenario index OK: #scenarios=%d", data_type, len(scenario_index) )
    _logger.debug( "- Last updated: %s", scenario_index.get( "_lastUpdated_", "n/a" ) )
    _logger.debug( "- # playings:   %s", str( scenario_index.get( "_nPlayings_", "n/a" ) ) )
    _logger.debug( "- Generated at: %s", scenario_index.get( "_generatedAt_", "n/a" ) )

    # install the new ROAR scenario index
    with _roar_scenario_index_lock:
        global _roar_scenario_index
        _roar_scenario_index = scenario_index

    return True

# ---------------------------------------------------------------------

@app.route( "/roar/scenario-index" )
def get_roar_scenario_index():
    """Return the ROAR scenario index."""
    with _roar_scenario_index_lock:
        return jsonify( _roar_scenario_index )

# ---------------------------------------------------------------------

@app.route( "/roar/check" )
def check_roar():
    """Check the ROAR data (for testing porpoises only)."""
    return render_template( "check-roar.html" )
