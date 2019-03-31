""" Test VASSAL integration. """

import os
import re
import json
import base64
import random
import typing.re #pylint: disable=import-error

import pytest

from vasl_templates.webapp.vassal import VassalShim
from vasl_templates.webapp.utils import TempFile, change_extn
from vasl_templates.webapp import globvars
from vasl_templates.webapp.tests.utils import \
    init_webapp, refresh_webapp, select_menu_option, get_stored_msg, set_stored_msg, set_stored_msg_marker, wait_for
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario, load_scenario_params, \
    assert_scenario_params_complete

# ---------------------------------------------------------------------

class DummyVaslMod:
    """Dummy VaslMod class that lets us run the VASSAL shim locally (to dump scenarios)."""
    def __init__( self, fname ):
        self.filename = fname

# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest.config.option.vasl_mods, reason="--vasl-mods not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( not pytest.config.option.vassal, reason="--vassal not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( pytest.config.option.short_tests, reason="--short-tests specified" ) #pylint: disable=no-member
def test_full_update( webapp, webdriver ):
    """Test updating a scenario that contains the full set of snippets."""

    # initialize
    control_tests = init_webapp( webapp, webdriver, vsav_persistence=1,
        reset = lambda ct: ct.set_data_dir( dtype="real" )
    )

    def do_test( enable_vo_notes ): #pylint: disable=missing-docstring

        # initialize
        control_tests.set_vo_notes_dir( dtype = "test" if enable_vo_notes else None )
        refresh_webapp( webdriver )

        # load the scenario fields
        SCENARIO_PARAMS = {
            "scenario": {
                "SCENARIO_NAME": "Modified scenario name (<>{}\"'\\)",
                "SCENARIO_ID": "xyz123",
                "SCENARIO_LOCATION": "Right here",
                "SCENARIO_THEATER": "PTO",
                "SCENARIO_DATE": "12/31/1945",
                "SCENARIO_WIDTH": "101",
                "PLAYER_1": "russian", "PLAYER_1_ELR": "5", "PLAYER_1_SAN": "4",
                "PLAYER_2": "german", "PLAYER_2_ELR": "3", "PLAYER_2_SAN": "2",
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
                    { "caption": "Modified Russian setup #1", "width": "" },
                    { "caption": "Modified Russian setup #2", "width": "200px" },
                    { "caption": "Modified Russian setup #3", "width": "" },
                    { "caption": "Modified Russian setup #4", "width": "" },
                    { "caption": "Modified Russian setup #5", "width": "" },
                ],
                "OB_NOTES_1": [
                    { "caption": "Modified Russian note #1", "width": "10em" },
                ],
                "OB_VEHICLES_1": [ "T-34/85 (MT)" ],
                "OB_VEHICLES_WIDTH_1": "202",
                "OB_ORDNANCE_1": [ "82mm BM obr. 37 (MTR)" ],
                "OB_ORDNANCE_WIDTH_1": "204",
            },
            "ob2": {
                "OB_SETUPS_2": [ { "caption": "Modified German setup #1", "width": "" } ],
                "OB_NOTES_2": [
                    { "caption": "Modified German note #1", "width": "" },
                    { "caption": "Modified German note #2", "width": "" },
                    { "caption": "Modified German note #3", "width": "" },
                    { "caption": "Modified German note #4", "width": "" },
                    { "caption": "Modified German note #5", "width": "" },
                ],
                "OB_VEHICLES_2": [ "PzKpfw VG (MT)" ],
                "OB_VEHICLES_WIDTH_2": "302",
                "OB_ORDNANCE_2": [ "3.7cm PaK 35/36 (AT)" ],
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
        vsav_dump = _dump_vsav( fname )
        _check_vsav_dump( vsav_dump, {
            "scenario": "Somewhere",
            "players": re.compile( r"American:.*Belgian:" ),
            "victory_conditions": "Make the other guy",
            "ssr": re.compile( r"SSR #1.*SSR #2.*SSR #3" ),
            "scenario_note.1": "scenario note #1",
            "ob_setup_1.1": "U.S. setup #1", "ob_setup_1.2": "U.S. setup #2", "ob_setup_1.3": "U.S. setup #3",
            "ob_note_1.1": "U.S. note #1", "ob_note_1.2": "U.S. note #2",
            "ob_vehicles_1": re.compile( r"M4A1.*Sherman Crab" ),
            "ob_ordnance_1": "M1 81mm Mortar",
            "baz": "Bazooka",
            "ob_setup_2.1": "Belgian setup #1", "ob_setup_2.2": "Belgian setup #2", "ob_setup_2.3": "Belgian setup #3",
            "ob_note_2.1": "Belgian note #1", "ob_note_2.2": "Belgian note #2",
            "ob_vehicles_2": re.compile( r"R-35\(f\).*Medium Truck" ),
            "ob_ordnance_2": re.compile( r"Bofors M34.*DBT" ),
        } )

        # update the VASL scenario with the new snippets
        expected = 13 if enable_vo_notes else 8
        updated_vsav_data = _update_vsav( fname, { "created": expected, "updated": 16, "deleted": 4 } )
        with TempFile() as temp_file:
            # check the results
            temp_file.write( updated_vsav_data )
            temp_file.close()
            updated_vsav_dump = _dump_vsav( temp_file.name )
            expected = {
                "scenario":  "Modified scenario name (<>{}\"'\\)",
                "players": re.compile( r"Russian:.*German:" ),
                "victory_conditions": "Just do it!",
                "ssr": re.compile( r"Modified SSR #1.*Modified SSR #2" ),
                "scenario_note.1": "Modified scenario note #1",
                "scenario_note.2": "Modified scenario note #2",
                "ob_setup_1.1": "Modified Russian setup #1", "ob_setup_1.2": "Modified Russian setup #2",
                "ob_setup_1.3": "Modified Russian setup #3", "ob_setup_1.4": "Modified Russian setup #4",
                "ob_setup_1.5": "Modified Russian setup #5",
                "ob_note_1.1": "Modified Russian note #1",
                "ob_vehicles_1": "T-34/85",
                "ob_ordnance_1": "82mm BM obr. 37",
                "ob_setup_2.1": "Modified German setup #1",
                "ob_note_2.1": "Modified German note #1", "ob_note_2.2": "Modified German note #2",
                "ob_note_2.3": "Modified German note #3", "ob_note_2.4": "Modified German note #4",
                "ob_note_2.5": "Modified German note #5",
                "pf": "Panzerfaust", "atmm": "Anti-Tank Magnetic Mines",
                "ob_vehicles_2": "PzKpfw VG",
                "ob_ordnance_2": "3.7cm PaK 35/36",
            }
            if enable_vo_notes:
                expected[ "ob_vehicle_note_1.1" ] = re.compile(
                    r'T-34/85.*<img src="http://[^/]+/vehicles/russian/note/18">'
                )
                expected[ "ob_vehicles_ma_notes_1" ] = "<span class='key'>J:</span> Unavailable."
                expected[ "ob_ordnance_note_2.1" ] = re.compile(
                    r'3.7cm PaK 35/36.*<img src="http://[^/]+/ordnance/german/note/6">'
                )
                expected[ "ob_vehicles_ma_notes_2" ] = "<span class='key'>H:</span> Unavailable."
                expected[ "ob_ordnance_ma_notes_2" ] = re.compile(
                    r"<span class='key'>B:</span> German Multi-Applicable Ordnance Note \"B\"." + ".*" \
                    r"<span class='key'>N:</span> Unavailable." + ".*" \
                    r"<span class='key'>P:</span> Unavailable."
                )
            _check_vsav_dump( updated_vsav_dump, expected )
            # update the VASL scenario again (nothing should change)
            updated_vsav_data = _update_vsav( temp_file.name, {} )
            assert updated_vsav_data == b"No changes."

    # run the test against all versions of VASSAL+VASL
    _run_tests( control_tests, lambda: do_test(True), True )

    # run the test again (once) with no Chapter H vehicle/ordnance notes
    _run_tests( control_tests, lambda: do_test(False), False )

# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest.config.option.vasl_mods, reason="--vasl-mods not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( not pytest.config.option.vassal, reason="--vassal not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( pytest.config.option.short_tests, reason="--short-tests specified" ) #pylint: disable=no-member
def test_latw_autocreate( webapp, webdriver ):
    """Test auto-creation of LATW labels."""

    # initialize
    control_tests = init_webapp( webapp, webdriver, vsav_persistence=1,
        reset = lambda ct: ct.set_data_dir( dtype="real" )
    )

    # NOTE: We're only interested in what happens with the LATW labels, we ignore everything else.
    ignore_labels = [ "scenario", "players", "victory_conditions" ]

    def do_test(): #pylint: disable=missing-docstring

        # check the VASL scenario
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/update-vsav/empty.vsav" )
        vsav_dump = _dump_vsav( fname )
        _check_vsav_dump( vsav_dump, {}, ignore_labels )

        # update the scenario (German/Russian, no date)
        load_scenario_params( { "scenario": { "PLAYER_1": "german", "PLAYER_2": "russian", "SCENARIO_DATE": "" } } )
        updated_vsav_dump = _update_vsav_and_dump( fname, { "created": 3 } )
        _check_vsav_dump( updated_vsav_dump, {
            # nb: no LATW labels should have been created
        }, ignore_labels )

        # update the scenario (German/Russian, OCT/43)
        load_scenario_params( {
            "scenario": { "PLAYER_1": "german", "PLAYER_2": "russian", "SCENARIO_DATE": "10/01/1943" }
        } )
        updated_vsav_dump = _update_vsav_and_dump( fname, { "created": 4 } )
        _check_vsav_dump( updated_vsav_dump, {
            "pf": "Panzerfaust",
        }, ignore_labels )

        # update the scenario (German/Russian, JAN/44)
        load_scenario_params( {
            "scenario": { "PLAYER_1": "german", "PLAYER_2": "russian", "SCENARIO_DATE": "01/01/1944" }
        } )
        updated_vsav_dump = _update_vsav_and_dump( fname, { "created": 5 } )
        _check_vsav_dump( updated_vsav_dump, {
            "pf": "Panzerfaust", "atmm": "ATMM check:",
        }, ignore_labels )

        # update the scenario (British/American, no date)
        load_scenario_params( { "scenario": { "PLAYER_1": "british", "PLAYER_2": "american", "SCENARIO_DATE": "" } } )
        updated_vsav_dump = _update_vsav_and_dump( fname, { "created": 3 } )
        _check_vsav_dump( updated_vsav_dump, {
            # nb: no LATW labels should have been created
        }, ignore_labels )

        # update the scenario (British/American, DEC/45)
        load_scenario_params( {
            "scenario": { "PLAYER_1": "british", "PLAYER_2": "american", "SCENARIO_DATE": "12/31/1945" }
        } )
        updated_vsav_dump = _update_vsav_and_dump( fname, { "created": 3 } )
        _check_vsav_dump( updated_vsav_dump, {
            # nb: no LATW labels should have been created
        }, ignore_labels )

    # run the test
    # NOTE: We're testing the logic in the front/back-ends that determine whether LATW labels
    # get created/updated/deleted, not the interaction with VASSAL, so we don't need to test
    # against every VASSAL+VASL combination (although we can, if we want, but it'll be slow!)
    _run_tests( control_tests, do_test, False )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@pytest.mark.skipif( not pytest.config.option.vasl_mods, reason="--vasl-mods not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( not pytest.config.option.vassal, reason="--vassal not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( pytest.config.option.short_tests, reason="--short-tests specified" ) #pylint: disable=no-member
def test_latw_update( webapp, webdriver ):
    """Test updating of LATW labels."""

    # initialize
    control_tests = init_webapp( webapp, webdriver, vsav_persistence=1,
        reset = lambda ct: ct.set_data_dir( dtype="real" )
    )

    # NOTE: We're only interested in what happens with the LATW labels, we ignore everything else.
    ignore_labels = [ "scenario", "players", "victory_conditions" ]

    def do_test(): #pylint: disable=missing-docstring

        # check the VASL scenario
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/update-vsav/latw.vsav" )
        vsav_dump = _dump_vsav( fname )
        _check_vsav_dump( vsav_dump, {
            "psk": "Panzerschrek", "atmm": "ATMM check:", # nb: the PF label has no snippet ID
            "mol-p": "TH#", # nb: the MOL label has no snippet ID
            "piat": "TH#",
            "baz": "Bazooka",
        }, ignore_labels )

        # update the scenario (German/Russian, no date)
        load_scenario_params( { "scenario": { "PLAYER_1": "german", "PLAYER_2": "russian", "SCENARIO_DATE": "" } } )
        # NOTE: We changed the MOL-P template (to add custom list bullets), so the snippet is different
        # to when this test was originally written, and so #updated changed from 2 to 3.
        updated_vsav_dump = _update_vsav_and_dump( fname, { "created": 3, "updated": 3, "deleted": 2 } )
        _check_vsav_dump( updated_vsav_dump, {
            "pf": "Panzerfaust", "psk": "Panzerschrek", "atmm": "ATMM check:", # nb: the PF label now has a snippet ID
            "mol": "Kindling Attempt:", "mol-p": "TH#", # nb: the MOL label now has a snippet ID
            # nb: the PIAT and BAZ labels are now gone
        }, ignore_labels )

        # update the scenario (British/American, DEC/1943)
        load_scenario_params( {
            "scenario": { "PLAYER_1": "british", "PLAYER_2": "american", "SCENARIO_DATE": "12/31/1943" }
        } )
        updated_vsav_dump = _update_vsav_and_dump( fname, { "created": 3, "updated": 1, "deleted": 3 } )
        _check_vsav_dump( updated_vsav_dump, {
            # nb: the PSK/ATMM and MOL-P label are now gone
            "piat": "TH#",
            "baz": "Bazooka  ('43)", # nb: this has changed from '45
        }, ignore_labels )

    # run the test
    # NOTE: We're testing the logic in the front/back-ends that determine whether LATW labels
    # get created/updated/deleted, not the interaction with VASSAL, so we don't need to test
    # against every VASSAL+VASL combination (although we can, if we want, but it'll be slow!)
    _run_tests( control_tests, do_test, False )

# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest.config.option.vasl_mods, reason="--vasl-mods not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( not pytest.config.option.vassal, reason="--vassal not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( pytest.config.option.short_tests, reason="--short-tests specified" ) #pylint: disable=no-member
def test_dump_vsav( webapp, webdriver ):
    """Test dumping a scenario."""

    # initialize
    control_tests = init_webapp( webapp, webdriver )

    def do_test(): #pylint: disable=missing-docstring

        # dump the VASL scenario
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/dump-vsav/labels.vsav" )
        vsav_dump = _dump_vsav( fname )

        # check the result
        fname = change_extn( fname, ".txt" )
        expected = open( fname, "r" ).read()
        assert vsav_dump == expected

    # run the test against all versions of VASSAL+VASL
    _run_tests( control_tests, do_test, True )

# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest.config.option.vasl_mods, reason="--vasl-mods not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( not pytest.config.option.vassal, reason="--vassal not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( pytest.config.option.short_tests, reason="--short-tests specified" ) #pylint: disable=no-member
def test_legacy_labels( webapp, webdriver ):
    """Test detection and updating of legacy labels."""

    # initialize
    control_tests = init_webapp( webapp, webdriver, vsav_persistence=1, scenario_persistence=1,
        reset = lambda ct: ct.set_data_dir( dtype="real" )
    )

    def do_test( enable_vo_notes ): #pylint: disable=missing-docstring

        # initialize
        control_tests.set_vo_notes_dir( dtype = "test" if enable_vo_notes else None )
        refresh_webapp( webdriver )

        # dump the VASL scenario
        # NOTE: We implemented snippet ID's in v0.5, this scenario is the "Hill 621" example from v0.4.
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/update-vsav/hill621-legacy.vsav" )
        vsav_dump = _dump_vsav( fname )
        labels = _get_vsav_labels( vsav_dump )
        assert len( [ lbl for lbl in labels if "vasl-templates:id" not in lbl ] ) == 20
        assert len( [ lbl for lbl in labels if "vasl-templates:id" in lbl ] ) == 0 #pylint: disable=len-as-condition

        # load the scenario into the UI and update the VSAV
        fname2 = change_extn( fname, ".json" )
        saved_scenario = json.load( open( fname2, "r" ) )
        load_scenario( saved_scenario )
        expected = 5 if enable_vo_notes else 1
        updated_vsav_dump = _update_vsav_and_dump( fname, { "created": expected, "updated": 20 } )

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
            "ob_setup_1.1": "whole hex of Board 3",
            "ob_setup_1.2": "Enter on Turn 2", "ob_setup_1.3": "Enter on Turn 5",
            "ob_vehicles_1": re.compile( r"T-34 M43.*SU-152.*SU-122.*ZIS-5" ),
            "ob_setup_2.1": "whole hex of Board 4",
            "ob_setup_2.2": "Enter on Turn 1", "ob_setup_2.3": "Enter on Turn 2", "ob_setup_2.4": "Enter on Turn 4",
            "ob_setup_2.5": "Enter on Turn 5", "ob_setup_2.6": "Enter on Turn 8",
            "ob_note_2.1": "80+mm Battalion Mortar",
            "ob_note_2.2": "100+mm OBA",
            "ob_vehicles_2": re.compile(
                r"PzKpfw IVH.*PzKpfw IIIN.*StuG IIIG \(L\).*StuH 42.*SPW 250/1.*SPW 251/1.*SPW 251/sMG"
            ),
            "ob_ordnance_2": re.compile( r"7.5cm PaK 40.*5cm PaK 38" ),
            "pf": "Panzerfaust", "atmm": "Anti-Tank Magnetic Mines",
        }
        if enable_vo_notes:
            expected[ "ob_vehicle_note_1.1" ] = re.compile(
                r'T-34 M43.*<img src="http://[^/]+/vehicles/russian/note/16">'
            )
            expected[ "ob_ordnance_note_2.2" ] = re.compile(
                r'5cm PaK 38.*<img src="http://[^/]+/ordnance/german/note/8">'
            )
            expected[ "ob_vehicles_ma_notes_2" ] = re.compile(
                r"<span class='key'>B:</span> German Multi-Applicable Vehicle Note \"B\"." + ".*" \
                r"<span class='key'>C:</span> German Multi-Applicable Vehicle Note \"C\"." + ".*" \
                r"<span class='key'>J:</span> Unavailable." + ".*" \
                r"<span class='key'>N:</span> Unavailable." + ".*" \
                r"<span class='key'>O:</span> Unavailable." + ".*" \
                r"<span class='key'>P:</span> Unavailable." + ".*" \
                r"<span class='key'>Q:</span> Unavailable." + ".*" \
                r"<span class='key'>S:</span> Unavailable." + ".*"
            )
            expected["ob_ordnance_ma_notes_2"] = r"<span class='key'>N:</span> Unavailable."
        _check_vsav_dump( updated_vsav_dump, expected )

    # run the test
    _run_tests( control_tests, lambda: do_test(True), False )

    # run the test again (once) with no Chapter H vehicle/ordnance notes
    _run_tests( control_tests, lambda: do_test(False), False )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@pytest.mark.skipif( not pytest.config.option.vasl_mods, reason="--vasl-mods not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( not pytest.config.option.vassal, reason="--vassal not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( pytest.config.option.short_tests, reason="--short-tests specified" ) #pylint: disable=no-member
def test_legacy_latw_labels( webapp, webdriver ):
    """Test detection and updating of legacy LATW labels."""

    # initialize
    control_tests = init_webapp( webapp, webdriver, vsav_persistence=1, scenario_persistence=1,
        reset = lambda ct: ct.set_data_dir( dtype="real" )
    )

    def do_test(): #pylint: disable=missing-docstring

        # dump the VASL scenario
        # NOTE: This scenario contains LATW labels created using v0.4 i.e. they have no snippet ID's.
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/update-vsav/latw-legacy.vsav" )
        vsav_dump = _dump_vsav( fname )
        labels = _get_vsav_labels( vsav_dump )
        assert len( [ lbl for lbl in labels if "vasl-templates:id" not in lbl ] ) == 8
        assert len( [ lbl for lbl in labels if "vasl-templates:id" in lbl ] ) == 0 #pylint: disable=len-as-condition

        # NOTE: We're only interested in what happens with the LATW labels, ignore everything else
        ignore_labels = [ "scenario", "players", "victory_conditions" ]

        # update the VSAV (all LATW are active)
        load_scenario_params( {
            "scenario": { "PLAYER_1": "german", "PLAYER_2": "russian", "SCENARIO_DATE": "12/31/1945" }
        } )
        updated_vsav_dump = _update_vsav_and_dump( fname, { "created": 3, "updated": 5 } )
        _check_vsav_dump( updated_vsav_dump, {
            "pf": "Panzerfaust", "psk": "Panzerschrek", "atmm": "ATMM check:",
            "mol": "Kindling Attempt:", "mol-p": "TH#",
        }, ignore_labels )
        labels = _get_vsav_labels( updated_vsav_dump )
        # nb: the legacy labels left in place: the scenario comment, and the PIAT/BAZ labels
        assert len( [ lbl for lbl in labels if "vasl-templates:id" not in lbl ] ) == 3

        # update the VSAV (all LATW are active)
        load_scenario_params( {
            "scenario": { "PLAYER_1": "british", "PLAYER_2": "american", "SCENARIO_DATE": "12/31/1945" }
        } )
        updated_vsav_dump = _update_vsav_and_dump( fname, { "created": 3, "updated": 2 } )
        _check_vsav_dump( updated_vsav_dump, {
            "piat": "PIAT",
            "baz": "Bazooka  ('45)",
        }, ignore_labels )
        labels = _get_vsav_labels( updated_vsav_dump )
        # nb: the legacy labels left in place: the scenario comment, the PF/PSK/ATMM and MOL/MOL-P labels
        assert len( [ lbl for lbl in labels if "vasl-templates:id" not in lbl ] ) == 6

        # update the VSAV (some LATW are active)
        load_scenario_params( { "scenario": { "PLAYER_1": "german", "PLAYER_2": "russian", "SCENARIO_DATE": "" } } )
        updated_vsav_dump = _update_vsav_and_dump( fname, { "created": 3, "updated": 5 } )
        _check_vsav_dump( updated_vsav_dump, {
            "pf": "Panzerfaust", "psk": "Panzerschrek", "atmm": "ATMM check:",
            "mol": "Kindling Attempt:", "mol-p": "TH#",
        }, ignore_labels )
        labels = _get_vsav_labels( updated_vsav_dump )
        # nb: the legacy labels left in place: the scenario comment, the PIAT/BAZ labels
        assert len( [ lbl for lbl in labels if "vasl-templates:id" not in lbl ] ) == 3

        # update the VSAV (some LATW are active)
        load_scenario_params( { "scenario": { "PLAYER_1": "british", "PLAYER_2": "american", "SCENARIO_DATE": "" } } )
        updated_vsav_dump = _update_vsav_and_dump( fname, { "created": 3, "updated": 2 } )
        _check_vsav_dump( updated_vsav_dump, {
            "piat": "PIAT",
            "baz": "Bazooka",
        }, ignore_labels )
        labels = _get_vsav_labels( updated_vsav_dump )
        # nb: the legacy labels left in place: the scenario comment, the PF/PSK/ATMM, MOL/MOL-P and BAZ labels
        assert len( [ lbl for lbl in labels if "vasl-templates:id" not in lbl ] ) == 6

    # run the test
    _run_tests( control_tests, do_test, False )

# ---------------------------------------------------------------------

def _run_tests( control_tests, func, test_all ):
    """Run the test function for each combination of VASSAL + VASL.

    This is, of course, going to be insanely slow, since we need to spin up a JVM
    and initialize VASSAL/VASL each time :-/
    """

    # locate all VASL modules and VASSAL engines
    vasl_mods = control_tests.get_vasl_mods()
    vassal_engines = control_tests.get_vassal_engines()

    # check if we want to test all VASSAL+VASL combinations (nb: if not, we test against only one combination,
    # and since they all should give the same results, it doesn't matter which one.
    if not test_all:
        vasl_mods = [ random.choice( vasl_mods ) ]
        vassal_engines = [ random.choice( vassal_engines ) ]

    # FUDGE! If we are running the tests against a remote server, we still need to be able to run
    # the VASSAL shim locally (to dump VASSAL save files), so we need to set up things up enough
    # for this to work.
    if control_tests.server_url:
        vasl_mods_local = control_tests._do_get_vasl_mods() #pylint: disable=protected-access
        globvars.vasl_mod = DummyVaslMod( random.choice( vasl_mods_local ) )

    # run the test for each VASSAL+VASL
    for vassal_engine in vassal_engines:
        control_tests.set_vassal_engine( vengine=vassal_engine )
        for vasl_mod in vasl_mods:
            control_tests.set_vasl_mod( vmod=vasl_mod )
            func()

# ---------------------------------------------------------------------

def _update_vsav( fname, expected ):
    """Update a VASL scenario."""

    # read the VSAV data
    vsav_data = open( fname, "rb" ).read()

    # send the VSAV data to the front-end to be updated
    set_stored_msg( "_vsav-persistence_", base64.b64encode( vsav_data ).decode( "utf-8" ) )
    _ = set_stored_msg_marker( "_last-info_" )
    _ = set_stored_msg_marker( "_last-warning_" )
    select_menu_option( "update_vsav" )

    # wait for the results to come back
    wait_for( 2, lambda: get_stored_msg( "_vsav-persistence_" ) == "" ) # nb: wait for the front-end to receive the data
    timeout = 120 if os.name == "nt" else 60
    wait_for( timeout, lambda: get_stored_msg( "_vsav-persistence_" ) != "" ) # nb: wait for the updated data to arrive
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

def _update_vsav_and_dump( fname, expected ):
    """Update a VASL scenario and dump the result."""

    # update the VASL
    updated_vsav_data = _update_vsav( fname, expected )

    # dump the updated VSAV
    with TempFile() as temp_file:
        temp_file.write( updated_vsav_data )
        temp_file.close()
        return _dump_vsav( temp_file.name )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _dump_vsav( fname ):
    """Dump a VASL scenario file."""
    # NOTE: This is run locally, even if we're running the tests against a remote server.
    vassal_shim = VassalShim()
    return vassal_shim.dump_scenario( fname )

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
    matches = re.finditer( r"AddPiece: DynamicProperty/User-Labeled.*?- Map", vsav_dump, re.DOTALL )
    labels = [ mo.group() for mo in matches ]
    regex = re.compile( r"<html>.*?</html>" )
    matches = [ regex.search(label) for label in labels ]
    return [ mo.group() if mo else "<???>" for mo in matches ]
