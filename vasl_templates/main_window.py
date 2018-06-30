""" Main application window. """

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtCore import QUrl

from vasl_templates.webapp.config.constants import APP_NAME
from vasl_templates.webapp import app as webapp

# ---------------------------------------------------------------------

class MainWindow( QWidget ):
    """Main application window."""

    def __init__( self, url ):

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
            browser = QWebEngineView()
            layout.addWidget( browser )
            browser.setUrl( QUrl(url) )
        else:
            label = QLabel()
            label.setText( "Running the {} application.\n\nClose this window when you're done.".format( APP_NAME ) )
            layout.addWidget( label )
            QDesktopServices.openUrl( QUrl(url) )
