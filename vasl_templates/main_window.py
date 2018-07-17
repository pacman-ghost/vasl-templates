""" Main application window. """

import os

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl

from vasl_templates.webapp.config.constants import APP_NAME
from vasl_templates.webapp import app as webapp

# ---------------------------------------------------------------------

class MainWindow( QWidget ):
    """Main application window."""

    _main_window = None
    _curr_scenario_fname = None

    def __init__( self, url ):

        # initialize
        assert MainWindow._main_window is None
        MainWindow._main_window = self

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
            # load the webapp
            # NOTE: We create an off-the-record profile to stop the view from using cached JS files :-/
            view = QWebEngineView()
            layout.addWidget( view )
            profile = QWebEngineProfile( None, view )
            profile.downloadRequested.connect( self.onDownloadRequested )
            page = QWebEnginePage( profile, view )
            view.setPage( page )
            view.load( QUrl(url) )
        else:
            label = QLabel()
            label.setText( "Running the {} application.\n\nClose this window when you're done.".format( APP_NAME ) )
            layout.addWidget( label )
            QDesktopServices.openUrl( QUrl(url) )

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
