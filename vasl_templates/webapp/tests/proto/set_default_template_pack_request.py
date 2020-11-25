""" Injected functions for SetDefaultTemplatePackRequest. """

from vasl_templates.webapp.tests.proto.generated.control_tests_pb2 import SetDefaultTemplatePackRequest
from .utils import enum_to_string

# ---------------------------------------------------------------------

def brief( self ):
    """Return a SetDefaultTemplatePackRequest as a brief string."""
    if self.HasField( "templatePackType" ):
        return enum_to_string(
            SetDefaultTemplatePackRequest.TemplatePackType, #pylint: disable=no-member
            self.templatePackType
        )
    elif self.HasField( "dirName" ):
        return self.dirName
    elif self.HasField( "zipData" ):
        return "zip: #bytes={}".format( len(self.zipData) )
    else:
        assert False
        return str( self ).strip()
