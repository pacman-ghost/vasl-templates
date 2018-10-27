"""Implement the "server settings" dialog."""

import os

from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QFileDialog
from PyQt5.QtGui import QIcon

from vasl_templates.main import app_settings
from vasl_templates.main_window import MainWindow
from vasl_templates.webapp.config.constants import DATA_DIR
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
        self.select_vasl_mod_button.setIcon(
            QIcon( os.path.join( base_dir, "resources/file_browser.png" ) )
        )
        self.setMinimumSize( self.size() )

        # initialize handlers
        self.select_vasl_mod_button.clicked.connect( self.on_select_vasl_mod )
        self.ok_button.clicked.connect( self.on_ok )
        self.cancel_button.clicked.connect( self.on_cancel )

        # load the current server settings
        self.vasl_mod.setText( app_settings.value( "ServerSettings/vasl-mod" ) )
        self.vasl_mod.setToolTip(
            "Supported versions: {}".format( SUPPORTED_VASL_MOD_VERSIONS_DISPLAY )
        )

    def on_select_vasl_mod( self ):
        """Let the user select a VASL module."""
        fname = QFileDialog.getOpenFileName(
            self, "Select VASL module",
            app_settings.value( "ServerSettings/vasl-mod" ),
            "VASL module files (*.vmod)|All files (*.*)"
        )[0]
        if fname:
            self.vasl_mod.setText( fname )

    def on_ok( self ):
        """Accept the new server settings."""

        # save the new settings
        fname = self.vasl_mod.text().strip()
        vasl_mod_changed = fname != app_settings.value( "ServerSettings/vasl-mod" )
        app_settings.setValue( "ServerSettings/vasl-mod", fname )

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

# ---------------------------------------------------------------------

def install_server_settings():
    """Install the server settings."""

    # load the VASL module
    fname = app_settings.value( "ServerSettings/vasl-mod" )
    if fname:
        vasl_mod = VaslMod( fname, DATA_DIR )
    else:
        vasl_mod = None
    install_vasl_mod( vasl_mod )
