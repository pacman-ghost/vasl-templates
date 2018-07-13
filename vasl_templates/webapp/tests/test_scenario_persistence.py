""" Test loading/saving scenarios. """

import json
import time

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.tests.utils import set_template_params, select_tab
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
            "PLAYER_1": "british", "PLAYER_1_ELR": "1", "PLAYER_1_SAN": "2",
            "PLAYER_2": "french", "PLAYER_2_ELR": "3", "PLAYER_2_SAN": "4",
            "VICTORY_CONDITIONS": "just do it!", "VICTORY_CONDITIONS_WIDTH": "102",
            "SSR": [ "This is an SSR.", "This is another SSR." ],
            "SSR_WIDTH": "103",
        },
        "ob1": {
            "OB_SETUP_1": "Player 1's OB", "OB_SETUP_WIDTH_1": "201",
        },
        "ob2": {
            "OB_SETUP_2": "Player 2's OB", "OB_SETUP_WIDTH_2": "301",
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
    elem = find_child( "#menu" )
    elem.click()
    elem = find_child( "a.PopMenu-Link[data-name='new']" )
    elem.click()
    elem = find_child( ".growl-close" )
    elem.click()
    time.sleep( 0.5 )

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
            if field == "SSR":
                continue # nb: this requires special handling, we do it below
            elem = next( c for c in ( \
                find_child( "{}[name='{}']".format(elem_type,field) ) \
                for elem_type in ["input","textarea","select"]
            ) if c )
            if elem.tag_name == "select":
                assert Select(elem).first_selected_option.get_attribute("value") == val
            else:
                assert elem.get_attribute("value") == val
    ssrs = _get_ssrs()
    assert ssrs == scenario_params["scenario"]["SSR"]

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

def _load_scenario( scenario ):
    """Load a scenario into the UI."""
    set_stored_msg( "scenario_persistence", json.dumps(scenario) )
    elem = find_child( "#menu" )
    elem.click()
    elem = find_child( "a.PopMenu-Link[data-name='load']" )
    elem.click()

def _save_scenario():
    """Save the scenario."""
    elem = find_child( "#menu" )
    elem.click()
    elem = find_child( "a.PopMenu-Link[data-name='save']" )
    elem.click()
    data = get_stored_msg( "scenario_persistence" )
    return json.loads( data )

def _get_ssrs():
    """Get the SSR's from the UI."""
    select_tab( "scenario" )
    return [ c.text for c in find_children("#ssr-sortable li") ]
