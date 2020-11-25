""" Injected functions for SetVaslVersionRequest. """

from vasl_templates.webapp.tests.proto.generated.control_tests_pb2 import SetVaslVersionRequest
from .utils import enum_to_string

# ---------------------------------------------------------------------

def brief( self ):
    """Return a SetVaslVersionRequest as a brief string."""
    return "{} (extns={})".format(
        self.vaslVersion,
        enum_to_string( SetVaslVersionRequest.VaslExtnsType, self.vaslExtnsType ) #pylint: disable=no-member
    )
