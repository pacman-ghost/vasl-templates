""" Main application window. """

import os
import re

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog, QMessageBox
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QObject, QUrl, pyqtSlot

from vasl_templates.webapp.config.constants import APP_NAME
from vasl_templates.webapp import app as webapp

_CONSOLE_SOURCE_REGEX = re.compile( r"^http://.+?/static/(.*)$" )

# ---------------------------------------------------------------------

class WebChannelHandler( QObject ):
    """Handle web channel requests."""

    def __init__( self, window ):
        # initialize
        super().__init__()
        self.window = window

    @pyqtSlot( str )
    def on_scenario_name_change( self, val ):
        """Update the main window title to show the scenario name."""
        self.window.setWindowTitle(
            "{} - {}".format( APP_NAME, val ) if val else APP_NAME
        )

# ---------------------------------------------------------------------

class AppWebPage( QWebEnginePage ):
    """Main webapp page."""

    def javaScriptConsoleMessage( self, level, msg, line_no, source_id ): #pylint: disable=unused-argument,no-self-use
        """Log a Javascript console message."""
        mo = _CONSOLE_SOURCE_REGEX.search( source_id )
        source = mo.group(1) if mo else source_id
        print( "{}:{} - {}".format( source, line_no, msg ) )

# ---------------------------------------------------------------------

class MainWindow( QWidget ):
    """Main application window."""

    _main_window = None
    _curr_scenario_fname = None

    def __init__( self, url ):

        # initialize
        assert MainWindow._main_window is None
        MainWindow._main_window = self
        self.view = None
        self._is_closing = False

        # initialize
        super().__init__()
        self.setWindowTitle( APP_NAME )

        # initialize the layout
        # FUDGE! We offer the option to disable the QWebEngineView since getting it to run
        # under Windows (especially older versions) is unreliable (since it uses OpenGL).
        # By disabling it, the program will at least start (in particular, the webapp server),
        # and non-technical users can then open an external browser and connect to the webapp
        # that way. Sigh...
        layout = QVBoxLayout( self )
        if not webapp.config.get( "DISABLE_WEBENGINEVIEW" ):

            # initialize the web view
            self.view = QWebEngineView()
            layout.addWidget( self.view )

            # initialize the web page
            # nb: we create an off-the-record profile to stop the view from using cached JS files :-/
            profile = QWebEngineProfile( None, self.view )
            profile.downloadRequested.connect( self.onDownloadRequested )
            page = AppWebPage( profile, self.view )
            self.view.setPage( page )

            # create a web channel to communicate with the front-end
            web_channel = QWebChannel( page )
            # FUDGE! We would like to register a WebChannelHandler instance as the handler, but this crashes PyQt :-/
            # Instead, we register ourself as the handler, and delegate processing to a WebChannelHandler.
            # The downside is that PyQt emits lots of warnings about our member variables not being properties :-/
            self.web_channel_handler = WebChannelHandler( self )
            web_channel.registerObject( "handler", self )
            page.setWebChannel( web_channel )

            # load the webapp
            url += "?pyqt=1"
            self.view.load( QUrl(url) )

        else:

            # show a minimal UI
            label = QLabel()
            label.setText( "Running the {} application.\n\nClose this window when you're done.".format( APP_NAME ) )
            layout.addWidget( label )

            # open the webapp in an external browser
            QDesktopServices.openUrl( QUrl(url) )

    def closeEvent( self, evt ) :
        """Handle requests to close the window (i.e. exit the application)."""

        # check if we need to check for a dirty scenario
        if self.view is None or self._is_closing:
            return

        # check if the scenario is dirty
        def callback( is_dirty ):
            """Callback for PyQt to return the result of running the Javascript."""
            if not is_dirty:
                # nope - just close the window
                self._is_closing = True
                self.close()
                return
            # yup - ask the user to confirm the close
            rc = QMessageBox.question( self, "Close program",
                "This scenario has been changed\n\nDo you want to close the program, and lose your changes?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if rc == QMessageBox.Yes:
                # confirmed - close the window
                self._is_closing = True
                self.close()
        self.view.page().runJavaScript( "is_scenario_dirty()", callback )
        evt.ignore() # nb: we wait until the Javascript finishes to process the event

    @staticmethod
    def onDownloadRequested( item ):
        """Handle download requests."""

        # ask the user where to save the scenario
        dlg = QFileDialog(
            MainWindow._main_window, "Save scenario",
            os.path.split(MainWindow._curr_scenario_fname)[0] if MainWindow._curr_scenario_fname else None,
            "Scenario files (*.json);;All files(*)"
        )
        dlg.setDefaultSuffix( ".json" )
        if MainWindow._curr_scenario_fname:
            dlg.selectFile( os.path.split(MainWindow._curr_scenario_fname)[1] )
        fname, _  = QFileDialog.getSaveFileName(
            MainWindow._main_window, "Save scenario",
            None,
            "Scenario files (*.json);;All files(*)"
        )
        if not fname:
            return

        # accept the download request
        item.setPath( fname )
        item.accept()
        MainWindow._curr_scenario_fname = fname

    @pyqtSlot( str )
    def on_scenario_name_change( self, val ):
        """Update the main window title to show the scenario name."""
        self.web_channel_handler.on_scenario_name_change( val )
