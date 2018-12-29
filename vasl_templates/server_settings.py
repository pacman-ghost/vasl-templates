"""Implement the "server settings" dialog."""

import os

from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QFileDialog, QGroupBox
from PyQt5.QtGui import QIcon

from vasl_templates.main import app_settings
from vasl_templates.main_window import MainWindow
from vasl_templates.utils import show_msg_store
from vasl_templates.webapp.vassal import VassalShim, SUPPORTED_VASSAL_VERSIONS_DISPLAY
from vasl_templates.webapp.utils import MsgStore
from vasl_templates.webapp.file_server.vasl_mod import set_vasl_mod, SUPPORTED_VASL_MOD_VERSIONS_DISPLAY

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
        for btn in ["vassal_dir", "vasl_mod", "vasl_extns_dir", "boards_dir",
                    "java", "webdriver",
                    "chapter_h_notes_dir", "user_files_dir"
        ]:
            getattr( self, "select_{}_button".format(btn) ).setIcon(
                QIcon( os.path.join( base_dir, "resources/file_browser.png" ) )
            )
        self.setFixedSize( self.size() )

        # initialize the UI
        for attr in dir(self):
            attr = getattr( self, attr )
            if isinstance( attr, QGroupBox ):
                attr.setStyleSheet("QGroupBox { font-weight: bold; } ")

        # initialize handlers
        self.select_vassal_dir_button.clicked.connect( self.on_select_vassal_dir )
        self.select_vasl_mod_button.clicked.connect( self.on_select_vasl_mod )
        self.select_vasl_extns_dir_button.clicked.connect( self.on_select_vasl_extns_dir )
        self.select_boards_dir_button.clicked.connect( self.on_select_boards_dir )
        self.select_java_button.clicked.connect( self.on_select_java )
        self.select_webdriver_button.clicked.connect( self.on_select_webdriver )
        self.select_chapter_h_notes_dir_button.clicked.connect( self.on_select_chapter_h_notes_dir )
        self.select_user_files_dir_button.clicked.connect( self.on_select_user_files_dir )
        self.ok_button.clicked.connect( self.on_ok )
        self.cancel_button.clicked.connect( self.on_cancel )

        # initialize handlers
        self.chapter_h_notes_dir.textChanged.connect( self.on_chapter_h_notes_dir_changed )

        # load the current server settings
        self.vassal_dir.setText( app_settings.value( "ServerSettings/vassal-dir" ) )
        self.vassal_dir.setToolTip(
            "Supported versions: {}".format( SUPPORTED_VASSAL_VERSIONS_DISPLAY )
        )
        self.vasl_mod.setText( app_settings.value( "ServerSettings/vasl-mod" ) )
        self.vasl_mod.setToolTip(
            "Supported versions: {}".format( SUPPORTED_VASL_MOD_VERSIONS_DISPLAY )
        )
        self.vasl_extns_dir.setText( app_settings.value( "ServerSettings/vasl-extns-dir" ) )
        self.boards_dir.setText( app_settings.value( "ServerSettings/boards-dir" ) )
        self.java_path.setText( app_settings.value( "ServerSettings/java-path" ) )
        self.webdriver_path.setText( app_settings.value( "ServerSettings/webdriver-path" ) )
        self.webdriver_path.setToolTip( "Configure either geckodriver or chromedriver here." )
        self.chapter_h_notes_dir.setText( app_settings.value( "ServerSettings/chapter-h-notes-dir" ) )
        scaling = app_settings.value( "ServerSettings/chapter-h-image-scaling" )
        if scaling:
            self.chapter_h_image_scaling.setText( str( scaling ) )
        self.user_files_dir.setText( app_settings.value( "ServerSettings/user-files-dir" ) )

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

    def on_select_vasl_extns_dir( self ):
        """Let the user locate the VASL extensions directory."""
        dname = QFileDialog.getExistingDirectory(
            self, "Select VASL extensions directory",
            self.vasl_extns_dir.text(),
            QFileDialog.ShowDirsOnly
        )
        if dname:
            self.vasl_extns_dir.setText( dname )

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
            self, "Select webdriver executable",
            self.webdriver_path.text(),
            _make_exe_filter_string()
        )[0]
        if fname:
            self.webdriver_path.setText( fname )

    def on_select_chapter_h_notes_dir( self ):
        """Let the user locate their Chapter H notes directory."""
        dname = QFileDialog.getExistingDirectory(
            self, "Select Chapter H notes directory",
            self.chapter_h_notes_dir.text(),
            QFileDialog.ShowDirsOnly
        )
        if dname:
            self.chapter_h_notes_dir.setText( dname )

    def on_select_user_files_dir( self ):
        """Let the user locate their user files directory."""
        dname = QFileDialog.getExistingDirectory(
            self, "Select user files directory",
            self.user_files_dir.text(),
            QFileDialog.ShowDirsOnly
        )
        if dname:
            self.user_files_dir.setText( dname )

    def on_ok( self ):
        """Accept the new server settings."""

        # unload the dialog
        try:
            chapter_h_image_scaling = self.chapter_h_image_scaling.text().strip()
            if chapter_h_image_scaling:
                chapter_h_image_scaling = int( self.chapter_h_image_scaling.text() )
        except ValueError:
            MainWindow.showErrorMsg( "Image scaling must be a numeric percentage value." )
            self.chapter_h_image_scaling.setFocus()
            return

        # save the current values for key settings
        KEY_SETTINGS = {
            "vassal-dir": "VASSAL directory",
            "vasl-mod": "VASL module",
            "vasl-extns-dir": "VASL extensions directory",
            "chapter-h-notes-dir": "Chapter H directory",
        }
        prev_vals = {
            k: app_settings.value( "ServerSettings/"+k, "" )
            for k in KEY_SETTINGS
        }

        # save the new settings
        app_settings.setValue( "ServerSettings/vassal-dir", self.vassal_dir.text().strip() )
        app_settings.setValue( "ServerSettings/vasl-mod", self.vasl_mod.text().strip() )
        app_settings.setValue( "ServerSettings/vasl-extns-dir", self.vasl_extns_dir.text().strip() )
        app_settings.setValue( "ServerSettings/boards-dir", self.boards_dir.text().strip() )
        app_settings.setValue( "ServerSettings/java-path", self.java_path.text().strip() )
        app_settings.setValue( "ServerSettings/webdriver-path", self.webdriver_path.text().strip() )
        app_settings.setValue( "ServerSettings/chapter-h-notes-dir", self.chapter_h_notes_dir.text().strip() )
        app_settings.setValue( "ServerSettings/chapter-h-image-scaling", chapter_h_image_scaling )
        app_settings.setValue( "ServerSettings/user-files-dir", self.user_files_dir.text().strip() )

        # install the new settings
        # NOTE: We should really do this before saving the new settings, but that's more trouble
        # than it's worth at this stage... :-/
        try:
            install_server_settings( False )
        except Exception as ex: #pylint: disable=broad-except
            MainWindow.showErrorMsg( "Couldn't install the server settings:\n\n{}".format( ex ) )
            return
        self.close()

        # check if any key settings were changed
        changed = [
            k for k in KEY_SETTINGS
            if app_settings.value( "ServerSettings/"+k, "" ) != prev_vals[k]
        ]
        if len(changed) == 1:
            MainWindow.showInfoMsg( "The {} was changed - you should restart the program.".format(
                KEY_SETTINGS[changed[0]]
            ) )
        elif len(changed) > 1:
            MainWindow.showInfoMsg( "Some key settings were changed - you should restart the program." )

    def on_cancel( self ):
        """Cancel the dialog."""
        self.close()

    def update_ui( self ):
        """Update the UI."""
        rc = self.chapter_h_notes_dir.text().strip() != ""
        self.chapter_h_image_scaling_label.setEnabled( rc )
        self.chapter_h_image_scaling_label2.setEnabled( rc )
        self.chapter_h_image_scaling.setEnabled( rc )

    def on_chapter_h_notes_dir_changed( self, val ): #pylint: disable=unused-argument
        """Called when the Chapter H notes directory is changed."""
        self.update_ui()

def _make_exe_filter_string():
    """Make a file filter string for executables."""
    buf = []
    if os.name == "nt":
        buf.append( "Executable files (*.exe)" )
    buf.append( "All files (*.*)" )
    return ";;".join( buf )

# ---------------------------------------------------------------------

def install_server_settings( is_startup ):
    """Install the server settings."""

    # install the server settings
    from vasl_templates.webapp import app as app
    app.config[ "VASSAL_DIR" ] = app_settings.value( "ServerSettings/vassal-dir" )
    app.config[ "VASL_MOD" ] = app_settings.value( "ServerSettings/vasl-mod" )
    app.config[ "VASL_EXTNS_DIR" ] = app_settings.value( "ServerSettings/vasl-extns-dir" )
    app.config[ "BOARDS_DIR" ] = app_settings.value( "ServerSettings/boards-dir" )
    app.config[ "JAVA_PATH" ] = app_settings.value( "ServerSettings/java-path" )
    app.config[ "WEBDRIVER_PATH" ] = app_settings.value( "ServerSettings/webdriver-path" )
    app.config[ "CHAPTER_H_NOTES_DIR" ] = app_settings.value( "ServerSettings/chapter-h-notes-dir" )
    app.config[ "CHAPTER_H_IMAGE_SCALING" ] = app_settings.value( "ServerSettings/chapter-h-image-scaling" )
    app.config[ "USER_FILES_DIR" ] = app_settings.value( "ServerSettings/user-files-dir" )

    # initialize
    if is_startup:
        # nb: we let the web page show startup messages
        msg_store = None
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
