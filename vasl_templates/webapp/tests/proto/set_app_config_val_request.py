""" Injected functions for SetAppConfigValRequest. """

# ---------------------------------------------------------------------

def brief( self ):
    """Return a SetAppConfigValRequest as a brief string."""
    for val_type in ( "strVal", "intVal", "boolVal" ):
        if self.HasField( val_type ):
            val = getattr( self, val_type )
            return "{} = {} ({})".format(
                self.key, val, type(val).__name__
            )
    assert False
    return "{} = ???".format( self.key )
