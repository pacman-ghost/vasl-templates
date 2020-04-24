""" Test serving files. """

import os
import re
import urllib.request

import pytest
import werkzeug.exceptions

from vasl_templates.webapp.files import FileServer
from vasl_templates.webapp.tests.utils import init_webapp, find_child, wait_for_clipboard

# ---------------------------------------------------------------------

def test_local_file_server( webapp ):
    """Test serving files from the local file system."""

    # initialize
    base_dir = os.path.normpath( os.path.join( os.path.split(__file__)[0], "fixtures/file-server" ) )
    file_server = FileServer( base_dir )

    # do the tests
    with webapp.test_request_context():

        assert _get_response_data( file_server.serve_file( "1.txt" ) ).strip() == b"file 1"
        with pytest.raises( werkzeug.exceptions.NotFound ):
            _get_response_data( file_server.serve_file( "/1.txt" ) )

        with pytest.raises( werkzeug.exceptions.NotFound ):
            _get_response_data( file_server.serve_file( "unknown.txt" ) )

        assert _get_response_data( file_server.serve_file( "subdir/2.txt" ) ).strip() == b"file 2"
        with pytest.raises( werkzeug.exceptions.NotFound ):
            _get_response_data( file_server.serve_file( "/subdir/2.txt" ) )

        # try to get a file outside the configured directory
        fname = "../new-default-scenario.json"
        assert os.path.isfile( os.path.join( base_dir, fname ) )
        with pytest.raises( werkzeug.exceptions.NotFound ):
            _get_response_data( file_server.serve_file( fname) )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_remote_file_server( webapp ):
    """Test serving files from a remote file system."""

    # initialize
    base_url = "{}/static/images".format( _get_base_url( webapp ) )
    file_server = FileServer( base_url )
    base_dir = os.path.join( os.path.split(__file__)[0], "../static/images" )

    def do_test( fname ):
        """Get the specified user file from the remote server and check the response."""
        buf = _get_response_data( file_server.serve_file( fname ) )
        with open( os.path.join( base_dir, fname ), "rb" ) as fp:
            assert buf == fp.read()

    # do the tests
    with webapp.test_request_context():
        do_test( "hint.gif" )
        do_test( "flags/german.png" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _get_base_url( webapp ):
    """Get the webapp base URL."""
    url = webapp.url_for( "get_user_file", path="unused" )
    mo = re.search( r"^http://.+?:\d+", url )
    return mo.group()

def _get_response_data( resp ):
    """Get the data from a Flask response."""
    resp.direct_passthrough = False
    return resp.get_data()

# ---------------------------------------------------------------------

def test_local_user_files( webapp, webdriver ):
    """Test serving user files from the local file system."""

    def do_test( enable_user_files ): #pylint: disable=missing-docstring

        # initialize
        init_webapp( webapp, webdriver,
            reset = lambda ct:
                ct.set_user_files_dir( dtype = "test" if enable_user_files else None )
        )

        # try getting a user file
        try:
            url = webapp.url_for( "get_user_file", path="hello.txt" )
            resp = urllib.request.urlopen( url )
            assert enable_user_files # nb: we should only get here if user files are enabled
            assert resp.code == 200
            assert resp.read().strip() == b"Yo, wassup!"
            assert resp.headers[ "Content-Type" ].startswith( "text/plain" )
        except urllib.error.HTTPError as ex:
            assert not enable_user_files # nb: we should only get here if user files are disabled
            assert ex.code == 404

        # try getting a non-existent file (nb: should always fail, whether user files are enabled/disabled)
        with pytest.raises( urllib.error.HTTPError ) as exc_info:
            url = webapp.url_for( "get_user_file", path="unknown" )
            resp = urllib.request.urlopen( url )
        assert exc_info.value.code == 404

        # try getting a file in a sub-directory
        try:
            url = webapp.url_for( "get_user_file", path="subdir/placeholder.png" )
            resp = urllib.request.urlopen( url )
            assert enable_user_files # nb: we should only get here if user files are enabled
            assert resp.code == 200
            assert resp.read().startswith( b"\x89PNG\r\n" )
            assert resp.headers[ "Content-Type" ] == "image/png"
        except urllib.error.HTTPError as ex:
            assert not enable_user_files # nb: we should only get here if user files are disabled
            assert ex.code == 404

        # try getting a file outside the configured directory (nb: should always fail)
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/vasl-pieces-legacy.txt" )
        assert os.path.isfile( fname )
        with pytest.raises( urllib.error.HTTPError ) as exc_info:
            url = webapp.url_for( "get_user_file", path="../vasl-pieces-legacy.txt" )
            resp = urllib.request.urlopen( url )
        assert exc_info.value.code == 404

        # try getting a file with special characters in its name
        try:
            url = webapp.url_for( "get_user_file", path="amp=& ; plus=+.txt" )
            resp = urllib.request.urlopen( url )
            assert enable_user_files # nb: we should only get here if user files are enabled
            assert resp.code == 200
            assert resp.read().strip() == b"special chars"
            assert resp.headers[ "Content-Type" ].startswith( "text/plain" )
        except urllib.error.HTTPError as ex:
            assert not enable_user_files # nb: we should only get here if user files are disabled
            assert ex.code == 404

    # do the tests with user files enabled/disabled
    do_test( True )
    do_test( False )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_remote_user_files( webapp, webdriver ):
    """Test serving user files from a remote server."""

    # initialize
    control_tests = init_webapp( webapp, webdriver )
    remote_app_config = control_tests.get_app_config()

    def do_test( enable_user_files ): #pylint: disable=missing-docstring

        # initialize
        base_url = "{}/static/images".format( _get_base_url( webapp ) )
        if remote_app_config.get( "IS_CONTAINER" ):
            # FUDGE! We test getting a file from a remote server by requesting a file from the webapp (since we know
            # it will be available). However, if it's running in a container, the port it needs to use to talk
            # to itself is not necessarily the same as the port an outside client (e.g. us) uses to talk with it,
            # so we need to adjust the user files base URL to reflect that.
            remote_base_url = "http://localhost:{}".format( remote_app_config["FLASK_PORT_NO"] )
            base_url = re.sub( r"http://.+?:\d+", remote_base_url, base_url )
        init_webapp( webapp, webdriver,
            reset = lambda ct:
                ct.set_user_files_dir( dtype = base_url if enable_user_files else None )
        )

        # try getting a user file
        try:
            url = webapp.url_for( "get_user_file", path="menu.png" )
            resp = urllib.request.urlopen( url )
            assert enable_user_files # nb: we should only get here if user files are enabled
            assert resp.code == 200
            assert resp.read().startswith( b"\x89PNG\r\n" )
            assert resp.headers[ "Content-Type" ] == "image/png"
        except urllib.error.HTTPError as ex:
            assert not enable_user_files # nb: we should only get here if user files are disabled
            assert ex.code == 404

    # do the tests with user files enabled/disabled
    do_test( True )
    do_test( False )

# ---------------------------------------------------------------------

def test_user_file_snippets( webapp, webdriver ):
    """Test user files in snippets."""

    def do_test( enable_user_files ): #pylint: disable=missing-docstring

        # initialize
        init_webapp( webapp, webdriver,
            reset = lambda ct: ct.set_user_files_dir( dtype = "test" if enable_user_files else None )
        )

        # set the victory conditions
        elem = find_child( "textarea[name='VICTORY_CONDITIONS']" )
        elem.send_keys( "my image: {{USER_FILES}}/subdir/placeholder.png" )
        btn = find_child( "button.generate[data-id='victory_conditions']" )
        btn.click()
        def get_user_file_url( clipboard ): #pylint: disable=missing-docstring
            # nb: the test template wraps {{VICTORY_CONDITIONS}} in square brackets :-/
            mo = re.search( r"http://.+?/([^]]+)", clipboard )
            return "/" + mo.group(1)
        wait_for_clipboard( 2, "/user/subdir/placeholder.png", transform=get_user_file_url )

    # do the tests with user files enabled/disabled
    # NOTE: The user file URL will be inserted into the snippet even if user files are disabled,
    # but the URL will 404 when somebody tries to resolve it.
    do_test( True )
    do_test( False )
