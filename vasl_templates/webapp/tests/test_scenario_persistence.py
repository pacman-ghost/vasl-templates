""" Test loading/saving scenarios. """

import json

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.tests.utils import \
    get_nationalities, set_template_params, select_tab, select_menu_option, get_sortable_entry_text, \
    get_stored_msg, set_stored_msg, find_child, find_children

# ---------------------------------------------------------------------

def test_scenario_persistence( webapp, webdriver ): #pylint: disable=too-many-locals
    """Test loading/saving scenarios."""

    # initialize
    webdriver.get( webapp.url_for( "main", scenario_persistence=1 ) )
    nationalities = get_nationalities( webapp )

    def check_ob_tabs( *args ):
        """Check that the OB tabs have been set correctly."""
        for player_no in [1,2]:
            elem = find_child( "#tabs .ui-tabs-nav a[href='#tabs-ob{}']".format( player_no ) )
            nat = args[  player_no-1 ]
            assert elem.text.strip() == "{} OB".format( nationalities[nat]["display_name"] )

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
    for tab_id,fields in scenario_params.items():
        select_tab( tab_id )
        set_template_params( fields )
    check_ob_tabs( "russian", "german" )

    # save the scenario and check the results
    saved_scenario = _save_scenario()
    expected = {
        k.upper(): v for tab in scenario_params.values() for k,v in tab.items()
    }
    assert saved_scenario == expected

    # reset the scenario and check the save results
    select_menu_option( "new_scenario" )
    check_ob_tabs( "german", "russian" )
    data = _save_scenario()
    data2 = { k: v for k,v in data.items() if v }
    assert data2 == {
        "PLAYER_1": "german", "PLAYER_1_ELR": "5", "PLAYER_1_SAN": "2",
        "PLAYER_2": "russian", "PLAYER_2_ELR": "5", "PLAYER_2_SAN": "2",
    }

    # initialize
    ssrs = find_child( "#ssr-sortable" )
    ob_setups1, ob_notes1 = find_child("#ob_setups-sortable_1"), find_child("#ob_notes-sortable_1")
    ob_setups2, ob_notes2 = find_child("#ob_setups-sortable_2"), find_child("#ob_notes-sortable_2")
    vehicles1, ordnance1 = find_child("#vehicles-sortable_1"), find_child("#ordnance-sortable_1")
    vehicles2, ordnance2 = find_child("#vehicles-sortable_2"), find_child("#ordnance-sortable_2")
    elems = {
        c.get_attribute("name"): c
        for elem_type in ("input","textarea","select") for c in find_children(elem_type)
    }

    # load a scenario and make sure it was loaded into the UI correctly
    _load_scenario( saved_scenario )
    check_ob_tabs( "russian", "german" )
    for tab_id in scenario_params:
        select_tab( tab_id )
        for field,val in scenario_params[tab_id].items():
            if field in ("SCENARIO_NOTES","SSR"):
                continue # nb: these require special handling, we do it below
            if field in ("OB_SETUPS_1","OB_SETUPS_2","OB_NOTES_1","OB_NOTES_2"):
                continue # nb: these require special handling, we do it below
            if field in ("VEHICLES_1","ORDNANCE_1","VEHICLES_2","ORDNANCE_2"):
                continue # nb: these require special handling, we do it below
            elem = elems[ field ]
            if elem.tag_name == "select":
                assert Select(elem).first_selected_option.get_attribute("value") == val
            else:
                assert elem.get_attribute("value") == val
    select_tab( "scenario" )
    scenario_notes = [ c.text for c in find_children("#scenario_notes-sortable li") ]
    assert scenario_notes == [ sn["caption"] for sn in scenario_params["scenario"]["SCENARIO_NOTES"] ]
    assert get_sortable_entry_text(ssrs) == scenario_params["scenario"]["SSR"]
    select_tab( "ob1" )
    assert get_sortable_entry_text(ob_setups1) == [ obs["caption"] for obs in scenario_params["ob1"]["OB_SETUPS_1"] ]
    assert get_sortable_entry_text(ob_notes1) == [ obs["caption"] for obs in scenario_params["ob1"]["OB_NOTES_1"] ]
    assert get_sortable_entry_text(vehicles1) == scenario_params["ob1"]["VEHICLES_1"]
    assert get_sortable_entry_text(ordnance1) == scenario_params["ob1"]["ORDNANCE_1"]
    select_tab( "ob2" )
    assert get_sortable_entry_text(ob_setups2) == [ obs["caption"] for obs in scenario_params["ob2"]["OB_SETUPS_2"] ]
    assert get_sortable_entry_text(ob_notes2) == [ obs["caption"] for obs in scenario_params["ob2"]["OB_NOTES_2"] ]
    assert get_sortable_entry_text(vehicles2) == scenario_params["ob2"]["VEHICLES_2"]
    assert get_sortable_entry_text(ordnance2) == scenario_params["ob2"]["ORDNANCE_2"]

# ---------------------------------------------------------------------

def test_loading_ssrs( webapp, webdriver ):
    """Test loading SSR's."""

    # initialize
    webdriver.get( webapp.url_for( "main", scenario_persistence=1 ) )
    _ = _save_scenario() # nb: force the "scenario-persistence" element to be created

    # initialize
    select_tab( "scenario" )
    sortable = find_child( "#ssr-sortable" )
    def do_test( ssrs ): # pylint: disable=missing-docstring
        _load_scenario( { "SSR": ssrs } )
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
    webdriver.get( webapp.url_for( "main", scenario_persistence=1, store_msgs=1 ) )
    _ = _save_scenario() # nb: force the "scenario-persistence" element to be created

    # load a scenario that has unknown vehicles/ordnance
    scenario_params = {
        "PLAYER_1": "german",
        "VEHICLES_1": [ "unknown vehicle 1a", "unknown vehicle 1b" ],
        "ORDNANCE_1":  [ "unknown ordnance 1a", "unknown ordnance 1b" ],
        "PLAYER_2": "russian",
        "VEHICLES_2": [ "unknown vehicle 2" ],
        "ORDNANCE_2":  [ "unknown ordnance 2" ],
    }
    _load_scenario( scenario_params )
    last_warning = get_stored_msg( "_last-warning_" )
    assert last_warning.startswith( "Unknown vehicles/ordnance:" )
    for key,vals in scenario_params.items():
        if not key.startswith( ("VEHICLES_","ORDNANCE_") ):
            continue
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
