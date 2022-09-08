""" Manage loading and saving files. """

import os

from PyQt5.QtWidgets import QFileDialog

# ---------------------------------------------------------------------

# NOTE: While loading/saving files works fine when handled by the embedded browser,
# we can't get the full path of the file loaded (because of browser security).
# This means that we can't do things like default to saving a scenario to the same file
# it was loaded from, or retrying a failed save. This is such a lousy UX,
# we handle load/save operations ourself, where we can manage things like this.

class FileDialog:
    """Manage loading and saving files."""

    def __init__( self, parent, object_name, default_extn, filters, default_fname ):
        self.parent = parent
        self.object_name = object_name
        self.default_extn = default_extn
        self.filters = filters
        self.curr_fname = default_fname
        # NOTE: We can't just use the directory of self.curr_fname, since this gets reset
        # when the user chooses "new scenario", but we want to remember the current directory.
        self._curr_dir = os.path.dirname( default_fname ) if default_fname else None

    def load_file( self, binary ):
        """Load a file."""

        # ask the user which file to load
        fname, _  = QFileDialog.getOpenFileName(
            self.parent, "Load {}".format( self.object_name ),
            self._get_start_path(),
            self.filters
        )
        if not fname:
            return None

        # load the file
        try:
            with open( fname, "rb" ) as fp:
                data = fp.read()
        except Exception as ex: #pylint: disable=broad-except
            self.parent.showErrorMsg( "Can't load the {}:\n\n{}".format( self.object_name, ex ) )
            return None
        if not binary:
            data = data.decode( "utf-8" )
        self.curr_fname = fname
        self._curr_dir = os.path.dirname( fname )

        return data

    def save_file( self, data ):
        """Save data to a file."""

        # initialize
        if isinstance( data, str ):
            data = data.encode( "utf-8" )

        while True: # nb: keep trying until the save succeeds or the user cancels the operation

            # ask the user where to save the file
            fname, _  = QFileDialog.getSaveFileName(
                self.parent, "Save {}".format( self.object_name ),
                self._get_start_path(),
                self.filters
            )
            if not fname:
                return False

            # check the file extension
            extn = os.path.splitext( fname )[1]
            if not extn:
                fname += self.default_extn
            elif fname.endswith( "." ):
                fname = fname[:-1]

            # save the file
            try:
                with open( fname, "wb", ) as fp:
                    fp.write( data )
            except Exception as ex: #pylint: disable=broad-except
                self.parent.showErrorMsg( "Can't save the {}:\n\n{}".format( self.object_name, ex ) )
                continue
            self.curr_fname = fname
            self._curr_dir = os.path.dirname( fname )
            return True

    def _get_start_path( self ):
        """Get the start filename or directory path for saving/loading files."""
        if self.curr_fname and os.path.isabs( self.curr_fname ):
            return self.curr_fname
        if self._curr_dir and self.curr_fname:
            return os.path.join( self._curr_dir, self.curr_fname )
        return self.curr_fname
