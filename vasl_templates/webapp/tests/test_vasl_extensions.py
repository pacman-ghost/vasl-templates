""" Test VASL extensions. """

import os
import zipfile
import typing

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.utils import TempFile
from vasl_templates.webapp.tests.utils import init_webapp, set_player, find_child, find_children
from vasl_templates.webapp.tests.test_vehicles_ordnance import add_vo

# ---------------------------------------------------------------------

def test_load_vasl_extensions( webapp, webdriver ):
    """Test loading VASL extensions."""

    # initialize
    control_tests = init_webapp( webapp, webdriver )

    def do_test( build_info_fname, build_info, expected ): #pylint: disable=missing-docstring

        # create the test VASL extension
        _set_test_vasl_extn( control_tests, build_info, build_info_fname )

        # reload the webapp
        control_tests.set_vasl_mod( vmod="random", extns_dtype="test" )
        webdriver.refresh()
        _check_warning_msgs( control_tests, expected )

    # try loading an extension that has no buildFile
    do_test( "foo", "<foo />", "Missing buildFile:" )

    # try loading extensions with missing information
    do_test( "buildFile", '<VASSAL.build.module.ModuleExtension version="v0.1" />',
        "Can't find ID for VASL extension:"
    )
    do_test( "buildFile", '<VASSAL.build.module.ModuleExtension extensionId="test" />',
        "Can't find version for VASL extension:"
    )

    # try loading an extension with an unknown ID
    do_test( "buildFile", '<VASSAL.build.module.ModuleExtension version="v0.1" extensionId="unknown" />',
        "Not accepting test.zip: no extension info for unknown/v0.1"
    )

    # try loading something that's not a ZIP file
    control_tests.set_test_vasl_extn( fname="test.zip", bin_data=b"This is not a ZIP file." ) \
                 .set_vasl_mod( vmod="random", extns_dtype="test" )
    webdriver.refresh()
    _check_warning_msgs( control_tests, "Can't check VASL extension (not a ZIP file):" )

# ---------------------------------------------------------------------

def test_vasl_extension_info( webapp, webdriver ):
    """Test matching VASL extensions with our extension info files."""

    # initialize
    control_tests = init_webapp( webapp, webdriver )

    # prepare our test VASL extension
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/vasl-extensions/test-extn.xml" )
    _set_test_vasl_extn( control_tests, open(fname,"r").read() )

    def do_test( dtype, expected ): #pylint: disable=missing-docstring
        control_tests.set_vasl_extn_info_dir( dtype=dtype ) \
                     .set_vasl_mod( vmod="random", extns_dtype="test" )
        webdriver.refresh()
        _check_warning_msgs( control_tests, expected )

    # try loading the VASL extension, with no matching extension info
    do_test( "mismatched-id",
        "Not accepting test.zip: no extension info for test/v0.1"
    )
    do_test( "mismatched-version",
        "Not accepting test.zip: no extension info for test/v0.1"
    )

    # try loading the VASL extension, with matching extension info
    do_test( "good-match", None )
    extns = control_tests.get_vasl_extns()
    assert len(extns) == 1
    extn = extns[0]
    assert extn[1] == { "extensionId": "test", "version": "v0.1" }

# ---------------------------------------------------------------------

@pytest.mark.skipif(
    not pytest.config.option.vasl_extensions, #pylint: disable=no-member
    reason = "--vasl-extensions not specified"
)
def test_kgs_extensions( webapp, webdriver ):
    """Test the KGS extension."""

    # initialize
    control_tests = init_webapp( webapp, webdriver,
        reset = lambda ct: ct.set_data_dir( dtype="real" )
    )

    def check_counter_images( veh_name, expected ):
        """Check the counter images available for the specified vehicle."""

        # add the specified vehicle
        add_vo( webdriver, "vehicles", 2, veh_name )

        # edit the vehicle
        vehicles_sortable = find_child( "#ob_vehicles-sortable_2" )
        elems = find_children( "li", vehicles_sortable )
        ActionChains(webdriver).double_click( elems[-1] ).perform()
        dlg = find_child( ".ui-dialog.edit-vo" )

        # check the currently-selected counter
        image_url = find_child( "img.vasl-image", dlg ).get_attribute( "src" )
        if expected:
            assert image_url.endswith( "/counter/{}/front".format( expected[0] ) )
        else:
            assert image_url.endswith( "/missing-image.png" )

        # check the available counters
        btn = find_child( "input.select-vo-image", dlg )
        if expected and len(expected) > 1:
            btn.click()
            dlg2 = find_child( ".ui-dialog.select-vo-image" )
            image_urls = [
                elem.get_attribute( "src" )
                for elem in find_children( ".vo-images img", dlg2 )
            ]
            assert len(image_urls) == len(expected)
            for image_url,piece_id in zip( image_urls, expected ):
                assert image_url.endswith( "/counter/{}/front/0".format(piece_id) )
            dlg2.send_keys( Keys.ESCAPE )
        else:
            assert btn is None
        dlg.send_keys( Keys.ESCAPE )

    def do_test( enable_extns ): #pylint: disable=missing-docstring

        # initialize
        control_tests.set_vasl_mod( vmod="random",
            extns_dtype = "real" if enable_extns else None
        )
        webdriver.refresh()
        set_player( 2, "russian" )

        # check the Matilda II(b)
        check_counter_images( "Matilda II(b) (HT)",
           ["f97:178","f97:184"] if enable_extns else None
        )

        # check the T60-M40
        check_counter_images( "T-60 M40 (Tt)",
            ["547","f97:186"] if enable_extns else ["547"]
        )

    # do the tests
    do_test( True )
    do_test( False )

# ---------------------------------------------------------------------

def _set_test_vasl_extn( control_tests, build_info, build_info_fname="buildFile" ):
    """Install a test VASL extension file."""
    with TempFile() as temp_file:
        with zipfile.ZipFile( temp_file.name, "w" ) as zip_file:
            zip_file.writestr( build_info_fname, build_info )
        temp_file.close()
        with open( temp_file.name, "rb" ) as fp:
            zip_data = fp.read()
    control_tests.set_test_vasl_extn( fname="test.zip", bin_data=zip_data )

def _check_warning_msgs( control_tests, expected ):
    """Check that the startup warning messages are what we expect."""
    warnings = control_tests.get_vasl_mod_warnings()
    if expected:
        assert len(warnings) == 1
        if isinstance( expected, typing.re.Pattern ):
            assert expected.search( warnings[0] )
        else:
            assert warnings[0].startswith( expected )
    else:
        assert not warnings
