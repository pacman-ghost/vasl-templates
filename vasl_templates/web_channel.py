""" Web channel handler. """

import os

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
            "scenario.json"
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
        return self.scenario_file_dialog.load_file( False )

    def save_scenario( self, data ):
        """Called when the user wants to save a scenario."""
        return self.scenario_file_dialog.save_file( data )

    def on_scenario_name_change( self, val ):
        """Update the main window title to show the scenario name."""
        self.parent.setWindowTitle(
            "{} - {}".format( APP_NAME, val ) if val else APP_NAME
        )

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
