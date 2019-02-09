""" Test VASL extensions. """

import os
import zipfile
import typing
import re

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.utils import TempFile
from vasl_templates.webapp.tests.utils import init_webapp, set_player, select_tab, new_scenario, \
    find_child, find_children, wait_for_clipboard
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario
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
@pytest.mark.skipif(
    not pytest.config.option.vo_notes, #pylint: disable=no-member
    reason = "--vo-notes not specified"
)
def test_dedupe_ma_notes( webapp, webdriver ):
    """Test deduping multi-applicable notes."""

    # initialize
    init_webapp( webapp, webdriver,
        reset = lambda ct:
            ct.set_data_dir( dtype="real" ) \
              .set_vasl_mod( vmod="random", extns_dtype="real" ) \
              .set_vo_notes_dir( dtype="real" )
    )

    def do_test( vehicles, expected ): #pylint: disable=missing-docstring
        # add the specified vehicles
        new_scenario()
        set_player( 1, "japanese" )
        for veh in vehicles:
            add_vo( webdriver, "vehicles", 1, veh )
        # get the multi-applicable notes
        btn = find_child( "button.generate[data-id='ob_vehicles_ma_notes_1']" )
        btn.click()
        wait_for_clipboard( 2, expected, transform=_extract_extn_ma_notes )

    # NOTE: The vehicles used in this test have the following multi-applicable notes:
    # - Type 92A:       A
    # - M3(a):          adf:A ; adf:B ; adf:C ; adf:Jp A ; adf:US B
    # - Type 98 MCT:    adf:Br H ; adf:Ge A

    # do the tests
    do_test( [ "Type 92A (Tt)", "M3(a) (LT)" ], [
        ( False, "A", "The MA <i>and all</i" ),
        ( True, "A", "The (a) indicates U." ),
        ( True, "B", "This vehicle uses Re" ),
        ( True, "C", "Although a captured " ),
        # nb: "Jp A" should be deleted as a dupe of A
        ( True, "US B", "Due to two of the MG" ),
    ] )
    do_test( [ "Type 92A (Tt)", "Type 98 MCT (AAtr)" ], [
        ( False, "A", "The MA <i>and all</i" ),
        ( True, "Br H", 'As signified by "Inf' ),
        ( True, "Ge A", "MA and CMG (if so eq" ), # nb: this is "Ge A", which is different to the Japanese "A"
    ] )
    do_test( [ "M3(a) (LT)", "Type 98 MCT (AAtr)" ], [
        ( True, "A", "The (a) indicates U." ),
        ( True, "B", "This vehicle uses Re" ),
        ( True, "C", "Although a captured " ),
        ( True, "Br H", 'As signified by "Inf' ),
        ( True, "Ge A", "MA and CMG (if so eq" ),
        ( True, "Jp A", "The MA <i>and all</i" ),
        ( True, "US B", "Due to two of the MG" ),
    ] )
    do_test( [ "Type 92A (Tt)", "M3(a) (LT)", "Type 98 MCT (AAtr)" ], [
        ( False, "A", "The MA <i>and all</i" ),
        ( True, "A", "The (a) indicates U." ),
        ( True, "B", "This vehicle uses Re" ),
        ( True, "C", "Although a captured " ),
        ( True, "Br H", 'As signified by "Inf' ),
        ( True, "Ge A", "MA and CMG (if so eq" ),
        # nb: "Jp A" should be deleted as a dupe of A
        ( True, "US B", "Due to two of the MG" ),
    ] )

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

@pytest.mark.skipif(
    not pytest.config.option.vasl_extensions, #pylint: disable=no-member
    reason = "--vasl-extensions not specified"
)
@pytest.mark.skipif(
    not pytest.config.option.vo_notes, #pylint: disable=no-member
    reason = "--vo-notes not specified"
)
def test_bfp_extensions( webapp, webdriver ):
    """Test the Bounding Fire extension."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct:
            ct.set_data_dir( dtype="real" ) \
              .set_vasl_mod( vmod="random", extns_dtype="real" ) \
              .set_vo_notes_dir( dtype="real" )
    )

    # load the test scenario
    load_scenario( {
        "PLAYER_1": "japanese",
        "OB_VEHICLES_1": [
            { "name": "Type 97A CHI-HA" }, # nb: this is a normal counter
            { "name": "M3A1 Scout Car(a)" } # nb: this is a BFP counter
        ],
    } )
    select_tab( "ob1" )

    # test the OB snippet
    btn = find_child( "button.generate[data-id='ob_vehicles_1']" )
    btn.click()
    wait_for_clipboard( 2, re.compile(
        'Type 97A CHI-HA'
        '.+<div class="note">'
        '.+8\u2020, B\u2020<sup>1</sup>, C\u2020<sup>2</sup>'
        '.+</div>'
        r'.+M3A1 Scout Car\(a\)'
        '.+<div class="note">'
        '.+&#x2756;'
        '.+17, A, C, AllM 34\u2020<sup>2</sup>, Jp A\u2020<sup>1</sup>, Ch F\u2020'
        '.+</div>',
        re.DOTALL
    ) )

    # test the multi-applicable notes
    btn = find_child( "button.generate[data-id='ob_vehicles_ma_notes_1']" )
    btn.click()
    wait_for_clipboard( 2, [
        ( False, "B", "sD becomes available" ),
        ( False, "C", "This tank has no rad" ),
        ( True, "A", "The (a) indicates U." ),
        ( True, "C", "Although a captured " ),
        ( True, "Ch F", "This vehicle, despit" ),
        ( True, "Jp A", "The MA <i>and all</i" ),
    ], transform=_extract_extn_ma_notes )

    # test the Chapter H note
    vehicles_sortable = find_child( "#ob_vehicles-sortable_1" )
    elems = find_children( "li img.snippet", vehicles_sortable )
    assert len(elems) == 2
    elems[0].click()
    wait_for_clipboard( 2, re.compile( r'<img src=".*?/vehicles/japanese/note/8">' ) )
    elems[1].click()
    wait_for_clipboard( 2, re.compile( r'<img src=".*?/vehicles/japanese/note/adf:17">' ) )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@pytest.mark.skipif(
    not pytest.config.option.vasl_extensions, #pylint: disable=no-member
    reason = "--vasl-extensions not specified"
)
@pytest.mark.skipif(
    not pytest.config.option.vo_notes, #pylint: disable=no-member
    reason = "--vo-notes not specified"
)
def test_bfp_extensions2( webapp, webdriver ):
    """Test the Bounding Fire extension (Operation Cobra counters)."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct:
            ct.set_data_dir( dtype="real" ) \
              .set_vasl_mod( vmod="random", extns_dtype="real" ) \
              .set_vo_notes_dir( dtype="real" )
    )

    # load the test scenario
    load_scenario( {
        "PLAYER_1": "american",
        "OB_VEHICLES_1": [
            { "name": "M5A1" }, # nb: this is a normal counter
            { "name": "M5A1F" }, # nb: this is the flamethrower version
            { "name": "M5A1C" }, # nb: this is the Culin version
        ],
    } )
    select_tab( "ob1" )

    # test the OB snippet
    btn = find_child( "button.generate[data-id='ob_vehicles_1']" )
    btn.click()
    wait_for_clipboard( 2, re.compile(
        r'\bM5A1\b'
        '.+<div class="note">'
        '.+5\u2020, C\u2020<sup>2</sup>, F\u2020<sup>1</sup>, G, N, Y'
        '.+</div>'
        r'.+\bM5A1F\b'
        '.+<div class="note">'
        '.+&#x2756;'
        '.+5\u2020, US C\u2020<sup>2</sup>, US F\u2020<sup>1</sup>, US G, US N, US Y, C'
        '.+</div>'
        r'.+\bM5A1C\b'
        '.+<div class="note">'
        '.+&#x2756;'
        '.+5\u2020, US C\u2020<sup>2</sup>, US F\u2020<sup>1</sup>, US G, US N, US Y, A, B'
        '.+</div>',
        re.DOTALL
    ) )

    # test the multi-applicable notes
    btn = find_child( "button.generate[data-id='ob_vehicles_ma_notes_1']" )
    btn.click()
    wait_for_clipboard( 2, [
        ( False, "C", "37mm canister has 12" ),
        ( False, "F", "This AFV may be equi" ),
        ( False, "G", "May be equipped with" ),
        ( False, "N", "This vehicle was use" ),
        ( False, "Y", "If the scenario date" ),
        ( True, "A", "Use U.S. Vehicle Not" ),
        ( True, "B", "A vehicle of the sam" ),
        ( True, "C", "A vehicle of the sam" ),
    ], transform=_extract_extn_ma_notes )

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

def _extract_ma_notes( clipboard ):
    """Extract the multi-applicable notes from a snippet."""
    return [
        mo.group(1).strip()
        for mo in re.finditer( r'<div class="ma-note">(.*?)</div>', clipboard, re.DOTALL )
    ]

def _extract_extn_ma_notes( clipboard ): #pylint: disable=missing-docstring
    """Extract the multi-applicable notes from a snippet, checking for extensions."""
    ma_notes = _extract_ma_notes( clipboard )
    # NOTE: We return the first few characters of the multi-applicable note content,
    # just enough for us to determine whether we're showing the right one or not.
    for i,ma_note in enumerate(ma_notes):
        is_extn = "&#x2756;" in ma_note
        mo = re.search( r"<span class='key'>(.+?):</span>(.*)", ma_note )
        ma_notes[i] = is_extn, mo.group(1).strip(), mo.group(2).strip()[:20]
    return ma_notes
