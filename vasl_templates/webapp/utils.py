""" Miscellaneous utilities. """

import os
import io
import tempfile
import pathlib
from collections import defaultdict

from flask import request, Response, send_file
from PIL import Image

# ---------------------------------------------------------------------

class MsgStore:
    """Store different types of messages."""

    def __init__( self ):
        self._msgs = None
        self.reset()

    def reset( self ):
        """Reset the MsgStore."""
        self._msgs = defaultdict( list )

    def info( self, msg, *args, **kwargs ):
        """Add an informational message."""
        self._add_msg( "info", msg, *args, **kwargs )

    def warning( self, msg, *args, **kwargs ):
        """Add a warning message."""
        self._add_msg( "warning", msg, *args, **kwargs )

    def error( self, msg, *args, **kwargs ):
        """Add an error message."""
        self._add_msg( "error", msg, *args, **kwargs )

    def get_msgs( self, msg_type ):
        """Get stored messages."""
        return self._msgs[ msg_type ]

    def _add_msg( self, msg_type, msg, *args, **kwargs ):
        """Add a message to the store."""
        logger = kwargs.pop( "logger", None )
        msg = msg.format( *args, **kwargs )
        self._msgs[ msg_type ].append( msg )
        if logger:
            func = getattr( logger, "warn" if msg_type == "warning" else msg_type )
            func( msg )

# ---------------------------------------------------------------------

class TempFile:
    """Manage a temp file that can be closed while it's still being used."""

    def __init__( self, mode="wb", extn=None, encoding=None ):
        self.mode = mode
        self.extn = extn
        self.encoding = encoding
        self.temp_file = None
        self.name = None

    def __enter__( self ):
        """Allocate a temp file."""
        if self.encoding:
            encoding = self.encoding
        else:
            encoding = "utf-8" if "b" not in self.mode else None
        self.temp_file = tempfile.NamedTemporaryFile(
            mode = self.mode,
            encoding = encoding,
            suffix = self.extn,
            delete = False
        )
        self.name = self.temp_file.name
        return self

    def __exit__( self, exc_type, exc_val, exc_tb ):
        """Clean up the temp file."""
        self.close()
        os.unlink( self.temp_file.name )

    def write( self, data ):
        """Write data to the temp file."""
        self.temp_file.write( data )

    def close( self ):
        """Close the temp file."""
        self.temp_file.close()

# ---------------------------------------------------------------------

def resize_image_response( resp, default_width=None, default_height=None, default_scaling=None ):
    """Resize an image that will be returned as a Flask response."""

    assert isinstance( resp, Response )

    def get_image():
        """Get the the image from the Flask response that was passed in."""
        resp.direct_passthrough = False
        buf = io.BytesIO()
        buf.write( resp.get_data() )
        buf.seek( 0 )
        return Image.open( buf )

    # check if the caller specified a width and/or height
    width = request.args.get( "width", default_width )
    height = request.args.get( "height", default_height )
    if width and height:
        # width and height were specified, just use them as-is
        img = get_image()
        width = int( width )
        height = int( height )
    elif width and not height:
        # width only, calculate the height
        img = get_image()
        aspect_ratio = float(img.size[0]) / float(img.size[1])
        height = int(width) / aspect_ratio
    elif not width and height:
        # height only, calculate the width
        img = get_image()
        aspect_ratio = float(img.size[0]) / float(img.size[1])
        width = int(height) * aspect_ratio
    elif not width and not height:
        # check if the caller specified a scaling factor
        scaling = request.args.get( "scaling", default_scaling )
        if scaling and scaling != 100:
            img = get_image()
            width = img.size[0] * float(scaling)/100
            height = img.size[1] * float(scaling)/100

    # check if we need to resize the image
    if width or height:
        assert width and height
        # yup - make it so
        img = img.resize( (int(width),int(height)), Image.ANTIALIAS )
        buf = io.BytesIO()
        img.save( buf, format="PNG" )
        buf.seek( 0 )
        return send_file( buf, mimetype="image/png" )
    else:
        # nope - return the image as-is
        return resp

# ---------------------------------------------------------------------

def change_extn( fname, extn ):
    """Change a filename's extension."""
    return pathlib.Path( fname ).with_suffix( extn )

def is_image_file( fname ):
    """Check if a file is an image."""
    if fname.startswith( "." ):
        extn = fname
    else:
        extn = os.path.splitext( fname )[1]
    return extn.lower() in (".png",".jpg",".jpeg",".gif")

def is_empty_file( fname ):
    """Check if a file is empty."""
    return os.stat( fname ).st_size == 0

# ---------------------------------------------------------------------

class SimpleError( Exception ):
    """Represents a simple error that doesn't require a stack trace (e.g. bad configuration)."""
    pass
