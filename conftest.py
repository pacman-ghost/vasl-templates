""" pytest support functions. """

import os
import threading
import logging
import tempfile
import urllib.request
from urllib.error import URLError
import pytest

from flask import url_for

from vasl_templates.webapp import app
app.testing = True
from vasl_templates.webapp.tests import utils

FLASK_WEBAPP_PORT = 5001

# ---------------------------------------------------------------------

def pytest_addoption( parser ):
    """Configure pytest options."""

    # NOTE: This file needs to be in the project root for this to work :-/

    # add test options
    # NOTE: Chrome seems to be ~15% faster than Firefox, headless ~5% faster than headful.
    parser.addoption(
        "--webdriver", action="store", dest="webdriver", default="chrome",
        help="Webdriver to use."
    )
    parser.addoption(
        "--headless", action="store_true", dest="headless", default=False,
        help="Run the tests headless."
    )
    parser.addoption(
        "--window-size", action="store", dest="window_size", default="1000x700",
        help="Browser window size."
    )

    # add test options
    parser.addoption(
        "--short-tests", action="store_true", dest="short_tests", default=False,
        help="Run a shorter version of the test suite."
    )
    # NOTE: Some tests require the VASL module file(s). We don't want to put these into source control,
    # so we provide this option to allow the caller to specify where they live.
    parser.addoption(
        "--vasl-mods", action="store", dest="vasl_mods", default=None,
        help="Directory containing the VASL .vmod file(s)."
    )
    # NOTE: It's not good to have the code run differently to how it will normally,
    # but using the clipboard to retrieve snippets causes more trouble than it's worth :-/
    # since any kind of clipboard activity while the tests are running could cause them to fail
    # (even when running in a VM, if it's configured to share the physical host's clipboard :wall:).
    parser.addoption(
        "--use-clipboard", action="store_true", dest="use_clipboard", default=False,
        help="Use the clipboard to get snippets."
    )

# ---------------------------------------------------------------------

@pytest.fixture( scope="session" )
def webapp():
    """Launch the webapp."""

    # initialize
    # WTF?! https://github.com/pallets/flask/issues/824
    def make_webapp_url( endpoint, **kwargs ):
        """Generate a webapp URL."""
        with app.test_request_context():
            # NOTE: When we perform actions at high speed, the notification balloons can build up
            # very quickly, causing problems by obscuring other elements and making them non-clickable :-/
            # We used to explicitly dismiss them, but it's simpler to just always disable them.
            kwargs["store_msgs"] = 1
            # stop the browser from checking for a dirty scenario when leaving the page
            kwargs["disable_close_window_check"] = 1
            # check if the tests are being run headless
            if pytest.config.option.headless: #pylint: disable=no-member
                # yup - there is no clipboard support :-/
                pytest.config.option.use_clipboard = False #pylint: disable=no-member
            # check if we should disable using the clipboard for snippets
            if not pytest.config.option.use_clipboard: #pylint: disable=no-member
                # NOTE: It's not a bad idea to bypass the clipboard, even when running in a browser,
                # to avoid problems if something else uses the clipboard while the tests are running.
                kwargs["store_clipboard"] = 1
            url = url_for( endpoint, _external=True, **kwargs )
            return url.replace( "localhost/", "localhost:{}/".format(FLASK_WEBAPP_PORT) )
    app.url_for = make_webapp_url

    # configure the webapp to use our test data
    # NOTE: Can't seem to change constants.DATA_DIR (probably some pytest funkiness :-/)
    app.config["DATA_DIR"] = os.path.join( os.path.split(__file__)[0], "vasl_templates/webapp/tests/fixtures/data" )

    # start the webapp server (in a background thread)
    logging.disable( logging.CRITICAL )
    thread = threading.Thread(
        target = lambda: app.run( host="0.0.0.0", port=FLASK_WEBAPP_PORT, use_reloader=False )
    )
    thread.start()

    # wait for the server to start up
    def is_ready():
        """Try to connect to the webapp server."""
        try:
            resp = urllib.request.urlopen( app.url_for("ping") ).read()
            assert resp == b"pong"
            return True
        except URLError:
            return False
        except Exception as ex: #pylint: disable=broad-except
            assert False, "Unexpected exception: {}".format(ex)
    utils.wait_for( 5, is_ready )

    # return the server to the caller
    yield app

    # shutdown the webapp server
    urllib.request.urlopen( app.url_for("shutdown") ).read()
    thread.join()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@pytest.fixture( scope="session" )
def test_client():
    """Return a test client that can be used to connect to the webapp."""
    logging.disable( logging.CRITICAL )
    return app.test_client()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@pytest.fixture( scope="session" )
def webdriver( request ):
    """Return a webdriver that can be used to control a browser.

    It would be nice to be able to drive the embedded browser in the wrapper
    Qt app with e.g. this:
        https://github.com/cisco-open-source/qtwebdriver
    but it only works with the old QtWebKit, which was removed in Qt 5.6 :-/
    """

    # initialize
    driver = request.config.getoption( "--webdriver" )
    from selenium import webdriver as wb
    if driver == "firefox":
        options = wb.FirefoxOptions()
        options.set_headless( headless = pytest.config.option.headless ) #pylint: disable=no-member
        driver = wb.Firefox(
            firefox_options = options,
            log_path = os.path.join( tempfile.gettempdir(), "geckodriver.log" )
        )
    elif driver == "chrome":
        options = wb.ChromeOptions()
        options.set_headless( headless = pytest.config.option.headless ) #pylint: disable=no-member
        driver = wb.Chrome( chrome_options=options )
    elif driver == "ie":
        # NOTE: IE11 requires a registry key to be set:
        #   https://github.com/SeleniumHQ/selenium/wiki/InternetExplorerDriver#required-configuration
        options = wb.IeOptions()
        if pytest.config.option.headless: #pylint: disable=no-member
            raise RuntimeError( "IE WebDriver cannot be run headless." )
        options.IntroduceInstabilityByIgnoringProtectedModeSettings = True
        options.EnsureCleanSession = True
        driver = wb.Ie( ie_options=options )
    else:
        raise RuntimeError( "Unknown webdriver: {}".format( driver ) )

    # set the browser size
    words = pytest.config.option.window_size.split( "x" ) #pylint: disable=no-member
    driver.set_window_size( int(words[0]), int(words[1]) )

    # return the webdriver to the caller
    try:
        yield driver
    finally:
        driver.quit()
