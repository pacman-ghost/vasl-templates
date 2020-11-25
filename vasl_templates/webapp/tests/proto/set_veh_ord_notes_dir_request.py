""" Injected functions for SetVehOrdNotesDirRequest. """

from vasl_templates.webapp.tests.proto.generated.control_tests_pb2 import SetVehOrdNotesDirRequest
from .utils import enum_to_string

# ---------------------------------------------------------------------

def brief( self ):
    """Return a SetVehOrdNotesDirRequest as a brief string."""
    return enum_to_string( SetVehOrdNotesDirRequest.DirType, self.dirType ) #pylint: disable=no-member
