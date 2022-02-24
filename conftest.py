""" pytest support functions. """

import threading
import json
import re
import logging
import urllib.request
from urllib.error import URLError
import pytest

from flask import url_for

from vasl_templates.webapp import app
from vasl_templates.webapp.tests import utils
from vasl_templates.webapp.tests.control_tests import ControlTests

FLASK_WEBAPP_PORT = 5011

_pytest_options = None

# ---------------------------------------------------------------------

def pytest_addoption( parser ):
    """Configure pytest options."""

    # NOTE: This file needs to be in the project root for this to work :-/

    # add test options
    parser.addoption(
        "--webapp", action="store", dest="webapp_url", default=None,
        help="Webapp server to test against."
    )
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

    # NOTE: It's not good to have the code run differently to how it will normally,
    # but using the clipboard to retrieve snippets causes more trouble than it's worth :-/
    # since any kind of clipboard activity while the tests are running could cause them to fail
    # (even when running in a VM, if it's configured to share the physical host's clipboard :wall:).
    parser.addoption(
        "--use-clipboard", action="store_true", dest="use_clipboard", default=False,
        help="Use the clipboard to get snippets."
    )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def pytest_configure( config ):
    """Called after command-line options have been parsed."""
    global _pytest_options
    _pytest_options = config.option
    import vasl_templates.webapp.tests
    vasl_templates.webapp.tests.pytest_options = config.option

# ---------------------------------------------------------------------

_webapp = None

@pytest.fixture( scope="function" )
def webapp():
    """Launch the webapp."""

    # get the global webapp fixture
    global _webapp
    if _webapp is None:
        _webapp = _make_webapp()

    # reset the remote webapp server
    _webapp.control_tests.start_tests()

    # return the webapp to the caller
    yield _webapp

    # reset the remote webapp server
    _webapp.control_tests.end_tests()

def _make_webapp():
    """Create the global webapp fixture."""

    # initialize
    webapp_url = _pytest_options.webapp_url
    if webapp_url and not webapp_url.startswith( "http://" ):
        webapp_url = "http://" + webapp_url
    app.base_url = webapp_url if webapp_url else "http://localhost:{}".format( FLASK_WEBAPP_PORT )
    logging.disable( logging.CRITICAL )

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
            if _pytest_options.headless:
                # yup - there is no clipboard support :-/
                _pytest_options.use_clipboard = False
            # check if we should disable using the clipboard for snippets
            if not _pytest_options.use_clipboard:
                # NOTE: It's not a bad idea to bypass the clipboard, even when running in a browser,
                # to avoid problems if something else uses the clipboard while the tests are running.
                kwargs["store_clipboard"] = 1
            url = url_for( endpoint, _external=True, **kwargs )
            url = url.replace( "http://localhost", app.base_url )
            return url
    app.url_for = make_webapp_url

    # check if we need to start a local webapp server
    if not webapp_url:
        # yup - make it so
        # NOTE: We run the server thread as a daemon so that it won't prevent the tests from finishing
        # when they're done. We used to call $/shutdown after yielding the webapp fixture, but when
        # we changed it from being per-session to per-function, we can no longer do that.
        # This means that the webapp doesn't get a chance to shutdown properly (in particular,
        # clean up the gRPC service), but since we send an EndTests message at the of each test,
        # the remote server gets a chance to clean up then. It's not perfect (e.g. if the tests fail
        # or otherwise finish early before they get a chance to send the EndTests message), but
        # we can live with it.
        thread = threading.Thread(
            target = lambda: app.run( host="0.0.0.0", port=FLASK_WEBAPP_PORT, use_reloader=False ),
            daemon = True
        )
        thread.start()
        # wait for the server to start up
        def is_ready():
            """Try to connect to the webapp server."""
            try:
                url = app.url_for( "ping" )
                with urllib.request.urlopen( url ) as resp:
                    assert resp.read().startswith( b"pong: " )
                return True
            except URLError:
                return False
            except Exception as ex: #pylint: disable=broad-except
                assert False, "Unexpected exception: {}".format(ex)
        utils.wait_for( 5, is_ready )

    # set up control of the remote webapp server
    try:
        url = app.url_for( "get_control_tests" )
        with urllib.request.urlopen( url ) as resp:
            resp_data = json.load( resp )
    except urllib.error.HTTPError as ex:
        if ex.code == 404:
            raise RuntimeError( "Can't get the test control port - has remote test control been enabled?" ) from ex
        raise
    port_no = resp_data.get( "port" )
    if not port_no:
        raise RuntimeError( "The webapp server is not running the test control service." )
    mo = re.search( r"^http://(.+):\d+$", app.base_url )
    addr = "{}:{}".format( mo.group(1), port_no )
    app.control_tests = ControlTests( addr )

    return app

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
        options.headless = _pytest_options.headless
        driver = wb.Firefox( options=options )
    elif driver == "chrome":
        options = wb.ChromeOptions()
        options.headless = _pytest_options.headless
        options.add_argument( "--disable-gpu" )
        driver = wb.Chrome( options=options )
    else:
        raise RuntimeError( "Unknown webdriver: {}".format( driver ) )

    # set the browser size
    words = _pytest_options.window_size.split( "x" )
    driver.set_window_size( int(words[0]), int(words[1]) )

    # return the webdriver to the caller
    try:
        yield driver
    finally:
        driver.quit()
