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
    parser.addoption(
        "--webdriver", action="store", dest="webdriver", default="firefox",
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
        "--no-clipboard", action="store_true", dest="no_clipboard", default=False,
        help="Don't use the clipboard to get snippets."
    )
    parser.addoption(
        "--vo-reports", action="store_true", dest="check_vo_reports", default=False,
        help="Check the vehicle/ordnance reports."
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
            if pytest.config.option.headless: #pylint: disable=no-member
                # headless browsers have no clipboard support :-/
                pytest.config.option.no_clipboard = True #pylint: disable=no-member
            if pytest.config.option.no_clipboard: #pylint: disable=no-member
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
    else:
        assert False, "Unknown webdriver: {}".format( driver )

    # set the browser size
    words = pytest.config.option.window_size.split( "x" ) #pylint: disable=no-member
    driver.set_window_size( int(words[0]), int(words[1]) )

    # return the webdriver to the caller
    utils._webdriver = driver #pylint: disable=protected-access
    yield driver

    # clean up
    driver.close()
