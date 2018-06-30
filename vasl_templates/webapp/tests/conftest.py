""" pytest support functions. """

import os
import threading
import logging
import tempfile
import urllib.request
import pytest

from flask import url_for

from vasl_templates.webapp import app
app.testing = True

FLASK_WEBAPP_PORT = 5001

# ---------------------------------------------------------------------

@pytest.fixture
def webapp():
    """Launch the webapp."""

    # initialize
    # WTF?! https://github.com/pallets/flask/issues/824
    def make_webapp_url( endpoint ):
        """Generate a webapp URL."""
        with app.test_request_context():
            url = url_for( endpoint, _external=True )
            return url.replace( "localhost/", "localhost:{}/".format(FLASK_WEBAPP_PORT) )
    app.url_for = make_webapp_url

    # start the webapp server (in a background thread)
    logging.disable( logging.CRITICAL )
    thread = threading.Thread(
        target = lambda: app.run( host="0.0.0.0", port=FLASK_WEBAPP_PORT, use_reloader=False )
    )
    thread.start()
    yield app

    # shutdown the webapp server
    urllib.request.urlopen( app.url_for("shutdown") ).read()
    thread.join()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@pytest.fixture
def test_client():
    """Return a test client that can be used to connect to the webapp."""
    logging.disable( logging.CRITICAL )
    return app.test_client()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@pytest.fixture
def webdriver():
    """Return a webdriver that can be used to control a browser.

    It would be nice to be able to drive the embedded browser in the wrapper
    Qt app with e.g. this:
        https://github.com/cisco-open-source/qtwebdriver
    but it only works with the old QtWebKit, which was removed in Qt 5.6 :-/
    """

    # initialize
    from selenium import webdriver as wb
    driver = wb.Firefox(
        log_path = os.path.join( tempfile.gettempdir(), "geckodriver.log" )
    )

    # return the webdriver to the caller
    yield driver

    # clean up
    driver.close()
