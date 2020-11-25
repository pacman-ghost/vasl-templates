""" Injected functions for DumpVsavRequest. """

# ---------------------------------------------------------------------

def brief( self ):
    """Return a DumpVsavRequest as a brief string."""
    return "#bytes={}".format( len(self.vsavData) )
