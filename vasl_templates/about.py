"""Implement the "about" dialog."""

import sys
import os
import time
import io
import re

from PyQt5 import uic, QtCore
from PyQt5.QtCore import QUrl
from PyQt5.QtGui import QDesktopServices, QIcon, QCursor
from PyQt5.QtWidgets import QDialog

from vasl_templates.webapp.config.constants import APP_NAME, APP_VERSION, APP_HOME_URL, IS_FROZEN
from vasl_templates.utils import get_build_info

# ---------------------------------------------------------------------

class AboutDialog( QDialog ):
    """Show the about box."""

    def __init__( self, parent ) :

        # initialize
        super().__init__( parent=parent )

        # initialize the UI
        base_dir = os.path.split( __file__ )[0]
        fname = os.path.join( base_dir, "ui/about.ui" )
        uic.loadUi( fname, self )
        self.setFixedSize( self.size() )
        self.close_button.clicked.connect( self.on_close )

        # initialize the UI
        if IS_FROZEN:
            dname = os.path.join( sys._MEIPASS, "vasl_templates/webapp" ) #pylint: disable=no-member,protected-access
        else:
            dname = os.path.join( os.path.split(__file__)[0], "webapp" )
        fname = os.path.join( dname, "static/images/app.ico" )
        self.app_icon.setPixmap( QIcon( fname ).pixmap(64,64) )
        self.app_icon.mouseReleaseEvent = self.on_app_icon_clicked
        self.app_icon.setCursor( QCursor( QtCore.Qt.PointingHandCursor ) )

        # load the dialog
        self.app_name.setText( "{} ({})".format( APP_NAME, APP_VERSION ) )
        self.license.setText( "Licensed under the GNU Affero General Public License (v3)." )
        build_info = get_build_info()
        if build_info:
            buf = io.StringIO()
            buf.write( "Built {}".format(
                time.strftime( "%d %B %Y %H:%M", time.localtime( build_info["timestamp"] ) )
            ) )
            if "git_info" in build_info:
                buf.write( " <small><em>({})</em></small>".format( build_info["git_info"] ) )
            buf.write( "." )
            self.build_info.setText( buf.getvalue() )
        else:
            self.build_info.setText( "" )
        mo = re.search( r"^https?://(.+)", APP_HOME_URL )
        self.home_url.setText( "Visit us at <a href='{}'>{}</a>.".format(
            APP_HOME_URL, mo.group(1) if mo else APP_HOME_URL
        ) )

    def on_app_icon_clicked( self, event ): #pylint: disable=no-self-use,unused-argument
        """Click handler."""
        QDesktopServices.openUrl( QUrl( APP_HOME_URL ) )

    def on_close( self ):
        """Close the dialog."""
        self.close()
