""" Miscellaneous utilities. """

import functools
import logging
import traceback

# ---------------------------------------------------------------------

def log_exceptions( caption="EXCEPTION" ):
    """Decorator that logs exceptions thrown by the wrapped function."""
    def decorator( func ):
        """The real decorator function."""
        @functools.wraps( func )
        def wrapper( *args, **kwargs ):
            """Wrapper around the function being decorated."""
            try:
                return func( *args, **kwargs )
            except Exception as ex:
                logging.critical( "%s: %s", caption, ex )
                logging.critical( traceback.format_exc() )
                raise
        return wrapper
    return decorator
