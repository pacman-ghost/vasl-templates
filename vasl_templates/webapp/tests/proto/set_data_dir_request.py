""" Injected functions for SetDataDirRequest. """

from .generated.control_tests_pb2 import SetDataDirRequest
from .utils import enum_to_string

# ---------------------------------------------------------------------

def brief( self ):
    """Return a SetDataDirRequest as a brief string."""
    return enum_to_string( SetDataDirRequest.DirType, self.dirType ) #pylint: disable=no-member
