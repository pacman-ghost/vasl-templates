""" Test VASL extensions. """

import os
import zipfile
import typing
import re

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.utils import TempFile
from vasl_templates.webapp.tests.utils import init_webapp, set_player, select_tab, new_scenario, \
    find_child, find_children, wait_for_clipboard, generate_sortable_entry_snippet
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario
from vasl_templates.webapp.tests.test_vehicles_ordnance import add_vo
from vasl_templates.webapp.tests.test_vassal import analyze_vsav

_TEST_VASL_EXTN_FNAME = "test-vasl-extension.zip"

# ---------------------------------------------------------------------

def test_load_vasl_extensions( webapp, webdriver ):
    """Test loading VASL extensions."""

    def do_test( build_info_fname, build_info, expected ): #pylint: disable=missing-docstring

        # create the test VASL extension
        extn_fname = _set_test_vasl_extn( webapp, build_info, build_info_fname )

        # reload the webapp
        webapp.control_tests.set_vasl_version( "random", "{TEMP_DIR}" )
        init_webapp( webapp, webdriver )
        expected = expected.replace( "{EXTN-FNAME}", extn_fname )
        _check_warning_msgs( webapp, expected )

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
        "Not accepting {EXTN-FNAME}: no extension info for unknown/v0.1"
    )

    # try loading something that's not a ZIP file
    webapp.control_tests \
        .save_temp_file( _TEST_VASL_EXTN_FNAME, b"This is not a ZIP file." ) \
        .set_vasl_version( "random", "{TEMP_DIR}" )
    init_webapp( webapp, webdriver )
    _check_warning_msgs( webapp, "Can't check VASL extension (not a ZIP file):" )

# ---------------------------------------------------------------------

def test_vasl_extension_info( webapp, webdriver ):
    """Test matching VASL extensions with our extension info files."""

    # prepare our test VASL extension
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/vasl-extensions/test-extn.xml" )
    with open( fname, "r", encoding="utf=8" ) as fp:
        extn_fname = _set_test_vasl_extn( webapp, fp.read() )

    def do_test( dname, expected ): #pylint: disable=missing-docstring
        webapp.control_tests \
            .set_vasl_version( "random", "{TEMP_DIR}" ) \
            .set_vasl_extn_info_dir( dname )
        init_webapp( webapp, webdriver )
        _check_warning_msgs( webapp, expected )

    # try loading the VASL extension, with no matching extension info
    do_test( "mismatched-id",
        "Not accepting {}: no extension info for test/v0.1".format( extn_fname )
    )
    do_test( "mismatched-version",
        "Not accepting {}: no extension info for test/v0.1".format( extn_fname )
    )

    # try loading the VASL extension, with matching extension info
    do_test( "good-match", None )
    extns = webapp.control_tests.get_vasl_extns()
    assert len(extns) == 1
    extn = extns[0]
    assert os.path.basename( extn[0] ) == _TEST_VASL_EXTN_FNAME
    assert extn[1] == { "extensionId": "test", "version": "v0.1" }

# ---------------------------------------------------------------------

def test_dedupe_ma_notes( webapp, webdriver ):
    """Test deduping multi-applicable notes."""

    # check if the remote webapp server supports this test
    if not webapp.control_tests.has_capability( "chapter-h" ):
        return

    # initialize
    webapp.control_tests \
        .set_data_dir( "{REAL}" ) \
        .set_vasl_version( "random", "{REAL}" ) \
        .set_vo_notes_dir( "{REAL}" )
    init_webapp( webapp, webdriver )

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
    # - M3(a):          adf-bj:A ; adf-bj:B ; adf-bj:C ; adf-bj:Jp A ; adf-bj:US B
    # - Type 98 MCT:    adf-bj:Br H ; adf-bj:Ge A

    # do the tests
    do_test( [ "Type 92A", "M3(a)" ], [
        ( False, "A", "The MA and <i>all MG" ),
        ( True, "A", "The (a) indicates U." ),
        ( True, "B", "This vehicle uses Re" ),
        ( True, "C", "Although a captured " ),
        # nb: "Jp A" should be deleted as a dupe of A
        ( True, "US B", "Due to two of the MG" ),
    ] )
    do_test( [ "Type 92A", "Type 98 MCT" ], [
        ( False, "A", "The MA and <i>all MG" ),
        ( True, "Br H", 'As signified by "Inf' ),
        ( True, "Ge A", "MA and CMG (if so eq" ), # nb: this is "Ge A", which is different to the Japanese "A"
    ] )
    do_test( [ "M3(a)", "Type 98 MCT" ], [
        ( True, "A", "The (a) indicates U." ),
        ( True, "B", "This vehicle uses Re" ),
        ( True, "C", "Although a captured " ),
        ( True, "Br H", 'As signified by "Inf' ),
        ( True, "Ge A", "MA and CMG (if so eq" ),
        ( True, "Jp A", "The MA and <i>all MG" ),
        ( True, "US B", "Due to two of the MG" ),
    ] )
    do_test( [ "Type 92A", "M3(a)", "Type 98 MCT" ], [
        ( False, "A", "The MA and <i>all MG" ),
        ( True, "A", "The (a) indicates U." ),
        ( True, "B", "This vehicle uses Re" ),
        ( True, "C", "Although a captured " ),
        ( True, "Br H", 'As signified by "Inf' ),
        ( True, "Ge A", "MA and CMG (if so eq" ),
        # nb: "Jp A" should be deleted as a dupe of A
        ( True, "US B", "Due to two of the MG" ),
    ] )

# ---------------------------------------------------------------------

def test_kgs_extensions( webapp, webdriver ):
    """Test the KGS extension."""

    def check_counter_images( veh_name, expected ):
        """Check the counter images available for the specified vehicle."""

        # add the specified vehicle
        add_vo( webdriver, "vehicles", 2, veh_name )

        # edit the vehicle
        elems = find_children( "#ob_vehicles-sortable_2 li" )
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
        webapp.control_tests \
            .set_data_dir( "{REAL}" ) \
            .set_vasl_version( "random", "{REAL}" if enable_extns else None )
        init_webapp( webapp, webdriver )
        set_player( 2, "russian" )

        # check the Matilda II(b)
        check_counter_images( "Matilda II(b)",
           ["7150","f97:178","f97:184"] if enable_extns else ["7150"]
        )

        # check the T60-M40
        check_counter_images( "T-60 M40",
            ["547","f97:186"] if enable_extns else ["547"]
        )

    # do the tests
    do_test( True )
    do_test( False )

# ---------------------------------------------------------------------

def test_bfp_extensions( webapp, webdriver ):
    """Test the Bounding Fire extension."""

    # check if the remote webapp server supports this test
    if not webapp.control_tests.has_capability( "chapter-h" ):
        return

    # initialize
    webapp.control_tests \
        .set_data_dir( "{REAL}" ) \
        .set_vasl_version( "random", "{REAL}" ) \
        .set_vo_notes_dir( "{REAL}" )
    init_webapp( webapp, webdriver, scenario_persistence=1 )

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
        '.+<td class="note"'
        '.+8\u2020, B\u2020<sup>1</sup>, C\u2020<sup>2</sup>'
        r'.+M3A1 Scout Car\(a\)'
        '.+<td class="note"'
        '.+&#x2756;'
        '.+17, A, C, AllM 34\u2020<sup>2</sup>, Jp A\u2020<sup>1</sup>, Ch F\u2020',
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
        ( True, "Jp A", "The MA and <i>all MG" ),
    ], transform=_extract_extn_ma_notes )

    # test the Chapter H note
    elems = find_children( "#ob_vehicles-sortable_1 li img.snippet" )
    assert len(elems) == 2
    elems[0].click()
    wait_for_clipboard( 2, "By 1935 the latest European tanks", contains=True )
    elems[1].click()
    wait_for_clipboard( 2, "The Japanese captured hundreds of vehicles", contains=True )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_bfp_extensions2( webapp, webdriver ):
    """Test the Bounding Fire extension (Operation Cobra counters)."""

    # check if the remote webapp server supports this test
    if not webapp.control_tests.has_capability( "chapter-h" ):
        return

    # initialize
    webapp.control_tests \
        .set_data_dir( "{REAL}" ) \
        .set_vasl_version( "random", "{REAL}" ) \
        .set_vo_notes_dir( "{REAL}" )
    init_webapp( webapp, webdriver, scenario_persistence=1 )

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
        '.+<td class="note"'
        '.+5\u2020, C\u2020<sup>2</sup>, F\u2020<sup>1</sup>, G, N, Y'
        r'.+\bM5A1F\b'
        '.+<td class="note"'
        '.+&#x2756;'
        '.+5\u2020, US C\u2020<sup>2</sup>, US F\u2020<sup>1</sup>, US G, US N, US Y, C'
        r'.+\bM5A1C\b'
        '.+<td class="note"'
        '.+&#x2756;'
        '.+5\u2020, US C\u2020<sup>2</sup>, US F\u2020<sup>1</sup>, US G, US N, US Y, A, B',
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

def test_ffs_extensions( webapp, webdriver ):
    """Test the Fight For Seoul extension."""

    # check if the remote webapp server supports this test
    if not webapp.control_tests.has_capability( "chapter-h" ):
        return

    # analyze a VASL scenario that has the FfS counters
    webapp.control_tests \
        .set_vassal_version( "random" ) \
        .set_vasl_version( "random", None ) # nb: we don't load the extension
    init_webapp( webapp, webdriver, vsav_persistence=1, scenario_persistence=1 )
    set_player( 1, "american" )
    analyze_vsav( "ffs.vsav",
        [ [], [] ],
        [ [], [] ],
        [ "No vehicles/ordnance were imported." ]
    )

    # analyze the same VASL scenario with the FfS extension loaded
    webapp.control_tests \
        .set_data_dir( "{REAL}" ) \
        .set_vassal_version( "random" ) \
        .set_vasl_version( "random", "{REAL}" ) \
        .set_vo_notes_dir( "{REAL}" )
    init_webapp( webapp, webdriver, vsav_persistence=1, scenario_persistence=1 )
    set_player( 1, "american" )
    analyze_vsav( "ffs.vsav",
        [ [ "ffs/v:000" ], [ "ffs/o:000" ] ],
        [ [], [] ],
        [ "Imported 1 American vehicle and 1 ordnance." ]
    )

    # NOTE: All the vehicle/ordnance and multi-applicable notes in the FfS extension
    # actually refer to K:FW, so we want to make sure we get the correct ones.
    select_tab( "ob1" )

    # check the vehicle's OB snippet
    btn = find_child( "button.generate[data-id='ob_vehicles_1']" )
    btn.click()
    wait_for_clipboard( 2, re.compile(
        'POA-CWS-H5'
        '.+<td class="note"'
        '.+&#x2756;'
        '.+5\u2020, C, M',
        re.DOTALL
    ) )

    # check the vehicle's multi-applicable notes
    btn = find_child( "button.generate[data-id='ob_vehicles_ma_notes_1']" )
    btn.click()
    clipboard = wait_for_clipboard( 2, [
        ( True, "C", "37mm canister has 12" ),
        ( True, "M", "Used by the U.S.M.C." ),
    ], transform=_extract_extn_ma_notes )
    # make sure we haven't incorrectly got the *American* multi-applicable notes
    assert "and is available in all theaters" not in clipboard

    # check the vehicle's Chapter H note
    sortable = find_child( "#ob_vehicles-sortable_1" )
    snippet = generate_sortable_entry_snippet( sortable, 0 )
    assert "U.S.M.C. tankers gave the H5 the nickname" in snippet

    # check the ordnance's OB snippet
    btn = find_child( "button.generate[data-id='ob_ordnance_1']" )
    btn.click()
    wait_for_clipboard( 2, re.compile(
        r'M20\(L\) 75mm Recoilless Rifle'
        '.+<td class="note"'
        '.+&#x2756;'
        '.+25\u2020, K, M, O, P, R',
        re.DOTALL
    ) )

    # check the ordnance's multi-applicable notes
    btn = find_child( "button.generate[data-id='ob_ordnance_ma_notes_1']" )
    btn.click()
    clipboard = wait_for_clipboard( 2, [
        ( True, "K", "Used by ROK Army for" ),
        ( True, "M", "Used by the U.S.M.C." ),
        ( True, "O", "Used by one or more " ),
        ( True, "P", "Used by the Korean M" ),
        ( True, "R", "Used by Royal Marine" ),
    ], transform=_extract_extn_ma_notes )

    # check the ordnance's Chapter H note
    sortable = find_child( "#ob_ordnance-sortable_1" )
    snippet = generate_sortable_entry_snippet( sortable, 0 )
    assert "The KMC received their M20's in August 1951." in snippet

# ---------------------------------------------------------------------

def _set_test_vasl_extn( webapp, build_info, build_info_fname="buildFile" ):
    """Install a test VASL extension file."""
    with TempFile() as temp_file:
        with zipfile.ZipFile( temp_file.name, "w" ) as zip_file:
            zip_file.writestr( build_info_fname, build_info )
        temp_file.close( delete=False )
        with open( temp_file.name, "rb" ) as fp:
            zip_data = fp.read()
    fname = _TEST_VASL_EXTN_FNAME
    webapp.control_tests.save_temp_file( fname, zip_data )
    return fname

def _check_warning_msgs( webapp, expected ):
    """Check that the startup warning messages are what we expect."""
    warnings = webapp.control_tests.get_vasl_mod_warnings()
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
        mo = re.search( r"<span class='key'>(.+?):</span>(.*)", ma_note, re.DOTALL )
        val = mo.group(2).replace( "<!-- disabled -->", "" )
        ma_notes[i] = is_extn, mo.group(1).strip(), val.strip()[:20]
    return ma_notes
