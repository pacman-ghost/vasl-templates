""" Wrapper for a Selenium webdriver. """

import os
import tempfile

from selenium import webdriver
from PIL import Image, ImageChops

from vasl_templates.webapp import app
from vasl_templates.webapp.utils import TempFile, SimpleError

# ---------------------------------------------------------------------

class WebDriver:
    """Wrapper for a Selenium webdriver."""

    def __init__( self ):
        self.driver = None

    def start( self ):
        """Start the webdriver."""

        # initialize
        assert not self.driver

        # locate the webdriver executable
        webdriver_path = app.config.get( "WEBDRIVER_PATH" )
        if not webdriver_path:
            raise SimpleError( "No webdriver has been configured." )

        # NOTE: If we are being run on Windows without a console (e.g. the frozen PyQt desktop app),
        # Selenium will launch the webdriver in a visible DOS box :-( There's no way to turn this off,
        # but it can be disabled by modifying the Selenium source code. Find the subprocess.Popen() call
        # in $/site-packages/selenium/webdriver/common/service.py and add the following parameter:
        #   creationflags = 0x8000000  # win32process.CREATE_NO_WINDOW
        # It's pretty icky to have to do this, but since we're in a virtualenv, it's not too bad...

        # create the webdriver
        kwargs = { "executable_path": webdriver_path }
        if "chromedriver" in webdriver_path:
            options = webdriver.ChromeOptions()
            options.set_headless( headless=True )
            # OMG! The chromedriver looks for Chrome/Chromium in a hard-coded, fixed location (the default
            # installation directory). We offer a way here to override this.
            chrome_path = app.config.get( "CHROME_PATH" )
            if chrome_path:
                options.binary_location = chrome_path
            kwargs["chrome_options"] = options
            self.driver = webdriver.Chrome( **kwargs )
        elif "geckodriver" in webdriver_path:
            options = webdriver.FirefoxOptions()
            options.set_headless( headless=True )
            kwargs["firefox_options"] = options
            kwargs["log_path"] = app.config.get( "GECKODRIVER_LOG",
                os.path.join( tempfile.gettempdir(), "geckodriver.log" )
            )
            self.driver = webdriver.Firefox( **kwargs )
        else:
            raise SimpleError( "Can't identify webdriver: {}".format( webdriver_path ) )

        return self

    def stop( self ):
        """Stop the webdriver."""
        assert self.driver
        self.driver.quit()
        self.driver = None

    def get_screenshot( self, html, window_size, large_window_size=None ):
        """Get a preview screenshot of the specified HTML."""

        def do_get_screenshot( fname ): #pylint: disable=missing-docstring
            self.driver.save_screenshot( fname )
            img = Image.open( fname )
            # trim the screenshot (nb: we assume a white background)
            bgd = Image.new( img.mode, img.size, (255,255,255,255) )
            diff = ImageChops.difference( img, bgd )
            bbox = diff.getbbox()
            return img.crop( bbox )

        with TempFile(extn=".html",mode="w") as html_tempfile, TempFile(extn=".png") as screenshot_tempfile:

            # NOTE: We could do some funky Javascript stuff to load the browser directly from the string,
            # but using a temp file is straight-forward and pretty much guaranteed to work :-/
            html_tempfile.write( html )
            html_tempfile.close()
            self.driver.get( "file://{}".format( html_tempfile.name ) )

            # take a screenshot of the HTML
            screenshot_tempfile.close()
            self.driver.set_window_size( window_size[0], window_size[1] )
            img = do_get_screenshot( screenshot_tempfile.name )
            if img.width > window_size[0]*9/10 or img.height > window_size[1]*9/10:
                # the image may have been cropped - try again with a larger window size
                if large_window_size:
                    self.driver.set_window_size( large_window_size[0], large_window_size[1] )
                    img = do_get_screenshot( screenshot_tempfile.name )

            return img

    def get_snippet_screenshot( self, snippet_id, snippet ):
        """Get a screenshot for an HTML snippet."""

        # NOTE: Screenshots take significantly longer for larger window sizes. Since most of our snippets
        # will be small, we first try with a smaller window, and switch to a larger one if necessary.
        # NOTE: While it's tempting to set the larger window really large here, if the label ends up
        # filling/overflowing the available space (e.g. because its width/height has been set to 100%),
        # then the auto-created label will push any subsequent labels far down the map, possibly to
        # somewhere unreachable. So, we set it somewhat more conservatively, so that if this happens,
        # the user still has a chance to recover from it. Note that this doesn't mean that they can't
        # have really large labels, it just affects the positioning of auto-created labels.

        window_size, window_size2 = (500,500), (1500,1500)
        if snippet_id and snippet_id.startswith(
            ("ob_vehicles_ma_notes_","ob_vehicle_note_","ob_ordnance_ma_notes_","ob_ordnance_note_")
        ):
            # nb: these tend to be large, don't bother with a smaller window
            window_size, window_size2 = window_size2, None
        return self.get_screenshot( snippet, window_size, window_size2 )

    def __enter__( self ):
        self.start()
        return self

    def __exit__( self, *args ):
        self.stop()
