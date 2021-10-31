""" Test VASSAL integration. """

import os
import re
import json
import base64
import random
import typing.re #pylint: disable=import-error

from vasl_templates.webapp.vassal import VassalShim
from vasl_templates.webapp.utils import TempFile, change_extn, compare_version_strings
from vasl_templates.webapp.tests import pytest_options
from vasl_templates.webapp.tests.utils import \
    init_webapp, select_menu_option, get_stored_msg, set_stored_msg, set_stored_msg_marker, wait_for, \
    new_scenario, set_player, find_child
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario, load_scenario_params, save_scenario, \
    assert_scenario_params_complete

# ---------------------------------------------------------------------

def test_full_update( webapp, webdriver ):
    """Test updating a scenario that contains the full set of snippets."""

    def do_test( enable_vo_notes ): #pylint: disable=missing-docstring

        # initialize
        webapp.control_tests \
            .set_data_dir( "{REAL}" ) \
            .set_vo_notes_dir( "{TEST}" if enable_vo_notes else None )
        init_webapp( webapp, webdriver, vsav_persistence=1, no_app_config_snippet_params=1 )

        # load the scenario fields
        SCENARIO_PARAMS = {
            "scenario": {
                "SCENARIO_NAME": "Modified scenario name (<>{}\"'\\)",
                "SCENARIO_ID": "xyz123",
                "SCENARIO_LOCATION": "Right here",
                "SCENARIO_THEATER": "PTO",
                "SCENARIO_DATE": "12/31/1945",
                "SCENARIO_WIDTH": "101",
                "ASA_ID": "", "ROAR_ID": "",
                # NOTE: We used to change both nationalities here, but since we started tagging labels
                # with their owning player, the old labels would be left in-place, so we have to test
                # using the same nationalities.
                "PLAYER_1": "american", "PLAYER_1_ELR": "5", "PLAYER_1_SAN": "4",
                "PLAYER_1_DESCRIPTION": "The Americans",
                "PLAYER_2": "belgian", "PLAYER_2_ELR": "3", "PLAYER_2_SAN": "2",
                "PLAYER_2_DESCRIPTION": "The Belgians",
                "PLAYERS_WIDTH": "42",
                "VICTORY_CONDITIONS": "Just do it!", "VICTORY_CONDITIONS_WIDTH": "102",
                "SCENARIO_NOTES": [
                    { "caption": "Modified scenario note #1", "width": "" },
                    { "caption": "Modified scenario note #2", "width": "100px" }
                ],
                "SSR": [ "Modified SSR #1", "Modified SSR #2" ],
                "SSR_WIDTH": "103",
            },
            "ob1": {
                "OB_SETUPS_1": [
                    { "caption": "Modified American setup #1", "width": "" },
                    { "caption": "Modified American setup #2", "width": "200px" },
                    { "caption": "Modified American setup #3", "width": "" },
                    { "caption": "Modified American setup #4", "width": "" },
                    { "caption": "Modified American setup #5", "width": "" },
                ],
                "OB_NOTES_1": [
                    { "caption": "Modified American note #1", "width": "10em" },
                ],
                "OB_VEHICLES_1": [ "M2A4" ],
                "OB_VEHICLES_WIDTH_1": "202",
                "OB_ORDNANCE_1": [ "M19 60mm Mortar" ],
                "OB_ORDNANCE_WIDTH_1": "204",
            },
            "ob2": {
                "OB_SETUPS_2": [ { "caption": "Modified Belgian setup #1", "width": "" } ],
                "OB_NOTES_2": [
                    { "caption": "Modified Belgian note #1", "width": "" },
                    { "caption": "Modified Belgian note #2", "width": "" },
                    { "caption": "Modified Belgian note #3", "width": "" },
                    { "caption": "Modified Belgian note #4", "width": "" },
                    { "caption": "Modified Belgian note #5", "width": "" },
                ],
                "OB_VEHICLES_2": [ "T-15(b)" ],
                "OB_VEHICLES_WIDTH_2": "302",
                "OB_ORDNANCE_2": [ "DBT" ],
                "OB_ORDNANCE_WIDTH_2": "304",
            },
        }
        if enable_vo_notes:
            SCENARIO_PARAMS["ob1"]["OB_VEHICLES_MA_NOTES_WIDTH_1"] = "203"
            SCENARIO_PARAMS["ob1"]["OB_ORDNANCE_MA_NOTES_WIDTH_1"] = "205"
            SCENARIO_PARAMS["ob2"]["OB_VEHICLES_MA_NOTES_WIDTH_2"] = "303"
            SCENARIO_PARAMS["ob2"]["OB_ORDNANCE_MA_NOTES_WIDTH_2"] = "305"
        load_scenario_params( SCENARIO_PARAMS )
        assert_scenario_params_complete( SCENARIO_PARAMS, enable_vo_notes )

        # dump the original VASL scenario
        # NOTE: We could arguably only do this once, but updating scenarios is the key functionality of the VASSAL shim,
        # and so it's worth checking that every VASSAL+VASL combination understands its input correctly.
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/update-vsav/full.vsav" )
        vsav_dump = _dump_vsav( webapp, fname )
        _check_vsav_dump( vsav_dump, {
            "scenario": "Somewhere",
            "players": re.compile( r"American:.*Belgian:" ),
            "victory_conditions": "Make the other guy",
            "ssr": re.compile( r"SSR #1.*SSR #2.*SSR #3" ),
            "scenario_note.1": "scenario note #1",
            "american/ob_setup_1.1": "U.S. setup #1", "american/ob_setup_1.2": "U.S. setup #2",
            "american/ob_setup_1.3": "U.S. setup #3",
            "american/ob_note_1.1": "U.S. note #1", "american/ob_note_1.2": "U.S. note #2",
            "american/ob_vehicles_1": re.compile( r"M4A1.*Sherman Crab" ),
            "american/ob_ordnance_1": "M1 81mm Mortar",
            "american/baz": "Bazooka",
            "belgian/ob_setup_2.1": "Belgian setup #1", "belgian/ob_setup_2.2": "Belgian setup #2",
            "belgian/ob_setup_2.3": "Belgian setup #3",
            "belgian/ob_note_2.1": "Belgian note #1", "belgian/ob_note_2.2": "Belgian note #2",
            "belgian/ob_vehicles_2": re.compile( r"R-35\(f\).*Medium Truck" ),
            "belgian/ob_ordnance_2": re.compile( r"Bofors M34.*DBT" ),
        } )

        # update the VASL scenario with the new snippets
        # NOTE: The expected changes are:
        #   - created: scenario note 2 ; american setup 4-5 ; belgian note 3-5
        #   - updated: scenario ; players ; VC ; SSR ; scenario note 1
        #     - american: setup 1-3 ; note 1 ; vehicles ; ordnance ; baz
        #     - belgian: setup 1 ; note 1-2 ; vehicles ; ordnance
        #     nb: the BAZ label wouldn't normally be updated, but the template has changed since we created the .vsav
        #   - deleted: american note 2 ; belgian setup 2-3
        # If v/o notes are enabled, we will also see 8 new labels created (one for each of the new
        # American and Belgian vehicle/ordnance added, and 4 more for the multi-applicable notes).
        expected = 14 if enable_vo_notes else 6
        updated_vsav_data = _update_vsav( fname, { "created": expected, "updated": 17, "deleted": 3 } )
        with TempFile() as temp_file:
            # check the results
            temp_file.write( updated_vsav_data )
            temp_file.close( delete=False )
            updated_vsav_dump = _dump_vsav( webapp, temp_file.name )
            expected = {
                "scenario":  "Modified scenario name (<>{}\"'\\)",
                "players": re.compile( r"American:.*Belgian:" ),
                "victory_conditions": "Just do it!",
                "ssr": re.compile( r"Modified SSR #1.*Modified SSR #2" ),
                "scenario_note.1": "Modified scenario note #1",
                "scenario_note.2": "Modified scenario note #2",
                "american/ob_setup_1.1": "Modified American setup #1",
                "american/ob_setup_1.2": "Modified American setup #2",
                "american/ob_setup_1.3": "Modified American setup #3",
                "american/ob_setup_1.4": "Modified American setup #4",
                "american/ob_setup_1.5": "Modified American setup #5",
                "american/ob_note_1.1": "Modified American note #1",
                "american/ob_vehicles_1": "M2A4",
                "american/ob_ordnance_1": "M19 60mm Mortar",
                "american/baz": "Bazooka",
                "belgian/ob_setup_2.1": "Modified Belgian setup #1",
                "belgian/ob_note_2.1": "Modified Belgian note #1",
                "belgian/ob_note_2.2": "Modified Belgian note #2",
                "belgian/ob_note_2.3": "Modified Belgian note #3",
                "belgian/ob_note_2.4": "Modified Belgian note #4",
                "belgian/ob_note_2.5": "Modified Belgian note #5",
                "belgian/ob_vehicles_2": "T-15(b)",
                "belgian/ob_ordnance_2": "DBT",
            }
            if enable_vo_notes:
                expected[ "american/ob_vehicle_note_1.1" ] = re.compile(
                    r'M2A4.*<img src="http://[^/]+/vehicles/american/note/1">'
                )
                expected[ "american/ob_vehicles_ma_notes_1" ] = re.compile(
                    "<span class='key'>B:</span> Unavailable." + ".*" \
                    "<span class='key'>C:</span> American Multi-Applicable Vehicle Note \"C\"." + ".*" \
                    "<span class='key'>P:</span> Unavailable."
                )
                expected[ "american/ob_ordnance_note_1.1" ] = re.compile(
                    r'M19 60mm Mortar.*<img src="http://[^/]+/ordnance/american/note/2">'
                )
                expected[ "american/ob_ordnance_ma_notes_1" ] = "<span class='key'>F:</span> Unavailable."
                expected[ "belgian/ob_vehicle_note_2.1" ] = re.compile(
                    r'T-15\(b\)..*<img src="http://[^/]+/vehicles/allied-minor/note/17">'
                )
                expected[ "belgian/ob_vehicles_ma_notes_2" ] = \
                    "<span class='key'>A:</span> Allied Minor Multi-Applicable Vehicle Note \"A\"."
                expected[ "belgian/ob_ordnance_note_2.1" ] = re.compile(
                    r'DBT.*<img src="http://[^/]+/ordnance/allied-minor/note/6">'
                )
                expected[ "belgian/ob_ordnance_ma_notes_2" ] = re.compile(
                    r"<span class='key'>A:</span> Allied Minor Multi-Applicable Ordnance Note \"A\"." + ".*" \
                    r"<span class='key'>B:</span> Unavailable." + ".*" \
                    r"<span class='key'>D:</span> Unavailable."
                )
            _check_vsav_dump( updated_vsav_dump, expected )

            # update the VASL scenario again (nothing should change)
            updated_vsav_data = _update_vsav( temp_file.name, {} )
            assert updated_vsav_data == b"No changes."

    # run the test against all versions of VASSAL+VASL
    run_vassal_tests( webapp, lambda: do_test(True) )

    # run the test again (once) with no Chapter H vehicle/ordnance notes
    run_vassal_tests( webapp, lambda: do_test(False), all_combos=False )

# ---------------------------------------------------------------------

def test_latw_autocreate( webapp, webdriver ):
    """Test auto-creation of LATW labels."""

    # NOTE: We're only interested in what happens with the LATW labels, we ignore everything else.
    ignore_labels = [ "scenario", "players", "victory_conditions" ]

    def do_test(): #pylint: disable=missing-docstring

        # initialize
        webapp.control_tests.set_data_dir( "{REAL}" )
        init_webapp( webapp, webdriver, vsav_persistence=1 )

        # check the VASL scenario
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/update-vsav/empty.vsav" )
        vsav_dump = _dump_vsav( webapp, fname )
        _check_vsav_dump( vsav_dump, {}, ignore_labels )

        # update the scenario (German/Russian, no date)
        load_scenario_params( { "scenario": { "PLAYER_1": "german", "PLAYER_2": "russian", "SCENARIO_DATE": "" } } )
        updated_vsav_dump = _update_vsav_and_dump( webapp, fname, { "created": 3 } )
        _check_vsav_dump( updated_vsav_dump, {
            # nb: no LATW labels should have been created
        }, ignore_labels )

        # update the scenario (German/Russian, OCT/43)
        load_scenario_params( {
            "scenario": { "PLAYER_1": "german", "PLAYER_2": "russian", "SCENARIO_DATE": "10/01/1943" }
        } )
        updated_vsav_dump = _update_vsav_and_dump( webapp, fname, { "created": 4 } )
        _check_vsav_dump( updated_vsav_dump, {
            "german/pf": "Panzerfaust",
        }, ignore_labels )

        # update the scenario (German/Russian, JAN/44)
        load_scenario_params( {
            "scenario": { "PLAYER_1": "german", "PLAYER_2": "russian", "SCENARIO_DATE": "01/01/1944" }
        } )
        updated_vsav_dump = _update_vsav_and_dump( webapp, fname, { "created": 5 } )
        _check_vsav_dump( updated_vsav_dump, {
            "german/pf": "Panzerfaust", "german/atmm": "ATMM check:",
        }, ignore_labels )

        # update the scenario (British/American, no date)
        load_scenario_params( { "scenario": { "PLAYER_1": "british", "PLAYER_2": "american", "SCENARIO_DATE": "" } } )
        updated_vsav_dump = _update_vsav_and_dump( webapp, fname, { "created": 3 } )
        _check_vsav_dump( updated_vsav_dump, {
            # nb: no LATW labels should have been created
        }, ignore_labels )

        # update the scenario (British/American, DEC/45)
        load_scenario_params( {
            "scenario": { "PLAYER_1": "british", "PLAYER_2": "american", "SCENARIO_DATE": "12/31/1945" }
        } )
        updated_vsav_dump = _update_vsav_and_dump( webapp, fname, { "created": 3 } )
        _check_vsav_dump( updated_vsav_dump, {
            # nb: no LATW labels should have been created
        }, ignore_labels )

    # run the test
    # NOTE: We're testing the logic in the front/back-ends that determine whether LATW labels
    # get created/updated/deleted, not the interaction with VASSAL, so we don't need to test
    # against every VASSAL+VASL combination (although we can, if we want, but it'll be slow!)
    run_vassal_tests( webapp, do_test, all_combos=False )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_latw_update( webapp, webdriver ):
    """Test updating of LATW labels."""

    # NOTE: We're only interested in what happens with the LATW labels, we ignore everything else.
    ignore_labels = [ "scenario", "players", "victory_conditions" ]

    def do_test(): #pylint: disable=missing-docstring

        # initialize
        webapp.control_tests.set_data_dir( "{REAL}" )
        init_webapp( webapp, webdriver, vsav_persistence=1 )

        # check the VASL scenario
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/update-vsav/latw.vsav" )
        vsav_dump = _dump_vsav( webapp, fname )
        _check_vsav_dump( vsav_dump, {
            "german/psk": "Panzerschrek", "german/atmm": "ATMM check:", # nb: the PF label has no snippet ID
            "russian/mol-p": "TH#", # nb: the MOL label has no snippet ID
            "british/piat": "TH#",
            "american/baz": "Bazooka",
        }, ignore_labels )

        # update the scenario (German/Russian, no date)
        load_scenario_params( { "scenario": { "PLAYER_1": "german", "PLAYER_2": "russian", "SCENARIO_DATE": "" } } )
        # NOTE: We changed the MOL-P template (to add custom list bullets), so the snippet is different
        # to when this test was originally written, and so #updated changed from 2 to 3.
        # NOTE: Same thing happened when we factored out the common CSS into common.css :-/ Sigh...
        updated_vsav_dump = _update_vsav_and_dump( webapp, fname,
            { "created": 3, "updated": 5 }
        )
        _check_vsav_dump( updated_vsav_dump, {
            "german/pf": "Panzerfaust", # nb: the PF label now has a snippet ID
            "german/psk": "Panzerschrek", "german/atmm": "ATMM check:",
            "russian/mol": "Kindling Attempt:", "russian/mol-p": "TH#", # nb: the MOL label now has a snippet ID
            # NOTE: We used to delete the PIAT and BAZ labels, but this no longer happens with player-owned labels.
            "british/piat": "TH#", "american/baz": "Bazooka",
        }, ignore_labels )

        # update the scenario (British/American, DEC/1943)
        load_scenario_params( {
            "scenario": { "PLAYER_1": "british", "PLAYER_2": "american", "SCENARIO_DATE": "12/31/1943" }
        } )
        updated_vsav_dump = _update_vsav_and_dump( webapp, fname,
            { "created": 3, "updated": 2 }
        )
        _check_vsav_dump( updated_vsav_dump, {
            # NOTE: We used to delete the PSK/ATMM/MOL-P labels, but this no longer happens with player-owned labels.
            "german/psk": "Panzerschrek", "german/atmm": "ATMM check:",
            "russian/mol-p": "TH#", # nb: the MOL label now has a snippet ID
            "british/piat": "TH#",
            "american/baz": "Bazooka  ('43)", # nb: this has changed from '45
        }, ignore_labels )

    # run the test
    # NOTE: We're testing the logic in the front/back-ends that determine whether LATW labels
    # get created/updated/deleted, not the interaction with VASSAL, so we don't need to test
    # against every VASSAL+VASL combination (although we can, if we want, but it'll be slow!)
    run_vassal_tests( webapp, do_test, all_combos=False )

# ---------------------------------------------------------------------

def test_dump_vsav( webapp, webdriver ):
    """Test dumping a scenario."""

    def do_test(): #pylint: disable=missing-docstring

        # initialize
        init_webapp( webapp, webdriver )

        # dump the VASL scenario
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/dump-vsav/labels.vsav" )
        vsav_dump = _dump_vsav( webapp, fname )

        # check the result
        fname = change_extn( fname, ".txt" )
        with open( fname, "r", encoding="utf-8" ) as fp:
            expected = fp.read()
        assert vsav_dump == expected

    # run the test against all versions of VASSAL+VASL
    run_vassal_tests( webapp, do_test )

# ---------------------------------------------------------------------

def test_update_legacy_labels( webapp, webdriver ):
    """Test detection and updating of legacy labels."""

    def do_test( enable_vo_notes ): #pylint: disable=missing-docstring

        # initialize
        webapp.control_tests \
            .set_data_dir( "{REAL}" ) \
            .set_vo_notes_dir( "{TEST}" if enable_vo_notes else None )
        init_webapp( webapp, webdriver, vsav_persistence=1, scenario_persistence=1 )

        # dump the VASL scenario
        # NOTE: We implemented snippet ID's in v0.5, this scenario is the "Hill 621" example from v0.4.
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/update-vsav/hill621-legacy.vsav" )
        vsav_dump = _dump_vsav( webapp, fname )
        labels = _get_vsav_labels( vsav_dump )
        assert len( [ lbl for lbl in labels if "vasl-templates:id" not in lbl ] ) == 20
        assert len( [ lbl for lbl in labels if "vasl-templates:id" in lbl ] ) == 0 #pylint: disable=len-as-condition

        # load the scenario into the UI and update the VSAV
        fname2 = change_extn( fname, ".json" )
        with open( fname2, "r", encoding="utf-8" ) as fp:
            saved_scenario = json.load( fp )
        load_scenario( saved_scenario )
        expected = 5 if enable_vo_notes else 1
        updated_vsav_dump = _update_vsav_and_dump( webapp, fname,
            { "created": expected, "updated": 20 }
        )

        # check the results
        # nb: the update process should create 1 new label (the "Download from MMP" scenario note)
        labels = _get_vsav_labels( updated_vsav_dump )
        assert len( [ lbl for lbl in labels if "vasl-templates:id" not in lbl ] ) == 0 #pylint: disable=len-as-condition
        assert len( [ lbl for lbl in labels if "vasl-templates:id" in lbl ] ) == 25 if enable_vo_notes else 21
        expected = {
            "scenario": "Near Minsk",
            "players": re.compile( r"Russian:.*German:" ),
            "victory_conditions": "five Level 3 hill hexes",
            "ssr": re.compile( r"no wind at start.*must take a TC" ),
            "scenario_note.1": "Download the scenario card",
            "russian/ob_setup_1.1": "whole hex of Board 3",
            "russian/ob_setup_1.2": "Enter on Turn 2", "russian/ob_setup_1.3": "Enter on Turn 5",
            "russian/ob_vehicles_1": re.compile( r"T-34 M43.*SU-152.*SU-122.*ZIS-5" ),
            "german/ob_setup_2.1": "whole hex of Board 4",
            "german/ob_setup_2.2": "Enter on Turn 1", "german/ob_setup_2.3": "Enter on Turn 2",
            "german/ob_setup_2.4": "Enter on Turn 4", "german/ob_setup_2.5": "Enter on Turn 5",
            "german/ob_setup_2.6": "Enter on Turn 8",
            "german/ob_note_2.1": "80+mm Battalion Mortar",
            "german/ob_note_2.2": "100+mm OBA",
            "german/ob_vehicles_2": re.compile(
                r"PzKpfw IVH.*PzKpfw IIIN.*StuG IIIG \(L\).*StuH 42.*SPW 250/1.*SPW 251/1.*SPW 251/sMG"
            ),
            "german/ob_ordnance_2": re.compile( r"7.5cm PaK 40.*5cm PaK 38" ),
            "german/pf": "Panzerfaust", "german/atmm": "Anti-Tank Magnetic Mines",
        }
        if enable_vo_notes:
            expected[ "russian/ob_vehicle_note_1.1" ] = re.compile(
                r'T-34 M43.*<img src="http://[^/]+/vehicles/russian/note/16">'
            )
            expected[ "german/ob_ordnance_note_2.2" ] = re.compile(
                r'5cm PaK 38.*<img src="http://[^/]+/ordnance/german/note/8">'
            )
            expected[ "german/ob_vehicles_ma_notes_2" ] = re.compile(
                r"<span class='key'>B:</span> German Multi-Applicable Vehicle Note \"B\"." + ".*" \
                r"<span class='key'>C:</span> German Multi-Applicable Vehicle Note \"C\"." + ".*" \
                r"<span class='key'>J:</span> Unavailable." + ".*" \
                r"<span class='key'>N:</span> Unavailable." + ".*" \
                r"<span class='key'>O:</span> Unavailable." + ".*" \
                r"<span class='key'>P:</span> Unavailable." + ".*" \
                r"<span class='key'>Q:</span> Unavailable." + ".*" \
                r"<span class='key'>S:</span> Unavailable." + ".*"
            )
            expected["german/ob_ordnance_ma_notes_2"] = r"<span class='key'>N:</span> Unavailable."
        _check_vsav_dump( updated_vsav_dump, expected )

    # run the test against all versions of VASSAL+VASL
    # NOTE: VASL 6.6.3 can no longer read the .vsav file (VassalShim.loadScenario() calls
    # GameState.decodeSavedGame(), which throws a java.util.NoSuchElementException).
    # The stack trace suggests that it's having trouble understanding some OBA-related element,
    # and Doug Rimmer tells me that he changed the names of a few things in the OBA dialog,
    # so I suspect the code is trying to deserialize something it no longers knows about :-/
    # The tests here are for handling legacy labels, which was an issue quite a long time ago
    # in vasl-templates years, so we just ignore this problem...
    run_vassal_tests( webapp, lambda: do_test(True), max_vasl_version="6.6.2" )

    # run the test again (once) with no Chapter H vehicle/ordnance notes
    run_vassal_tests( webapp, lambda: do_test(False), all_combos=False, max_vasl_version="6.6.2" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_update_legacy_latw_labels( webapp, webdriver ):
    """Test detection and updating of legacy LATW labels."""

    def do_test(): #pylint: disable=missing-docstring

        # initialize
        webapp.control_tests.set_data_dir( "{REAL}" )
        init_webapp( webapp, webdriver, vsav_persistence=1, scenario_persistence=1 )

        # dump the VASL scenario
        # NOTE: This scenario contains LATW labels created using v0.4 i.e. they have no snippet ID's.
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/update-vsav/latw-legacy.vsav" )
        vsav_dump = _dump_vsav( webapp, fname )
        labels = _get_vsav_labels( vsav_dump )
        assert len( [ lbl for lbl in labels if "vasl-templates:id" not in lbl ] ) == 8
        assert len( [ lbl for lbl in labels if "vasl-templates:id" in lbl ] ) == 0 #pylint: disable=len-as-condition

        # NOTE: We're only interested in what happens with the LATW labels, ignore everything else
        ignore_labels = [ "scenario", "players", "victory_conditions" ]

        # update the VSAV (all LATW are active)
        load_scenario_params( {
            "scenario": { "PLAYER_1": "german", "PLAYER_2": "russian", "SCENARIO_DATE": "12/31/1945" }
        } )
        updated_vsav_dump = _update_vsav_and_dump( webapp, fname,
            { "created": 3, "updated": 5 }
        )
        _check_vsav_dump( updated_vsav_dump, {
            "german/pf": "Panzerfaust", "german/psk": "Panzerschrek", "german/atmm": "ATMM check:",
            "russian/mol": "Kindling Attempt:", "russian/mol-p": "TH#",
        }, ignore_labels )
        labels = _get_vsav_labels( updated_vsav_dump )
        # nb: the legacy labels left in place: the scenario comment, and the PIAT/BAZ labels
        assert len( [ lbl for lbl in labels if "vasl-templates:id" not in lbl ] ) == 3

        # update the VSAV (all LATW are active)
        load_scenario_params( {
            "scenario": { "PLAYER_1": "british", "PLAYER_2": "american", "SCENARIO_DATE": "12/31/1945" }
        } )
        updated_vsav_dump = _update_vsav_and_dump( webapp, fname,
            { "created": 3, "updated": 2 }
        )
        _check_vsav_dump( updated_vsav_dump, {
            "british/piat": "PIAT",
            "american/baz": "Bazooka  ('45)",
        }, ignore_labels )
        labels = _get_vsav_labels( updated_vsav_dump )
        # nb: the legacy labels left in place: the scenario comment, the PF/PSK/ATMM and MOL/MOL-P labels
        assert len( [ lbl for lbl in labels if "vasl-templates:id" not in lbl ] ) == 6

        # update the VSAV (some LATW are active)
        load_scenario_params( { "scenario": { "PLAYER_1": "german", "PLAYER_2": "russian", "SCENARIO_DATE": "" } } )
        updated_vsav_dump = _update_vsav_and_dump( webapp, fname,
            { "created": 3, "updated": 5 }
        )
        _check_vsav_dump( updated_vsav_dump, {
            "german/pf": "Panzerfaust", "german/psk": "Panzerschrek", "german/atmm": "ATMM check:",
            "russian/mol": "Kindling Attempt:", "russian/mol-p": "TH#",
        }, ignore_labels )
        labels = _get_vsav_labels( updated_vsav_dump )
        # nb: the legacy labels left in place: the scenario comment, the PIAT/BAZ labels
        assert len( [ lbl for lbl in labels if "vasl-templates:id" not in lbl ] ) == 3

        # update the VSAV (some LATW are active)
        load_scenario_params( { "scenario": { "PLAYER_1": "british", "PLAYER_2": "american", "SCENARIO_DATE": "" } } )
        updated_vsav_dump = _update_vsav_and_dump( webapp, fname,
            { "created": 3, "updated": 2 }
        )
        _check_vsav_dump( updated_vsav_dump, {
            "british/piat": "PIAT",
            "american/baz": "Bazooka",
        }, ignore_labels )
        labels = _get_vsav_labels( updated_vsav_dump )
        # nb: the legacy labels left in place: the scenario comment, the PF/PSK/ATMM, MOL/MOL-P and BAZ labels
        assert len( [ lbl for lbl in labels if "vasl-templates:id" not in lbl ] ) == 6

    # run the test against all versions of VASSAL+VASL
    run_vassal_tests( webapp, do_test )

# ---------------------------------------------------------------------

def test_player_owned_labels( webapp, webdriver ):
    """Test how we update labels owned by different player nationalities."""

    def do_test(): #pylint: disable=missing-docstring

        # initialize
        webapp.control_tests.set_data_dir( "{REAL}" )
        init_webapp( webapp, webdriver, vsav_persistence=1 )
        load_scenario_params( {
            "scenario": {
                "SCENARIO_NAME": "Player-owned labels",
                "SCENARIO_DATE": "01/01/1940",
                "PLAYER_1": "german",
                "PLAYER_2": "american",
            },
            "ob1": { "OB_SETUPS_1": [ { "caption": "german setup #1" } ] },
            "ob2": { "OB_SETUPS_2": [ { "caption": "american setup #1" } ] },
        } )

        # update a legacy scenario (i.e. labels have *not* been tagged with their owner player nationality)
        # NOTE: We expect to see 4 labels updated:
        #   - the 2 OB setup labels (they will get the new-style ID's)
        #   - scenario (timestamp)
        #   - players (new American player)
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/update-vsav/player-owned-labels-legacy.vsav" )
        updated_vsav_dump  = _update_vsav_and_dump( webapp, fname,
            { "updated": 4 }
        )
        _check_vsav_dump( updated_vsav_dump , {
            "german/ob_setup_1.1": "german setup #1",
            "american/ob_setup_2.1": "american setup #1",
        }, ignore=["scenario","players","victory_conditions"] )

        # update a new-style scenario (i.e. labels *have* been tagged with their owner player nationality)
        # NOTE: We expect to see 1 label created:
        #   - a new American OB setup label
        # and 2 labels updated:
        #   - scenario (timestamp)
        #   - players (new American player)
        # The existing Russian OB setup label should be ignored and left in-place.
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/update-vsav/player-owned-labels.vsav" )
        updated_vsav_dump  = _update_vsav_and_dump( webapp, fname,
            { "created": 1, "updated": 2 }
        )
        _check_vsav_dump( updated_vsav_dump , {
            "german/ob_setup_1.1": "german setup #1",
            "american/ob_setup_2.1": "american setup #1",
            "russian/ob_setup_2.1": "russian setup #1",
        }, ignore=["scenario","players","victory_conditions"] )

    # run the test against all versions of VASSAL+VASL
    run_vassal_tests( webapp, do_test )

# ---------------------------------------------------------------------

def test_analyze_vsav( webapp, webdriver ):
    """Test analyzing a scenario."""

    def do_test(): #pylint: disable=missing-docstring

        # initialize
        webapp.control_tests.set_data_dir( "{REAL}" )
        init_webapp( webapp, webdriver, vsav_persistence=1, scenario_persistence=1 )

        # analyze a basic scenario
        new_scenario()
        set_player( 1, "german" )
        set_player( 2, "russian" )
        analyze_vsav( "basic.vsav",
            [ [ "ge/v:033", "ge/v:066" ], [ "ge/o:029" ] ],
            [ [ "ru/v:064" ], [ "ru/o:002", "ru/o:006" ] ],
            [ "Imported 2 German vehicles and 1 ordnance.", "Imported 1 Russian vehicle and 2 ordnance." ]
        )

        # try again with different nationalities
        new_scenario()
        set_player( 1, "french" )
        set_player( 2, "british" )
        analyze_vsav( "basic.vsav",
            [ [], [] ],
            [ [], [] ],
            [ "No vehicles/ordnance were imported." ]
        )

        # analyze a scenario with landing craft
        new_scenario()
        set_player( 1, "american" )
        set_player( 2, "japanese" )
        analyze_vsav( "landing-craft.vsav",
            [ [ ("sh/v:000","397/0"), ("sh/v:000","399/0"), ("sh/v:006","413/0"), ("sh/v:006","415/0") ], [] ],
            [ [ "sh/v:007", "sh/v:008" ], [] ],
            [ "Imported 4 American vehicles.", "Imported 2 Japanese vehicles." ]
        )

        # analyze a scenario with common vehicles/ordnance
        new_scenario()
        set_player( 1, "belgian" )
        set_player( 2, "romanian" )
        analyze_vsav( "common-vo.vsav",
            [ [ "be/v:000", "alc/v:011" ], [ "be/o:001", "alc/o:012" ] ],
            [ [ "ro/v:000", "axc/v:027" ], [ "ro/o:003", "axc/o:002" ] ],
            [ "Imported 2 Belgian vehicles and 2 ordnance.", "Imported 2 Romanian vehicles and 2 ordnance." ]
        )
        # try again with the Yugoslavians/Croatians
        new_scenario()
        set_player( 1, "yugoslavian" )
        set_player( 2, "croatian" )
        analyze_vsav( "common-vo.vsav",
            [ [ "alc/v:011" ], [ "alc/o:012" ] ],
            [ [ "axc/v:027" ], [ "axc/o:002" ] ],
            [ "Imported 1 Yugoslavian vehicle and 1 ordnance.", "Imported 1 Croatian vehicle and 1 ordnance." ]
        )
        # try again with the Germans/Russians
        new_scenario()
        analyze_vsav( "common-vo.vsav",
            [ [], [] ],
            [ [], [] ],
            [ "No vehicles/ordnance were imported." ]
        )

        # analyze a scenario using counters from an extension
        new_scenario()
        set_player( 1, "american" )
        set_player( 2, "japanese" )
        analyze_vsav( "extensions-bfp.vsav",
            [ [ "am/v:906" ], [ "am/o:900" ] ],
            [ [ "ja/v:902" ], [ "ja/o:902" ] ],
            [ "Imported 1 American vehicle and 1 ordnance.", "Imported 1 Japanese vehicle and 1 ordnance." ]
        )

    # run the test against all versions of VASSAL+VASL
    run_vassal_tests( webapp, do_test, vasl_extns_type="{REAL}" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_analyze_vsav_hip_concealed( webapp, webdriver ):
    """Test analyzing a scenario that contains HIP and concealed units."""

    def do_test(): #pylint: disable=missing-docstring

        # initialize
        init_webapp( webapp, webdriver, vsav_persistence=1, scenario_persistence=1 )

        # do the test
        # NOTE: The test scenario contains hidden/concealed units belonging to the Russians and Germans,
        # but because the owning user is test/password, they should be ignored (unless you configure VASSAL
        # with these credentials, so don't do that :-/).
        new_scenario()
        analyze_vsav( "hip-concealed.vsav",
            [ [], [] ],
            [ [], [] ],
            [ "No vehicles/ordnance were imported." ]
        )

    # run the test against all versions of VASSAL+VASL
    run_vassal_tests( webapp, do_test )

# ---------------------------------------------------------------------

def test_reverse_remapped_gpids( webapp, webdriver ):
    """Test reverse mapping of GPID's."""

    def do_test(): #pylint: disable=missing-docstring

        # initialize
        webapp.control_tests.set_data_dir( "{REAL}" )
        init_webapp( webapp, webdriver, vsav_persistence=1, scenario_persistence=1 )

        # do the test
        new_scenario()
        set_player( 1, "american" )
        set_player( 2, "croatian" )
        analyze_vsav( "reverse-remapped-gpids-650.vsav",
            [ ["am/v:044"], ["am/o:002","am/o:021"] ],
            [ ["cr/v:002","cr/v:003"], ["cr/o:000"] ],
            [ "Imported 1 American vehicle and 2 ordnance.", "Imported 2 Croatian vehicles and 1 ordnance." ]
        )

    # run the test against all versions of VASSAL+VASL
    run_vassal_tests( webapp, do_test, min_vasl_version="6.5.0" )

# ---------------------------------------------------------------------

def test_vo_entry_selection_for_theater( webapp, webdriver ):
    """Test selection of vehicle/ordnance entries by theater."""

    def do_test( theater, expected ): #pylint: disable=missing-docstring

        # initialize
        webapp.control_tests.set_data_dir( "{REAL}" )
        init_webapp( webapp, webdriver, vsav_persistence=1, scenario_persistence=1 )

        # do the test
        new_scenario()
        load_scenario_params( { "scenario": {
            "SCENARIO_THEATER": theater,
            "PLAYER_1": "american",
        } } )
        analyze_vsav( "vo-entry-selection-for-theater.vsav",
            [ [], expected ],
            [ [], [] ],
            [ "Imported 4 American ordnance." ]
        )

    # do the tests
    def do_tests(): #pylint: disable=missing-docstring
        # NOTE: The .vsav file contains ROK and OUNC variants of the M2 60* Mortar which, strictly speaking,
        # should only be imported for ROK and OUNC players respectively. However, due to the way the data files
        # are currently set up (the kfw/un-common.json file gets appended to the US, British, ROK and OUNC
        # player lists, and all the GPID's become available to all the players), they are currently (incorrectly)
        # imported. However, this isn't a big problem since these players will never be fighting against each other.
        do_test( "ETO", [
            # NOTE: The normal M2 60* Mortar gets imported as an old-style American entry (because we're in ETO).
            ("am/o:000",None),
            # NOTE The other variants always get imported as K:FW counters.
            ("kfw-un-common/o:002","12689/0"), ("kfw-un-common/o:002","11391/0"), ("kfw-un-common/o:002","11440/0")
        ] )
        do_test( "Korea", [
            # NOTE: The normal M2 60* Mortar gets imported as new-style K:FW entry (because we're in Korea).
            ("kfw-un-common/o:002","849/0"),
            # NOTE The other variants always get imported as K:FW counters.
            ("kfw-un-common/o:002","12689/0"), ("kfw-un-common/o:002","11391/0"), ("kfw-un-common/o:002","11440/0")
        ] )
    run_vassal_tests( webapp, do_tests, min_vasl_version="6.5.0" )

# ---------------------------------------------------------------------

def run_vassal_tests( webapp, func, vasl_extns_type=None,
    all_combos=None, min_vasl_version=None, max_vasl_version=None
):
    """Run the test function for each combination of VASSAL + VASL.

    This is, of course, going to be insanely slow, since we need to spin up a JVM
    and initialize VASSAL/VASL each time :-/
    """

    # get the available VASSAL and VASL versions
    vassal_versions = webapp.control_tests.get_vassal_versions()
    vasl_versions = webapp.control_tests.get_vasl_versions()

    # check if we want to test all VASSAL+VASL combinations (nb: if not, we test against only one combination,
    # and since they all should give the same results, it doesn't matter which one.
    if all_combos is None:
        all_combos = not pytest_options.short_tests
    if not all_combos:
        for _ in range(0,100):
            vasl_version = random.choice( vasl_versions )
            vassal_version = random.choice( vassal_versions )
            if VassalShim.is_compatible_version( vassal_version, vasl_version ):
                vasl_versions = [ vasl_version ]
                vassal_versions = [ vassal_version ]
                break
        else:
            assert False, "Can't find a valid combination of VASSAL and VASL."

    # run the test for each VASSAL+VASL
    for vassal_version in vassal_versions:
        for vasl_version in vasl_versions:
            if min_vasl_version and compare_version_strings( vasl_version, min_vasl_version ) < 0:
                continue
            if max_vasl_version and compare_version_strings( vasl_version, max_vasl_version ) > 0:
                continue
            if not VassalShim.is_compatible_version( vassal_version, vasl_version ):
                continue
            webapp.control_tests \
                .set_vassal_version( vassal_version ) \
                .set_vasl_version( vasl_version, vasl_extns_type )
            func()

# ---------------------------------------------------------------------

def _update_vsav( fname, expected ):
    """Update a VASL scenario."""

    # read the VSAV data
    with open( fname, "rb" ) as fp:
        vsav_data = fp.read()

    # send the VSAV data to the front-end to be updated
    set_stored_msg( "_vsav-persistence_", base64.b64encode( vsav_data ).decode( "utf-8" ) )
    _ = set_stored_msg_marker( "_last-info_" )
    _ = set_stored_msg_marker( "_last-warning_" )
    select_menu_option( "update_vsav" )

    # wait for the front-end to receive the data
    def check_response():
        # NOTE: If something is misconfigured, the error response can get stored in the persistence buffer
        # really quickly i.e. before we get a chance to detect it here being cleared first.
        resp = get_stored_msg( "_vsav-persistence_" )
        return resp == "" or resp.startswith( "ERROR:" )
    wait_for( 2, check_response )

    # wait for the updated data to come back
    timeout = 120 if os.name == "nt" else 60
    wait_for( timeout, lambda: get_stored_msg( "_vsav-persistence_" ) != "" )
    updated_vsav_data = get_stored_msg( "_vsav-persistence_" )
    if updated_vsav_data.startswith( "ERROR: " ):
        raise RuntimeError( updated_vsav_data )
    updated_vsav_data = base64.b64decode( updated_vsav_data )

    # parse the VASSAL shim report
    if expected:
        report = {}
        msg = get_stored_msg( "_last-warning_" if "deleted" in expected else "_last-info_" )
        assert "The VASL scenario was updated:" in msg
        for mo2 in re.finditer( "<li>([^<]+)", msg ):
            mo3 = re.search( r"^(\d+) labels? (were|was) ([a-z]+)", mo2.group(1) )
            report[ mo3.group(3) ] = int( mo3.group(1) )
        assert report == expected
    else:
        assert "No changes were made" in get_stored_msg( "_last-info_" )

    return updated_vsav_data

def _update_vsav_and_dump( webapp, fname, expected ):
    """Update a VASL scenario and dump the result."""

    # update the VSAV
    updated_vsav_data = _update_vsav( fname, expected )

    # dump the updated VSAV
    with TempFile() as temp_file:
        temp_file.write( updated_vsav_data )
        temp_file.close( delete=False )
        return _dump_vsav( webapp, temp_file.name )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _dump_vsav( webapp, fname ):
    """Dump a VASL scenario file."""
    return webapp.control_tests.dump_vsav( fname )

def _check_vsav_dump( vsav_dump, expected, ignore=None ):
    """"Check that a VASL scenario dump contains what we expect."""

    # extract the information of interest from the dump
    labels = {}
    for label in _get_vsav_labels(vsav_dump):
        mo2 = re.search( r"<!-- vasl-templates:id (.*?) -->", label, re.DOTALL )
        if not mo2:
            continue # nb: this is not one of ours
        snippet_id = mo2.group( 1 )
        if snippet_id.startswith( "extras/" ):
            continue
        labels[snippet_id] = label

    # compare what we extracted from the dump with what's expected
    for snippet_id in expected:
        if isinstance( expected[snippet_id], typing.re.Pattern ):
            rc = expected[snippet_id].search( labels[snippet_id] ) is not None
        else:
            assert isinstance( expected[snippet_id], str )
            rc = expected[snippet_id] in labels[snippet_id]
        if not rc:
            print( "Can't find {} in label: {}".format( expected[snippet_id], labels[snippet_id] ) )
            assert False
        del labels[snippet_id]

    # check for unexpected extra labels in the VASL scenario
    if ignore:
        labels = [ lbl for lbl in labels if lbl not in ignore ]
    if labels:
        for snippet_id in labels:
            print( "Extra label in the VASL scenario: {}".format( snippet_id ) )
        assert False

def _get_vsav_labels( vsav_dump ):
    """Extract the labels from a VSAV dump."""
    matches = re.finditer( r"AddPiece: DynamicProperty/User-Labeled.*?^\s*?(?=[^- ])",
        vsav_dump,
        re.MULTILINE+re.DOTALL
    )
    labels = [ mo.group() for mo in matches ]
    regex = re.compile( r"<html>.*?</html>" )
    matches = [ regex.search(label) for label in labels ]
    return [ mo.group() if mo else "<???>" for mo in matches ]

# ---------------------------------------------------------------------

def analyze_vsav( fname, expected_ob1, expected_ob2, expected_report ):
    """Analyze a VASL scenario."""

    # read the VSAV data
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/analyze-vsav/"+fname )
    with open( fname, "rb" ) as fp:
        vsav_data = fp.read()

    # send the VSAV data to the front-end to be analyzed
    set_stored_msg( "_vsav-persistence_", base64.b64encode( vsav_data ).decode( "utf-8" ) )
    prev_info_msg = set_stored_msg_marker( "_last-info_" )
    set_stored_msg_marker( "_last-warning_" )
    select_menu_option( "analyze_vsav" )

    # wait for the analysis to finish
    wait_for( 2, lambda: find_child( "#please-wait" ).is_displayed() )
    wait_for( 60, lambda: not find_child( "#please-wait" ).is_displayed() )

    # check the results
    saved_scenario = save_scenario()
    def get_ids( key ): #pylint: disable=missing-docstring
        return set(
            ( v["id"], v.get("image_id") )
            for v in saved_scenario.get( key, [] )
        )
    def adjust_expected( vals ): #pylint: disable=missing-docstring
        return set(
            v if isinstance(v,tuple) else (v,None)
            for v in vals
        )
    assert get_ids( "OB_VEHICLES_1" ) == adjust_expected( expected_ob1[0] )
    assert get_ids( "OB_ORDNANCE_1" ) == adjust_expected( expected_ob1[1] )
    assert get_ids( "OB_VEHICLES_2" ) == adjust_expected( expected_ob2[0] )
    assert get_ids( "OB_ORDNANCE_2" ) == adjust_expected( expected_ob2[1] )

    # check the report
    msg = get_stored_msg( "_last-info_" )
    if msg == prev_info_msg:
        msg = get_stored_msg( "_last-warning_" )
    assert all( e in msg for e in expected_report )
