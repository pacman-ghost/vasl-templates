"""Implement the "server settings" dialog."""

import os

from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QFileDialog
from PyQt5.QtGui import QIcon

from vasl_templates.main import app_settings
from vasl_templates.main_window import MainWindow
from vasl_templates.webapp.config.constants import DATA_DIR
from vasl_templates.webapp.vassal import SUPPORTED_VASSAL_VERSIONS_DISPLAY
from vasl_templates.webapp.file_server.vasl_mod import VaslMod, SUPPORTED_VASL_MOD_VERSIONS_DISPLAY
from vasl_templates.webapp.files import install_vasl_mod

# ---------------------------------------------------------------------

class ServerSettingsDialog( QDialog ):
    """Let the user manage the server settings."""

    def __init__( self, parent ) :

        # initialize
        super().__init__( parent=parent )

        # initialize the UI
        base_dir = os.path.split( __file__ )[0]
        dname = os.path.join( base_dir, "ui/server_settings.ui" )
        uic.loadUi( dname, self )
        for btn in ["vassal_dir","vasl_mod","boards_dir","java","webdriver"]:
            getattr( self, "select_{}_button".format(btn) ).setIcon(
                QIcon( os.path.join( base_dir, "resources/file_browser.png" ) )
            )
        self.setMinimumSize( self.size() )

        # initialize handlers
        self.select_vassal_dir_button.clicked.connect( self.on_select_vassal_dir )
        self.select_vasl_mod_button.clicked.connect( self.on_select_vasl_mod )
        self.select_boards_dir_button.clicked.connect( self.on_select_boards_dir )
        self.select_java_button.clicked.connect( self.on_select_java )
        self.select_webdriver_button.clicked.connect( self.on_select_webdriver )
        self.ok_button.clicked.connect( self.on_ok )
        self.cancel_button.clicked.connect( self.on_cancel )

        # load the current server settings
        self.vassal_dir.setText( app_settings.value( "ServerSettings/vassal-dir" ) )
        self.vassal_dir.setToolTip(
            "Supported versions: {}".format( SUPPORTED_VASSAL_VERSIONS_DISPLAY )
        )
        self.vasl_mod.setText( app_settings.value( "ServerSettings/vasl-mod" ) )
        self.vasl_mod.setToolTip(
            "Supported versions: {}".format( SUPPORTED_VASL_MOD_VERSIONS_DISPLAY )
        )
        self.boards_dir.setText( app_settings.value( "ServerSettings/boards-dir" ) )
        self.java_path.setText( app_settings.value( "ServerSettings/java-path" ) )
        self.webdriver_path.setText( app_settings.value( "ServerSettings/webdriver-path" ) )
        self.webdriver_path.setToolTip( "Configure either geckodriver or chromedriver here." )

    def on_select_vassal_dir( self ):
        """Let the user locate the VASSAL installation directory."""
        dname = QFileDialog.getExistingDirectory(
            self, "Select VASSAL installation directory",
            self.vassal_dir.text(),
            QFileDialog.ShowDirsOnly
        )
        if dname:
            self.vassal_dir.setText( dname )

    def on_select_vasl_mod( self ):
        """Let the user select a VASL module."""
        fname = QFileDialog.getOpenFileName(
            self, "Select VASL module",
            self.vasl_mod.text(),
            "VASL module files (*.vmod);;All files (*.*)"
        )[0]
        if fname:
            self.vasl_mod.setText( fname )

    def on_select_boards_dir( self ):
        """Let the user locate the VASL boards directory."""
        dname = QFileDialog.getExistingDirectory(
            self, "Select VASL boards directory",
            self.boards_dir.text(),
            QFileDialog.ShowDirsOnly
        )
        if dname:
            self.boards_dir.setText( dname )

    def on_select_java( self ):
        """Let the user locate the Java executable."""
        fname = QFileDialog.getOpenFileName(
            self, "Select Java executable",
            self.java_path.text(),
            _make_exe_filter_string()
        )[0]
        if fname:
            self.java_path.setText( fname )

    def on_select_webdriver( self ):
        """Let the user locate the webdriver executable."""
        fname = QFileDialog.getOpenFileName(
            self, "Select webdriver",
            self.webdriver_path.text(),
            _make_exe_filter_string()
        )[0]
        if fname:
            self.webdriver_path.setText( fname )

    def on_ok( self ):
        """Accept the new server settings."""

        # save the new settings
        app_settings.setValue( "ServerSettings/vassal-dir", self.vassal_dir.text() )
        fname = self.vasl_mod.text().strip()
        vasl_mod_changed = fname != app_settings.value( "ServerSettings/vasl-mod" )
        app_settings.setValue( "ServerSettings/vasl-mod", fname )
        app_settings.setValue( "ServerSettings/boards-dir", self.boards_dir.text() )
        app_settings.setValue( "ServerSettings/java-path", self.java_path.text() )
        app_settings.setValue( "ServerSettings/webdriver-path", self.webdriver_path.text() )

        # install the new settings
        # NOTE: We should really do this before saving the new settings, but that's more trouble
        # than it's worth at this stage... :-/
        try:
            install_server_settings()
        except Exception as ex: #pylint: disable=broad-except
            MainWindow.showErrorMsg( "Couldn't install the server settings:\n\n{}".format( ex ) )
            return
        self.close()

        # check if the VASL module was changed
        if vasl_mod_changed:
            # NOTE: It would be nice not to require a restart, but calling QWebEngineProfile.clearHttpCache() doesn't
            # seem to, ya know, clear the cache, nor does setting the cache type to NoCache seem to do anything :-/
            MainWindow.showInfoMsg( "The VASL module was changed - you should restart the program." )

    def on_cancel( self ):
        """Cancel the dialog."""
        self.close()

def _make_exe_filter_string():
    """Make a file filter string for executables."""
    buf = []
    if os.name == "nt":
        buf.append( "Executable files (*.exe)" )
    buf.append( "All files (*.*)" )
    return ";;".join( buf )

# ---------------------------------------------------------------------

def install_server_settings():
    """Install the server settings."""

    # install the server settings
    from vasl_templates.webapp import app as app
    app.config["VASSAL_DIR"] = app_settings.value( "ServerSettings/vassal-dir" )
    app.config["VASL_MOD"] = app_settings.value( "ServerSettings/vasl-mod" )
    app.config["BOARDS_DIR"] = app_settings.value( "ServerSettings/boards-dir" )
    app.config["JAVA_PATH"] = app_settings.value( "ServerSettings/java-path" )
    app.config["WEBDRIVER_PATH"] = app_settings.value( "ServerSettings/webdriver-path" )

    # load the VASL module
    fname = app_settings.value( "ServerSettings/vasl-mod" )
    if fname:
        vasl_mod = VaslMod( fname, DATA_DIR )
    else:
        vasl_mod = None
    install_vasl_mod( vasl_mod )
