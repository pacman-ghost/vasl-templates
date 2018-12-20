""" Miscellaneous utilities. """

import os
import tempfile
import pathlib

# ---------------------------------------------------------------------

class TempFile:
    """Manage a temp file that can be closed while it's still being used."""

    def __init__( self, mode="wb", extn=None ):
        self.mode = mode
        self.extn = extn
        self.temp_file = None
        self.name = None

    def __enter__( self ):
        """Allocate a temp file."""
        self.temp_file = tempfile.NamedTemporaryFile( mode=self.mode, suffix=self.extn, delete=False )
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

def change_extn( fname, extn ):
    """Change a filename's extension."""
    return pathlib.Path( fname ).with_suffix( extn )

def is_image_file( fname ):
    """Check if a file is an image."""
    if fname.startswith( "." ):
        extn = fname
    else:
        extn = os.path.splitext( fname )[0]
    return extn.lower() in (".png",".jpg",".jpeg",".gif")

# ---------------------------------------------------------------------

class SimpleError( Exception ):
    """Represents a simple error that doesn't require a stack trace (e.g. bad configuration)."""
    pass
