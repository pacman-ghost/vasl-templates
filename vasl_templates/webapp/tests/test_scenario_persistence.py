""" Test loading/saving scenarios. """

import json
import itertools
import re

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.config.constants import APP_NAME, APP_VERSION
from vasl_templates.webapp.tests.utils import \
    init_webapp, get_nationality_display_name, load_scenario_params, select_tab, select_menu_option, \
    get_sortable_entry_text, get_sortable_vo_names, get_stored_msg, set_stored_msg, set_stored_msg_marker, \
    find_child, find_children, wait_for

# this table lists all parameters stored in a scenario
ALL_SCENARIO_PARAMS = {
    "scenario": [
        "SCENARIO_NAME", "SCENARIO_ID",
        "SCENARIO_LOCATION", "SCENARIO_THEATER",
        "SCENARIO_DATE", "SCENARIO_WIDTH",
        "PLAYER_1", "PLAYER_1_ELR", "PLAYER_1_SAN",
        "PLAYER_2", "PLAYER_2_ELR", "PLAYER_2_SAN",
        "VICTORY_CONDITIONS", "VICTORY_CONDITIONS_WIDTH",
        "SCENARIO_NOTES",
        "SSR", "SSR_WIDTH",
    ],
    "ob1": [
        "OB_SETUPS_1", "OB_NOTES_1",
        "OB_VEHICLES_1", "OB_VEHICLES_WIDTH_1", "OB_VEHICLES_MA_NOTES_WIDTH_1",
        "OB_ORDNANCE_1", "OB_ORDNANCE_WIDTH_1", "OB_ORDNANCE_MA_NOTES_WIDTH_1",
    ],
    "ob2": [
        "OB_SETUPS_2", "OB_NOTES_2",
        "OB_VEHICLES_2", "OB_VEHICLES_WIDTH_2", "OB_VEHICLES_MA_NOTES_WIDTH_2",
        "OB_ORDNANCE_2", "OB_ORDNANCE_WIDTH_2", "OB_ORDNANCE_MA_NOTES_WIDTH_2",
    ],
}

# ---------------------------------------------------------------------

def test_scenario_persistence( webapp, webdriver ): #pylint: disable=too-many-statements,too-many-locals,too-many-branches
    """Test loading/saving scenarios."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct: ct.set_vo_notes_dir( dtype="test" )
    )

    def check_ob_tabs( *args ):
        """Check that the OB tabs have been set correctly."""
        for player_no in [1,2]:
            elem = find_child( "#tabs .ui-tabs-nav a[href='#tabs-ob{}']".format( player_no ) )
            nat = args[  player_no-1 ]
            assert elem.text.strip() == "{} OB".format( get_nationality_display_name(nat) )

    def check_window_title( expected ):
        """Check the window title."""
        if expected:
            expected = "{} - {}".format( APP_NAME, expected )
        else:
            expected = APP_NAME
        assert webdriver.title == expected

    # load the scenario fields
    SCENARIO_PARAMS = {
        "scenario": {
            "SCENARIO_NAME": "my test scenario",
            "SCENARIO_ID": "xyz123",
            "SCENARIO_LOCATION": "right here",
            "SCENARIO_THEATER": "PTO",
            "SCENARIO_DATE": "12/31/1945",
            "SCENARIO_WIDTH": "101",
            "PLAYER_1": "russian", "PLAYER_1_ELR": "1", "PLAYER_1_SAN": "2",
            "PLAYER_2": "german", "PLAYER_2_ELR": "3", "PLAYER_2_SAN": "4",
            "VICTORY_CONDITIONS": "just do it!", "VICTORY_CONDITIONS_WIDTH": "102",
            "SCENARIO_NOTES": [
                { "caption": "note #1", "width": "" },
                { "caption": "note #2", "width": "100px" }
            ],
            "SSR": [ "This is an SSR.", "This is another SSR." ],
            "SSR_WIDTH": "103",
        },
        "ob1": {
            "OB_SETUPS_1": [
                { "caption": "ob setup 1a", "width": "" },
                { "caption": "ob setup 1b", "width": "200px" }
            ],
            "OB_NOTES_1": [
                { "caption": "ob note 1a", "width": "10em" },
                { "caption": "ob note 1b", "width": "" }
            ],
            "OB_VEHICLES_1": [ "a russian vehicle", "another russian vehicle" ],
            "OB_VEHICLES_WIDTH_1": "202",
            "OB_VEHICLES_MA_NOTES_WIDTH_1": "203",
            "OB_ORDNANCE_1": [ "a russian ordnance", "another russian ordnance" ],
            "OB_ORDNANCE_WIDTH_1": "204",
            "OB_ORDNANCE_MA_NOTES_WIDTH_1": "205",
        },
        "ob2": {
            "OB_SETUPS_2": [ { "caption": "ob setup 2", "width": "" } ],
            "OB_NOTES_2": [ { "caption": "ob note 2", "width": "" } ],
            "OB_VEHICLES_2": [ "a german vehicle" ],
            "OB_VEHICLES_WIDTH_2": "302",
            "OB_VEHICLES_MA_NOTES_WIDTH_2": "303",
            "OB_ORDNANCE_2": [ "a german ordnance" ],
            "OB_ORDNANCE_WIDTH_2": "304",
            "OB_ORDNANCE_MA_NOTES_WIDTH_2": "305",
        },
    }
    load_scenario_params( SCENARIO_PARAMS )
    check_window_title( "my test scenario (xyz123)" )
    check_ob_tabs( "russian", "german" )
    assert_scenario_params_complete( SCENARIO_PARAMS, True )

    # save the scenario and check the results
    saved_scenario = save_scenario()
    assert saved_scenario["_app_version"] == APP_VERSION
    scenario_creation_time = saved_scenario["_creation_time"]
    assert saved_scenario["_last_update_time"] == scenario_creation_time
    expected = {
        k: v for tab in SCENARIO_PARAMS.values() for k,v in tab.items()
    }
    mo = re.search( r"^(\d{2})/(\d{2})/(\d{4})$", expected["SCENARIO_DATE"] )
    expected["SCENARIO_DATE"] = "{}-{}-{}".format( mo.group(3), mo.group(1), mo.group(2) ) # nb: convert from ISO-8601
    saved_scenario2 = { k: v for k,v in saved_scenario.items() if not k.startswith("_") }
    for key in saved_scenario2:
        if re.search( r"^OB_(VEHICLES|ORDNANCE)_\d$", key ):
            for vo_entry in saved_scenario2[key]:
                del vo_entry["id"]
    for key in expected:
        if re.search( r"^OB_(VEHICLES|ORDNANCE)_\d$", key ):
            expected[key] = [ { "name": name } for name in expected[key] ]
    for player_no in (1,2):
        for vo_type in ("OB_SETUPS","OB_NOTES"):
            entries = expected[ "{}_{}".format( vo_type, player_no ) ]
            for i,entry in enumerate(entries):
                entry["id"] = 1+i
        for vo_type in ("OB_VEHICLES","OB_ORDNANCE"):
            entries = expected[ "{}_{}".format( vo_type, player_no ) ]
            for i,entry in enumerate(entries):
                entry["seq_id"] = 1+i
    for i,entry in enumerate(expected["SCENARIO_NOTES"]):
        entry["id"] = 1+i
    assert saved_scenario2 == expected

    # make sure that our list of scenario parameters is correct
    lhs = set( saved_scenario2.keys() )
    rhs = set( itertools.chain( *ALL_SCENARIO_PARAMS.values() ) )
    assert lhs == rhs

    # reset the scenario and check the save results
    _ = set_stored_msg_marker( "_last-info_" )
    select_menu_option( "new_scenario" )
    wait_for( 2, lambda: get_stored_msg("_last-info_") == "The scenario was reset." )
    check_window_title( "" )
    check_ob_tabs( "german", "russian" )
    data = save_scenario()
    assert data["_app_version"] == APP_VERSION
    assert data["_last_update_time"] == data["_creation_time"]
    assert data["_creation_time"] > scenario_creation_time
    data2 = { k: v for k,v in data.items() if not k.startswith("_") and v }
    assert data2 == {
        "SCENARIO_THEATER": "ETO",
        "PLAYER_1": "german", "PLAYER_1_ELR": "5", "PLAYER_1_SAN": "2",
        "OB_VEHICLES_MA_NOTES_WIDTH_1": "300px", "OB_ORDNANCE_MA_NOTES_WIDTH_1": "300px",
        "PLAYER_2": "russian", "PLAYER_2_ELR": "5", "PLAYER_2_SAN": "2",
        "OB_VEHICLES_MA_NOTES_WIDTH_2": "300px", "OB_ORDNANCE_MA_NOTES_WIDTH_2": "300px",
    }

    # initialize
    ssrs = find_child( "#ssr-sortable" )
    ob_setups1, ob_notes1 = find_child("#ob_setups-sortable_1"), find_child("#ob_notes-sortable_1")
    ob_setups2, ob_notes2 = find_child("#ob_setups-sortable_2"), find_child("#ob_notes-sortable_2")
    vehicles1, ordnance1 = find_child("#ob_vehicles-sortable_1"), find_child("#ob_ordnance-sortable_1")
    vehicles2, ordnance2 = find_child("#ob_vehicles-sortable_2"), find_child("#ob_ordnance-sortable_2")
    elems = {
        c.get_attribute("name"): c
        for elem_type in ("input","textarea","select") for c in find_children(elem_type)
    }

    # load a scenario and make sure it was loaded into the UI correctly
    load_scenario( saved_scenario )
    check_window_title( "my test scenario (xyz123)" )
    check_ob_tabs( "russian", "german" )
    for tab_id in SCENARIO_PARAMS:
        select_tab( tab_id )
        for field,val in SCENARIO_PARAMS[tab_id].items():
            if field in ("SCENARIO_NOTES","SSR"):
                continue # nb: these require special handling, we do it below
            if field in ("OB_SETUPS_1","OB_SETUPS_2","OB_NOTES_1","OB_NOTES_2"):
                continue # nb: these require special handling, we do it below
            if field in ("OB_VEHICLES_1","OB_ORDNANCE_1","OB_VEHICLES_2","OB_ORDNANCE_2"):
                continue # nb: these require special handling, we do it below
            elem = elems[ field ]
            if elem.tag_name == "select":
                assert Select(elem).first_selected_option.get_attribute("value") == val
            else:
                assert elem.get_attribute("value") == val
    select_tab( "scenario" )
    scenario_notes = [ c.text for c in find_children("#scenario_notes-sortable li") ]
    assert scenario_notes == [ sn["caption"] for sn in SCENARIO_PARAMS["scenario"]["SCENARIO_NOTES"] ]
    assert get_sortable_entry_text(ssrs) == SCENARIO_PARAMS["scenario"]["SSR"]
    select_tab( "ob1" )
    assert get_sortable_entry_text(ob_setups1) == [ obs["caption"] for obs in SCENARIO_PARAMS["ob1"]["OB_SETUPS_1"] ]
    assert get_sortable_entry_text(ob_notes1) == [ obs["caption"] for obs in SCENARIO_PARAMS["ob1"]["OB_NOTES_1"] ]
    # NOTE: We deleted the "id" fields above, so we rely on the legacy handling of loading by name :-/
    assert get_sortable_vo_names(vehicles1) == SCENARIO_PARAMS["ob1"]["OB_VEHICLES_1"]
    assert get_sortable_vo_names(ordnance1) == SCENARIO_PARAMS["ob1"]["OB_ORDNANCE_1"]
    select_tab( "ob2" )
    assert get_sortable_entry_text(ob_setups2) == [ obs["caption"] for obs in SCENARIO_PARAMS["ob2"]["OB_SETUPS_2"] ]
    assert get_sortable_entry_text(ob_notes2) == [ obs["caption"] for obs in SCENARIO_PARAMS["ob2"]["OB_NOTES_2"] ]
    assert get_sortable_vo_names(vehicles2) == SCENARIO_PARAMS["ob2"]["OB_VEHICLES_2"]
    assert get_sortable_vo_names(ordnance2) == SCENARIO_PARAMS["ob2"]["OB_ORDNANCE_2"]

    # save the scenario, make sure the timestamps are correct
    data = save_scenario()
    assert data["_creation_time"] == scenario_creation_time
    assert data["_last_update_time"] > scenario_creation_time

def assert_scenario_params_complete( scenario_params, vo_notes_enabled ):
    """Check that a set of scenario parameters is complete."""
    lhs = { k: set(v) for k,v in scenario_params.items() }
    rhs = { k: set(v) for k,v in ALL_SCENARIO_PARAMS.items() }
    if not vo_notes_enabled:
        for key in ("ob1","ob2"):
            rhs[key] = set( v for v in rhs[key] if "_MA_" not in v )
    assert lhs == rhs

# ---------------------------------------------------------------------

def test_loading_ssrs( webapp, webdriver ):
    """Test loading SSR's."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # initialize
    select_tab( "scenario" )
    sortable = find_child( "#ssr-sortable" )
    def do_test( ssrs ): # pylint: disable=missing-docstring
        load_scenario( { "SSR": ssrs } )
        assert get_sortable_entry_text(sortable) == ssrs

    # load a scenario that has SSR's into a UI with no SSR's
    do_test( [ "ssr 1", "ssr 2" ] )

    # load a scenario that has more SSR's than are currently in the UI
    do_test( [ "ssr 5", "ssr 6", "ssr 7", "ssr 8" ] )

    # load a scenario that has fewer SSR's than are currently in the UI
    do_test( [ "ssr 10", "ssr 11" ] )

    # load a scenario that has no SSR's into a UI that has SSR's
    do_test( [] )

# ---------------------------------------------------------------------

def test_unknown_vo( webapp, webdriver ):
    """Test detection of unknown vehicles/ordnance."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # load a scenario that has unknown vehicles/ordnance
    SCENARIO_PARAMS = {
        "PLAYER_1": "german",
        "OB_VEHICLES_1": [
            { "name": "unknown vehicle 1a" },
            { "name": "unknown vehicle 1b" },
        ],
        "OB_ORDNANCE_1": [
            { "name": "unknown ordnance 1a" },
            { "name": "unknown ordnance 1b" },
        ],
        "PLAYER_2": "russian",
        "OB_VEHICLES_2": [ { "name": "unknown vehicle 2" } ],
        "OB_ORDNANCE_2": [ { "name": "unknown ordnance 2" } ],
    }
    _ = set_stored_msg_marker( "_last-warning_" )
    load_scenario( SCENARIO_PARAMS )
    last_warning = get_stored_msg( "_last-warning_" )
    assert last_warning.startswith( "Unknown vehicles/ordnance:" )
    for key,vals in SCENARIO_PARAMS.items():
        if not key.startswith( ("OB_VEHICLES_","OB_ORDNANCE_") ):
            continue
        assert all( v["name"] in last_warning for v in vals )

# ---------------------------------------------------------------------

def load_scenario( scenario, webdriver=None ):
    """Load a scenario into the UI."""
    set_stored_msg( "_scenario-persistence_", json.dumps(scenario), webdriver )
    _ = set_stored_msg_marker( "_last-info_", webdriver )
    select_menu_option( "load_scenario", webdriver )
    wait_for( 2,
        lambda: get_stored_msg( "_last-info_", webdriver ) == "The scenario was loaded."
    )

def save_scenario():
    """Save the scenario."""
    marker = set_stored_msg_marker( "_scenario-persistence_" )
    select_menu_option( "save_scenario" )
    wait_for( 2, lambda: get_stored_msg("_scenario-persistence_") != marker )
    data = get_stored_msg( "_scenario-persistence_" )
    return json.loads( data )
