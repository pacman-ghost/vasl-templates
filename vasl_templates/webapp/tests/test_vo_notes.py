""" Test Chapter H vehicle/ordnance notes. """

import os
import shutil
import io
import re

import pytest
import lxml.html
import lxml.etree
import tabulate

from vasl_templates.webapp.tests.utils import \
    init_webapp, get_nationalities, select_tab, set_player, find_child, find_children, wait_for, wait_for_clipboard
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario, save_scenario
from vasl_templates.webapp.tests.test_vehicles_ordnance import add_vo, delete_vo

# ---------------------------------------------------------------------

def test_vo_notes( webapp, webdriver ):
    """Test generating snippets for vehicle/ordnance notes."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct: ct.set_vo_notes_dir( dtype="test" )
    )

    # load the test scenario
    load_scenario( {
        "PLAYER_1": "german",
        "OB_VEHICLES_1": [ { "name": "a german vehicle" }, { "name": "another german vehicle" } ],
        "OB_ORDNANCE_1": [ { "name": "a german ordnance" }, { "name": "another german ordnance" } ],
        "PLAYER_2": "russian",
        "OB_VEHICLES_2": [ { "name": "a russian vehicle" }, { "name": "another russian vehicle" } ],
        "OB_ORDNANCE_2": [ { "name": "a russian ordnance" }, { "name": "another russian ordnance" } ],
    } )

    # check the snippets
    _check_vo_snippets( 1, "vehicles", [
        ( "a german vehicle", "vehicles/german/note/1" ),
        None
    ] )
    _check_vo_snippets( 1, "ordnance", [
        ( "a german ordnance", "ordnance/german/note/1" ),
        None
    ] )
    _check_vo_snippets( 2, "vehicles", [
        ( "a russian vehicle", "vehicles/russian/note/1" ),
        None
    ] )
    _check_vo_snippets( 2, "ordnance", [
        ( "a russian ordnance", "ordnance/russian/note/1" ),
        None
    ] )

# ---------------------------------------------------------------------

def test_ma_notes( webapp, webdriver ):
    """Test generating snippets for vehicle/ordnance multi-applicable notes."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct: ct.set_vo_notes_dir( dtype="test" )
    )

    def do_test( player_no, nat, vo_type, vo_entries, expected ):
        """Load the specified vehicles and check the resulting snippet."""
        load_scenario( {
            "PLAYER_{}".format(player_no):nat,
            "OB_{}_{}".format(vo_type.upper(),player_no): [ { "name": v } for v in vo_entries ],
        } )
        select_tab( "ob{}".format( player_no ) )
        btn = find_child(
            "button.generate[data-id='ob_{}_ma_notes_{}']".format( vo_type, player_no )
        )
        btn.click()
        wait_for_clipboard( 2, expected, transform=_extract_ma_note_keys )

    # test multi-applicable notes for German vehicles
    do_test( 1, "german", "vehicles",
        [], []
    )
    do_test( 1, "german", "vehicles",
        [ "a german vehicle" ],
        [ "A", "B" ]
    )
    do_test( 1, "german", "vehicles",
        [ "a german vehicle", "another german vehicle" ],
        [ "A", "B", "C", "b" ]
    )
    do_test( 1, "german", "vehicles",
        [ "a german vehicle", "another german vehicle", "one more german vehicle", "name only" ],
        [ "A", "B", "C", "b" ]
    )

    # test multi-applicable notes for Russian ordnance
    do_test( 2, "russian", "ordnance",
        [], []
    )
    do_test( 2, "russian", "ordnance",
        [ "a russian ordnance" ],
        [ "X", "Y" ]
    )
    do_test( 2, "russian", "ordnance",
        [ "another russian ordnance" ],
        [ "ZZ" ]
    )
    do_test( 2, "russian", "ordnance",
        [ "name only", "another russian ordnance", "a russian ordnance" ],
        [ "X", "Y", "ZZ" ]
    )

# ---------------------------------------------------------------------

def test_common_vo_notes( webapp, webdriver ):
    """Test handling of Allied/Axis Minor common vehicles/ordnance."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct: ct.set_vo_notes_dir( dtype="test" )
    )

    # load the test scenario
    load_scenario( {
        "PLAYER_1": "dutch",
        "OB_VEHICLES_1": [ { "name": "dutch vehicle" }, { "name": "common allied minor vehicle" } ],
        "OB_ORDNANCE_1": [ { "name": "dutch ordnance" }, { "name": "common allied minor ordnance" } ],
        "PLAYER_2": "romanian",
        "OB_VEHICLES_2": [ { "name": "romanian vehicle" }, { "name": "common axis minor vehicle" } ],
        "OB_ORDNANCE_2": [ { "name": "romanian ordnance" }, { "name": "common axis minor ordnance" } ],
    } )

    # check the snippets
    _check_vo_snippets( 1, "vehicles", [
        ( "dutch vehicle", "vehicles/dutch/note/1" ),
        ( "common allied minor vehicle", "vehicles/allied-minor/note/101" ),
    ] )
    _check_vo_snippets( 1, "ordnance", [
        ( "dutch ordnance", "ordnance/dutch/note/2" ),
        ( "common allied minor ordnance", "ordnance/allied-minor/note/102" ),
    ] )
    _check_vo_snippets( 2, "vehicles", [
        ( "romanian vehicle", "vehicles/romanian/note/3" ),
        ( "common axis minor vehicle", "vehicles/axis-minor/note/103" ),
    ] )
    _check_vo_snippets( 2, "ordnance", [
        ( "romanian ordnance", "ordnance/romanian/note/4" ),
        ( "common axis minor ordnance", "ordnance/axis-minor/note/104" ),
    ] )

# ---------------------------------------------------------------------

def test_extra_ma_notes( webapp, webdriver ):
    """Test handling of Landing Craft and Allied/Axis Minor common vehicles/ordnance."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct: ct.set_vo_notes_dir( dtype="test" )
    )

    # load the test scenario
    load_scenario( {
        "PLAYER_1": "dutch",
        "OB_VEHICLES_1": [ { "name": "dutch vehicle" }, { "name": "common allied minor vehicle" } ],
        "OB_ORDNANCE_1": [ { "name": "dutch ordnance" }, { "name": "common allied minor ordnance" } ],
        "PLAYER_2": "romanian",
        "OB_VEHICLES_2": [ { "name": "romanian vehicle" }, { "name": "common axis minor vehicle" } ],
        "OB_ORDNANCE_2": [ { "name": "romanian ordnance" }, { "name": "common axis minor ordnance" } ],
    } )

    # test Allied Minor vehicles/ordnance
    select_tab( "ob1" )
    btn = find_child( "button.generate[data-id='ob_vehicles_ma_notes_1']" )
    btn.click()
    wait_for_clipboard( 2, [
        ( "A", 'Dutch Multi-Applicable Vehicle Note "A".' ),
        ( "Du", 'Allied Minor Multi-Applicable Vehicle Note "Du".' ),
    ], transform=_extract_ma_notes )
    btn = find_child( "button.generate[data-id='ob_ordnance_ma_notes_1']" )
    btn.click()
    wait_for_clipboard( 2, [
        ( "A", 'Dutch Multi-Applicable Ordnance Note "A".' ),
        ( "Du", 'Allied Minor Multi-Applicable Ordnance Note "Du".' ),
    ], transform=_extract_ma_notes )

    # test Axis Minor vehicles/ordnance
    select_tab( "ob2" )
    btn = find_child( "button.generate[data-id='ob_vehicles_ma_notes_2']" )
    btn.click()
    wait_for_clipboard( 2, [
        ( "A", 'Romanian Multi-Applicable Vehicle Note "A".' ),
        ( "Ro", 'Axis Minor Multi-Applicable Vehicle Note "Ro".' ),
    ], transform=_extract_ma_notes )
    btn = find_child( "button.generate[data-id='ob_ordnance_ma_notes_2']" )
    btn.click()
    wait_for_clipboard( 2, [
        ( "A", 'Romanian Multi-Applicable Ordnance Note "A".' ),
        ( "Ro", 'Axis Minor Multi-Applicable Ordnance Note "Ro".' ),
    ], transform=_extract_ma_notes )

    # test Landing Craft
    load_scenario( {
        "PLAYER_1": "american",
        "OB_VEHICLES_1": [ { "name": "M10 GMC" }, { "name": "landing craft" } ],
        "PLAYER_2": "japanese",
        "OB_VEHICLES_2": [ { "name": "japanese vehicle" }, { "name": "Daihatsu" } ],
    } )
    select_tab( "ob1" )
    btn = find_child( "button.generate[data-id='ob_vehicles_ma_notes_1']" )
    btn.click()
    wait_for_clipboard( 2, [
        ( "A", 'American Multi-Applicable Vehicle Note "A".' ),
        ( "N", "Unavailable." ),
        ( "Y", "Unavailable." ),
        "Landing Craft",
        ( "A", 'Landing Craft Multi-Applicable Note "A".' ),
    ], transform=_extract_ma_notes )
    select_tab( "ob2" )
    btn = find_child( "button.generate[data-id='ob_vehicles_ma_notes_2']" )
    btn.click()
    wait_for_clipboard( 2, [
        ( "A", 'Japanese Multi-Applicable Vehicle Note "A".' ),
        "Landing Craft",
        ( "B", 'Landing Craft Multi-Applicable Note "B".' ),
    ], transform=_extract_ma_notes )

# ---------------------------------------------------------------------

def test_update_ui( webapp, webdriver ):
    """Check that the UI is updated correctly for multi-applicable notes."""

    # initialize
    init_webapp( webapp, webdriver,
        reset = lambda ct: ct.set_vo_notes_dir( dtype="test" )
    )

    def do_test( nat, veh_expected, ord_expected ):
        """Do the test."""
        # set the specified player
        set_player( 1, nat )
        select_tab( "ob1" )
        # check that the Multi-Applicable Notes controls are visible/hidden
        fieldset = find_child( "#tabs-ob1 fieldset[name='ob_vehicles_1']" )
        assert find_child( ".snippets-notes", fieldset ).is_displayed() == veh_expected
        assert find_child( "label[for='ob']", fieldset ).is_displayed() == veh_expected
        fieldset = find_child( "#tabs-ob1 fieldset[name='ob_ordnance_1']" )
        assert find_child( ".snippets-notes", fieldset ).is_displayed() == ord_expected
        assert find_child( "label[for='ob']", fieldset ).is_displayed() == ord_expected
        # the OB snippet controls should always be visible
        assert find_child( ".snippets-ob", fieldset ).is_displayed()

    # do the tests
    do_test( "german", True, True )
    do_test( "russian", True, True )
    do_test( "british", True, False )
    do_test( "french", False, True )
    do_test( "finnish", False, False )
    do_test( "dutch", True, True ) # nb: because they are Allied Minor
    do_test( "romanian", True, True ) # nb: because they are Axis Minor

# ---------------------------------------------------------------------

def test_seq_ids( webapp, webdriver ):
    """Test handling of vehicle/ordnance sequence ID's."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct: ct.set_vo_notes_dir( dtype="test" )
    )

    # load the test scenario
    load_scenario( {
        "PLAYER_1": "german",
        "OB_VEHICLES_1": [ { "name": "a german vehicle" }, { "name": "another german vehicle" } ]
    } )
    select_tab( "ob1" )
    sortable = find_child( "#ob_vehicles-sortable_1" )

    def check_seq_ids( expected ): #pylint: disable=missing-docstring
        entries = find_children( "li", sortable )
        assert len(entries) == len(expected)
        for i,entry in enumerate(entries):
            data = webdriver.execute_script( "return $(arguments[0]).data('sortable2-data')", entry )
            assert expected[i] == ( data["caption"], data["id"] )

    # check the initial seq ID's (nb: they weren't in the loaded scenario, so they should have been auto-assigned)
    check_seq_ids( [
        ( "a german vehicle", 1 ),
        ( "another german vehicle", 2 ),
    ] )

    # add another vehicle
    add_vo( webdriver, "vehicles", 1, "one more german vehicle" )
    check_seq_ids( [
        ( "a german vehicle", 1 ),
        ( "another german vehicle", 2 ),
        ( "one more german vehicle", 3 ),
    ] )

    # delete the 2nd vehicle
    delete_vo( "vehicles", 1, "another german vehicle", webdriver )
    check_seq_ids( [
        ( "a german vehicle", 1 ),
        ( "one more german vehicle", 3 ),
    ] )

    # add another vehicle
    add_vo( webdriver, "vehicles", 1, "name only" )
    check_seq_ids( [
        ( "a german vehicle", 1 ),
        ( "one more german vehicle", 3 ),
        ( "name only", 2 ), # nb: this seq ID gets re-used
    ] )

    # make sure the seq ID's are saved out
    saved_scenario = save_scenario()
    entries = [
        ( veh["name"], veh.get("seq_id") )
        for veh in saved_scenario[ "OB_VEHICLES_1" ]
    ]
    assert entries == [
        ( "a german vehicle", 1 ),
        ( "one more german vehicle", 3 ),
        ( "name only", 2 ),
    ]

# ---------------------------------------------------------------------

def test_special_cases( webapp, webdriver ):
    """Test special cases."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct: ct.set_vo_notes_dir( dtype="test" )
    )

    # check that Italian Multi-Applicable Ordnance (only) Note R has a line-through
    load_scenario( {
        "PLAYER_1": "italian",
        "OB_ORDNANCE_1": [ { "name": "Cannone-aa da 90/53" } ],
        "OB_VEHICLES_1": [ { "name": "SMV L40 47/32" } ],
    } )
    select_tab( "ob1" )
    btn = find_child( "button.generate[data-id='ob_ordnance_ma_notes_1']" )
    btn.click()
    wait_for_clipboard( 2, ["N","<s>R</s>"], transform=_extract_ma_note_keys )
    btn = find_child( "button.generate[data-id='ob_vehicles_ma_notes_1']" )
    btn.click()
    wait_for_clipboard( 2, ["N","R"], transform=_extract_ma_note_keys )

# ---------------------------------------------------------------------

@pytest.mark.skipif(
    not pytest.config.option.vo_notes, #pylint: disable=no-member
    reason = "--vo-notes not specified"
) #pylint: disable=too-many-locals,too-many-branches
# NOTE: The expected output files contain pieces from the supported extensions,
# so the VASL extensions directory must be loaded.
@pytest.mark.skipif(
    not pytest.config.option.vasl_extensions, #pylint: disable=no-member
    reason = "--vasl-extensions not specified"
    ) #pylint: disable=too-many-locals
def test_vo_notes_reports( webapp, webdriver ):
    """Check the vehicle/ordnance notes reports."""

    # initialize
    # NOTE: The server must be configured with the *real* Chapter H vehicle/ordnance notes.
    vo_notes_dir = pytest.config.option.vo_notes #pylint: disable=no-member
    init_webapp( webapp, webdriver,
        reset = lambda ct:
            ct.set_data_dir( dtype="real" ) \
              .set_vasl_mod( vmod="random", extns_dtype="real" ) \
              .set_vo_notes_dir( dtype="real" )
    )

    # initialize
    check_dir = os.path.join( vo_notes_dir, "tests/" )
    save_dir = None # nb: define this to save the generated reports

    # initialize
    if save_dir and os.path.isdir(save_dir):
        shutil.rmtree( save_dir )

    # check each nationality's multi-applicable notes
    nationalities = list( get_nationalities( webapp ).keys() )
    nationalities.extend( [ "allied-minor", "axis-minor", "landing-craft" ] )
    for nat in nationalities:
        for vo_type in ["vehicles","ordnance"]:

            # get the next report
            vo_notes, ma_notes, keys = get_vo_notes_report( webapp, webdriver, nat, vo_type )
            if nat in ("burmese","filipino") or (nat,vo_type) in [("landing-craft","ordnance"),("anzac","ordnance")]:
                assert not vo_notes and not ma_notes and not keys
                continue

            # convert the report to plain-text
            buf = io.StringIO()
            print( "=== {}/{} ===".format( nat, vo_type ), file=buf )
            print( "", file=buf )
            if not vo_notes:
                print( "No vehicle/ordnance notes found.", file=buf )
            else:
                for vo_note in vo_notes:
                    print( "{}: {}".format( vo_note[0], vo_note[1]), file=buf )
            print( "", file=buf )
            if not ma_notes:
                print( "No multi-applicable notes found.", file=buf )
                print( "", file=buf )
            else:
                for ma_note in ma_notes:
                    print( "--- {} ---".format( ma_note[0] ), file=buf )
                    print( ma_note[1], file=buf )
                    print( "", file=buf )
            print(
                tabulate.tabulate( keys, headers="firstrow", numalign="left" ),
                file = buf
            )
            report = buf.getvalue()

            # check if we should save the report
            fname = "{}/{}.txt".format( nat, vo_type )
            if save_dir:
                fname2 = os.path.join( save_dir, fname )
                os.makedirs( os.path.split(fname2)[0], exist_ok=True )
                with open( os.path.join(save_dir,fname2), "w", encoding="utf-8" ) as fp:
                    fp.write( report )

            # check the report
            fname = os.path.join( check_dir, fname )
            assert open( fname, "r", encoding="utf-8" ).read() == report

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def get_vo_notes_report( webapp, webdriver, nat, vo_type ):
    """Get a vehicle/ordnance notes report.

    NOTE: We can't get the report to return its results as, say, plain-text, for easy checking,
    since it's all done in Javascript, asynchronously i.e. we need something that will wait until
    the results are ready i.e. Selenium, not wget :-/
    """

    # initialize
    url = webapp.url_for( "get_vo_notes_report", nat=nat, vo_type=vo_type )
    webdriver.get( url )
    wait_for( 2, lambda: find_child("#results").is_displayed() )

    # parse the report
    vo_notes, ma_notes, keys = _parse_report( webdriver.page_source )

    return vo_notes, ma_notes, keys

def _parse_report( buf ):
    """Parse a multi-applicable notes report."""

    def tidy( cell ):
        """Tidy up a cell value."""
        val = lxml.etree.tostring( cell ).decode( "utf-8" ) #pylint: disable=c-extension-no-member
        if re.search( r"^<(td|th)[^>]*/>", val ):
            return ""
        mo = re.search( r"^<(th|td|div).*?>(.*)</\1>$", val, re.DOTALL )
        val = mo.group(2)
        val = val.replace( "&#8224;", "\u2020" ).replace( "&#174;", "\u00ae" )
        val = val.replace( "&#8804;", "&le;" ).replace( "&#8805;", "&ge;" )
        val = val.replace( "&#176;", "&deg;" )
        val = val.replace( "&#8734;", "&infin;" )
        val = val.replace( "&#228;", "&auml;" ).replace( "&#235;", "&euml;" ).replace( "&#252;", "&uml;" )
        val = val.replace( "&#188;", "&frac14;" ).replace( "&#189;", "&frac12;" ).replace( "&#190;", "&frac34;" )
        val = re.sub(
            r"<sup>(.*?)</sup>",
            lambda mo: "[{}]".format( mo.group(1) ),
            val
        )
        return val.strip()

    # NOTE: Getting each table cell via Selenium is insanely slow - we parse the HTML manually :-/
    doc = lxml.html.fromstring( buf )

    # extract the vehicle/ordnance notes
    vo_notes = []
    for row in doc.xpath( "//table[@id='vo-notes']//tr" ):
        cells = row.xpath( ".//td" )
        assert len(cells) == 2
        key = tidy( cells[0] )
        if key.endswith( ":" ):
            key = key[:-1]
        content = tidy( cells[1] )
        vo_notes.append( ( key, content ) )

    # extract the multi-applicable notes
    ma_notes = []
    for row in doc.xpath( "//div[@class='ma-note']" ):
        cells = row.xpath( ".//div[@class='key']" )
        assert len(cells) == 1
        key = tidy( cells[0] )
        assert key.endswith( ":" )
        key = key[:-1]
        cells = row.xpath( ".//div[@class='content']" )
        assert len(cells) == 1
        content = tidy( cells[0] )
        ma_notes.append( ( key, content ) )

    # extract the keys report
    keys = []
    for row in doc.xpath( "//table[@id='vo-entries']//tr" ):
        tag = "td" if keys else "th"
        cells = row.xpath( ".//{}".format( tag ) )
        assert len(cells) == 7
        keys.append( list( tidy(c) for c in cells ) )

    return vo_notes, ma_notes, keys

# ---------------------------------------------------------------------

def _extract_ma_note_keys( snippet ):
    """Extract the multi-applicable note keys in a snippet."""
    matches = re.finditer( r"<span class='key'>(.+):</span>", snippet )
    return [ mo.group(1) for mo in matches ]

def _extract_ma_notes( snippet ):
    """Extract the multi-applicable notes in a snippet."""
    mo = re.search( "=== ([^=]+) ===", snippet )
    if mo:
        caption = mo.group(1).strip()
        pos = mo.start(1)
    else:
        caption, pos = None, None
    ma_notes = []
    for mo in re.finditer( r"<span class='key'>(.+):</span> (.*)$", snippet, re.MULTILINE ):
        if caption and mo.start() > pos:
            ma_notes.append( caption )
            caption = pos = None
        ma_notes.append( ( mo.group(1), mo.group(2).strip() ) )
    return ma_notes

# ---------------------------------------------------------------------

def _check_vo_snippets( player_no, vo_type, expected ):
    """Generate and check vehicle/ordnance snippets."""
    select_tab( "ob{}".format( player_no ) )
    sortable = find_child( "#ob_{}-sortable_{}".format( vo_type, player_no ) )
    elems = find_children( "li", sortable )
    assert len(elems) == len(expected)
    for i,elem in enumerate(elems):
        btn = find_child( "img.snippet", elem )
        if expected[i]:
            btn.click()
            wait_for_clipboard( 2, expected[i], transform=_extract_vo_note )
        else:
            assert btn is None

def _extract_vo_note( clipboard ):
    """Extract the details from a vehicle/ordnance note snippet."""
    mo = re.search( "^(.+?): http://.+?/(.*)$", clipboard )
    return ( mo.group(1), mo.group(2) )
