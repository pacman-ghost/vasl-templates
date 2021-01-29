""" Miscellaneous utilities. """

import os
import shutil
import io
import tempfile
import pathlib
import math
import re
import logging
from collections import defaultdict

from flask import request, Response, send_file
from PIL import Image, ImageChops

from vasl_templates.webapp import app

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
        if args or kwargs:
            # NOTE: We only format the message if there are any parameters, to handle the case
            # where the caller passed us a single string that happens to contain a {.
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

    def open( self ):
        """Allocate a temp file."""
        if self.encoding:
            encoding = self.encoding
        else:
            encoding = "utf-8" if "b" not in self.mode else None
        assert self.temp_file is None
        self.temp_file = tempfile.NamedTemporaryFile(
            mode = self.mode,
            encoding = encoding,
            suffix = self.extn,
            delete = False
        )
        self.name = self.temp_file.name

    def close( self, delete ):
        """Close the temp file."""
        self.temp_file.close()
        if delete:
            os.unlink( self.temp_file.name )

    def write( self, data ):
        """Write data to the temp file."""
        self.temp_file.write( data )

    def save_copy( self, fname, logger, caption ):
        """Make a copy of the temp file (for debugging porpoises)."""
        if not fname:
            return
        logger.debug( "Saving a copy of the %s: %s", caption, fname )
        shutil.copyfile( self.temp_file.name, fname )

    def __enter__( self ):
        """Enter the context manager."""
        self.open()
        return self

    def __exit__( self, exc_type, exc_val, exc_tb ):
        """Exit the context manager."""
        self.close( delete=True )

# ---------------------------------------------------------------------

def read_text_file( fname ):
    """Read a text file."""
    # NOTE: There are several places where we read user-generated files (e.g. template packs, Chapter H notes),
    # which contain HTML content, so the ideal case is that they be plain ASCII, with special characters specified
    # as HTML entities. However, people are copy-and-pasting Chapter H content from their eASLRB's, which means
    # we need to handle encoding. chardet is overkill for what we need, and we simply try the most common cases.
    encodings = app.config.get( "TEXT_FILE_ENCODINGS", "ascii,utf-8,windows-1252,iso-8859-1" )
    with open( fname, "rb" ) as fp:
        buf = fp.read()
        if buf[0:3] == b"\xEF\xBB\xBF":
            buf = buf[3:]
            encodings = "utf-8"
        for enc in encodings.split( "," ):
            try:
                return buf.decode( enc.strip() )
            except UnicodeDecodeError:
                pass
    msg = "Can't decode text file: {}".format( fname )
    logging.warning( msg )
    return msg

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

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def trim_image( img ):
    """Trim whitespace from an image."""
    if isinstance( img, str ):
        img = Image.open( img )
    # trim the screenshot (nb: we assume a white background)
    img = remove_alpha_from_image( img )
    bgd = Image.new( img.mode, img.size, (255,255,255) )
    diff = ImageChops.difference( img, bgd )
    bbox = diff.getbbox()
    return img.crop( bbox )

def get_image_data( img, **kwargs ):
    """Get the data from a Pillow image."""
    buf = io.BytesIO()
    img.save( buf, format=kwargs.pop("format","PNG"), **kwargs )
    buf.seek( 0 )
    return buf.read()

def remove_alpha_from_image( img ):
    """Remove the alpha channel from an image."""
    return img.convert( "RGB" )

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

def parse_int( val, default=None ):
    """Parse an integer."""
    try:
        return int( val )
    except (ValueError, TypeError):
        return default

# ---------------------------------------------------------------------

def compare_version_strings( lhs, rhs  ):
    """Compare two version strings."""
    def parse( val ): #pylint: disable=missing-docstring
        mo = re.search( r"^(\d+)\.(\d+)\.(\d+)$", val )
        return ( int(mo.group(1)), int(mo.group(2)), int(mo.group(3)) )
    lhs, rhs = parse(lhs), parse(rhs)
    if lhs < rhs:
        return -1
    elif lhs > rhs:
        return +1
    else:
        return 0

def friendly_fractions( val, postfix=None, postfix2=None ):
    """Convert decimal values to more friendly fractions."""
    if val is None:
        return None
    frac, val = math.modf( float( val ) )
    if frac >= 0.875:
        val = str( int(val) + 1 )
    else:
        val = str( int( val ) )
        if frac >= 0.625:
            val = val + "&frac34;"
        elif frac >= 0.375:
            val = val + "&frac12;"
        elif frac >= 0.125:
            val = val + "&frac14;"
    if postfix:
        if val == "0":
            return "0 " + postfix2
        elif val.startswith( "0&" ):
            return val[1:] + " " + postfix
        elif val == "1":
            return "1 " + postfix
        val = "{} {}".format( val, postfix2 )
    return val[1:] if val.startswith( "0&" ) else val

# ---------------------------------------------------------------------

_MONTH_NAMES = [ # nb: we assume English :-/
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]

_DAY_OF_MONTH_POSTFIXES = { # nb: we assume English :-/
    0: "th",
    1: "st", 2: "nd", 3: "rd", 4: "th", 5: "th", 6: "th", 7: "th", 8: "th", 9: "th", 10: "th",
    11: "th", 12: "th", 13: "th"
}

def get_month_name( month ):
    """Return a month name."""
    return _MONTH_NAMES[ month-1 ]

def make_formatted_day_of_month( dom ):
    """Generate a formatted day of the month."""
    if dom in _DAY_OF_MONTH_POSTFIXES:
        return str(dom) + _DAY_OF_MONTH_POSTFIXES[ dom ]
    else:
        return str(dom) + _DAY_OF_MONTH_POSTFIXES[ dom % 10 ]

# ---------------------------------------------------------------------

class SimpleError( Exception ):
    """Represents a simple error that doesn't require a stack trace (e.g. bad configuration)."""
