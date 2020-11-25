""" Injected functions for SaveTempFileRequest. """

# ---------------------------------------------------------------------

def brief( self ):
    """Return a SaveTempFileRequest as a brief string."""
    return "{} (#bytes={})".format( self.fileName, len(self.data) )
