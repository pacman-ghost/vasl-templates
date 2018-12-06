""" Test serving counter images. """

import os
import io
import json
import re
import urllib.request

import pytest
import tabulate

from vasl_templates.webapp.file_server.vasl_mod import VaslMod
from vasl_templates.webapp.file_server.utils import get_vo_gpids
from vasl_templates.webapp.config.constants import DATA_DIR
from vasl_templates.webapp.tests.utils import init_webapp, select_tab, find_child, find_children
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario
from vasl_templates.webapp.tests.remote import ControlTests

# ---------------------------------------------------------------------

@pytest.mark.skipif(
    not pytest.config.option.vasl_mods, #pylint: disable=no-member
    reason = "--vasl-mods not specified"
)
@pytest.mark.skipif(
    pytest.config.option.short_tests, #pylint: disable=no-member
    reason = "--short-tests specified"
) #pylint: disable=too-many-statements
def test_counter_images( webapp ):
    """Test that counter images are served correctly."""

    # NOTE: This is ridiculously slow on Windows :-/

    # figure out which pieces we're interested in
    gpids = get_vo_gpids( DATA_DIR )

    def check_images( check_front, check_back ): #pylint: disable=unused-argument
        """Check getting the front and back images for each counter."""
        for gpid in gpids:
            for side in ("front","back"):
                url = webapp.url_for( "get_counter_image", gpid=gpid, side=side )
                try:
                    resp = urllib.request.urlopen( url )
                    resp_code = resp.code
                    resp_data = resp.read()
                except urllib.error.HTTPError as ex:
                    resp_code = ex.code
                    resp_data = None
                assert locals()["check_"+side]( resp_code, resp_data )

    # test counter images when no VASL module has been configured
    control_tests = ControlTests( webapp )
    control_tests.set_vasl_mod( vmod=None )
    fname = os.path.join( os.path.split(__file__)[0], "../static/images/missing-image.png" )
    missing_image_data = open( fname, "rb" ).read()
    check_images(
        check_front = lambda code,data: code == 200 and data == missing_image_data,
        check_back = lambda code,data: code == 200 and data == missing_image_data
    )

    # test each VASL module file in the specified directory
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/vasl-pieces.txt" )
    expected_vasl_pieces = open( fname, "r" ).read()
    vasl_mods = control_tests.get_vasl_mods()
    for vasl_mod in vasl_mods:

        # install the VASL module file
        control_tests.set_vasl_mod( vmod=vasl_mod )

        # NOTE: We assume we have access to the same VASL modules as the server, but the path on the webserver
        # might be different to what it is locally, so we translate it here.
        fname = os.path.split( vasl_mod )[1]
        vasl_mods_dir = pytest.config.option.vasl_mods #pylint: disable=no-member
        fname = os.path.join( vasl_mods_dir, fname )

        # check the pieces loaded
        vasl_mod = VaslMod( fname, DATA_DIR )
        buf = io.StringIO()
        _dump_pieces( vasl_mod, buf )
        assert buf.getvalue() == expected_vasl_pieces

        # check each counter
        check_images(
            check_front = lambda code,data: code == 200 and data,
            check_back = lambda code,data: (code == 200 and data) or (code == 404 and not data)
        )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _dump_pieces( vasl_mod, out ):
    """Dump the VaslMod pieces."""

    # dump the VASL pieces
    results = [ [ "GPID", "Name", "Front images", "Back images"] ]
    for gpid in sorted(vasl_mod.pieces.keys()):
        piece = vasl_mod.pieces[ gpid ]
        assert piece["gpid"] == gpid
        results.append( [ gpid, piece["name"], piece["front_images"], piece["back_images"] ] )
    print( tabulate.tabulate( results, headers="firstrow" ), file=out )

# ---------------------------------------------------------------------

@pytest.mark.skipif(
    not pytest.config.option.vasl_mods, #pylint: disable=no-member
    reason = "--vasl-mods not specified"
)
def test_gpid_remapping( webapp, webdriver ):
    """Test GPID remapping."""

    # initialize
    control_tests = init_webapp( webapp, webdriver )

    def check_gpid_image( gpid ):
        """Check if we can get the image for the specified GPID."""
        url = webapp.url_for( "get_counter_image", gpid=gpid, side="front" )
        try:
            resp = urllib.request.urlopen( url )
            return resp.code
        except urllib.error.HTTPError as ex:
            assert ex.code != 200
            return ex.code

    def check_entry( entry, url_stem, valid_image ):
        """Check a vehicle entry in the UI."""
        img = find_child( "img.vasl-image", entry )
        assert img.get_attribute( "src" ).endswith( url_stem )
        mo = re.search( r"^/counter/(\d+)/", url_stem )
        gpid = mo.group(1)
        if valid_image:
            assert check_gpid_image( gpid ) == 200
            assert img.get_attribute( "width" ) == "45"
        else:
            assert check_gpid_image( gpid ) == 404

    def do_test( vasl_mod, valid_images ):
        """Do the test."""
        # initialize (using the specified VASL vmod)
        init_webapp( webapp, webdriver, scenario_persistence=1,
            reset = lambda ct:
                ct.set_data_dir( ddtype="real" ) \
                  .set_vasl_mod( vmod=vasl_mod )
        )
        load_scenario( scenario_data )
        # check that the German vehicles loaded correctly
        select_tab( "ob1" )
        vehicles_sortable = find_child( "#ob_vehicles-sortable_1" )
        entries = find_children( "li", vehicles_sortable )
        assert len(entries) == 2
        check_entry( entries[0], "/counter/7140/front/0", valid_images )
        check_entry( entries[1], "/counter/7146/front", valid_images )

    # load the test scenario
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/gpid-remapping.json" )
    scenario_data = json.load( open( fname, "r" ) )

    # locate the VASL modules
    vasl_mods = control_tests.get_vasl_mods()
    def find_vasl_mod( version ):
        """Find the VASL module for the specified version."""
        matches = [ vmod for vmod in vasl_mods if "vasl-{}.vmod".format(version) in vmod ]
        assert len(matches) == 1
        return matches[0]

    # run the tests using VASL 6.4.2 and 6.4.3
    do_test( find_vasl_mod("6.4.2"), True )
    do_test( find_vasl_mod("6.4.3"), True )

    # disable GPID remapping and try again
    prev_gpid_mappings = control_tests.set_gpid_remappings( gpids={} )
    try:
        do_test( find_vasl_mod("6.4.2"), True )
        do_test( find_vasl_mod("6.4.3"), False )
    finally:
        # NOTE: This won't get done if Python exits unexpectedly in the try block,
        # which will leave the server in the wrong state if it's remote.
        control_tests.set_gpid_remappings( gpids=prev_gpid_mappings )
