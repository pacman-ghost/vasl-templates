#!/usr/bin/env python3
""" Run the webapp server. """

import os
import threading
import urllib.request
import time
import glob

import click

# ---------------------------------------------------------------------

@click.command()
@click.option( "--addr","-a","bind_addr", help="Webapp server address (host:port)." )
@click.option( "--force-init-delay", default=0, help="Force the webapp to initialize (#seconds delay)." )
@click.option( "--debug","flask_debug", is_flag=True, default=False, help="Run Flask in debug mode." )
def main( bind_addr, force_init_delay, flask_debug ):
    """Run the vasl-templates webapp server."""

    # initialize
    from vasl_templates.webapp import app
    flask_port = None
    if bind_addr:
        words = bind_addr.split( ":" )
        flask_host = words[0]
        if len(words) > 1:
            flask_port = words[1]
    else:
        flask_host = app.config.get( "FLASK_HOST", "localhost" )
    if not flask_port:
        flask_port = app.config.get( "FLASK_PORT_NO" )
    if not flask_debug:
        flask_debug = app.config.get( "FLASK_DEBUG", False )

    # validate the configuration
    if not flask_host:
        raise RuntimeError( "The server host was not set." )
    if not flask_port:
        raise RuntimeError( "The server port was not set." )

    # monitor extra files for changes
    extra_files = []
    fspecs = [ "static/", "static/css/", "static/help/", "templates/", "config/" ]
    fspecs.extend( [ "data/default-template-pack/", "data/default-template-pack/extras/" ] )
    fspecs.extend( [ "tests/control_tests_servicer.py", "tests/proto/generated/" ] )
    for fspec in fspecs:
        fspec = os.path.abspath( os.path.join( os.path.dirname(__file__), fspec ) )
        if os.path.isdir( fspec ):
            files = [ os.path.join(fspec,f) for f in os.listdir(fspec) ]
            files = [ f for f in files if os.path.isfile(f) and os.path.splitext(f)[1] not in [".swp"] ]
        else:
            files = glob.glob( fspec )
        extra_files.extend( files )

    # check if we should force webapp initialization
    if force_init_delay > 0:
        def _start_server():
            """Force the server to do "first request" initialization."""
            # NOTE: This is not needed when running the desktop app (since it will request the home page),
            # but if we're running just the server (i.e. from the console, or a Docker container), then
            # it's useful to send a request (any request), since this will trigger "first request" initialization
            # (in particular, starting the download thread).
            time.sleep( force_init_delay )
            url = "http://{}:{}/ping".format( flask_host, flask_port )
            with urllib.request.urlopen( url ) as resp:
                _ = resp.read()
        threading.Thread( target=_start_server, daemon=True ).start()

    # run the server
    if flask_debug:
        # NOTE: It's useful to run the webapp using the Flask development server, since it will
        # automatically reload itself when the source files change.
        app.run(
            host=flask_host, port=flask_port,
            debug=flask_debug,
            extra_files=extra_files
        )
    else:
        import waitress
        # FUDGE! Browsers tend to send a max. of 6-8 concurrent requests per server, so we increase
        # the number of worker threads to avoid task queue warnings :-/
        nthreads = app.config.get( "WAITRESS_THREADS", 8 )
        waitress.serve( app,
            host=flask_host, port=flask_port,
            threads=nthreads
        )


# ---------------------------------------------------------------------

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
