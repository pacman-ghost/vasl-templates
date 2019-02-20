""" Web channel handler. """

import os
import base64

from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QImage

from vasl_templates.webapp.config.constants import APP_NAME
from vasl_templates.file_dialog import FileDialog

# ---------------------------------------------------------------------

class WebChannelHandler:
    """Handle web channel requests."""

    def __init__( self, parent  ):
        self.parent = parent
        self.scenario_file_dialog = FileDialog(
            self.parent,
            "scenario", ".json",
            "Scenario files (*.json);;All files (*)",
            None
        )
        self.updated_vsav_file_dialog = FileDialog(
            self.parent,
            "VASL scenario", ".vsav",
            "VASL scenario files (*.vsav);;All files (*)",
            "scenario.vsav"
        )

    def on_new_scenario( self ):
        """Called when the scenario is reset."""
        self.scenario_file_dialog.curr_fname = None

    def load_scenario( self ):
        """Called when the user wants to load a scenario."""
        data = self.scenario_file_dialog.load_file( False )
        if data is None:
            return None, None
        return self.scenario_file_dialog.curr_fname, data

    def save_scenario( self, fname, data ):
        """Called when the user wants to save a scenario."""
        prev_curr_fname = self.scenario_file_dialog.curr_fname
        if not self.scenario_file_dialog.curr_fname:
            # NOTE: We are tracking the current scenario filename ourself, so we only use the filename
            # passed to us by the web page if a new scenario is being saved for the first time.
            self.scenario_file_dialog.curr_fname = fname
        rc = self.scenario_file_dialog.save_file( data )
        if not rc:
            self.scenario_file_dialog.curr_fname = prev_curr_fname
            return None
        return self.scenario_file_dialog.curr_fname

    def on_scenario_details_change( self, val ):
        """Update the main window title to show the scenario details."""
        self.parent.setWindowTitle(
            "{} - {}".format( APP_NAME, val ) if val else APP_NAME
        )

    def on_snippet_image( self, img_data ): #pylint: disable=no-self-use
        """Called when a snippet image has been generated."""
        # NOTE: We could maybe add an HTML object to the clipboard as well, but having two formats on the clipboard
        # simultaneously might confuse some programs, causing problems for no real benefit :shrug:
        img = QImage.fromData( base64.b64decode( img_data ) )
        QApplication.clipboard().setImage( img )

    def load_vsav( self ):
        """Called when the user wants to load a VASL scenario to update."""
        data = self.updated_vsav_file_dialog.load_file( True )
        if data is None:
            return None, None
        fname = os.path.split( self.updated_vsav_file_dialog.curr_fname )[1]
        return fname, data

    def save_updated_vsav( self, fname, data ):
        """Called when a VASL scenario has been updated and is ready to be saved."""
        dname = os.path.split( self.updated_vsav_file_dialog.curr_fname )[0]
        self.updated_vsav_file_dialog.curr_fname = os.path.join( dname, fname )
        return self.updated_vsav_file_dialog.save_file( data )
