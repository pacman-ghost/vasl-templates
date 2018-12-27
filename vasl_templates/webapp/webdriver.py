""" Wrapper for a Selenium webdriver. """

import os
import threading
import tempfile
import atexit
import logging

from selenium import webdriver
from PIL import Image, ImageChops

from vasl_templates.webapp import app, cleanup_handlers
from vasl_templates.webapp.utils import TempFile, SimpleError

_logger = logging.getLogger( "webdriver" )

# ---------------------------------------------------------------------

class WebDriver:
    """Wrapper for a Selenium webdriver."""

    # NOTE: The thread-safety lock controls access to the _shared_instance variable,
    # not the WebDriver it points to (it has its own lock).
    _shared_instance_lock = threading.RLock()
    _shared_instance = None

    def __init__( self ):
        self.driver = None
        self.lock = threading.RLock() # nb: the shared instance must be locked for use
        self.start_count = 0
        _logger.debug( "Created WebDriver: %x", id(self) )

    def __del__( self ):
        try:
            _logger.debug( "Destroying WebDriver: %x", id(self) )
        except NameError:
            pass # nb: workaround a weird crash during shutdown (name 'open' is not defined)

    def start( self ):
        """Start the webdriver."""
        self.lock.acquire()
        self._do_start()

    def _do_start( self ):
        """Start the webdriver."""

        # initialize
        self.start_count += 1
        _logger.info( "Starting WebDriver (%x): count=%d", id(self), self.start_count )
        if self.start_count > 1:
            assert self.driver
            return
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
        _logger.debug( "- Launching webdriver process: %s", webdriver_path )
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
        _logger.debug( "- Started OK." )

    def stop( self ):
        """Stop the webdriver."""
        self._do_stop()
        self.lock.release()

    def _do_stop( self ):
        """Stop the webdriver."""
        assert self.driver
        self.start_count -= 1
        _logger.info( "Stopping WebDriver (%x): count=%d", id(self), self.start_count )
        if self.start_count == 0:
            _logger.debug( "- Stopping webdriver process." )
            self.driver.quit()
            _logger.debug( "- Stopped OK." )
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

    @staticmethod
    def get_instance():
        """Return the shared WebDriver instance.

        A Selenium webdriver has a hefty startup time, so we create one on first use, and then re-use it.
        There are 2 main issues with this approach:
        - thread-safety: Flask handles requests in multiple threads, so we need to serialize access.
        - clean-up: it's difficult to know when to clean up the shared WebDriver object. The WebDriver object
            wraps a chrome/geckodriver process, so we can't just let it leak, since these abandoned processes
            will just build up. We install atexit and SIGINT handlers, but webdriver processes will still leak
            if we abend.

        There is a script to stress-test this in the tools directory.
        """

        # NOTE: We provide a debug switch to disable the shared instance, in case it causes problems
        # (although things will, of course, run insanely slowly :-/).
        if app.config.get( "DISABLE_SHARED_WEBDRIVER" ):
            return WebDriver()

        with WebDriver._shared_instance_lock:

            # check if we've already created the shared WebDriver
            if WebDriver._shared_instance:
                # yup - just return it (nb: the caller is responsible for locking it)
                _logger.info( "Returning shared WebDriver: %x", id(WebDriver._shared_instance) )

                return WebDriver._shared_instance

            # nope - create a new WebDriver instance
            # NOTE: We start it here to keep it alive even after the caller has finished with it,
            # and take steps to make sure it gets stopped and cleaned up when the program exits.
            wdriver = WebDriver()
            _logger.info( "Created shared WebDriver: %x", id(wdriver) )
            wdriver._do_start() #pylint: disable=protected-access
            WebDriver._shared_instance = wdriver

            # make sure the shared WebDriver gets cleaned up
            def cleanup(): #pylint: disable=missing-docstring
                _logger.info( "Cleaning up shared WebDriver: %x", id(wdriver) )
                wdriver._do_stop() #pylint: disable=protected-access
            atexit.register( cleanup )
            cleanup_handlers.append( cleanup )

            return wdriver

    def __enter__( self ):
        self.start()
        return self

    def __exit__( self, *args ):
        self.stop()
