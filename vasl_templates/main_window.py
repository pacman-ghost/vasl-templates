""" Main application window. """

import sys
import os
import re
import json
import io
import logging

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QMenuBar, QAction, QLabel, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtCore import Qt, QUrl, QMargins, pyqtSlot

from vasl_templates.webapp.config.constants import APP_NAME
from vasl_templates.main import app_settings
from vasl_templates.web_channel import WebChannelHandler
from vasl_templates.utils import log_exceptions

_CONSOLE_SOURCE_REGEX = re.compile( r"^http://.+?/static/(.*)$" )

# ---------------------------------------------------------------------

class AppWebPage( QWebEnginePage ):
    """Application web page."""

    def acceptNavigationRequest( self, url, nav_type, is_mainframe ): #pylint: disable=no-self-use,unused-argument
        """Called when a link is clicked."""
        if url.host() in ("localhost","127.0.0.1"):
            return True
        QDesktopServices.openUrl( url )
        return False

    def javaScriptConsoleMessage( self, level, msg, line_no, source_id ): #pylint: disable=unused-argument,no-self-use
        """Log a Javascript console message."""
        mo = _CONSOLE_SOURCE_REGEX.search( source_id )
        source = mo.group(1) if mo else source_id
        logger = logging.getLogger( "javascript" )
        logger.info( "%s:%d - %s", source, line_no, msg )

# ---------------------------------------------------------------------

class MainWindow( QWidget ):
    """Main application window."""

    instance = None

    def __init__( self, url, disable_browser ):

        # initialize
        super().__init__()
        self._view = None
        self._is_closing = False

        # initialize the main window
        self.setWindowTitle( APP_NAME )
        if getattr( sys, "frozen", False ):
            dname = sys._MEIPASS #pylint: disable=no-member,protected-access
        else:
            dname = os.path.join( os.path.split(__file__)[0], "webapp" )
        self.setWindowIcon( QIcon(
            os.path.join( dname, "static/images/app.ico" )
        ) )

        # create the menu
        menu_bar = QMenuBar( self )
        file_menu = menu_bar.addMenu( "&File" )
        def add_action( caption, handler ):
            """Add a menu action."""
            action = QAction( caption, self )
            action.triggered.connect( handler )
            file_menu.addAction( action )
        add_action( "&Settings", self.on_settings )
        add_action( "E&xit", self.on_exit )

        # set the window geometry
        if disable_browser:
            self.setFixedSize( 300, 108 )
        else:
            # restore it from the previous session
            val = app_settings.value( "MainWindow/geometry" )
            if val :
                self.restoreGeometry( val )
            else :
                self.resize( 1000, 600 )
            self.setMinimumSize( 800, 500 )

        # initialize the layout
        layout = QVBoxLayout( self )
        layout.addWidget( menu_bar )
        # FUDGE! We offer the option to disable the QWebEngineView since getting it to run
        # under Windows (especially older versions) is unreliable (since it uses OpenGL).
        # By disabling it, the program will at least start (in particular, the webapp server),
        # and non-technical users can then open an external browser and connect to the webapp
        # that way. Sigh...
        if not disable_browser:

            # initialize the web view
            self._view = QWebEngineView()
            layout.addWidget( self._view )

            # initialize the web page
            # nb: we create an off-the-record profile to stop the view from using cached JS files :-/
            profile = QWebEngineProfile( None, self._view )
            page = AppWebPage( profile, self._view )
            self._view.setPage( page )

            # create a web channel to communicate with the front-end
            web_channel = QWebChannel( page )
            # FUDGE! We would like to register a WebChannelHandler instance as the handler, but this crashes PyQt :-/
            # Instead, we register ourself as the handler, and delegate processing to a WebChannelHandler.
            # The downside is that PyQt emits lots of warnings about our member variables not being properties,
            # but we filter them out in qtMessageHandler() :-/
            self._web_channel_handler = WebChannelHandler( self )
            web_channel.registerObject( "handler", self )
            page.setWebChannel( web_channel )

            # load the webapp
            url += "?pyqt=1"
            self._view.load( QUrl(url) )

        else:

            # show a minimal UI
            label = QLabel()
            label.setTextFormat( Qt.RichText )
            label.setText(
                "Running the <em>{}</em> application. <br>" \
                "Click <a href='{}'>here</a> to connect." \
                "<p> Close this window when you're done.".format(
                APP_NAME, url
            ) )
            label.setStyleSheet( "QLabel { background-color: white ; padding: 0.5em ; }" )
            label.setOpenExternalLinks( True )
            layout.addWidget( label )
            layout.setContentsMargins( QMargins(0,0,0,0) )

        # register the instance
        assert MainWindow.instance is None
        MainWindow.instance = self

    def closeEvent( self, evt ) :
        """Handle requests to close the window (i.e. exit the application)."""

        # check if we need to check for a dirty scenario
        if self._view is None or self._is_closing:
            return

        def close_window():
            """Close the main window."""
            if self._view:
                app_settings.setValue( "MainWindow/geometry", self.saveGeometry() )
            self.close()

        # check if the scenario is dirty
        def callback( is_dirty ):
            """Callback for PyQt to return the result of running the Javascript."""
            if not is_dirty:
                # nope - just close the window
                self._is_closing = True
                close_window()
                return
            # yup - ask the user to confirm the close
            rc = MainWindow.ask(
                "This scenario has been changed\n\nDo you want to close the program, and lose your changes?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if rc == QMessageBox.Yes:
                # confirmed - close the window
                self._is_closing = True
                close_window()
        self._view.page().runJavaScript( "is_scenario_dirty()", callback )
        evt.ignore() # nb: we wait until the Javascript finishes to process the event

    @staticmethod
    def showInfoMsg( msg ):
        """Show an informational message."""
        QMessageBox.information( MainWindow.instance, APP_NAME, msg )

    @staticmethod
    def showErrorMsg( msg ):
        """Show an error message."""
        QMessageBox.warning( MainWindow.instance, APP_NAME, msg )

    @staticmethod
    def ask( msg, buttons, default ) :
        """Ask the user a question."""
        return QMessageBox.question( MainWindow.instance, APP_NAME, msg, buttons, default )

    def on_exit( self ):
        """Menu action handler."""
        self.close()

    def on_settings( self ):
        """Menu action handler."""
        from vasl_templates.server_settings import ServerSettingsDialog #pylint: disable=cyclic-import
        dlg = ServerSettingsDialog( self )
        dlg.exec_()

    @pyqtSlot()
    @log_exceptions( caption="SLOT EXCEPTION" )
    def on_app_loaded( self ):
        """Called when the application has finished loading.

        NOTE: This handler might be called multiple times.
        """
        # load and install the user settings
        buf = io.StringIO()
        buf.write( "{" )
        for key in app_settings.allKeys():
            if key.startswith( "UserSettings/" ):
                val = app_settings.value(key)
                if val in ("true","false") or val.isdigit():
                    buf.write( '"{}": {},'.format( key[13:], val ) )
                else:
                    buf.write( '"{}": "{}",'.format( key[13:], val ) )
        buf.write( '"_dummy_": null }' )
        buf = buf.getvalue()
        user_settings = {}
        try:
            user_settings = json.loads( buf )
        except Exception as ex: #pylint: disable=broad-except
            MainWindow.showErrorMsg( "Couldn't load the user settings:\n\n{}".format( ex ) )
            logging.error( "Couldn't load the user settings: %s", ex )
            logging.error( buf )
            return
        del user_settings["_dummy_"]
        self._view.page().runJavaScript(
            "install_user_settings('{}')".format( json.dumps( user_settings ) )
        )

    @pyqtSlot()
    @log_exceptions( caption="SLOT EXCEPTION" )
    def on_new_scenario( self ):
        """Called when the user wants to load a scenario."""
        self._web_channel_handler.on_new_scenario()

    @pyqtSlot( result=str )
    @log_exceptions( caption="SLOT EXCEPTION" )
    def load_scenario( self ):
        """Called when the user wants to load a scenario."""
        return self._web_channel_handler.load_scenario()

    @pyqtSlot( str, result=bool )
    @log_exceptions( caption="SLOT EXCEPTION" )
    def save_scenario( self, data ):
        """Called when the user wants to save a scenario."""
        return self._web_channel_handler.save_scenario( data )

    @pyqtSlot( str )
    @log_exceptions( caption="SLOT EXCEPTION" )
    def on_user_settings_change( self, user_settings ): #pylint: disable=no-self-use
        """Called when the user changes the user settings."""
        # delete all existing keys
        for key in app_settings.allKeys():
            if key.startswith( "UserSettings/" ):
                app_settings.remove( key )
        # save the new user settings
        user_settings = json.loads( user_settings )
        for key,val in user_settings.items():
            app_settings.setValue( "UserSettings/{}".format(key), val )

    @pyqtSlot( str )
    @log_exceptions( caption="SLOT EXCEPTION" )
    def on_scenario_name_change( self, val ):
        """Update the main window title to show the scenario name."""
        self._web_channel_handler.on_scenario_name_change( val )
