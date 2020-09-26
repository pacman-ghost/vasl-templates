""" Manage downloading files.

This module manages downloading files on a schedule e.g. the ASL Scenario Archive and ROAR scenario indexes.
"""

import os
import threading
import json
import urllib.request
import time
import datetime
import tempfile
import logging

from vasl_templates.webapp import app
from vasl_templates.webapp.utils import parse_int

_registry = set()
_logger = logging.getLogger( "downloads" )

# ---------------------------------------------------------------------

class DownloadedFile:
    """Manage a downloaded file."""

    def __init__( self, key, ttl, fname, url, on_data, extra_args=None ):

        # initialize
        self.key = key
        self.ttl = ttl
        self.fname = fname
        self.url = url
        self.on_data = on_data
        self.error_msg = None

        # initialize
        self._lock = threading.Lock()
        self._data = None

        # install any extra member variables
        if extra_args:
            for k,v in extra_args.items():
                setattr( self, k, v )

        # register this instance
        _registry.add( self )

        # check if we have a cached copy of the file
        self.cache_fname = os.path.join( tempfile.gettempdir(), "vasl-templates."+fname )
        if os.path.isfile( self.cache_fname ):
            # yup - load it
            _logger.info( "Using cached %s file: %s", key, self.cache_fname )
            self._set_data( self.cache_fname )
        else:
            # nope - start with an empty data set
            _logger.debug( "No cached %s file: %s", key, self.cache_fname )

    def _set_data( self, data ):
        """Install a new data set."""
        with self:
            try:
                # install the new data
                if len(data) < 1024 and os.path.isfile( data ):
                    with open( data, "r", encoding="utf-8" ) as fp:
                        data = fp.read()
                self._data = json.loads( data )
                # notify the owner
                if self.on_data:
                    self.on_data( self, self._data, _logger )
            except Exception as ex: #pylint: disable=broad-except
                # NOTE: It would be nice to report this to the user in the UI, but because downloading
                # happens in a background thread, the web page will probably have already finished rendering,
                # and without the ability to push notifications, it's too late to tell the user.
                _logger.error( "Can't install %s data: %s", self.key, ex )

    def __enter__( self ):
        """Gain access to the underlying data.

        Since the file is downloaded in a background thread, access to the underlying data
        must be protected by a lock.
        """
        self._lock.acquire()
        return self._data

    def __exit__( self, exc_type, exc_val, exc_tb ):
        """Relinquish access to the underlying data."""
        self._lock.release()

    @staticmethod
    def download_files():
        """Download fresh copies of each file."""
        #pylint: disable=protected-access

        # process each DownloadedFile
        for df in _registry:

            # check if we should simulate slow downloads
            delay = parse_int( app.config.get( "DOWNLOADED_FILES_DELAY" ) )
            if delay:
                _logger.debug( "Simulating a slow download for the %s file: delay=%s", df.key, delay )
                time.sleep( delay )

            # get the download URL
            url = app.config.get( "{}_DOWNLOAD_URL".format( df.key.upper() ), df.url )
            if os.path.isfile( url ):
                # read the data directly from a file (for debugging porpoises)
                _logger.info( "Loading the %s data directly from a file: %s", df.key, url )
                df._set_data( url )
                continue

            # check if we have a cached copy of the file
            ttl = parse_int( app.config.get( "{}_DOWNLOAD_CACHE_TTL".format( df.key ), df.ttl ), 24 )
            if ttl <= 0:
                _logger.info( "Download of the %s file has been disabled.", df.key )
                continue
            ttl *= 60*60
            if os.path.isfile( df.cache_fname ):
                # yup - check how long ago it was downloaded
                mtime = os.path.getmtime( df.cache_fname )
                age = int( time.time() - mtime )
                _logger.debug( "Checking the cached %s file: age=%s, ttl=%s (mtime=%s)",
                    df.key,
                    datetime.timedelta( seconds=age ),
                    datetime.timedelta( seconds=ttl ),
                    time.strftime( "%Y-%m-%d %H:%M:%S", time.localtime(mtime) )
                )
                if age < ttl:
                    continue

            # download the file
            _logger.info( "Downloading the %s file: %s", df.key, url )
            try:
                req = urllib.request.Request( url,
                    headers = { "Accept-Encoding": "gzip, deflate" }
                )
                fp = urllib.request.urlopen( req )
                data = fp.read().decode( "utf-8" )
            except Exception as ex: #pylint: disable=broad-except
                msg = str( getattr(ex,"reason",None) or ex )
                _logger.error( "Can't download the %s file: %s", df.key, msg )
                df.error_msg = msg
                continue
            _logger.info( "Downloaded the %s file OK: %d bytes", df.key, len(data) )

            # install the new data
            df._set_data( data )
            # NOTE: We only need to worry about thread-safety because a fresh copy of the file is downloaded
            # while the old one is in use, but because downloads are only done once at startup, once we get here,
            # we could delete the lock and allow unfettered access to the underlying data (since it's all
            # going to be read-only).
            # For simplicty, we leave the lock in place. It will slow things down a bit, since we will be
            # serializing access to the data (unnecessarily, because it's all read-only) but none of the code
            # is performance-critical and we can probably live it.

            # save a cached copy of the data
            _logger.debug( "Saving a cached copy of the %s file: %s", df.key, df.cache_fname )
            with open( df.cache_fname, "w", encoding="utf-8" ) as fp:
                fp.write( data )
