#!/usr/bin/env python3
""" Main entry point for the application. """

import sys
import os
import os.path
import threading
import time
import traceback
import logging
import urllib.request
from urllib.error import URLError

# FUDGE! This works around a problem running the compiled desktop app on Fedora 30.
#  https://github.com/pyinstaller/pyinstaller/issues/1113#issuecomment-244855512
#  https://github.com/pyinstaller/pyinstaller/issues/1113#issuecomment-551934945
import encodings.idna #pylint: disable=unused-import

import PyQt5.QtWebEngineWidgets
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt, QSettings, QDir
import PyQt5.QtCore
import click

from vasl_templates.webapp.utils import SimpleError, is_windows

# NOTE: We're supposed to do the following to support HiDPI, but it causes the main window
# to become extremely large when the Windows zoom level is high (and it doesn't really fix
# the dialog layout problems anyway :-/).# Since we're a webapp running in a browser,
# desktop DPI isn't really an issue for us, we just need to make sure that the Qt dialogs
# look OK. I adjusted the layout for the About box so it's correct for HiDPI; it doesn't
# look great for normal DPI (too much whitespace), but it's useable.
#   # nb: this must be done before the QApplication object is created
#   QApplication.setAttribute( PyQt5.QtCore.Qt.AA_EnableHighDpiScaling, True )
#   QApplication.setAttribute( PyQt5.QtCore.Qt.AA_UseHighDpiPixmaps, True )

# FUDGE! This needs to be created before showing any UI elements e.g. an error message box.
qt_app = QApplication( sys.argv )

app_settings = None

_webapp_error = None # nb: this needs to be global :shrug:

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
def main( template_pack, default_scenario, remote_debugging, debug ):
    """Manage HTML labels in a VASL scenario."""
    try:
        return _do_main( template_pack, default_scenario, remote_debugging, debug )
    except Exception as ex: #pylint: disable=broad-except
        # log the error
        # NOTE: If we get here, there was probably an error during startup, so we can't
        # assume too much about how much of our expected environment has been set up.
        try:
            fname = os.path.join( QDir.homePath(), "vasl-templates.log"  )
            with open( fname, "w", encoding="utf-8" ) as fp:
                traceback.print_exc( file=fp )
        except: #pylint: disable=bare-except
            pass
        QMessageBox.warning( None, "Unexpected error", str(ex) )
        return -1

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _do_main( template_pack, default_scenario, remote_debugging, debug ): #pylint: disable=too-many-locals,too-many-branches
    """Do main processing."""

    # NOTE: We do these imports here (instead of at the top of the file) so that we can catch errors.
    from vasl_templates.webapp import app as webapp
    from vasl_templates.webapp import load_debug_config
    from vasl_templates.webapp import main as webapp_main, snippets as webapp_snippets

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
            raise SimpleError( "Can't find the default scenario file." )
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

    # install the server settings
    try:
        from vasl_templates.server_settings import install_server_settings #pylint: disable=cyclic-import
        install_server_settings( True )
    except Exception as ex: #pylint: disable=broad-except
        # NOTE: We used to advise the user to check the app config file for errors, but exceptions can be thrown
        # for reasons other than errors in that file (e.g. bad JSON in the vehicle/ordnance data files).
        logging.critical( traceback.format_exc() )
        from vasl_templates.main_window import MainWindow #pylint: disable=cyclic-import
        MainWindow.showErrorMsg( "Couldn't install the server settings:\n\n{}".format( ex ) )
        return 2

    # start the webapp server
    flask_port = webapp.config[ "FLASK_PORT_NO" ]
    def webapp_thread():
        """Run the webapp server."""
        try:
            import waitress
            # FUDGE! Browsers tend to send a max. of 6-8 concurrent requests per server, so we increase
            # the number of worker threads to avoid task queue warnings :-/
            nthreads = webapp.config.get( "WAITRESS_THREADS", 8 )
            waitress.serve( webapp,
                host="localhost", port=flask_port,
                threads=nthreads
            )
        except Exception as ex: #pylint: disable=broad-except
            logging.critical( "WEBAPP SERVER EXCEPTION: %s", ex )
            logging.critical( traceback.format_exc() )
            # NOTE: We pass the exception to the GUI thread, where it can be shown to the user.
            global _webapp_error
            _webapp_error = ex
    thread = threading.Thread( target=webapp_thread )
    # FUDGE! If we detect another instance, we hang on Windows after reporting the error. Running the webapp
    # in a daemon thread makes the problem go away - you would think the thread would terminate, since it wouldn't
    # be able to listen on the same server port - but I guess not :-/
    thread.daemon = True
    thread.start()

    # NOTE: We want to detect if another instance of the program is already running, but we can't simply
    # try to connect to the webapp, since we can't tell the difference between connecting to the webapp
    # we just started above, and an already-running instance. We handle this by assigning each instance
    # a unique ID, which lets us figure out if we've connected to ourself, or another instance.
    from vasl_templates.webapp.main import INSTANCE_ID

    # wait for the webapp server to start
    while True:
        if _webapp_error:
            break
        try:
            url = "http://localhost:{}/ping".format( flask_port )
            with urllib.request.urlopen( url ) as resp:
                resp_data = resp.read().decode( "utf-8" )
                # we got a response - figure out if we connected to ourself or another instance
                if resp_data[:6] != "pong: ":
                    raise SimpleError( "Unexpected server check response: {}".format( resp_data ) )
                if resp_data[6:] == INSTANCE_ID:
                    break
            from vasl_templates.webapp.config.constants import APP_NAME
            QMessageBox.warning( None, APP_NAME, "The program is already running." )
            return -1
        except URLError:
            # no response - the webapp server is probably still starting up
            time.sleep( 0.25 )
            continue
        except Exception as ex: #pylint: disable=broad-except
            raise ex
    if _webapp_error:
        # the webapp server didn't start up - re-raise the error in this thread
        raise _webapp_error #pylint: disable=raising-bad-type

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

    #pylint: disable=line-too-long
    # FUDGE! This works around a weird problem on Windows, if it has been configured to *not* show
    # accelerator underlines by default. Pressing ALT is supposed to show them, but doesn't :-/
    # The odd thing is, the default theme is "windowsvista", but we need to set it anyway (probably
    # a timing issue during startup). It might also have something to do with virtualenv's:
    #   https://stackoverflow.com/questions/69032767/show-hide-menu-underline-accelerators-with-pyqt-according-to-platform-integratio#comment122036986_69032767
    #pylint: enable=line-too-long
    if is_windows():
        QApplication.setStyle( "windowsvista" )

    # check if we should disable the embedded browser
    disable_browser = webapp.config.get( "DISABLE_WEBENGINEVIEW" )

    # run the application
    url = "http://localhost:{}".format( flask_port )
    from vasl_templates.main_window import MainWindow #pylint: disable=cyclic-import
    main_window = MainWindow( url, disable_browser )
    main_window.show()
    ret_code = qt_app.exec_()

    return ret_code

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

if __name__ == "__main__":
    sys.exit( main() ) #pylint: disable=no-value-for-parameter
