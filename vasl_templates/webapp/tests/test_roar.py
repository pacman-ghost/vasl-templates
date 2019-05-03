"""Test ROAR integration."""

import re

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.tests.utils import init_webapp, select_tab, select_menu_option, click_dialog_button, \
    set_stored_msg_marker, get_stored_msg, set_template_params, add_simple_note, \
    find_child, find_children, wait_for_elem

# ---------------------------------------------------------------------

def test_roar( webapp, webdriver ):
    """Test ROAR integration."""

    # initialize
    init_webapp( webapp, webdriver )

    # check the ROAR info panel
    _check_roar_info( webdriver, None )

    # select a ROAR scenario
    _select_roar_scenario( "fighting withdrawal" )
    _check_roar_info( webdriver, (
        ( "Fighting Withdrawal", "TEST 1" ),
        ( "Finnish", 200, "Russian", 300 ),
        ( 40, 60 )
    ) )

    # select some other ROAR scenarios
    # NOTE: The scenario name/ID are already populated, so they don't get updated with the new details.
    _select_roar_scenario( "whitewash 1" )
    _check_roar_info( webdriver, (
        ( "Fighting Withdrawal", "TEST 1" ),
        ( "American", 10, "Japanese", 0 ),
        ( 100, 0 )
    ) )
    _select_roar_scenario( "whitewash 2" )
    _check_roar_info( webdriver, (
        ( "Fighting Withdrawal", "TEST 1" ),
        ( "American", 0, "Japanese", 10 ),
        ( 0, 100 )
    ) )

    # unlink from the ROAR scenario
    btn = find_child( "#disconnect-roar" )
    btn.click()
    _check_roar_info( webdriver, None )

    # select another ROAR scenario (that has no playings)
    set_template_params( { "SCENARIO_NAME": "", "SCENARIO_ID": "" } )
    _select_roar_scenario( "no playings" )
    _check_roar_info( webdriver, (
        ( "No playings", "TEST 4" ),
        ( "British", 0, "French", 0 ),
        None
    ) )

# ---------------------------------------------------------------------

def test_setting_players( webapp, webdriver ):
    """Test setting players after selecting a ROAR scenario."""

    # initialize
    init_webapp( webapp, webdriver )

    # select a ROAR scenario
    _select_roar_scenario( "fighting withdrawal" )
    _check_players( "finnish", "russian" )

    # add something to the Player 1 OB
    select_tab( "ob1" )
    add_simple_note( find_child("#ob_setups-sortable_1"), "a setup note", None )

    # select another ROAR scenario
    select_tab( "scenario" )
    _select_roar_scenario( "whitewash 1" )
    _check_players( "finnish", "japanese" ) # nb: player 1 remains unchanged

    # add something to the Player 2 OB
    select_tab( "ob2" )
    add_simple_note( find_child("#ob_setups-sortable_2"), "another setup note", None )

    # select another ROAR scenario
    select_tab( "scenario" )
    _select_roar_scenario( "no playings" )
    _check_players( "finnish", "japanese" ) # nb: both players remain unchanged

    # reset the scenario and select a ROAR scenario with an unknown nationality
    select_menu_option( "new_scenario" )
    click_dialog_button( "OK" ) # nb: dismiss the "discard changes?" prompt
    _ = set_stored_msg_marker( "_last-warning_" )
    _select_roar_scenario( "unknown nationality" )
    _check_players( "american", "russian" )
    last_warning = get_stored_msg( "_last-warning_" )
    assert re.search( r"Unrecognized nationality.+\bMartian\b", last_warning )

# ---------------------------------------------------------------------

def _select_roar_scenario( scenario_name ):
    """Select a ROAR scenario."""
    btn = find_child( "#search-roar" )
    btn.click()
    dlg = wait_for_elem( 2, ".ui-dialog.select-roar-scenario" )
    search_field = find_child( "input", dlg )
    search_field.send_keys( scenario_name )
    elems = find_children( ".select2-results li", dlg )
    assert len(elems) == 1
    search_field.send_keys( Keys.RETURN )

def _check_roar_info( webdriver, expected ):
    """Check the state of the ROAR info panel."""

    # check if the panel is displayed or hidden
    panel = find_child( "#roar-info" )
    if not expected:
        assert not panel.is_displayed()
        return
    assert panel.is_displayed()

    # check the displayed information
    assert find_child( ".name.player1", panel ).text == expected[1][0]
    assert find_child( ".count.player1", panel ).text == "({})".format( expected[1][1] )
    assert find_child( ".name.player2", panel ).text == expected[1][2]
    assert find_child( ".count.player2", panel ).text == "({})".format( expected[1][3] )

    # check the progress bars
    progress1 = find_child( ".progressbar.player1", panel )
    progress2 = find_child( ".progressbar.player2", panel )
    if expected[2]:
        label1 = "{}%".format( expected[2][0] )
        label2 = "{}%".format( expected[2][1] )
        expected1, expected2 = 100-expected[2][0], expected[2][1]
    else:
        label1 = label2 = ""
        expected1, expected2 = 100, 0
    assert find_child( ".label", progress1 ).text == label1
    assert webdriver.execute_script( "return $(arguments[0]).progressbar('value')", progress1 ) == expected1
    assert find_child( ".label", progress2 ).text == label2
    assert webdriver.execute_script( "return $(arguments[0]).progressbar('value')", progress2 ) == expected2

def _check_players( expected1, expected2 ):
    """Check the selected players."""
    sel = Select( find_child( "select[name='PLAYER_1']" ) )
    assert sel.first_selected_option.get_attribute("value") == expected1
    sel = Select( find_child( "select[name='PLAYER_2']" ) )
    assert sel.first_selected_option.get_attribute("value") == expected2
