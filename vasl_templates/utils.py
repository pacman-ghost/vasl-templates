""" Miscellaneous utilities. """

import functools
import logging
import traceback

# ---------------------------------------------------------------------

def catch_exceptions( caption="EXCEPTION", retval=None ):
    """Decorator that handles exceptions thrown by the wrapped function.

    We have to wrap every callback fuction that the front-end invokes with this,
    otherwise an exception will cause the program to crash and die :-/
    """
    def decorator( func ):
        """The real decorator function."""
        @functools.wraps( func )
        def wrapper( *args, **kwargs ):
            """Wrapper around the function being decorated."""
            try:
                return func( *args, **kwargs )
            except Exception as ex: #pylint: disable=broad-except
                logging.critical( "%s: %s", caption, ex )
                logging.critical( traceback.format_exc() )
                from vasl_templates.main_window import MainWindow #pylint: disable=cyclic-import
                MainWindow.showErrorMsg( "Unexpected callback error:\n\n{}".format( str(ex) ) )
                return retval
        return wrapper
    return decorator
