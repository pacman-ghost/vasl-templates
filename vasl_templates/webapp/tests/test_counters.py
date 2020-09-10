""" Test serving counter images. """

import os
import io
import json
import re
import shutil
import urllib.request

import pytest
import tabulate

from vasl_templates.webapp.vasl_mod import VaslMod, get_vo_gpids, compare_vasl_versions, SUPPORTED_VASL_MOD_VERSIONS
from vasl_templates.webapp.config.constants import DATA_DIR
from vasl_templates.webapp.vo import _kfw_listings #pylint: disable=protected-access
from vasl_templates.webapp.utils import change_extn
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
) #pylint: disable=too-many-statements,too-many-locals
def test_counter_images( webapp ):
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
    control_tests = ControlTests( webapp )
    control_tests.set_vasl_mod( vmod=None )
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

    def _do_check_front( gpid, code, data ):
        if vasl_version not in ("6.5.0","6.5.1") and gpid in expected_missing_gpids:
            return code == 404 and not data
        return code == 200 and data
    def _do_check_back( gpid, code, data ):
        if vasl_version not in ("6.5.0","6.5.1") and gpid in expected_missing_gpids:
            return code == 404 and not data
        return (code == 200 and data) or (code == 404 and not data)

    # initialize
    check_dir = os.path.join( os.path.split(__file__)[0], "fixtures" )
    save_dir = os.environ.get( "COUNTERS_SAVEDIR" ) # nb: define this to save the generated reports
    if save_dir and os.path.isdir(save_dir):
        shutil.rmtree( save_dir )
        os.makedirs( save_dir )

    # test each VASL module file in the specified directory
    failed = False
    vmod_fnames = control_tests.get_vasl_mods()
    for vmod_fname in vmod_fnames:

        # install the VASL module file
        control_tests.set_vasl_mod( vmod=vmod_fname )

        # NOTE: We assume we have access to the same VASL modules as the server, but the path on the webserver
        # might be different to what it is locally, so we translate it here.
        fname = os.path.split( vmod_fname )[1]
        vasl_mods_dir = pytest.config.option.vasl_mods #pylint: disable=no-member
        fname = os.path.join( vasl_mods_dir, fname )

        # figure out what we're expecting to see
        # NOTE: The results were the same across 6.4.0-6.4.4, but 6.5.0 introduced some changes.
        vasl_mod = VaslMod( fname, DATA_DIR, None )
        vasl_version = vasl_mod.vasl_version
        fname = os.path.join( check_dir, "vasl-pieces-{}.txt".format( vasl_version ) )
        if not os.path.isfile( fname ):
            fname = os.path.join( check_dir, "vasl-pieces-legacy.txt" )
        expected_vasl_pieces = open( fname, "r" ).read()

        # generate a report for the pieces loaded
        buf = io.StringIO()
        _dump_pieces( vasl_mod, buf )
        report = buf.getvalue()
        if save_dir:
            fname2 = change_extn( os.path.split(vmod_fname)[1], ".txt" )
            with open( os.path.join(save_dir,fname2), "w" ) as fp:
                fp.write( report )

        # check the report
        if report != expected_vasl_pieces:
            if save_dir:
                print( "FAILED:", vasl_version )
                failed = True
            else:
                assert False, "Report mismatch: {}".format( vasl_version )

        # check each counter
        gpids = get_vo_gpids( vasl_mod )
        check_images( gpids, check_front=_do_check_front, check_back=_do_check_back )

    assert not failed

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _dump_pieces( vasl_mod, out ):
    """Dump the VaslMod pieces."""

    # dump the VASL pieces
    results = [ [ "GPID", "Name", "Front images", "Back images"] ]
    pieces = vasl_mod._pieces #pylint: disable=protected-access
    # GPID's were originally int's but then changed to str's. We then started seeing non-numeric GPID's :-/
    # For back-compat, we try to maintain sort order for numeric values.
    def sort_key( val ): #pylint: disable=missing-docstring
        if val.isdigit():
            return ( "0"*10 + val )[-10:]
        else:
            # nb: we make sure that alphanumeric values appear after numeric values, even if they start with a number
            return "_" + val
    gpids = sorted( pieces.keys(), key=sort_key ) # nb: because GPID's changed from int to str :-/
    for gpid in gpids:
        piece = pieces[ gpid ]
        assert piece["gpid"] == gpid
        results.append( [ gpid, piece["name"], piece["front_images"], piece["back_images"] ] )
    print( tabulate.tabulate( results, headers="firstrow", numalign="left" ), file=out )

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
            assert img.get_attribute( "width" ) == "47" # nb: this value depends on the CSS settings!
        else:
            assert check_gpid_image( gpid ) == 404

    def do_test( vmod_fname, valid_images ):
        """Do the test."""
        # initialize (using the specified VASL vmod)
        init_webapp( webapp, webdriver, scenario_persistence=1,
            reset = lambda ct:
                ct.set_data_dir( dtype="real" ) \
                  .set_vasl_mod( vmod=vmod_fname )
        )
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

    # locate the VASL modules
    vmod_fnames = control_tests.get_vasl_mods()
    def find_vasl_mod( version ):
        """Find the VASL module for the specified version."""
        matches = [ fname for fname in vmod_fnames if "vasl-{}.vmod".format(version) in fname ]
        assert len(matches) == 1
        return matches[0]

    # run the tests using VASL 6.4.4 and 6.5.0
    do_test( find_vasl_mod("6.4.4"), True )
    do_test( find_vasl_mod("6.5.0"), True )
    do_test( find_vasl_mod("6.5.1"), True )

    # disable GPID remapping and try again
    prev_gpid_mappings = control_tests.set_gpid_remappings( gpids=[] )
    try:
        do_test( find_vasl_mod("6.4.4"), True )
        do_test( find_vasl_mod("6.5.0"), False )
        do_test( find_vasl_mod("6.5.1"), False )
    finally:
        # NOTE: This won't get done if Python exits unexpectedly in the try block,
        # which will leave the server in the wrong state if it's remote.
        control_tests.set_gpid_remappings( gpids=prev_gpid_mappings )

# ---------------------------------------------------------------------

def test_compare_vasl_versions():
    """Test comparing VASL version strings."""
    for i,vasl_version in enumerate(SUPPORTED_VASL_MOD_VERSIONS):
        if i > 0:
            assert compare_vasl_versions( SUPPORTED_VASL_MOD_VERSIONS[i-1], vasl_version ) < 0
        assert compare_vasl_versions( vasl_version, vasl_version ) == 0
        if i < len(SUPPORTED_VASL_MOD_VERSIONS)-1:
            assert compare_vasl_versions( vasl_version, SUPPORTED_VASL_MOD_VERSIONS[i+1] ) < 0
