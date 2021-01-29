""" Test serving counter images. """

import os
import json
import re
import shutil
import urllib.request

import pytest

from vasl_templates.webapp.vassal import SUPPORTED_VASSAL_VERSIONS
from vasl_templates.webapp.vasl_mod import get_vo_gpids, SUPPORTED_VASL_MOD_VERSIONS
from vasl_templates.webapp.vo import _kfw_listings #pylint: disable=protected-access
from vasl_templates.webapp.utils import compare_version_strings
from vasl_templates.webapp.tests import pytest_options
from vasl_templates.webapp.tests.utils import init_webapp, select_tab, find_child, find_children
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario

_EXPECTED_MISSING_GPIDS_EXCEPTIONS = [ "6.5.0", "6.5.1", "6.6.0", "6.6.1" ]

# ---------------------------------------------------------------------

@pytest.mark.skipif( pytest_options.short_tests, reason="--short-tests specified" )
def test_counter_images( webapp, webdriver ): #pylint: disable=too-many-locals
    """Test that counter images are served correctly."""

    # NOTE: This is ridiculously slow on Windows :-/

    def check_images( gpids, check_front, check_back ): #pylint: disable=unused-argument
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
                assert locals()["check_"+side]( gpid, resp_code, resp_data )

    # test counter images when no VASL module has been configured
    webapp.control_tests.set_vasl_version( None, None )
    init_webapp( webapp, webdriver )
    # NOTE: It doesn't really matter which set of GPID's we use, since we're expecting
    # a missing image for everything anyway. We just use the most recent supported version.
    gpids = get_vo_gpids( None )
    fname = os.path.join( os.path.split(__file__)[0], "../static/images/missing-image.png" )
    missing_image_data = open( fname, "rb" ).read()
    check_images( gpids,
        check_front = lambda gpid,code,data: code == 200 and data == missing_image_data,
        check_back = lambda gpid,code,data: code == 200 and data == missing_image_data
    )

    # FUDGE! 6.5.0 introduced a lot of new counters for K:FW. The vehicle/ordnance entries for these
    # will always be loaded, but if an older version of VASL has been configured, requests to get images
    # for these counters will, of course, fail, since the new counters won't be in the older VASL modules.
    # We figure out here what those GPID's are.
    # NOTE: All of this is horrendously complicated, and the problem will re-appear if new counters
    # are added to the core VASL module in the future. At that point, we should probably drop testing
    # against older versions of VASL and just test against the latest version :-/
    expected_missing_gpids = set()
    for vo_type in ("vehicles","ordnance"):
        kfw_listings = _kfw_listings[ vo_type ]
        for entries in kfw_listings.values():
            for entry in entries:
                if isinstance( entry["gpid"], list ):
                    expected_missing_gpids.update( entry["gpid"] )
                else:
                    expected_missing_gpids.add( entry["gpid"] )
    expected_missing_gpids = set( str(e) for e in expected_missing_gpids )
    # NOTE: However, some of the GPID's used by the new K:FW counters use old images that are available
    # even in older versions of VASL, so we figure out here what those are.
    def get_gpids( fname ):
        """Extract the GPID's from the specified file."""
        dname = os.path.join( os.path.split(__file__)[0], "fixtures" )
        fname = os.path.join( dname, fname )
        gpids = set()
        for line_buf in open(fname,"r"):
            mo = re.search( "^[0-9a-z:]+", line_buf )
            if mo:
                gpids.add( mo.group() )
        return gpids
    legacy_gpids = get_gpids( "vasl-pieces-legacy.txt" )
    latest_gpids = get_gpids( "vasl-pieces-6.5.1.txt" )
    common_gpids = legacy_gpids.intersection( latest_gpids )
    expected_missing_gpids = expected_missing_gpids.difference( common_gpids )
    expected_missing_gpids.remove( "1002" ) # FUDGE! this is a remapped GPID (11340)
    expected_missing_gpids.remove( "1527" ) # FUDGE! this is a remapped GPID (12730)

    vasl_version = None
    def _do_check_front( gpid, code, data ):
        if vasl_version not in _EXPECTED_MISSING_GPIDS_EXCEPTIONS and gpid in expected_missing_gpids:
            return code == 404 and not data
        return code == 200 and data
    def _do_check_back( gpid, code, data ):
        if vasl_version not in _EXPECTED_MISSING_GPIDS_EXCEPTIONS and gpid in expected_missing_gpids:
            return code == 404 and not data
        return (code == 200 and data) or (code == 404 and not data)

    # initialize
    check_dir = os.path.join( os.path.split(__file__)[0], "fixtures" )
    save_dir = os.environ.get( "COUNTERS_SAVEDIR" ) # nb: define this to save the generated reports
    if save_dir:
        if os.path.isdir( save_dir ):
            shutil.rmtree( save_dir )
        os.makedirs( save_dir )

    # test each VASL version
    failed = False
    vasl_versions = webapp.control_tests.get_vasl_versions()
    for vasl_version in vasl_versions:

        # initialize
        webapp.control_tests \
            .set_data_dir( "{REAL}" ) \
            .set_vasl_version( vasl_version, None )
        init_webapp( webapp, webdriver )

        # figure out what we're expecting to see
        # NOTE: The results were the same across 6.4.0-6.4.4, but 6.5.0 introduced some changes.
        fname = os.path.join( check_dir, "vasl-pieces-{}.txt".format( vasl_version ) )
        if not os.path.isfile( fname ):
            fname = os.path.join( check_dir, "vasl-pieces-legacy.txt" )
        expected_vasl_pieces = open( fname, "r" ).read()

        # generate a report for the pieces loaded
        report, gpids = webapp.control_tests.get_vasl_pieces( vasl_version )
        if save_dir:
            fname2 = os.path.join( save_dir, vasl_version+".txt" )
            with open( fname2, "w" ) as fp:
                fp.write( report )

        # check the report
        if report != expected_vasl_pieces:
            if save_dir:
                print( "FAILED:", vasl_version )
                failed = True
            else:
                assert False, "Report mismatch: {}".format( vasl_version )

        # check each counter
        check_images( gpids, check_front=_do_check_front, check_back=_do_check_back )

    assert not failed

# ---------------------------------------------------------------------

def test_gpid_remapping( webapp, webdriver ):
    """Test GPID remapping."""

    # initialize
    init_webapp( webapp, webdriver )

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
            assert img.get_attribute( "width" ) == "47" # nb: this value depends on the CSS settings!
        else:
            assert check_gpid_image( gpid ) == 404

    def do_test( vasl_version, valid_images ):
        """Do the test."""
        # initialize (using the specified version of VASL)
        webapp.control_tests \
            .set_data_dir( "{REAL}" ) \
            .set_vasl_version( vasl_version, None )
        init_webapp( webapp, webdriver, scenario_persistence=1 )
        load_scenario( scenario_data )
        # check that the German vehicles loaded correctly
        select_tab( "ob1" )
        vehicles_sortable = find_child( "#ob_vehicles-sortable_1" )
        entries = find_children( "li", vehicles_sortable )
        assert len(entries) == 2
        check_entry( entries[0], "/counter/2542/front", True )
        check_entry( entries[1], "/counter/7124/front/0", valid_images )
        # check that the American ordnance loaded correctly
        select_tab( "ob2" )
        vehicles_sortable = find_child( "#ob_ordnance-sortable_2" )
        entries = find_children( "li", vehicles_sortable )
        assert len(entries) == 1
        check_entry( entries[0], "/counter/879/front", valid_images )

    # load the test scenario
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/gpid-remapping.json" )
    scenario_data = json.load( open( fname, "r" ) )

    # run the tests using VASL 6.4.4 and 6.5.0
    # NOTE: Versions of VASL prior to 6.6.0 are no longer officially supported (since they use Java 8),
    # but we would still like to run these tests. See VassalShim._run_vassal_shim(), where we figure out
    # which version of Java to use, and run_vassal_tests() in test_vassal.py, where we check for invalid
    # combinations of VASSAL and VASL. Sigh...
    do_test( "6.4.4", True )
    do_test( "6.5.0", True )
    do_test( "6.5.1", True )

    # disable GPID remapping and try again
    webapp.control_tests.set_gpid_remappings( {} )
    do_test( "6.4.4", True )
    do_test( "6.5.0", False )
    do_test( "6.5.1", False )

# ---------------------------------------------------------------------

def test_compare_version_strings():
    """Test comparing version strings."""

    # test comparing VASSAL version strings
    for i,vassal_version in enumerate( SUPPORTED_VASSAL_VERSIONS):
        if i > 0:
            assert compare_version_strings( SUPPORTED_VASSAL_VERSIONS[i-1], vassal_version ) < 0
        assert compare_version_strings( SUPPORTED_VASSAL_VERSIONS[i], vassal_version ) == 0
        if i < len(SUPPORTED_VASSAL_VERSIONS)-1:
            assert compare_version_strings( vassal_version, SUPPORTED_VASSAL_VERSIONS[i+1] ) < 0

    # test comparing VASL version strings
    for i,vasl_version in enumerate(SUPPORTED_VASL_MOD_VERSIONS):
        if i > 0:
            assert compare_version_strings( SUPPORTED_VASL_MOD_VERSIONS[i-1], vasl_version ) < 0
        assert compare_version_strings( vasl_version, vasl_version ) == 0
        if i < len(SUPPORTED_VASL_MOD_VERSIONS)-1:
            assert compare_version_strings( vasl_version, SUPPORTED_VASL_MOD_VERSIONS[i+1] ) < 0
