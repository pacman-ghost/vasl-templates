""" Manage downloading files.

This module manages downloading files on a schedule e.g. the ASL Scenario Archive and ROAR scenario indexes.
"""

import os
import threading
import json
import urllib.request
import urllib.error
import time
import datetime
import tempfile
import logging

from vasl_templates.webapp import app
from vasl_templates.webapp.utils import parse_int

_registry = set()
_logger = logging.getLogger( "downloads" )

_etags = {}

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
                self.error_msg = str(ex)

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

        # loop forever (until the program exits)
        while True:

            # process each DownloadedFile
            # NOTE: The DownloadedFile registry is built once at startup, so we don't need to lock it.
            for df in _registry:

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
                if app.config.get( "DISABLE_DOWNLOADED_FILES" ):
                    _logger.info( "Download disabled (%s): %s", df.key, url )
                    continue
                _logger.info( "Downloading the %s file: %s", df.key, url )
                try:
                    headers = { "Accept-Encoding": "gzip, deflate" }
                    if url in _etags:
                        _logger.debug( "- If-None-Match = %s", _etags[url] )
                        headers[ "If-None-Match" ] = _etags[ url ]
                    req = urllib.request.Request( url, headers=headers )
                    resp = urllib.request.urlopen( req )
                    data = resp.read().decode( "utf-8" )
                    etag = resp.headers.get( "ETag" )
                    _logger.info( "Downloaded the %s file OK: %d bytes", df.key, len(data) )
                    if etag:
                        _logger.debug( "- Got etag: %s", etag )
                        _etags[ url ] = etag
                except Exception as ex: #pylint: disable=broad-except
                    if isinstance( ex, urllib.error.HTTPError ) and ex.code == 304: #pylint: disable=no-member
                        _logger.info( "Download %s file: 304 Not Modified", df.key )
                        if os.path.isfile( df.cache_fname ):
                            # NOTE: We touch the file so that the TTL check will work the next time around.
                            os.utime( df.cache_fname )
                        continue
                    msg = str( getattr(ex,"reason",None) or ex )
                    _logger.error( "Can't download the %s file: %s", df.key, msg )
                    df.error_msg = msg
                    continue

                # install the new data
                df._set_data( data )

                # save a cached copy of the data
                _logger.debug( "Saving a cached copy of the %s file: %s", df.key, df.cache_fname )
                with open( df.cache_fname, "w", encoding="utf-8" ) as fp:
                    fp.write( data )

            # sleep before looping back and doing it all again
            delay = parse_int( app.config.get( "DOWNLOAD_CHECK_INTERVAL" ), 2 )
            time.sleep( delay * 60*60 )
