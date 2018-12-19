""" Test serving files. """

import os

from vasl_templates.webapp.files import FileServer

# ---------------------------------------------------------------------

def test_file_server():
    """Test serving files."""

    # initialize
    base_dir = os.path.normpath( os.path.join( os.path.split(__file__)[0], "fixtures/file-server" ) )
    file_server = FileServer( base_dir )

    # do the tests
    assert file_server.get_file( "1.txt" ) == os.path.join( base_dir, "1.txt" )
    assert file_server.get_file( "/1.txt" ) is None
    assert file_server.get_file( "unknown.txt" ) is None
    assert file_server.get_file( "subdir/2.txt" ) == os.path.normpath( os.path.join( base_dir, "subdir/2.txt" ) )
    assert file_server.get_file( "/subdir/2.txt" ) is None

    # try access a file outside the configured directory
    fname = "../new-default-scenario.json"
    assert os.path.isfile( os.path.join( base_dir, fname ) )
    assert file_server.get_file( fname ) is None
