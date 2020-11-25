"""gRPC protobuf definitions (for controlling tests)."""

import sys
import importlib

# ---------------------------------------------------------------------

def _init_classes():
    """Initialize the gRPC classes."""

    # process each request/response class
    from .utils import get_classes, split_words
    for cls in get_classes():

        # check if the class has a corresponding module
        words = split_words( cls.__name__ )
        mod_name = "_".join( words )
        try:
            mod2 = importlib.import_module( "vasl_templates.webapp.tests.proto." + mod_name )
        except ModuleNotFoundError:
            continue

        # yup - inject the functions into the class
        for elem2 in dir(mod2):
            obj = getattr( mod2, elem2 )
            if not callable( obj ):
                continue
            setattr( cls, elem2, obj )

# ---------------------------------------------------------------------

_init_classes()
