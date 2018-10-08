#!/usr/bin/env python3
""" Main entry point for the application. """

import sys
import os
import os.path
import threading
import traceback
import logging
import urllib.request

import PyQt5.QtWebEngineWidgets
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QSettings, QDir
import PyQt5.QtCore
import click

from vasl_templates.webapp import app as webapp
from vasl_templates.webapp import load_debug_config
from vasl_templates.webapp import main as webapp_main, snippets as webapp_snippets

app_settings = None

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
@click.option( "--default-scenario", help="Default scenario settings." )
@click.option( "--remote-debugging", help="Chrome DevTools port number." )
@click.option( "--debug", help="Debug config file." )
def main( template_pack, default_scenario, remote_debugging, debug ): #pylint: disable=too-many-locals,too-many-branches
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
        webapp_snippets.default_template_pack = template_pack

    # configure the default scenario
    if default_scenario:
        if not os.path.isfile( default_scenario ):
            raise RuntimeError( "Can't find the default scenario file." )
        webapp_main.default_scenario = default_scenario

    # configure remote debugging
    if remote_debugging:
        remote_debugging = remote_debugging.replace( "localhost", "127.0.0.1" )
        os.environ["QTWEBENGINE_REMOTE_DEBUGGING"] = remote_debugging

    # load the application settings
    app_settings_fname = "vasl-templates.ini" if sys.platform == "win32" else ".vasl-templates.conf"
    if not os.path.isfile( app_settings_fname ) :
        app_settings_fname = os.path.join( QDir.homePath(), app_settings_fname  )
    # FUDGE! Declaring app_settings as global here doesn't work on Windows (?!), we have to do this weird import :-/
    import vasl_templates.main #pylint: disable=import-self
    vasl_templates.main.app_settings = QSettings( app_settings_fname, QSettings.IniFormat )

    # install the debug config file
    if debug:
        load_debug_config( debug )

    # connect PyQt's logging to Python logging
    PyQt5.QtCore.qInstallMessageHandler( qtMessageHandler )

    # FUDGE! We need to do this before showing any UI elements e.g. an error message box.
    app = QApplication( sys.argv )

    # install the server settings
    try:
        from vasl_templates.server_settings import install_server_settings #pylint: disable=cyclic-import
        install_server_settings()
    except Exception as ex: #pylint: disable=broad-except
        from vasl_templates.main_window import MainWindow #pylint: disable=cyclic-import
        MainWindow.showErrorMsg(
            "Couldn't install the server settings:\n    {}\n\n"
            "Please correct them in the \"Server settings\" dialog, or in the config file:\n    {}".format(
                ex, app_settings_fname
            )
        )

    # disable the Flask "do not use in a production environment" warning
    import flask.cli
    flask.cli.show_server_banner = lambda *args: None

    # see if we can connect to the webapp server
    port = webapp.config["FLASK_PORT_NO"]
    url = "http://localhost:{}/ping".format( port )
    try:
        resp = urllib.request.urlopen( url ).read()
    except: #pylint: disable=bare-except
        resp = None
    if resp:
        raise RuntimeError( "The application is already running." )

    # start the webapp server
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
    url = "http://localhost:{}".format( port )
    from vasl_templates.main_window import MainWindow #pylint: disable=cyclic-import
    main_window = MainWindow( url, disable_browser )
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
