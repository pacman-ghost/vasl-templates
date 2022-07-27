""" Test generating vehicle/ordnance snippets. """

import os
import re
import json

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.tests import pytest_options
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario, save_scenario
from vasl_templates.webapp.tests.utils import \
    init_webapp, get_nationalities, select_tab, set_template_params, find_child, find_children, \
    wait_for_clipboard, click_dialog_button, select_menu_option, set_player, \
    set_stored_msg_marker, get_stored_msg, get_sortable_vo_names
from vasl_templates.webapp.config.constants import DATA_DIR

# ---------------------------------------------------------------------

def test_crud( webapp, webdriver ):
    """Test basic create/read/update/delete of vehicles/ordnance."""

    # initialize
    init_webapp( webapp, webdriver )

    # initialize
    _expected = {
        ("vehicles",1): [], ("ordnance",1): [],
        ("vehicles",2): [], ("ordnance",2): []
    }
    _width = {
        ("vehicles",1): None, ("ordnance",1): None,
        ("vehicles",2): None, ("ordnance",2): None
    }

    def _add_vo( vo_type, player_no, name ):
        """Add a vehicle/ordnance."""
        # check the hint
        select_tab( "ob{}".format( player_no ) )
        _check_hint( vo_type, player_no )
        # add the vehicle/ordnance
        add_vo( webdriver, vo_type, player_no, name )
        _expected[ (vo_type,player_no) ].append( name )
        # check the snippet and hint
        _check_snippet( vo_type, player_no )
        _check_hint( vo_type, player_no )

    def _delete_vo( vo_type, player_no, name, webdriver ):
        """Delete a vehicle/ordnance."""
        # check the hint
        select_tab( "ob{}".format( player_no ) )
        _check_hint( vo_type, player_no )
        # delete the vehicle/ordnance
        delete_vo( vo_type, player_no, name, webdriver )
        _expected[ (vo_type,player_no) ].remove( name )
        # check the snippet and hint
        _check_snippet( vo_type, player_no )
        _check_hint( vo_type, player_no )

    def _set_width( vo_type, player_no, width ):
        """Set the snippet width."""
        select_tab( "ob{}".format( player_no ) )
        elem = find_child( "input[name='OB_{}_WIDTH_{}']".format( vo_type.upper(), player_no ) )
        elem.clear()
        if width is not None:
            elem.send_keys( str(width) )
        _width[ (vo_type,player_no) ] = width

    def _check_snippet( vo_type, player_no ):
        """Check the generated vehicle/ordnance snippet."""
        # check the snippet
        select_tab( "ob{}".format( player_no ) )
        btn = find_child( "button[data-id='ob_{}_{}']".format( vo_type, player_no ) )
        btn.click()
        def reformat( clipboard ): #pylint: disable=missing-docstring
            return [
                mo.group(1)
                for mo in re.finditer( r"^\[\*\] (.*):" , clipboard, re.MULTILINE )
            ]
        clipboard = wait_for_clipboard( 2, _expected[(vo_type,player_no)], transform=reformat )
        # check the snippet width
        expected = _width[ (vo_type,player_no) ]
        mo = re.search(
            r"width={}$".format( expected if expected else "" ),
            clipboard,
            re.MULTILINE
        )
        assert mo

    def _check_hint( vo_type, player_no ):
        """Check the hint visibility."""
        hint = find_child( "#ob_{}-hint_{}".format( vo_type, player_no ) )
        expected = "none" if _expected[(vo_type,player_no)] else "block"
        assert hint.value_of_css_property("display") == expected

    def do_test( vo_type ):
        """Run the test."""
        vo_type0 = vo_type[:-1] if vo_type.endswith("s") else vo_type
        # add a German vehicle/ordnance
        _add_vo( vo_type, 1, "a german {}".format(vo_type0) )
        # generate a Russian vehicle/ordnance snippet
        _check_snippet( vo_type, 2 )
        # add a Russian vehicle/ordnance
        _add_vo( vo_type, 2, "another russian {}".format(vo_type0) )
        # go back and check the German snippet again
        _check_snippet( vo_type, 1 )
        # add another Russian vehicle/ordnance
        _set_width( vo_type, 2, "200px" )
        _add_vo( vo_type, 2, "name only" )
        # delete the German vehicle/ordnance
        _set_width( vo_type, 1, "100px" )
        _delete_vo( vo_type, 1, "a german {}".format(vo_type0), webdriver )
        _set_width( vo_type, 1, None )
        _check_snippet( vo_type, 1 )
        # go back and check the Russian snippet again
        _check_snippet( vo_type, 2 )
        # delete the Russian vehicles/ordnance
        _delete_vo( vo_type, 2, "another russian {}".format(vo_type0), webdriver )
        _set_width( vo_type, 2, None )
        _delete_vo( vo_type, 2, "name only", webdriver )
        # check the final state
        assert not _expected[ (vo_type,1) ]
        assert not _expected[ (vo_type,2) ]

    # do the test
    do_test( "vehicles" )
    do_test( "ordnance" )

# ---------------------------------------------------------------------

def test_snippets( webapp, webdriver ):
    """Test vehicle/ordnance snippet generation in detail."""

    # initialize
    init_webapp( webapp, webdriver )

    def do_test( vo_type ):
        """Run the test."""
        vo_type0 = vo_type[:-1] if vo_type.endswith("s") else vo_type
        # test a full example
        add_vo( webdriver, vo_type, 1, "a german {}".format(vo_type0) )
        btn = find_child( "button[data-id='ob_{}_1']".format( vo_type ) )
        btn.click()
        caps = '"XYZ" "IR" "A1" "H2"'
        if vo_type == "vehicles":
            caps += ' "CS 5"'
        expected = [
            '[German] ; width=',
            '[*] a german {}: #=1'.format( vo_type0 ),
            '- notes: "A" "B†"',
            '- capabilities: {}'.format( caps ),
            '- raw capabilities: {}'.format( caps ),
        ]
        wait_for_clipboard( 2, "\n".join(expected) )
        delete_vo( vo_type, 1, "a german {}".format(vo_type0), webdriver )

        # test a partial example
        add_vo( webdriver, vo_type, 1, "another german {}".format(vo_type0) )
        btn = find_child( "button[data-id='ob_{}_1']".format( vo_type ) )
        btn.click()
        caps = '"XYZ"'
        if vo_type == "vehicles":
            caps += ' "<span class=\'brewup\'>cs 4</span>"'
        expected = [
            '[German] ; width=',
            '[*] another german {}: #=2'.format( vo_type0 ),
            '- capabilities: {}'.format( caps ),
            '- raw capabilities: {}'.format( caps ),
        ]
        if vo_type == "vehicles":
            expected.insert( 2, '- notes: "<s>b</s>" "C"' )
        wait_for_clipboard( 2, "\n".join(expected) )
        delete_vo( vo_type, 1, "another german {}".format(vo_type0), webdriver )

        # test a minimal example
        add_vo( webdriver, vo_type, 1, "name only" )
        btn = find_child( "button[data-id='ob_{}_1']".format( vo_type ) )
        btn.click()
        expected = [
            '[German] ; width=',
            '[*] name only: #=',
            '- capabilities:',
            '- raw capabilities:',
        ]
        wait_for_clipboard( 2, "\n".join(expected) )

    # do the test
    set_player( 1, "german" )
    do_test( "vehicles" )
    do_test( "ordnance" )

# ---------------------------------------------------------------------

def test_variable_capabilities( webapp, webdriver ):
    """Test date-based variable capabilities."""

    # initialize
    init_webapp( webapp, webdriver )

    # add a vehicle
    add_vo( webdriver, "vehicles", 2, "Churchill III(b)" )

    # change the scenario date and check the generated snippet
    vehicles2 = find_child( "button.generate[data-id='ob_vehicles_2']" )
    def do_test( month, year, expected ):
        """Set the date and check the vehicle snippet."""
        select_tab( "scenario" )
        set_template_params( { "SCENARIO_DATE": "{:02d}/01/{}".format(month,year) } )
        select_tab( "ob2" )
        vehicles2.click()
        def reformat( clipboard ): #pylint: disable=missing-docstring
            mo = re.search( r"^- capabilities: (.*)$", clipboard, re.MULTILINE )
            return mo.group( 1 )
        wait_for_clipboard( 2, expected, transform=reformat )
    do_test( 1, 1940, '"sM8\u2020" "CS 7"' )
    do_test( 1, 1943, '"sM8\u2020" "CS 7"' )
    do_test( 2, 1943, '"HE7\u2020" "sM8\u2020" "CS 7"' )
    do_test( 12, 1943, '"HE7\u2020" "sM8\u2020" "CS 7"' )
    do_test( 1, 1944, '"HE8\u2020" "sD6" "sM8\u2020" "CS 7"' )
    do_test( 5, 1944, '"HE8\u2020" "sD6" "sM8\u2020" "CS 7"' )
    do_test( 6, 1944, '"D6\u2020" "HE8\u2020" "sD6" "sM8\u2020" "CS 7"' )
    do_test( 12, 1944, '"D6\u2020" "HE8\u2020" "sD6" "sM8\u2020" "CS 7"' )
    do_test( 1, 1945, '"D7\u2020" "HE8\u2020" "sD6" "sM8\u2020" "CS 7"' )
    do_test( 12, 1945, '"D7\u2020" "HE8\u2020" "sD6" "sM8\u2020" "CS 7"' )
    do_test( 1, 1946, '"HE8\u2020" "sD6" "sM8\u2020" "CS 7"' )

# ---------------------------------------------------------------------

def test_html_names( webapp, webdriver ):
    """Test handling of vehicles/ordnance that have HTML in their name."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver )

    def get_available_ivfs():
        """Get the PzKw IVF's available for selection."""
        entries = find_children( "#select-vo .select2-results li" )
        entries = [ e.text for e in entries ]
        return [ e for e in entries if "IVF" in e ]

    # start to add a vehicle - make sure the two PzKw IVF's are available
    set_player( 1, "german" )
    select_tab( "ob1" )
    add_vehicle_btn = find_child( "#ob_vehicles-add_1" )
    add_vehicle_btn.click()
    assert get_available_ivfs() == [ "PzKpfw IVF1 (MT)", "PzKpfw IVF2 (MT)" ]

    # add the PzKw IVF2
    elem = find_child( ".ui-dialog .select2-search__field" )
    elem.send_keys( "IVF2" )
    elem.send_keys( Keys.RETURN )

    # make sure it was added to the player's OB
    vehicles_sortable = find_child( "#ob_vehicles-sortable_1" )
    assert get_sortable_vo_names( vehicles_sortable ) == [ "PzKpfw IVF2" ]

    # start to add another vehicle - make sure both PzKw IVF's are still available
    add_vehicle_btn.click()
    assert get_available_ivfs() == [ "PzKpfw IVF1 (MT)", "PzKpfw IVF2 (MT)" ]

    # add the PzKw IVF1
    elem = find_child( ".ui-dialog .select2-search__field" )
    elem.send_keys( "IVF1" )
    elem.send_keys( Keys.RETURN )

    # make sure it was added to the player's OB
    assert get_sortable_vo_names( vehicles_sortable ) == [ "PzKpfw IVF2", "PzKpfw IVF1" ]

    # start to add another vehicle - make sure both PzKw IVF's are still available
    add_vehicle_btn.click()
    assert get_available_ivfs() == [ "PzKpfw IVF1 (MT)", "PzKpfw IVF2 (MT)" ]
    elem = find_child( ".ui-dialog .select2-search__field" )
    elem.send_keys( Keys.ESCAPE )

    # delete the PzKw IVF2
    delete_vo( "vehicles", 1, "PzKpfw IVF2" , webdriver )

    # start to add another vehicle - make sure both PzKw IVF's are still available
    add_vehicle_btn.click()
    assert get_available_ivfs() == [ "PzKpfw IVF1 (MT)", "PzKpfw IVF2 (MT)" ]

# ---------------------------------------------------------------------

def test_duplicate_vo_entries( webapp, webdriver ):
    """Test adding duplicate vehicles/ordnance."""

    # initialize
    init_webapp( webapp, webdriver )
    set_player( 1, "german" )
    select_tab( "ob1" )

    def get_available_vo_entries():
        """Get the available vehicles/ordnance for selection."""
        entries = find_children( "#select-vo .select2-results li" )
        return [ e.text for e in entries ]

    def do_test( vo_type, vo_name ): #pylint: disable=missing-docstring

        # start to add a vehicle/ordnance
        add_btn = find_child( "#ob_" + vo_type + "-add_1" )
        add_btn.click()
        assert vo_name in get_available_vo_entries()

        # add the vehicle/ordnance
        elem = find_child( ".ui-dialog .select2-search__field" )
        elem.send_keys( vo_name )
        elem.send_keys( Keys.RETURN )

        # make sure it was added to the player's OB
        sortable = find_child( "#ob_" + vo_type + "-sortable_1" )
        assert get_sortable_vo_names( sortable ) == [ vo_name ]

        # add the vehicle/ordnance, dismiss the warning
        add_btn.click()
        elem = find_child( ".ui-dialog .select2-search__field" )
        elem.send_keys( vo_name )
        elem.send_keys( Keys.RETURN )
        elem = find_child( "#ask" )
        assert "already in the OB" in elem.text
        click_dialog_button( "Cancel" )
        click_dialog_button( "Cancel" )

        # make sure the player's OB is unchanged
        assert get_sortable_vo_names( sortable ) == [ vo_name ]

        # add the vehicle/ordnance, accept the warning
        add_btn.click()
        elem = find_child( ".ui-dialog .select2-search__field" )
        elem.send_keys( vo_name )
        elem.send_keys( Keys.RETURN )
        elem = find_child( "#ask" )
        assert "already in the OB" in elem.text
        click_dialog_button( "OK" )

        # make sure the vehicle/ordnance was added to the player's OB
        assert get_sortable_vo_names( sortable ) == [ vo_name, vo_name ]

    # do the test
    do_test( "vehicles", "a german vehicle" )
    do_test( "ordnance", "name only" )

# ---------------------------------------------------------------------

@pytest.mark.skipif( pytest_options.short_tests, reason="--short-tests specified" )
def test_common_vo( webapp, webdriver ): #pylint: disable=too-many-locals
    """Test loading of common vehicles/ordnance and landing craft."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver )

    # initialize
    ALLIED_MINOR = [ "belgian", "danish", "dutch", "greek", "polish", "yugoslavian" ]
    AXIS_MINOR = [ "bulgarian", "croatian", "hungarian", "romanian", "slovakian" ]

    # get the common vehicles/ordnance
    def get_common_vo( fname ):
        """Get the vehicle/ordnance information from the specified file."""
        fname = os.path.join( DATA_DIR, fname )
        with open( fname, "r", encoding="utf-8" ) as fp:
            data = json.load( fp )
        def get_gpid( val ): #pylint: disable=missing-docstring
            if isinstance( val, list ):
                val = val[0]
            assert isinstance(val,int) or val is None
            return val
        return [ ( vo["name"], get_gpid(vo["gpid"]) ) for vo in data ]
    common_vo = {
        "vehicles": {
            "allied": get_common_vo( "vehicles/allied-minor/common.json" ),
            "axis": get_common_vo( "vehicles/axis-minor/common.json" ),
        },
        "ordnance": {
            "allied": get_common_vo( "ordnance/allied-minor/common.json" ),
            "axis": get_common_vo( "ordnance/axis-minor/common.json" ),
        },
    }
    landing_craft = get_common_vo( "vehicles/landing-craft.json" )

    tidy_vo_name_regex = re.compile( r" \([A-Za-z]+\)$" ) # nb: removes the trailing vehicle/ordnance type
    gpid_regex = re.compile( r"/counter/(\d+)/front" )
    def get_vo_entry( elem ):
        """Get the vehicle/ordnance information from the Selenium element."""
        vo_name = tidy_vo_name_regex.sub( "", elem.text )
        image_url = find_child( "img", elem ).get_attribute( "src" )
        mo = gpid_regex.search( image_url )
        return ( vo_name, int(mo.group(1)) if mo else None )

    def is_valid_vo_entry( vo_entry ):
        """Check if a V/O entry is valid."""
        return isinstance( vo_entry, tuple ) and len(vo_entry) == 2 \
               and isinstance( vo_entry[0], str ) \
               and isinstance( vo_entry[1], (int,type(None)) )
    def is_same_vo( lhs, rhs ):
        """Check if two V/O entries are the same."""
        assert is_valid_vo_entry(lhs) and is_valid_vo_entry(rhs)
        return lhs == rhs
    def is_vo_entry_in_list( vo_entry, vo_entries ):
        """Check if a V/O entry appears in a list of V/O entries."""
        assert is_valid_vo_entry( vo_entry )
        return any( is_same_vo(vo_entry,e) for e in vo_entries )

    # check the vehicles/ordnance for each nationality
    nationalities = get_nationalities( webapp )
    for nat in nationalities: #pylint: disable=too-many-nested-blocks

        # select the next nationality
        set_player( 1, nat )

        select_tab( "ob1" )
        for vo_type in ("vehicles","ordnance"):

            # check if the nationality has any vehicles/ordnance
            elem = find_child( "#ob_{}-add_1".format( vo_type ) )
            if nat in ["thai","indonesian","anzac","burmese","filipino","partisan"]:
                assert not elem.is_displayed()
                continue
            if (nat, vo_type) in [ ("kfw-cpva","vehicles"), ("swedish","vehicles") ]:
                assert not elem.is_displayed()
                continue
            elem.click()

            # get the vehicles/ordnance
            vo_entries = find_children( "#select-vo .select2-results li" )
            vo_entries = [ get_vo_entry(e) for e in vo_entries ]
            click_dialog_button( "Cancel" )

            # check that the common vehicles/ordnance are present/absent
            if nat in ALLIED_MINOR:
                assert all(
                    is_vo_entry_in_list( vo_entry, vo_entries )
                    for vo_entry in common_vo[vo_type]["allied"]
                )
            elif nat in AXIS_MINOR:
                assert all(
                    is_vo_entry_in_list( vo_entry, vo_entries )
                    for vo_entry in common_vo[vo_type]["axis"]
                )
            else:
                assert all(
                    not is_vo_entry_in_list( vo_entry, vo_entries )
                    for vo_entry in common_vo[vo_type]["allied"]
                )
                assert all(
                    not is_vo_entry_in_list( vo_entry, vo_entries )
                    for vo_entry in common_vo[vo_type]["axis"]
                )

            # check that the landing craft are present/absent
            if vo_type == "vehicles":
                if nat in ("british","american"):
                    for vo_entry in landing_craft:
                        if vo_entry[0] in ("Daihatsu","Shohatsu"):
                            assert not is_vo_entry_in_list( vo_entry, vo_entries )
                        else:
                            assert is_vo_entry_in_list( vo_entry, vo_entries )
                elif nat == "japanese":
                    for vo_entry in landing_craft:
                        if vo_entry[0] in ("Daihatsu","Shohatsu"):
                            assert is_vo_entry_in_list( vo_entry, vo_entries )
                        else:
                            assert not is_vo_entry_in_list( vo_entry, vo_entries )
                else:
                    assert all(
                        not is_vo_entry_in_list( vo_entry, vo_entries )
                        for vo_entry in landing_craft
                    )

# ---------------------------------------------------------------------

def test_vo_images( webapp, webdriver ): #pylint: disable=too-many-statements
    """Test handling of vehicles/ordnance that have multiple images."""

    # initialize
    webapp.control_tests \
        .set_data_dir( "{REAL}" ) \
        .set_vasl_version( "random", None )
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    def check_sortable2_entries( player_no, expected ):
        """Check the settings on the player's vehicles."""
        entries = find_children( "#ob_vehicles-sortable_{} li".format( player_no ) )
        for i,entry in enumerate(entries):
            # check the displayed image
            elem = find_child( "img", entry )
            assert elem.get_attribute( "src" ).endswith( expected[i][0] )
            # check the attached data
            data = webdriver.execute_script( "return $(arguments[0]).data('sortable2-data')", entry )
            assert data["vo_entry"]["id"] == expected[i][1]
            assert data["vo_image_id"] == expected[i][2]

    def check_save_scenario( player_no, expected ):
        """Check the vo_entry and vo_image_id fields are saved correctly."""
        data = save_scenario()
        assert data[ "OB_VEHICLES_{}".format(player_no) ] == expected
        return data

    # start to add a PzKw VIB
    set_player( 1, "german" )
    select_tab( "ob1" )
    add_vehicle_btn = find_child( "#ob_vehicles-add_1" )
    add_vehicle_btn.click()
    search_field = find_child( ".ui-dialog .select2-search__field" )
    search_field.send_keys( "VIB" )

    # make sure there is only 1 image available
    elem = find_child( "#select-vo .select2-results li img[class='vasl-image']" )
    assert elem.get_attribute( "src" ).endswith( "/counter/2602/front" )
    vo_images = webdriver.execute_script( "return $(arguments[0]).data('vo-images')", elem )
    assert vo_images is None
    assert not find_child( "#select-vo .select2-results li input.select-vo-image" )

    # add the PzKw VIB, make sure the sortable2 entry has its data set correctly
    search_field.send_keys( Keys.RETURN )
    check_sortable2_entries( 1, [
        ( "/counter/2602/front", "ge/v:035", None )
    ] )

    # check that the vehicles are saved correctly
    check_save_scenario( 1, [
        { "id": "ge/v:035", "name": "PzKpfw VIB", "seq_id": 1 },
    ] )

    # start to add a PzKw IVH (this has multiple GPID's)
    add_vehicle_btn.click()
    search_field = find_child( ".ui-dialog .select2-search__field" )
    search_field.send_keys( "IVH" )

    # make sure multiple images are available
    elem = find_child( "#select-vo .select2-results li img[class='vasl-image']" )
    assert elem.get_attribute( "src" ).endswith( "/counter/2584/front" )
    vo_images = webdriver.execute_script( "return $(arguments[0]).data('vo-images')", elem )
    assert vo_images == [ [2584,0], [2586,0], [2807,0], [2809,0] ]
    assert find_child( "#select-vo .select2-results li input.select-vo-image" )

    # add the PzKw IVH, make sure the sortable2 entry has its data set correctly
    search_field.send_keys( Keys.RETURN )
    check_sortable2_entries( 1, [
        ( "/counter/2602/front", "ge/v:035", None ),
        ( "/counter/2584/front", "ge/v:027", None ) # nb: there is no V/O image ID if it's not necessary
    ] )

    # check that the vehicles are saved correctly
    check_save_scenario( 1, [
        { "id": "ge/v:035", "name": "PzKpfw VIB", "seq_id": 1 },
        { "id": "ge/v:027", "name": "PzKpfw IVH", "seq_id": 2 }, # nb: there is no V/O image ID if it's not necessary
    ] )

    # delete the PzKw IVH
    delete_vo( "vehicles", 1, "PzKpfw IVH", webdriver )

    # add the PzKw IVH, with a different image, make sure the sortable2 entry has its data set correctly
    add_vehicle_btn.click()
    search_field = find_child( ".ui-dialog .select2-search__field" )
    search_field.send_keys( "IVH" )
    elem = find_child( "#select-vo .select2-results li img[class='vasl-image']" )
    assert elem.get_attribute( "src" ).endswith( "/counter/2584/front" )
    btn = find_child( "#select-vo .select2-results li input.select-vo-image" )
    btn.click()
    images = find_children( ".ui-dialog.select-vo-image .vo-images img" )
    assert len(images) == 4
    images[2].click()
    check_sortable2_entries( 1, [
        ( "/counter/2602/front", "ge/v:035", None ),
        ( "/counter/2807/front/0", "ge/v:027", [2807,0] )
    ] )

    # check that the vehicles are saved correctly
    check_save_scenario( 1, [
        { "id": "ge/v:035", "name": "PzKpfw VIB", "seq_id": 1 },
        { "id": "ge/v:027", "image_id": "2807/0", "name": "PzKpfw IVH", "seq_id": 2 },
    ] )

    # set the British as player 2
    set_player( 2, "british" )

    # start to add a 2pdr Portee (this has multiple images for a single GPID)
    select_tab( "ob2" )
    add_vehicle_btn = find_child( "#ob_vehicles-add_2" )
    add_vehicle_btn.click()
    search_field = find_child( ".ui-dialog .select2-search__field" )
    search_field.send_keys( "2pdr" )

    # make sure multiple images are available
    elem = find_child( "#select-vo .select2-results li img[class='vasl-image']" )
    assert elem.get_attribute( "src" ).endswith( "/counter/1555/front" )
    vo_images = webdriver.execute_script( "return $(arguments[0]).data('vo-images')", elem )
    assert vo_images == [ [1555,0], [1555,1] ]
    assert find_child( "#select-vo .select2-results li input.select-vo-image" )

    # add the 2pdr Portee, make sure the sortable2 entry has its data set correctly
    search_field.send_keys( Keys.RETURN )
    check_sortable2_entries( 2, [
        ( "/counter/1555/front", "br/v:115", None ) # nb: there is no V/O image ID if it's not necessary
    ] )

    # check that the vehicles are saved correctly
    check_save_scenario( 2, [
        { "id": "br/v:115", "name": "2pdr Portee", "seq_id": 1 }, # nb: there is no V/O image ID if it's not necessary
    ] )

    # delete the 2pdr Portee
    delete_vo( "vehicles", 2, "2pdr Portee", webdriver )

    # add the 2pdr Portee, with a different image, make sure the sortable2 entry has its data set correctly
    add_vehicle_btn.click()
    search_field = find_child( ".ui-dialog .select2-search__field" )
    search_field.send_keys( "2pdr" )
    elem = find_child( "#select-vo .select2-results li img[class='vasl-image']" )
    assert elem.get_attribute( "src" ).endswith( "/counter/1555/front" )
    btn = find_child( "#select-vo .select2-results li input.select-vo-image" )
    btn.click()
    images = find_children( ".ui-dialog.select-vo-image .vo-images img" )
    assert len(images) == 2
    images[1].click()
    check_sortable2_entries( 2, [
        ( "/counter/1555/front/1", "br/v:115", [1555,1] )
    ] )

    # check that the vehicles are saved correctly
    saved_scenario = check_save_scenario( 2, [
        { "id": "br/v:115", "image_id": "1555/1", "name": "2pdr Portee", "seq_id": 1 },
    ] )

    # reset the scenario
    select_menu_option( "new_scenario" )
    check_sortable2_entries( 1, [] )
    check_sortable2_entries( 2, [] )

    # load the last saved scenario, make sure the correct images are displayed
    load_scenario( saved_scenario )
    check_sortable2_entries( 1, [
        ( "/counter/2602/front", "ge/v:035", None ),
        ( "/counter/2807/front/0", "ge/v:027", ["2807",0] )
    ] )
    check_sortable2_entries( 2, [
        ( "/counter/1555/front/1", "br/v:115", ["1555",1] )
    ] )

# ---------------------------------------------------------------------

def test_change_vo_image( webapp, webdriver ):
    """Test changing a V/O image."""

    # initialize
    webapp.control_tests \
        .set_data_dir( "{REAL}" ) \
        .set_vasl_version( "random", None )
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # add an ISU-152
    set_player( 2, "russian" )
    add_vo( webdriver, "vehicles", 2, "ISU-152" )

    # save the scenario
    saved_scenario = save_scenario()
    assert saved_scenario["OB_VEHICLES_2"] ==  [ { "id": "ru/v:049", "name": "ISU-152", "seq_id": 1 } ]

    # change the vehicle's image
    vehicles_sortable = find_child( "#ob_vehicles-sortable_2" )
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 1
    ActionChains(webdriver).double_click( elems[0] ).perform()
    img = find_child( "#edit-vo img.vasl-image" )
    assert img.get_attribute( "src" ).endswith( "/counter/657/front" )
    btn = find_child( "#edit-vo input.select-vo-image" )
    btn.click()
    images = find_children( ".ui-dialog.select-vo-image .vo-images img" )
    assert len(images) == 2
    images[1].click()
    assert img.get_attribute( "src" ).endswith( "/counter/659/front/0" )
    click_dialog_button( "OK" )
    elems = find_children( "img.vasl-image", vehicles_sortable )
    assert len(elems) == 1
    assert elems[0].get_attribute( "src" ).endswith( "/counter/659/front/0" )

    # save the scenario
    saved_scenario = save_scenario()
    assert saved_scenario["OB_VEHICLES_2"] ==  [
        { "id": "ru/v:049", "image_id": "659/0", "name": "ISU-152", "seq_id": 1 }
    ]

    # reload the scenario, and check the vehicle's image
    select_menu_option( "new_scenario" )
    load_scenario( saved_scenario )
    select_tab( "ob2" )
    elems = find_children( "img.vasl-image", vehicles_sortable )
    assert len(elems) == 1
    assert elems[0].get_attribute( "src" ).endswith( "/counter/659/front/0" )

    # change the vehicle's image back to the default
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 1
    ActionChains(webdriver).double_click( elems[0] ).perform()
    img = find_child( "#edit-vo img.vasl-image" )
    assert img.get_attribute( "src" ).endswith( "/counter/659/front/0" )
    btn = find_child( "#edit-vo input.select-vo-image" )
    btn.click()
    images = find_children( ".ui-dialog.select-vo-image .vo-images img" )
    assert len(images) == 2
    images[0].click()
    assert img.get_attribute( "src" ).endswith( "/counter/657/front/0" )
    click_dialog_button( "OK" )
    elems = find_children( "img.vasl-image", vehicles_sortable )
    assert len(elems) == 1
    assert elems[0].get_attribute( "src" ).endswith( "/counter/657/front/0" )

    # save the scenario
    saved_scenario = save_scenario()
    assert saved_scenario["OB_VEHICLES_2"] ==  [
        { "id": "ru/v:049", "image_id": "657/0", "name": "ISU-152", "seq_id": 1 }
    ]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_change_vo_image2( webapp, webdriver ):
    """Test changing the image for a V/O that has no alternative images."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # add an 107mm GVPM
    set_player( 2, "russian" )
    add_vo( webdriver, "ordnance", 2, "107mm GVPM obr. 38" )

    # make sure the "change image" button is not present
    ordnance_sortable = find_child( "#ob_ordnance-sortable_2" )
    elems = find_children( "li", ordnance_sortable )
    assert len(elems) == 1
    ActionChains(webdriver).double_click( elems[0] ).perform()
    btn = find_child( "#edit-vo input.select-vo-image" )
    assert btn is None

# ---------------------------------------------------------------------

def test_invalid_vo_image_ids( webapp, webdriver ):
    """Test loading scenarios that contain invalid V/O image ID's."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # test each save file
    dname = os.path.join( os.path.split(__file__)[0], "fixtures/invalid-vo-image-ids" )
    for root,_,fnames in os.walk(dname):
        for fname in fnames:
            fname = os.path.join( root, fname )
            if os.path.splitext( fname )[1] != ".json":
                continue

            # load the next scenario, make sure a warning was issued for the V/O image ID
            with open( fname, "r", encoding="utf-8" ) as fp:
                data = json.load( fp )
            set_stored_msg_marker( "_last-warning_" )
            load_scenario( data )
            last_warning = get_stored_msg( "_last-warning_" )
            assert "Invalid V/O image ID" in last_warning

# ---------------------------------------------------------------------

def add_vo( webdriver, vo_type, player_no, name ): #pylint: disable=unused-argument
    """Add a vehicle/ordnance."""

    # add the vehicle/ordnance
    select_tab( "ob{}".format( player_no ) )
    elem = find_child( "#ob_{}-add_{}".format( vo_type, player_no ) )
    elem.click()
    # FUDGE! Locating the vehicle/ordnance by name and selecting it is finicky, I suspect
    # because select2 is sensitive about where the mouse is, and we sometimes end up
    # selecting the wrong item :-/ Selecting by name won't work if there are multiple items
    # that start with the same thing, but that shouldn't be a problem.
    dlg = find_child( "#select-vo" )
    elem = find_child( "input", dlg )
    elem.send_keys( name )
    entries = find_children( ".select2-results li", dlg )
    assert len(entries) == 1
    click_dialog_button( "OK" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def delete_vo( vo_type, player_no, name, webdriver ):
    """Delete a vehicle/ordnance."""

    # delete the vehicle/ordnance
    select_tab( "ob{}".format( player_no ) )
    sortable = find_child( "#ob_{}-sortable_{}".format( vo_type, player_no ) )
    elems = [
        c for c in find_children( "li .vo-name", sortable )
        if c.text == name
    ]
    assert len(elems) == 1
    elem = elems[0]
    trash = find_child( "#ob_{}-trash_{}".format( vo_type, player_no ) )
    ActionChains(webdriver).drag_and_drop( elem, trash ).perform()
