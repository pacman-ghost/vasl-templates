""" Manage information about the current user. """

import sys
import os
import shutil
import tempfile
import logging

import appdirs

_APP_NAME = "vasl-templates"
_APP_AUTHOR = "pacman-ghost"

_logger = logging.getLogger( "user_profile" )

# ---------------------------------------------------------------------

class UserProfile:
    """Manage information about the current user."""

    def __init__( self, app_config ):

        # initialize
        is_desktop_app = os.environ.get( "IS_DESKTOP_APP" ) is not None
        is_container = app_config.get( "IS_CONTAINER" ) is not None

        # configure the location of the user's config files
        if is_desktop_app:
            self.config_dname = "/tmp" if is_container \
              else self._check_dir( appdirs.user_config_dir( _APP_NAME, _APP_AUTHOR, roaming=True ) )
            self.desktop_settings_fname = os.path.join( self.config_dname,
                "settings.ini" if sys.platform == "win32" else "settings.conf"
            )

        # configure the location of the user's local data files
        self.local_data_dname = "/tmp" if is_container \
          else self._check_dir( appdirs.user_data_dir( _APP_NAME, _APP_AUTHOR, roaming=False ) )
        self.flask_lock_fname = os.path.join( self.local_data_dname, "flask.lock" )

        # configure the location of the log files
        self.logs_dname = "/tmp" if is_container \
          else self._check_dir( appdirs.user_log_dir( _APP_NAME, _APP_AUTHOR ) )
        self.webdriver_log_fname = app_config.get( "WEBDRIVER_LOG",
            os.path.join( self.logs_dname, "webdriver.log" )
        )

        # configure the location of the cached data files
        self.cache_dname = "/tmp" if is_container \
          else self._check_dir( appdirs.user_cache_dir( _APP_NAME, _APP_AUTHOR ) )
        self.downloaded_files = {
            "ASA": os.path.join( self.cache_dname, "asl-scenario-archive.json" ),
            "ROAR": os.path.join( self.cache_dname, "roar-scenario-index.json" ),
        }
        self.vo_notes_image_cache_dname = self._check_dir( os.path.join( self.cache_dname, "vo-notes-image-cache" ) )

        # log our settings
        _logger.info( "UserProfile:" )
        if is_desktop_app:
            _logger.info( "- config = %s", self.config_dname )
            _logger.debug( "  - settings = %s", self.desktop_settings_fname )
        _logger.info( "- local data = %s", self.local_data_dname )
        _logger.debug( "  - Flask lock file = %s", self.flask_lock_fname )
        _logger.info( "- logs = %s", self.logs_dname )
        _logger.debug( "  - webdriver = %s", self.webdriver_log_fname )
        _logger.info( "- cache = %s", self.cache_dname )
        for key, val in self.downloaded_files.items():
            _logger.debug( "  - Downloaded file (%s) = %s", key, val )
        _logger.debug( "  - V/O note image cache = %s", self.vo_notes_image_cache_dname )

        # fixup any legacy files
        if not is_container:
            self._fixup_legacy()

    def _fixup_legacy( self ):
        """Fixup any legacy files and directories.

        NOTE: Config and data files were moved to the standard locations in v1.10.beta3; this function
        looks for them in the legacy locations and moves them to their new location.
        """

        def move_file( caption, src_fname, dest_fname ):
            if not os.path.isfile( src_fname ):
                _logger.debug( "Legacy %s file not found: %s", caption, src_fname )
                return
            _logger.info( "Moving legacy %s file:\n- from: %s\n- to:   %s",
                caption, src_fname, dest_fname
            )
            try:
                shutil.move( src_fname, dest_fname )
            except Exception as ex: #pylint: disable=broad-except
                # NOTE: It would be nice to report this as a startup error, but this happens
                # so early in the startup process, nothing has been initialized yet :-/
                logging.error( "Can't move legacy %s file: %s\n- %s", caption, src_fname, ex )
                # NOTE: We try to keep going.

        def remove_dir( caption, dname ):
            if not os.path.isdir( dname ):
                _logger.debug( "Legacy %s directory not found: %s", caption, dname )
                return
            _logger.info( "Deleting legacy %s directory: %s", caption, dname )
            try:
                shutil.rmtree( dname )
            except Exception as ex: #pylint: disable=broad-except
                logging.error( "Can't delete legacy %s directory: %s\n- %s", caption, dname, ex )
                # NOTE: We try to keep going.

        # fixup the desktop settings file
        qdir_home_path = os.environ.get( "QDIR_HOME_PATH" )
        if qdir_home_path:
            fname = os.path.join( qdir_home_path,
                "vasl-templates.ini" if sys.platform == "win32" else ".vasl-templates.conf"
            )
            move_file( "desktop settings", fname, self.desktop_settings_fname )

        # fixup the ASA/ROAR downloaded files
        # NOTE: We don't *need* to do this (since the files will just be downloaded again), and they're
        # in the temp directory (so we don't *need* to remove them), but it'd be nice to have scenario search
        # working straight away after startup.
        move_file( "ASA scenarios",
            os.path.join( tempfile.gettempdir(), "vasl-templates.asl-scenario-archive.json" ),
            self.downloaded_files[ "ASA" ]
        )
        move_file( "ROAR scenarios",
            os.path.join( tempfile.gettempdir(), "vasl-templates.roar-scenario-index.json" ),
            self.downloaded_files[ "ROAR" ]
        )

        # NOTE: The Flask lock file and webdriver log file are temp files, so we don't move them.

        # NOTE: The V/O notes image cache can either be:
        # - disabled
        # - manually configured (via VO_NOTES_IMAGE_CACHE_DIR)
        # - default ($TEMP-DIR/vasl-templates/vo-notes-image-cache/)
        # In the first 2 cases, we don't need to do anything, in the last case, we delete our temp directory.
        # Note that while we could try to move it, it may well not be on the same file system (which makes it
        # a non-trivial operation), and there have been CSS changes in the v1.10 release cycle, which normally
        # won't cause an image to be re-generated, so it's not a bad idea to force this to happen.
        remove_dir( "app temp",
            os.path.join( tempfile.gettempdir(), "vasl-templates" )
        )

    @staticmethod
    def _check_dir( dname ):
        """Check that a directory exists."""
        try:
            if not os.path.isdir( dname ):
                os.makedirs( dname )
        except Exception as ex: #pylint: disable=broad-except
            logging.error( "Can't create UserProfile directory: %s\n- %s", dname, ex )
            raise
        if dname[-1] != os.sep:
            dname += os.sep
        return dname
