"""Implement the "server settings" dialog."""

import os
import shutil
import logging
import traceback

from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QFileDialog, QGroupBox
from PyQt5.QtGui import QIcon

from vasl_templates.main import app_settings
from vasl_templates.main_window import MainWindow
from vasl_templates.utils import show_msg_store
from vasl_templates.webapp.vassal import VassalShim, SUPPORTED_VASSAL_VERSIONS_DISPLAY
from vasl_templates.webapp.vasl_mod import set_vasl_mod, SUPPORTED_VASL_MOD_VERSIONS_DISPLAY
from vasl_templates.webapp.utils import MsgStore

# ---------------------------------------------------------------------

_EXE_FSPEC = [ "Executable files (*.exe)" ] if os.name == "nt" else []

SERVER_SETTINGS = {
    "vassal-dir": { "type": "dir", "name": "VASSAL directory" },
    "vasl-mod": { "type": "file", "name": "VASL module", "fspec": ["VASL module files (*.vmod)"] },
    "vasl-extns-dir": { "type": "dir", "name": "VASL extensions directory" },
    "boards-dir": { "type": "dir", "name": "VASL boards directory" },
    "java-path": { "type": "file", "name": "Java executable", "allow_on_path": True, "fspec": _EXE_FSPEC },
    "webdriver-path": { "type": "file", "name": "webdriver", "allow_on_path": True, "fspec": _EXE_FSPEC },
    "chapter-h-notes-dir": { "type": "dir", "name": "Chapter H notes directory" },
    "chapter-h-image-scaling": { "type": "int", "name": "Chapter H image scaling" },
    "user-files-dir": { "type": "dir", "name": "user files directory" },
}

# ---------------------------------------------------------------------

class ServerSettingsDialog( QDialog ):
    """Let the user configure the server settings."""

    def __init__( self, parent ) :

        # initialize
        super().__init__( parent=parent )

        # initialize the UI
        base_dir = os.path.split( __file__ )[0]
        dname = os.path.join( base_dir, "ui/server_settings.ui" )
        uic.loadUi( dname, self )
        self.setFixedSize( self.size() )

        # initialize the UI
        for key in SERVER_SETTINGS:
            btn = getattr( self, "select_{}_button".format( key.replace("-","_") ), None )
            if btn:
                btn.setIcon( QIcon( os.path.join( base_dir, "resources/file_browser.png" ) ) )
        self.vassal_dir.setToolTip( "Supported versions: {}".format( SUPPORTED_VASSAL_VERSIONS_DISPLAY ) )
        self.vasl_mod.setToolTip( "Supported versions: {}".format( SUPPORTED_VASL_MOD_VERSIONS_DISPLAY ) )
        self.webdriver_path.setToolTip( "Configure either geckodriver or chromedriver here." )

        # initialize the UI
        for attr in dir(self):
            attr = getattr( self, attr )
            if isinstance( attr, QGroupBox ):
                attr.setStyleSheet( "QGroupBox { font-weight: bold; } " )

        # initialize click handlers
        def make_click_handler( func, *args ): #pylint: disable=missing-docstring
            # FUDGE! Python looks up variables passed in to a lambda when it is *invoked*, so we need
            # this intermediate function to create lambda's with their arguments at *creation time*.
            return lambda: func( *args )
        for key,vals in SERVER_SETTINGS.items():
            key2 = key.replace( "-", "_" )
            btn = getattr( self, "select_{}_button".format( key2 ), None )
            if btn:
                ctrl = self._get_control( key )
                if vals["type"] == "dir":
                    func = make_click_handler( self._on_select_dir, ctrl, vals["name"] )
                elif vals["type"] == "file":
                    func = make_click_handler( self._on_select_file, ctrl, vals["name"], vals["fspec"] )
                else:
                    assert False
                btn.clicked.connect( func )
        self.ok_button.clicked.connect( self.on_ok )
        self.cancel_button.clicked.connect( self.on_cancel )

        # initialize handlers
        self.chapter_h_notes_dir.textChanged.connect( self.on_chapter_h_notes_dir_changed )

        # load the current server settings
        for key in SERVER_SETTINGS:
            val = app_settings.value( "ServerSettings/"+key ) or ""
            ctrl = self._get_control( key )
            ctrl.setText( str(val).strip() )

    def _on_select_dir( self, ctrl, name ):
        """Ask the user to select a directory."""
        dname = QFileDialog.getExistingDirectory(
            self, "Select {}".format( name ),
            ctrl.text(),
            QFileDialog.ShowDirsOnly
        )
        if dname:
            ctrl.setText( dname )

    def _on_select_file( self, ctrl, name, fspec ):
        """Ask the user to select a file."""
        assert isinstance( fspec, list )
        fspec = fspec[:]
        fspec.append( "All files ({})".format( "*.*" if os.name == "nt" else "*" ) )
        fname = QFileDialog.getOpenFileName(
            self, "Select {}".format( name ),
            ctrl.text(),
            ";;".join( fspec )
        )[0]
        if fname:
            ctrl.setText( fname )

    def on_ok( self ):
        """Accept the new server settings."""

        # save a copy of the current settings
        prev_settings = {
            key: app_settings.value( "ServerSettings/"+key, "" )
            for key in SERVER_SETTINGS
        }

        # unload the dialog
        # NOTE: Typing an unknown path into QFileDialog.getExistingDirectory() causes that directory
        # to be created!?!? It doesn't really matter, since the user could have also manually typed
        # an unknown path into an edit box, so we need to validate everything anyway.
        new_settings = {}
        for key, vals in SERVER_SETTINGS.items():
            ctrl = self._get_control( key )
            func = getattr( self, "_unload_"+vals["type"] )
            args, kwargs = [ vals["name"] ], {}
            if "allow_on_path" in vals:
                kwargs[ "allow_on_path" ] = vals["allow_on_path"]
            val = func( ctrl, *args, **kwargs )
            if val is None:
                # nb: something failed validation, an error message has already been shown
                return
            new_settings[ key ] = val

        # install the new settings
        for key in SERVER_SETTINGS:
            app_settings.setValue( "ServerSettings/"+key, new_settings[key] )
        try:
            install_server_settings( False )
        except Exception as ex: #pylint: disable=broad-except
            logging.error( traceback.format_exc() )
            MainWindow.showErrorMsg( "Couldn't install the server settings:\n\n{}".format( ex ) )
            # rollback the changes
            for key,val in prev_settings.items():
                app_settings.setValue( "ServerSettings/"+key, val )
            try:
                install_server_settings( False )
            except Exception as ex: #pylint: disable=broad-except
                logging.error( traceback.format_exc() )
                MainWindow.showErrorMsg( "Couldn't rollback the server settings:\n\n{}".format( ex ) )
            return
        self.close()

        # check if any key settings were changed
        KEY_SETTINGS = [ "vassal-dir", "vasl-mod", "vasl-extns-dir", "chapter-h-notes-dir" ]
        changed = [
            key for key in KEY_SETTINGS
            if app_settings.value( "ServerSettings/"+key, "" ) != prev_settings[key]
        ]
        if len(changed) == 1:
            MainWindow.showInfoMsg( "The {} was changed - you should restart the program.".format(
                SERVER_SETTINGS[ changed[0] ][ "name" ]
            ) )
        elif len(changed) > 1:
            MainWindow.showInfoMsg( "Some key settings were changed - you should restart the program." )

    def on_cancel( self ):
        """Cancel the dialog."""
        self.close()

    def _update_ui( self ):
        """Update the UI."""
        rc = self.chapter_h_notes_dir.text().strip() != ""
        self.chapter_h_image_scaling_label.setEnabled( rc )
        self.chapter_h_image_scaling_label2.setEnabled( rc )
        self.chapter_h_image_scaling.setEnabled( rc )

    def on_chapter_h_notes_dir_changed( self, val ): #pylint: disable=unused-argument
        """Called when the Chapter H notes directory is changed."""
        self._update_ui()

    @staticmethod
    def _unload_dir( ctrl, name ):
        """Unload and validate a directory path."""
        dname = ctrl.text().strip()
        if dname and not os.path.isdir( dname ):
            MainWindow.showErrorMsg( "Can't find the {}:\n    {}".format( name, dname ) )
            ctrl.setFocus()
            return None
        return dname

    @staticmethod
    def _unload_file( ctrl, name, allow_on_path=False ):
        """Unload and validate a file path."""
        fname = ctrl.text().strip()
        def is_valid( fname ): #pylint: disable=missing-docstring
            if not os.path.isabs(fname) and allow_on_path:
                return shutil.which( fname ) is not None
            return os.path.isfile( fname )
        if fname and not is_valid(fname):
            if not os.path.isabs(fname) and allow_on_path:
                MainWindow.showErrorMsg( "Can't find the {} on the PATH:\n    {}".format( name, fname ) )
            else:
                MainWindow.showErrorMsg( "Can't find the {}:\n    {}".format( name, fname ) )
            ctrl.setFocus()
            return None
        return fname

    @staticmethod
    def _unload_int( ctrl, name ):
        """Unload and validate an integer value."""
        val = ctrl.text().strip()
        if val and not val.isdigit():
            MainWindow.showErrorMsg( "{} must be a numeric value.".format( name ) )
            ctrl.setFocus()
            return None
        return val

    def _get_control( self, key ):
        """Return the UI control for the specified server setting."""
        return getattr( self, key.replace("-","_") )

# ---------------------------------------------------------------------

def install_server_settings( is_startup ):
    """Install the server settings."""

    # install the server settings
    from vasl_templates.webapp import app
    for key in SERVER_SETTINGS:
        key2 = key.replace( "-", "_" ).upper()
        app.config[ key2 ] = app_settings.value( "ServerSettings/"+key )

    # initialize
    if is_startup:
        msg_store = None # nb: we let the web page show startup messages
    else:
        msg_store = MsgStore()

    # load the VASL module
    fname = app_settings.value( "ServerSettings/vasl-mod" )
    set_vasl_mod( fname, msg_store )

    # check the VASSAL version
    VassalShim.check_vassal_version( msg_store )

    # show any messages
    if msg_store:
        show_msg_store( msg_store )
