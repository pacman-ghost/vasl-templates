""" Miscellaneous utilities. """

import os
import tempfile
import pathlib

from selenium import webdriver
from PIL import Image, ImageChops

from vasl_templates.webapp import app

# ---------------------------------------------------------------------

class TempFile:
    """Manage a temp file that can be closed while it's still being used."""

    def __init__( self, mode="wb", extn=None ):
        self.mode = mode
        self.extn = extn
        self.temp_file = None
        self.name = None

    def __enter__( self ):
        """Allocate a temp file."""
        self.temp_file = tempfile.NamedTemporaryFile( mode=self.mode, suffix=self.extn, delete=False )
        self.name = self.temp_file.name
        return self

    def __exit__( self, exc_type, exc_val, exc_tb ):
        """Clean up the temp file."""
        self.close()
        os.unlink( self.temp_file.name )

    def write( self, data ):
        """Write data to the temp file."""
        self.temp_file.write( data )

    def close( self ):
        """Close the temp file."""
        self.temp_file.close()

# ---------------------------------------------------------------------

class HtmlScreenshots:
    """Generate preview screenshots of HTML."""

    def __init__( self ):
        self.webdriver = None

    def __enter__( self ):
        """Initialize the HTML screenshot engine."""
        webdriver_path = app.config.get( "WEBDRIVER_PATH" )
        if not webdriver_path:
            raise SimpleError( "No webdriver has been configured." )
        # NOTE: If we are being run on Windows without a console (e.g. the frozen PyQt desktop app),
        # Selenium will launch the webdriver in a visible DOS box :-( There's no way to turn this off,
        # but it can be disabled by modifying the Selenium source code. Find the subprocess.Popen() call
        # in $/site-packages/selenium/webdriver/common/service.py and add the following parameter:
        #   creationflags = 0x8000000  # win32process.CREATE_NO_WINDOW
        # It's pretty icky to have to do this, but since we're in a virtualenv, it's not too bad...
        kwargs = { "executable_path": webdriver_path }
        if "chromedriver" in webdriver_path:
            options = webdriver.ChromeOptions()
            options.set_headless( headless=True )
            kwargs["chrome_options"] = options
            self.webdriver = webdriver.Chrome( **kwargs )
        elif "geckodriver" in webdriver_path:
            options = webdriver.FirefoxOptions()
            options.set_headless( headless=True )
            kwargs["firefox_options"] = options
            kwargs["log_path"] = app.config.get( "GECKODRIVER_LOG",
                os.path.join( tempfile.gettempdir(), "geckodriver.log" )
            )
            self.webdriver = webdriver.Firefox( **kwargs )
        else:
            raise SimpleError( "Can't identify webdriver: {}".format( webdriver_path ) )
        return self

    def __exit__( self, exc_type, exc_val, exc_tb ):
        """Clean up."""
        if self.webdriver:
            self.webdriver.quit()

    def get_screenshot( self, html, window_size ):
        """Get a preview screenshot of the specified HTML."""

        self.webdriver.set_window_size( window_size[0], window_size[1] )
        with TempFile( extn=".html", mode="w" ) as html_tempfile:

            # take a screenshot of the HTML
            # NOTE: We could do some funky Javascript stuff to load the browser directly from the string,
            # but using a temp file is straight-forward and pretty much guaranteed to work :-/
            html_tempfile.write( html )
            html_tempfile.close()
            self.webdriver.get( "file://{}".format( html_tempfile.name ) )
            with TempFile( extn=".png" ) as screenshot_tempfile:
                screenshot_tempfile.close()
                self.webdriver.save_screenshot( screenshot_tempfile.name )
                img = Image.open( screenshot_tempfile.name )

                # trim the screenshot (nb: we assume a white background)
                bgd = Image.new( img.mode, img.size, (255,255,255,255) )
                diff = ImageChops.difference( img, bgd )
                bbox = diff.getbbox()
                return img.crop( bbox )

# ---------------------------------------------------------------------

def change_extn( fname, extn ):
    """Change a filename's extension."""
    return pathlib.Path( fname ).with_suffix( extn )

# ---------------------------------------------------------------------

class SimpleError( Exception ):
    """Represents a simple error that doesn't require a stack trace (e.g. bad configuration)."""
    pass
