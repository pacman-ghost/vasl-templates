"""Implement the "about" dialog."""

import os
import json
import time

from PyQt5 import uic
from PyQt5.QtWidgets import QDialog

from vasl_templates.webapp.config.constants import APP_NAME, APP_VERSION, BASE_DIR

# ---------------------------------------------------------------------

class AboutDialog( QDialog ):
    """Show the about box."""

    def __init__( self, parent ) :

        # initialize
        super().__init__( parent=parent )

        # initialize the UI
        base_dir = os.path.split( __file__ )[0]
        dname = os.path.join( base_dir, "ui/about.ui" )
        uic.loadUi( dname, self )
        self.setFixedSize( self.size() )
        self.close_button.clicked.connect( self.on_close )

        # get the build info
        dname = os.path.join( BASE_DIR, "config" )
        fname = os.path.join( dname, "build-info.json" )
        if os.path.isfile( fname ):
            build_info = json.load( open( fname, "r" ) )
        else:
            build_info = None

        # load the dialog
        self.app_name.setText( "{} ({})".format( APP_NAME, APP_VERSION ) )
        self.license.setText( "Licensed under the GNU Affero General Public License (v3)." )
        if build_info:
            timestamp = build_info[ "timestamp" ]
            self.build_info.setText( "Built {}.".format(
                time.strftime( "%d %B %Y %H:%S", time.localtime( timestamp ) ) # nb: "-d" doesn't work on Windows :-/
            ) )
        else:
            self.build_info.setText( "" )
        self.home_url.setText(
            "Get the source code and releases from <a href='http://github.com/pacman-ghost/vasl-templates'>Github</a>."
        )

    def on_close( self ):
        """Close the dialog."""
        self.close()