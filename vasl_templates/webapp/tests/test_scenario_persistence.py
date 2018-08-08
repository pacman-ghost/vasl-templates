""" Test loading/saving scenarios. """

import json

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.tests.utils import set_template_params, select_tab, select_menu_option
from vasl_templates.webapp.tests.utils import get_stored_msg, set_stored_msg, find_child, find_children

# ---------------------------------------------------------------------

def test_scenario_persistence( webapp, webdriver ):
    """Test loading/saving scenarios."""

    # initialize
    webdriver.get( webapp.url_for( "main", scenario_persistence=1 ) )

    # initialize
    def load_scenario_fields( fields ):
        """Load the scenario fields."""
        for tab_id in fields:
            select_tab( tab_id )
            set_template_params( fields[tab_id] )

    # load the scenario fields
    scenario_params = {
        "scenario": {
            "SCENARIO_NAME": "my test scenario", "SCENARIO_LOCATION": "right here", "SCENARIO_DATE": "12/31/1945",
            "SCENARIO_WIDTH": "101",
            "PLAYER_1": "russian", "PLAYER_1_ELR": "1", "PLAYER_1_SAN": "2",
            "PLAYER_2": "german", "PLAYER_2_ELR": "3", "PLAYER_2_SAN": "4",
            "VICTORY_CONDITIONS": "just do it!", "VICTORY_CONDITIONS_WIDTH": "102",
            "SCENARIO_NOTES": [ { "caption": "note #1", "width": "" }, { "caption": "note #2", "width": "100px" } ],
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
            "VEHICLES_1": [ "a russian vehicle", "another russian vehicle" ],
            "VEHICLES_WIDTH_1": "202",
            "ORDNANCE_1": [ "a russian ordnance", "another russian ordnance" ],
            "ORDNANCE_WIDTH_1": "203",
        },
        "ob2": {
            "OB_SETUPS_2": [ { "caption": "ob setup 2", "width": "" } ],
            "OB_NOTES_2": [ { "caption": "ob note 2", "width": "" } ],
            "VEHICLES_2": [ "a german vehicle" ],
            "VEHICLES_WIDTH_2": "302",
            "ORDNANCE_2": [ "a german ordnance" ],
            "ORDNANCE_WIDTH_2": "303",
        },
    }
    load_scenario_fields( scenario_params )

    # save the scenario and check the results
    saved_scenario = _save_scenario()
    expected = {
        k.upper(): v for tab in scenario_params.values() for k,v in tab.items()
    }
    assert saved_scenario == expected

    # reset the scenario
    select_menu_option( "new_scenario" )

    # check the save results
    data = _save_scenario()
    data2 = { k: v for k,v in data.items() if v }
    assert data2 == {
        "PLAYER_1": "german", "PLAYER_1_ELR": "5", "PLAYER_1_SAN": "2",
        "PLAYER_2": "russian", "PLAYER_2_ELR": "5", "PLAYER_2_SAN": "2",
    }

    # load a scenario
    _load_scenario( saved_scenario )

    # make sure the scenario was loaded into the UI correctly
    for tab_id in scenario_params:
        select_tab( tab_id )
        for field,val in scenario_params[tab_id].items():
            if field == "SCENARIO_NOTES":
                continue # nb: this requires special handling, we do it below
            if field == "SSR":
                continue # nb: this requires special handling, we do it below
            if field in ("OB_SETUPS_1","OB_SETUPS_2"):
                continue # nb: this requires special handling, we do it below
            if field in ("OB_NOTES_1","OB_NOTES_2"):
                continue # nb: this requires special handling, we do it below
            if field in ("VEHICLES_1","ORDNANCE_1","VEHICLES_2","ORDNANCE_2"):
                continue # nb: this requires special handling, we do it below
            elem = next( c for c in ( \
                find_child( "{}[name='{}']".format(elem_type,field) ) \
                for elem_type in ["input","textarea","select"]
            ) if c )
            if elem.tag_name == "select":
                assert Select(elem).first_selected_option.get_attribute("value") == val
            else:
                assert elem.get_attribute("value") == val
    select_tab( "scenario" )
    scenario_notes = [ c.text for c in find_children("#scenario_notes-sortable li") ]
    assert scenario_notes == [ sn["caption"] for sn in scenario_params["scenario"]["SCENARIO_NOTES"] ]
    ssrs = _get_ssrs()
    assert ssrs == scenario_params["scenario"]["SSR"]
    assert _get_ob_entries("ob_setups",1) == [ obs["caption"] for obs in scenario_params["ob1"]["OB_SETUPS_1"] ]
    assert _get_ob_entries("ob_setups",2) == [ obs["caption"] for obs in scenario_params["ob2"]["OB_SETUPS_2"] ]
    assert _get_ob_entries("ob_notes",1) == [ obs["caption"] for obs in scenario_params["ob1"]["OB_NOTES_1"] ]
    assert _get_ob_entries("ob_notes",2) == [ obs["caption"] for obs in scenario_params["ob2"]["OB_NOTES_2"] ]
    assert _get_vo("vehicle",1) == scenario_params["ob1"]["VEHICLES_1"]
    assert _get_vo("ordnance",1) == scenario_params["ob1"]["ORDNANCE_1"]
    assert _get_vo("vehicle",2) == scenario_params["ob2"]["VEHICLES_2"]
    assert _get_vo("ordnance",2) == scenario_params["ob2"]["ORDNANCE_2"]

# ---------------------------------------------------------------------

def test_loading_ssrs( webapp, webdriver ):
    """Test loading SSR's."""

    # initialize
    webdriver.get( webapp.url_for( "main", scenario_persistence=1 ) )
    _ = _save_scenario() # nb: force the "scenario-persistence" element to be created

    # initialize
    def do_test( ssrs ): # pylint: disable=missing-docstring
        _load_scenario( { "SSR": ssrs } )
        assert _get_ssrs() == ssrs

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
    webdriver.get( webapp.url_for( "main", scenario_persistence=1, store_msgs=1 ) )
    _ = _save_scenario() # nb: force the "scenario-persistence" element to be created

    # load a scenario that has unknown vehicles/ordnance
    scenario_params = {
        "VEHICLES_1": [ "unknown vehicle 1a", "unknown vehicle 1b" ],
        "ORDNANCE_1":  [ "unknown ordnance 1a", "unknown ordnance 1b" ],
        "VEHICLES_2": [ "unknown vehicle 2" ],
        "ORDNANCE_2":  [ "unknown ordnance 2" ],
    }
    _load_scenario( scenario_params )
    last_warning = get_stored_msg( "_last-warning_" )
    assert last_warning.startswith( "Unknown vehicles/ordnance:" )
    for vals in scenario_params.values():
        assert all( v in last_warning for v in vals )

# ---------------------------------------------------------------------

def _load_scenario( scenario ):
    """Load a scenario into the UI."""
    set_stored_msg( "scenario_persistence", json.dumps(scenario) )
    select_menu_option( "load_scenario" )

def _save_scenario():
    """Save the scenario."""
    select_menu_option( "save_scenario" )
    data = get_stored_msg( "scenario_persistence" )
    return json.loads( data )

def _get_ssrs():
    """Get the SSR's from the UI."""
    select_tab( "scenario" )
    return [ c.text for c in find_children("#ssr-sortable li") ]

def _get_ob_entries( ob_type, player_id ):
    """Get the OB setup/notes from the UI."""
    select_tab( "ob{}".format( player_id ) )
    return [
        c.text
        for c in find_children( "#{}-sortable_{} li".format( ob_type, player_id ) )
    ]

def _get_vo( vo_type, player_id ):
    """Get the vehicles/ordnance from the UI."""
    select_tab( "ob{}".format( player_id ) )
    return [
        c.text
        for c in find_children( "#{}-sortable_{} li".format( vo_type, player_id ) )
    ]
