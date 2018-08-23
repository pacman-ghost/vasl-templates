#!/usr/bin/env python3
""" Main entry point for the application. """

import sys
import os
import os.path
import threading
import traceback
import logging
import urllib.request

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QSettings, QDir
import PyQt5.QtCore
import click

from vasl_templates.main_window import MainWindow
from vasl_templates.webapp import app as webapp
from vasl_templates.webapp import snippets, load_debug_config

# ---------------------------------------------------------------------

_QT_LOGGING_LEVELS = {
    PyQt5.QtCore.QtCriticalMsg: logging.CRITICAL,
    PyQt5.QtCore.QtFatalMsg: logging.ERROR,
    PyQt5.QtCore.QtWarningMsg: logging.WARNING,
    PyQt5.QtCore.QtInfoMsg: logging.INFO,
    PyQt5.QtCore.QtDebugMsg: logging.DEBUG,
}

def qtMessageHandler( msg_type, context, msg ):# pylint: disable=unused-argument
    """Handle PyQt logging messages."""
    # FUDGE! PyQt issues a bunch of warning messages because we had to proxy WebChannel requests
    # via the MainWindow object - we filter them out here.
    if "has no notify signal and is not constant" in msg:
        return
    logging.getLogger( "qt" ).log( _QT_LOGGING_LEVELS[msg_type], "%s", msg )

# ---------------------------------------------------------------------

@click.command()
@click.option( "--template-pack", help="Template pack to auto-load (ZIP file or directory)." )
@click.option( "--remote-debugging", help="Chrome DevTools port number." )
@click.option( "--debug", help="Debug config file." )
def main( template_pack, remote_debugging, debug ):
    """Main entry point for the application."""

    # configure the default template pack
    if template_pack:
        if template_pack.lower().endswith( ".zip" ):
            rc = os.path.isfile( template_pack )
        else:
            rc = os.path.isdir( template_pack )
        if not rc:
            click.echo( "ERROR: The template pack must be a ZIP file, or a directory containing the template files." )
            return 1
        snippets.default_template_pack = template_pack

    # configure remote debugging
    if remote_debugging:
        remote_debugging = remote_debugging.replace( "localhost", "127.0.0.1" )
        os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = remote_debugging

    # load the application settings
    fname = "vasl-templates.ini" if sys.platform == "win32" else ".vasl-templates.conf"
    if not os.path.isfile( fname ) :
        fname = os.path.join( QDir.homePath(), fname  )
    settings = QSettings( fname, QSettings.IniFormat )

    # install the debug config file
    if debug:
        load_debug_config( debug )

    # connect PyQt's logging to Python logging
    PyQt5.QtCore.qInstallMessageHandler( qtMessageHandler )

    # disable the Flask "do not use in a production environment" warning
    import flask.cli
    flask.cli.show_server_banner = lambda *args: None

    # start the webapp server
    port = webapp.config["FLASK_PORT_NO"]
    def webapp_thread():
        """Run the webapp server."""
        try:
            webapp.run( host="localhost", port=port, use_reloader=False )
        except Exception as ex:
            logging.critical( "WEBAPP SERVER EXCEPTION: %s", ex )
            logging.critical( traceback.format_exc() )
            raise
    thread = threading.Thread( target=webapp_thread )
    thread.start()

    # check if we should disable OpenGL
    # Using the QWebEngineView crashes on Windows 7 in a VM. It uses OpenGL, which is
    # apparently not well supported on Windows, and is dependent on the graphics card driver:
    #   https://stackoverflow.com/a/50393872
    #   https://stackoverflow.com/questions/33090346/is-there-any-way-to-use-qtwebengine-without-opengl
    # Switching to software rendering (AA_UseSoftwareOpenGL) got things going :shrug:
    # Also see: https://doc.qt.io/qt-5/windows-requirements.html
    opengl_type = webapp.config.get( "OPENGL_TYPE" )
    if opengl_type:
        logging.info( "Setting OpenGL: %s", opengl_type )
        opengl_type = getattr( Qt, opengl_type )
        QApplication.setAttribute( opengl_type )

    # check if we should disable the embedded browser
    disable_browser = webapp.config.get( "DISABLE_WEBENGINEVIEW" )

    # run the application
    app = QApplication( sys.argv )
    url = "http://localhost:{}".format( port )
    main_window = MainWindow( settings, url, disable_browser )
    main_window.show()
    ret_code = app.exec_()

    # shutdown the webapp server
    url = "http://localhost:{}/shutdown".format( port )
    urllib.request.urlopen( url ).read()
    thread.join()

    return ret_code

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

if __name__ == "__main__":
    sys.exit( main() ) #pylint: disable=no-value-for-parameter
