""" Miscellaneous utilities. """

import os
import functools
import logging
import traceback
import json

from vasl_templates.webapp import app
from vasl_templates.webapp.config.constants import BASE_DIR, IS_FROZEN

# ---------------------------------------------------------------------

def get_build_info():
    """Get the program build info."""

    # locate and load the build info file
    fname = os.path.join( BASE_DIR, "config", "build-info.json" )
    if not os.path.isfile( fname ):
        return None
    with open( fname, "r", encoding="utf-8" ) as fp:
        build_info = json.load( fp )

    # get the build timestamp
    result = { "timestamp": build_info["timestamp"] }

    # get the git info
    if "branch_name" in build_info:
        git_info = build_info[ "branch_name" ]
        if "last_commit_id" in build_info:
            git_info += ":{}".format( build_info["last_commit_id"][:8] )
        result["git_info"] = git_info

    return result

def get_build_git_info():
    """Get the git details for the current build."""
    if IS_FROZEN:
        build_info = get_build_info()
        if build_info:
            return build_info[ "git_info" ]
    elif app.config.get( "IS_CONTAINER" ):
        return os.environ.get( "BUILD_GIT_INFO" )
    return None

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

# ---------------------------------------------------------------------

def show_msg_store( msg_store ):
    """Show messages in a MsgStore."""

    # NOTE: It would be nice to show a single dialog with all the messages, each one tagged with
    # a pretty little icon, but for now, we just show a message box for each message :-/
    from vasl_templates.main_window import MainWindow
    for msg_type in ("error","warning"):
        for msg in msg_store.get_msgs( msg_type ):
            MainWindow.showErrorMsg( msg )
