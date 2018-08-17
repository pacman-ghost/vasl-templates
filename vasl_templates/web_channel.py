""" Web channel handler. """

import os

from PyQt5.QtWidgets import QFileDialog

from vasl_templates.webapp.config.constants import APP_NAME

# ---------------------------------------------------------------------

class WebChannelHandler:
    """Handle web channel requests."""

    _FILE_FILTERS = "Scenario files (*.json);;All files (*)"

    def __init__( self, window ):

        # initialize
        self._window = window

        # NOTE: While loading/saving scenarios works fine when handled by the embedded browser,
        # we can't get the full path of the file saved loaded (because of browser security).
        # This means that we can't e.g. default saving a scenario to the same file it was loaded from.
        # This is such a lousy UX, we handle load/save operations ourself, where we can manage this.
        self._curr_scenario_fname = None

    def on_new_scenario( self ):
        """Called when the scenario is reset."""
        self._curr_scenario_fname = None

    def load_scenario( self ):
        """Called when the user wants to load a scenario."""

        # ask the user which file to load
        fname, _  = QFileDialog.getOpenFileName(
            self._window, "Load scenario",
            os.path.split(self._curr_scenario_fname)[0] if self._curr_scenario_fname else None,
            WebChannelHandler._FILE_FILTERS
        )
        if not fname:
            return None

        # load the scenario
        try:
            with open( fname, "r", encoding="utf-8" ) as fp:
                data = fp.read()
        except Exception as ex: #pylint: disable=broad-except
            self._window.showErrorMsg( "Can't load the scenario:\n\n{}".format( ex ) )
            return None
        self._curr_scenario_fname = fname

        return data

    def save_scenario( self, data ):
        """Called when the user wants to save a scenario."""

        # ask the user where to save the scenario
        fname, _  = QFileDialog.getSaveFileName(
            self._window, "Save scenario",
            self._curr_scenario_fname,
            WebChannelHandler._FILE_FILTERS
        )
        if not fname:
            return False

        # check the file extension
        extn = os.path.splitext( fname )[1]
        if not extn:
            fname += ".json"
        elif fname.endswith( "." ):
            fname = fname[:-1]

        # save the file
        try:
            with open( fname, "w", encoding="utf-8" ) as fp:
                fp.write( data )
        except Exception as ex: #pylint: disable=broad-except
            self._window.showErrorMsg( "Can't save the scenario:\n\n{}".format( ex ) )
            return False
        self._curr_scenario_fname = fname

        return True

    def on_scenario_name_change( self, val ):
        """Update the main window title to show the scenario name."""
        self._window.setWindowTitle(
            "{} - {}".format( APP_NAME, val ) if val else APP_NAME
        )
