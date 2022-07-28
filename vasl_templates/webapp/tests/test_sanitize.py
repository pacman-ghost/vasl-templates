""" Test sanitizing HTML. """

import os
import re

from selenium.webdriver.common.action_chains import ActionChains

from vasl_templates.webapp.tests.utils import \
    init_webapp, select_tab, click_dialog_button, load_trumbowyg, unload_trumbowyg, \
    find_child, find_sortable_helper, wait_for_elem, wait_for_clipboard

from vasl_templates.webapp.tests.test_vassal import run_vassal_tests, update_vsav_and_dump, get_vsav_labels
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario, save_scenario

# ---------------------------------------------------------------------

def test_sanitize_load_scenario( webapp, webdriver ):
    """Test sanitization of HTML content in scenarios as they are loaded."""

    # initialize
    # NOTE: The Trumbowyg tag black-list is active, which will affect results (by removing tags *and their contents).
    webapp.control_tests.set_vo_notes_dir( "{TEST}" )
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # load a scenario with unsafe content
    load_scenario( _make_scenario_params( False ) )

    def check_val( name, expected ):
        elem = find_child( ".param[name='{}']".format( name ) )
        assert elem.get_attribute( "value" ) == expected
    def check_trumbowyg( name, expected ):
        assert unload_trumbowyg( name ) == expected
    def check_sortable( sortable_sel, expected, expected_width ):
        sortable = find_child( sortable_sel )
        entry = find_child( "li", sortable ) # nb: we assume there's only 1 entry
        assert entry.text == expected
        if expected_width:
            ActionChains( webdriver ).double_click( entry ).perform()
            elem = find_child( ".ui-dialog-buttonpane input[name='width']" )
            assert elem.get_attribute( "value" ) == expected_width
            click_dialog_button( "OK" )
    def check_custom_cap( sortable_sel, expected ):
        elem = find_child( "{} li".format( sortable_sel ) ) # nb: we assume there's only 1 entry
        ActionChains( webdriver ).double_click( elem ).perform()
        elem = find_child( ".ui-dialog.edit-vo .sortable input" )
        assert elem.get_attribute( "value" ) == expected
        click_dialog_button( "Cancel" )

    # check what was loaded into the UI
    # NOTE: We can't use save_scenario), since that also sanitizes HTML.
    check_val( "SCENARIO_NAME", "!scenario_name:#" )
    check_val( "SCENARIO_ID", "!scenario_id:@@@#" )
    check_val( "SCENARIO_LOCATION", "!scenario_location:<div style=\"text-align:right;\">@@@</div>#" )
    check_val( "SCENARIO_WIDTH", "!scenario_width:@@@#" )
    check_val( "PLAYER_1_DESCRIPTION", "!player1_description:#" )
    check_val( "PLAYER_2_DESCRIPTION", "!player2_description:#" )
    check_val( "PLAYERS_WIDTH", "!players_width:@@@#" )
    check_trumbowyg( "VICTORY_CONDITIONS", "!victory_conditions:@@@#" )
    check_val( "VICTORY_CONDITIONS_WIDTH", "!victory_conditions_width:@@@#" )
    check_sortable( "#scenario_notes-sortable", "!scenario_note:#", "!scenario_note_width:@@@#" )
    check_sortable( "#ssr-sortable", "!ssr:#", None )
    check_val( "SSR_WIDTH", "!ssr_width:@@@#" )

    # check what was loaded into the UI
    for player_no in (1,2):
        select_tab( "ob{}".format( player_no ) )
        check_sortable( "#ob_setups-sortable_{}".format( player_no ), "!ob_setup:#", "!ob_setup_width:@@@#" )
        check_sortable( "#ob_notes-sortable_{}".format( player_no ), "!ob_note:#", "!ob_note_width:@@@#" )
        check_val( "OB_VEHICLES_WIDTH_{}".format( player_no ), "!ob_vehicles_width:@@@#" )
        check_val( "OB_VEHICLES_MA_NOTES_WIDTH_{}".format( player_no ), "!ob_vehicles_ma_notes_width:@@@#" )
        check_val( "OB_ORDNANCE_WIDTH_{}".format( player_no ), "!ob_ordnance_width:@@@#" )
        check_val( "OB_ORDNANCE_MA_NOTES_WIDTH_{}".format( player_no ), "!ob_ordnance_ma_notes_width:@@@#" )
        check_custom_cap( "#ob_vehicles-sortable_{}".format( player_no ), "!custom_cap:@@@#" )
        check_custom_cap( "#ob_ordnance-sortable_{}".format( player_no ), "!custom_cap:@@@#" )

# ---------------------------------------------------------------------

def test_sanitize_save_scenario( webapp, webdriver, monkeypatch ):
    """Test sanitization of HTML content when saving scenarios."""

    # initialize
    monkeypatch.setitem( webapp.config, "TRUMBOWYG_TAG_BLACKLIST", "[]" )
    webapp.control_tests.set_vo_notes_dir( "{TEST}" )
    init_webapp( webapp, webdriver, no_sanitize_load=1, scenario_persistence=1 )

    # load a scenario with unsafe content
    load_scenario( _make_scenario_params( False ) )

    # unload the scenario
    params = save_scenario()
    # NOTE: It's a bit tedious to have to list every single parameter in a save file, but this lets us detect
    # the case where a new parameter has been added, and we haven't updated these sanitization tests for it.
    for key in ( "SCENARIO_THEATER", "PLAYER_1_ELR", "PLAYER_1_SAN", "PLAYER_2_ELR", "PLAYER_2_SAN" ):
        params.pop( key )
    params = { k: v for k, v in params.items() if not k[0] == "_" }
    assert params == {
        "PLAYER_1": "german",
        "PLAYER_2": "russian",
        "SCENARIO_NAME": "!scenario_name:#",
        "SCENARIO_ID": "!scenario_id:@@@#",
        "SCENARIO_LOCATION": "!scenario_location:<div style=\"text-align:right;\">@@@</div>#",
        "SCENARIO_WIDTH": "!scenario_width:@@@#",
        "PLAYER_1_DESCRIPTION": "!player1_description:#",
        "PLAYER_2_DESCRIPTION": "!player2_description:#",
        "PLAYERS_WIDTH": "!players_width:@@@#",
        "VICTORY_CONDITIONS": "!victory_conditions:@@@#",
        "VICTORY_CONDITIONS_WIDTH": "!victory_conditions_width:@@@#",
        "SCENARIO_NOTES": [ { "id": 1,
            "caption": "!scenario_note:#",
            "width": "!scenario_note_width:@@@#"
        } ],
        "SSR": [ "!ssr:#" ],
        "SSR_WIDTH": "!ssr_width:@@@#",
        #
        "OB_SETUPS_1": [ { "id": 1, "caption": "!ob_setup:#", "width": "!ob_setup_width:@@@#" } ],
        "OB_NOTES_1": [ { "id": 1, "caption": "!ob_note:#", "width": "!ob_note_width:@@@#" } ],
        "OB_VEHICLES_1": [ { "seq_id": 1,
            "id": "ge/v:990", "name": "a german vehicle",
            "custom_capabilities": [ "!custom_cap:@@@#" ]
        } ],
        "OB_VEHICLES_WIDTH_1": "!ob_vehicles_width:@@@#",
        "OB_VEHICLES_MA_NOTES_WIDTH_1": "!ob_vehicles_ma_notes_width:@@@#",
        "OB_ORDNANCE_1": [ { "seq_id": 1,
            "id": "ge/o:990", "name": "a german ordnance",
            "custom_capabilities": [ "!custom_cap:@@@#" ]
        } ],
        "OB_ORDNANCE_WIDTH_1": "!ob_ordnance_width:@@@#",
        "OB_ORDNANCE_MA_NOTES_WIDTH_1": "!ob_ordnance_ma_notes_width:@@@#",
        #
        "OB_SETUPS_2": [ { "id": 1, "caption": "!ob_setup:#", "width": "!ob_setup_width:@@@#" } ],
        "OB_NOTES_2": [ { "id": 1, "caption": "!ob_note:#", "width": "!ob_note_width:@@@#" } ],
        "OB_VEHICLES_2": [ { "seq_id": 1,
            "id": "ru/v:990", "name": "a russian vehicle",
            "custom_capabilities": [ "!custom_cap:@@@#" ]
        } ],
        "OB_VEHICLES_WIDTH_2": "!ob_vehicles_width:@@@#",
        "OB_VEHICLES_MA_NOTES_WIDTH_2": "!ob_vehicles_ma_notes_width:@@@#",
        "OB_ORDNANCE_2": [ { "seq_id": 1,
            "id": "ru/o:990", "name": "a russian ordnance",
            "custom_capabilities": [ "!custom_cap:@@@#" ]
        } ],
        "OB_ORDNANCE_WIDTH_2": "!ob_ordnance_width:@@@#",
        "OB_ORDNANCE_MA_NOTES_WIDTH_2": "!ob_ordnance_ma_notes_width:@@@#",
        #
        "ASA_ID": "", "ROAR_ID": "",
        "COMPASS": "", "SCENARIO_DATE": "",
    }

# ---------------------------------------------------------------------

def test_sanitize_update_vsav( webapp, webdriver, monkeypatch ):
    """Test sanitization of HTML content when updating a VASL save file."""

    def do_test():

        # initialize
        monkeypatch.setitem( webapp.config, "TRUMBOWYG_TAG_BLACKLIST", "[]" )
        webapp.control_tests \
            .set_data_dir( "{REAL}" ) \
            .set_vo_notes_dir( "{TEST}" )
        init_webapp( webapp, webdriver, no_sanitize_load=1, scenario_persistence=1, vsav_persistence=1 )

        # load a scenario with unsafe content
        load_scenario( _make_scenario_params( True ) )

        # update the VSAV, then dump it
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/update-vsav/empty.vsav" )
        vsav_dump = update_vsav_and_dump( webapp, fname, { "created": 22 } )
        labels, _ = get_vsav_labels( vsav_dump )

        # remove labels we don't need to check
        for player_no, nat in ( (1,"german"), (2,"russian") ):
            for key in ( "{}/nat_caps_{}", "{}/ob_vehicle_note_{}.1", "{}/ob_ordnance_note_{}.1" ):
                key = key.format( nat, player_no )
                assert all(
                    tag not in labels[key]
                    for tag in ( "<script", "<iframe", "<object", "<applet", "<x" )
                )
                del labels[ key ]

        # check the labels in the VSAV
        expected = {
            "scenario": [
                r'width: !scenario_width:@@@# ;',
                r'!scenario_name:#',
                r'\(!scenario_id:@@@#\)',
                r'!scenario_location:<div style="text-align:right;">@@@</div>#'
            ],
            "players": [
                r'width: !players_width:@@@# ;',
                r'!player1_description:#',
                r'!player2_description:#'
            ],
            "victory_conditions": [
                r'width: !victory_conditions_width:@@@# ;',
                r'!victory_conditions:@@@#'
            ],
            "ssr": [
                r'width: !ssr_width:@@@# ;',
                r'!ssr:#'
            ],
            "scenario_note.1": [
                r'width: !scenario_note_width:@@@# ;',
                r'!scenario_note:#'
            ],
            "german/ob_setup_1.1": [
                r'width: !ob_setup_width:@@@# ;',
                r'!ob_setup:#'
            ],
            "german/ob_note_1.1": [
                r'width: !ob_note_width:@@@# ;',
                r'!ob_note:#'
            ],
            "german/ob_vehicles_1": [
                "width: !ob_vehicles_width:@@@# ;",
                "!custom_cap:@@@#"
            ],
            "german/ob_vehicles_ma_notes_1": [ "width: !ob_vehicles_ma_notes_width:@@@# ;" ],
            "german/ob_ordnance_1": [
                "width: !ob_ordnance_width:@@@# ;",
                "!custom_cap:@@@#"
            ],
            "german/ob_ordnance_ma_notes_1": [ "width: !ob_ordnance_ma_notes_width:@@@# ;" ],
            "russian/ob_setup_2.1": [
                r'width: !ob_setup_width:@@@# ;',
                r'!ob_setup:#'
            ],
            "russian/ob_note_2.1": [
                r'width: !ob_note_width:@@@# ;',
                r'!ob_note:#'
            ],
            "russian/ob_vehicles_2": [
                "width: !ob_vehicles_width:@@@# ;",
                "!custom_cap:@@@#"
            ],
            "russian/ob_vehicles_ma_notes_2": [ "width: !ob_vehicles_ma_notes_width:@@@# ;" ],
            "russian/ob_ordnance_2": [
                "width: !ob_ordnance_width:@@@# ;",
                "!custom_cap:@@@#"
            ],
            "russian/ob_ordnance_ma_notes_2": [ "width: !ob_ordnance_ma_notes_width:@@@# ;" ],
        }
        for snippet_id in list( labels.keys() ):
            if snippet_id in expected:
                label = labels.pop( snippet_id )
                regex = re.compile( ".*".join( expected.pop( snippet_id ) ) )
                assert regex.search( label )
        assert len( labels ) == 0

    # do the test
    run_vassal_tests( webapp, do_test, all_combos=False )

# ---------------------------------------------------------------------

def test_sanitize_input( webapp, webdriver ):
    """Test sanitizing HTML as it is entered in the UI."""

    # initialize
    # NOTE: The Trumbowyg tag black-list is active, which will affect results (by removing tags *and their contents).
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # NOTE: We don't sanitize things like the scenario name, since it is entered into an <input> textbox,
    # and so can't do any harm (these are sanitized when the scenario is unloaded from the UI).

    # test sanitizing HTML in Trumbowyg controls
    # NOTE: Trumbowyg only sanitizes tags, not attributes.
    elem = find_child( ".param[name='VICTORY_CONDITIONS']" )
    load_trumbowyg( elem, "foo <script>xyz</script> bar" )
    find_child( ".trumbowyg-viewHTML-button" ).click()
    # FUDGE! We need to switch back to raw HTML mode for the <textarea> to be updated with the sanitized HTML.
    find_child( ".trumbowyg-viewHTML-button" ).click()
    assert unload_trumbowyg( elem ) == "foo  bar"

    # test sanitizing HTML in a simple note dialog that hasn't been saved yet
    sortable = find_child( "#scenario_notes-sortable" )
    find_sortable_helper( sortable, "add" ).click()
    dlg = wait_for_elem( 2, ".ui-dialog.edit-simple_note" )
    load_trumbowyg( find_child( ".trumbowyg-editor", dlg ),
        "foo <script>format_hdd();</script> bar"
    )
    find_child( "button.snippet", dlg ).click()
    wait_for_clipboard( 2, "foo  bar", contains=True )
    click_dialog_button( "OK" )

# ---------------------------------------------------------------------

def _make_scenario_params( real_vo ):
    """Generate scenario parameters that contain unsafe HTML."""

    # generate the scenario parameters
    params = {
        "PLAYER_1": "german",
        "PLAYER_2": "russian",
        "SCENARIO_NAME": "!scenario_name:<script>@@@</script>#",
        "SCENARIO_ID": "!scenario_id:<x>@@@</x>#",
        "SCENARIO_LOCATION": "!scenario_location:<div foo='bar' style='text-align:right;'>@@@</div>#",
        "SCENARIO_WIDTH": "!scenario_width:<x>@@@</x>#",
        "PLAYER_1_DESCRIPTION": "!player1_description:<iframe>@@@</iframe>#",
        "PLAYER_2_DESCRIPTION": "!player2_description:<iframe>@@@</iframe>#",
        "PLAYERS_WIDTH": "!players_width:<x>@@@</x>#",
        "VICTORY_CONDITIONS": "!victory_conditions:<applet>@@@</applet>#",
        "VICTORY_CONDITIONS_WIDTH": "!victory_conditions_width:<x>@@@</x>#",
        "SCENARIO_NOTES": [
            { "caption": "!scenario_note:<iframe>@@@</iframe>#", "width": "!scenario_note_width:<x>@@@</x>#" }
        ],
        "SSR": [ "!ssr:<iframe>@@@</iframe>#" ],
        "SSR_WIDTH": "!ssr_width:<x>@@@</x>#",
    }

    # add in player-specific parameters
    params.update( {
        "OB_VEHICLES_1": [ {
            "name": "PzKpfw IB" if real_vo else "a german vehicle",
            "custom_capabilities": [ "!custom_cap:<x>@@@</x>#" ]
        } ],
        "OB_ORDNANCE_1": [ {
            "name": "5cm leGrW" if real_vo else "a german ordnance",
            "custom_capabilities": [ "!custom_cap:<x>@@@</x>#" ]
        } ],
        "OB_VEHICLES_2": [ {
            "name": "T-37" if real_vo else "a russian vehicle",
            "custom_capabilities": [ "!custom_cap:<x>@@@</x>#" ]
        } ],
        "OB_ORDNANCE_2": [ {
            "name": "50mm RM obr. 40" if real_vo else "a russian ordnance",
            "custom_capabilities": [ "!custom_cap:<x>@@@</x>#" ]
        } ],
    } )
    for player_no in (1,2):
        params.update( {
            "OB_SETUPS_{}".format( player_no ): [ {
                "caption": "!ob_setup:<script foo='bar' style='text-align:right;'>@@@</script>#",
                "width": "!ob_setup_width:<x>@@@</x>#"
            } ],
            "OB_NOTES_{}".format( player_no ): [ {
                "caption": "!ob_note:<iframe foo='bar' style='text-align:right;'>@@@</iframe>#",
                "width": "!ob_note_width:<x>@@@</x>#"
            } ],
            "OB_VEHICLES_WIDTH_{}".format( player_no ): "!ob_vehicles_width:<x>@@@</x>#",
            "OB_VEHICLES_MA_NOTES_WIDTH_{}".format( player_no ): "!ob_vehicles_ma_notes_width:<x>@@@</x>#",
            "OB_ORDNANCE_WIDTH_{}".format( player_no ): "!ob_ordnance_width:<x>@@@</x>#",
            "OB_ORDNANCE_MA_NOTES_WIDTH_{}".format( player_no ): "!ob_ordnance_ma_notes_width:<x>@@@</x>#",
        } )

    return params
