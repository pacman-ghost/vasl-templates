"""Test the loading of the default scenario."""
import os

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp import main
from vasl_templates.webapp.tests.utils import select_tab, find_child, get_sortable_entry_text, \
    wait_for, init_webapp

# ---------------------------------------------------------------------

def test_default_scenario( webapp, webdriver, monkeypatch ):
    """Test loading the default scenario."""

    # configure a new default scenario
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/new-default-scenario.json" )
    monkeypatch.setattr( main, "default_scenario", fname )

    # initialize
    init_webapp( webapp, webdriver )

    # wait for the scenario to load
    elem = find_child( "input[name='SCENARIO_NAME']" )
    wait_for( 5, lambda: elem.get_attribute("value") != "" )

    def check_textbox( field_name, expected ):
        """Check that a field has been loaded correctly."""
        elem = find_child( "input[name='{}']".format( field_name ) )
        assert elem.get_attribute( "value" ) == expected
    def check_textarea( field_name, expected ):
        """Check that a field has been loaded correctly."""
        elem = find_child( "textarea[name='{}']".format( field_name ) )
        assert elem.get_attribute( "value" ) == expected
    def check_droplist( field_name, expected ):
        """Check that a field has been loaded correctly."""
        elem = find_child( "select[name='{}']".format( field_name ) )
        assert Select(elem).first_selected_option.get_attribute("value") == expected

    select_tab( "scenario" )

    # check the scenario fields
    check_textbox( "SCENARIO_NAME", "default scenario name" )
    check_textbox( "SCENARIO_LOCATION", "default location" )
    check_textbox( "SCENARIO_DATE", "12/25/2000" )
    check_textbox( "SCENARIO_WIDTH", "1px" )

    # check the player fields
    check_droplist( "PLAYER_1", "american" )
    check_droplist( "PLAYER_1_ELR", "1" )
    check_droplist( "PLAYER_1_SAN", "2" )
    check_droplist( "PLAYER_2", "japanese" )
    check_droplist( "PLAYER_2_ELR", "3" )
    check_droplist( "PLAYER_2_SAN", "4" )

    # check the victory conditions
    check_textarea( "VICTORY_CONDITIONS", "default victory conditions" )
    check_textbox( "VICTORY_CONDITIONS_WIDTH", "123px" )

    # check the scenario notes
    assert get_sortable_entry_text( find_child( "#scenario_notes-sortable" ) ) \
        == [ "default scenario note #{}".format(i) for i in [1,2,3] ]
    # nb: should check the snippet widths as well (not really important for a default scenario)

    # check the SSR's
    assert get_sortable_entry_text( find_child( "#ssr-sortable" ) ) \
        == [ "default SSR #{}".format(i) for i in [1,2,3] ]
    check_textbox( "SSR_WIDTH", "999px" )

    select_tab( "ob1" )

    # check the OB setups/notes (player 1)
    assert get_sortable_entry_text( find_child( "#ob_setups-sortable_1" ) ) \
        == [ "default american OB setup #{}".format(i) for i in [1,2] ]
    assert get_sortable_entry_text( find_child( "#ob_notes-sortable_1" ) ) \
        == [ "default american OB note #{}".format(i) for i in [1,2] ]
    # nb: should check the snippet widths as well (not really important for a default scenario)

    # check the vehicles/ordnance (player 1)
    assert get_sortable_entry_text( find_child( "#ob_vehicles-sortable_1" ) ) == []
    check_textbox( "OB_VEHICLES_WIDTH_1", "110px" )
    assert get_sortable_entry_text( find_child( "#ob_ordnance-sortable_1" ) ) == []
    check_textbox( "OB_ORDNANCE_WIDTH_1", "120px" )

    select_tab( "ob2" )

    # check the OB setups/notes (player 2)
    assert get_sortable_entry_text( find_child( "#ob_setups-sortable_2" ) ) \
        == [ "default japanese OB setup #{}".format(i) for i in [1,2] ]
    assert get_sortable_entry_text( find_child( "#ob_notes-sortable_2" ) ) \
        == [ "default japanese OB note #{}".format(i) for i in [1,2] ]
    # nb: should check the snippet widths as well (not really important for a default scenario)

    # check the vehicles/ordnance (player 2)
    assert get_sortable_entry_text( find_child( "#ob_vehicles-sortable_2" ) ) == []
    check_textbox( "OB_VEHICLES_WIDTH_2", "210px" )
    assert get_sortable_entry_text( find_child( "#ob_ordnance-sortable_2" ) ) == []
    check_textbox( "OB_ORDNANCE_WIDTH_2", "211px" )

    # check that the default OB setup/note width is being used
    elem = find_child( "#ob_setups-add_2" )
    elem.click()
    elem = find_child( ".ui-dialog-buttonpane input[name='width']" )
    assert elem.get_attribute( "value" ) == "900px"
    elem.send_keys( Keys.ESCAPE )
    elem = find_child( "#ob_notes-add_2" )
    elem.click()
    elem = find_child( ".ui-dialog-buttonpane input[name='width']" )
    assert elem.get_attribute( "value" ) == "901px"
