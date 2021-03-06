""" Test checks for a dirty scenario. """

import re

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.tests import pytest_options
from vasl_templates.webapp.tests.test_scenario_persistence import ALL_SCENARIO_PARAMS
from vasl_templates.webapp.tests.test_vehicles_ordnance import add_vo
from vasl_templates.webapp.tests.utils import \
    init_webapp, select_tab, select_menu_option, add_simple_note, select_droplist_val, select_droplist_index, \
    drag_sortable_entry_to_trash, get_sortable_entry_count, \
    get_stored_msg, set_stored_msg_marker, find_child, wait_for, click_dialog_button

# ---------------------------------------------------------------------

def test_dirty_scenario_checks( webapp, webdriver ):
    """Test checking for a dirty scenario."""

    # initialize
    init_webapp( webapp, webdriver )

    # initialize
    SIMPLE_NOTES = {
        "SCENARIO_NOTES": "#scenario_notes-sortable",
        "SSR": "#ssr-sortable",
        "OB_SETUPS_1": "#ob_setups-sortable_1",
        "OB_NOTES_1": "#ob_notes-sortable_1",
        "OB_SETUPS_2": "#ob_setups-sortable_2",
        "OB_NOTES_2": "#ob_notes-sortable_2",
    }
    VEHICLE_ORDNANCE = {
        "OB_VEHICLES_1": ( "#ob_vehicles-sortable_1", 1, "a german vehicle" ),
        "OB_ORDNANCE_1": ( "#ob_ordnance-sortable_1", 1, "a german ordnance" ),
        "OB_VEHICLES_2": ( "#ob_vehicles-sortable_2", 2, "a russian vehicle" ),
        "OB_ORDNANCE_2": ( "#ob_ordnance-sortable_2", 2, "a russian ordnance" ),
    }

    def change_field( param ):
        """Make a change to a field."""
        # make a change to the specified field
        if param in SIMPLE_NOTES:
            target = find_child( SIMPLE_NOTES[param] )
            add_simple_note( target, "changed value", None )
            return target
        if param in VEHICLE_ORDNANCE:
            info = VEHICLE_ORDNANCE[param]
            target = find_child( info[0] )
            mo = re.search( r"([a-z]+)-", info[0] )
            add_vo( webdriver, mo.group(1), info[1], info[2] )
            return target
        target = next( e for e in [
            find_child( "{}[name='{}']".format( ctype, param ) )
            for ctype in ["input","select","textarea"]
        ] if e  )
        if target.tag_name in ("input","textarea"):
            prev_val = target.get_attribute( "value" )
            new_val = "01/01/2000" if param == "SCENARIO_DATE" else "changed value"
            if target.is_displayed():
                target.clear()
                target.send_keys( new_val )
            else:
                webdriver.execute_script( "arguments[0].value = arguments[1]", target, new_val )
            return target, prev_val, new_val
        elif target.tag_name == "select":
            sel = Select( target )
            prev_val = sel.first_selected_option.get_attribute( "value" )
            select_droplist_index( sel, 2 )
            new_val = sel.first_selected_option.get_attribute( "value" )
            return target, prev_val, new_val
        assert False
        return None

    def check_field( param, state ):
        """Check that a change we made to a field is still there."""
        if param in SIMPLE_NOTES:
            assert get_sortable_entry_count( state ) == 1
        elif param in VEHICLE_ORDNANCE:
            assert get_sortable_entry_count( state ) == 1
        elif state[0].tag_name in ("input","textarea"):
            assert state[0].get_attribute("value") == state[2]
        elif state[0].tag_name == "select":
            assert Select(state[0]).first_selected_option.get_attribute("value") == state[2]
        else:
            assert False

    def revert_field( param, state ):
        """Revert a change we made to a field."""
        if param in SIMPLE_NOTES:
            drag_sortable_entry_to_trash( state, 0 )
        elif param in VEHICLE_ORDNANCE:
            drag_sortable_entry_to_trash( state, 0 )
        elif state[0].tag_name in ("input","textarea"):
            if state[0].is_displayed():
                state[0].clear()
                state[0].send_keys( state[1] )
            else:
                webdriver.execute_script( "arguments[0].value = arguments[1]", state[0], state[1] )
        elif state[0].tag_name == "select":
            select_droplist_val( Select(state[0]), state[1] )
        else:
            assert False

    def check_is_dirty( expected ):
        """Check if the scenario is being flagged as dirty."""
        if expected:
            func = lambda: webdriver.title.endswith( " (*)" )
        else:
            func = lambda: not webdriver.title.endswith( " (*)" )
        # NOTE: There is a race condition here if things are not working properly. Since the window title
        # is updated on a timer, if we're expecting it to be (say) not modified, but the UI thinks that
        # it is modified, we could check the window title here, see that the scenario is being flagged
        # as not modified and continue on. The timer then fires, updates the UI to flag the scenario
        # as modified, and we will have missed the error.
        # To fix this, we force the scenario status to be updated.
        webdriver.execute_script( "update_scenario_status()" )
        wait_for( 2, func )

    def do_test( tab_id, param ):
        """Test checking for a dirty scenario."""

        # change the specified field
        check_is_dirty( False )
        select_tab( tab_id )
        state = change_field( param )
        check_is_dirty( True )

        # make sure we get asked to confirm a "new scenario" operation
        select_menu_option( "new_scenario" )
        wait_for( 2, lambda: find_child("#ask") is not None )
        elem = find_child( "#ask" )
        assert "This scenario has been changed" in elem.text

        # cancel the confirmation request, make sure the change we made is still there
        click_dialog_button( "Cancel" )
        select_tab( tab_id )
        check_field( param, state )
        check_is_dirty( True )

        # revert the change
        revert_field( param, state )
        check_is_dirty( False )

        # we should now be able to reset the scenario without a confirmation
        _ = set_stored_msg_marker( "_last-info_" )
        select_menu_option( "new_scenario" )
        wait_for( 2, lambda: get_stored_msg("_last-info_") == "The scenario was reset." )

        # change the field again
        select_tab( tab_id )
        state = change_field( param )
        check_is_dirty( True )

        # make sure we get asked to confirm a "load scenario" operation
        select_menu_option( "load_scenario" )
        wait_for( 2, lambda: find_child("#ask") is not None )
        elem = find_child( "#ask" )
        assert "This scenario has been changed" in elem.text

        # cancel the confirmation request, make sure the change we made is still there
        click_dialog_button( "Cancel" )
        select_tab( tab_id )
        check_field( param, state )
        check_is_dirty( True )

        # revert the change
        revert_field( param, state )
        check_is_dirty( False )

        # we should be able to load a scenario without a confirmation
        # NOTE: We don't do this, since it will cause the OPEN FILE dialog to come up :-/

    # change each parameter, then try to reset/load the scenario
    for tab_id,params in ALL_SCENARIO_PARAMS.items():
        for param in params:
            do_test( tab_id, param )
            if pytest_options.short_tests:
                break # nb: it's a bit excessive to check *every* parameter :-/
