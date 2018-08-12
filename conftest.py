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

    # add an option to control which webdriver to use
    parser.addoption(
        "--webdriver", action="store", dest="webdriver", default="firefox",
        help="Webdriver to use."
    )

    # add an option to control checking of vehicle/ordnance reports
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
        driver = wb.Firefox(
            log_path = os.path.join( tempfile.gettempdir(), "geckodriver.log" )
        )
    elif driver == "chrome":
        driver = wb.Chrome()
    else:
        assert False, "Unknown webdriver: {}".format( driver )

    # return the webdriver to the caller
    utils._webdriver = driver #pylint: disable=protected-access
    yield driver

    # clean up
    driver.close()