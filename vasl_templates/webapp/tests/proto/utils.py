"""Utility functions."""

import inspect

# ---------------------------------------------------------------------

def get_classes():
    """Get the request/response classes."""
    from .generated import control_tests_pb2
    for elem in dir( control_tests_pb2 ):
        if not inspect.isclass( type(elem) ):
            continue
        if not elem.endswith( ( "Request", "Response" ) ):
            continue
        cls = getattr( control_tests_pb2, elem )
        yield cls

# ---------------------------------------------------------------------

def split_words( val ):
    """Extract words from a camel-cased string."""
    words, curr_word = [], []
    for ch in val:
        if ch.isupper():
            if curr_word:
                words.append( "".join( curr_word ) )
            curr_word = []
        curr_word.append( ch.lower() )
    if curr_word:
        words.append( "".join( curr_word ) )
    return words

# ---------------------------------------------------------------------

def enum_to_string( enum, val ):
    """Convert an enum value to a string."""
    val = enum.Name( val )
    return "{%s}" % val

def enum_from_string( enum, val ):
    """Convert a string to an enum value."""
    if not val.startswith( "{" ) or not val.endswith( "}" ):
        raise ValueError( "Invalid enumerated value for {}: {}".format( enum.DESCRIPTOR.full_name, val ) )
    return enum.Value( val[1:-1] )
