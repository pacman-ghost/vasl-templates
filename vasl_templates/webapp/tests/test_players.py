""" Test how players are handled. """

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.tests.utils import get_nationalities, select_tab, find_child, \
    select_droplist_val, init_webapp, load_scenario_params, get_sortable_entry_count

# ---------------------------------------------------------------------

def test_player_change( webapp, webdriver ):
    """Test changing players."""

    # initialize
    init_webapp( webapp, webdriver )
    select_tab( "scenario" )
    nationalities = get_nationalities( webapp )
    player_sel = {
        1: Select( find_child( "select[name='PLAYER_1']" ) ),
        2: Select( find_child( "select[name='PLAYER_2']" ) )
    }
    ob_tabs = {
        1: find_child( "#tabs .ui-tabs-nav a[href='#tabs-ob1']" ),
        2: find_child( "#tabs .ui-tabs-nav a[href='#tabs-ob2']" )
    }

    # make sure that the UI was updated correctly for the initial players
    for player_no in [1,2]:
        player_id = player_sel[player_no].first_selected_option.get_attribute( "value" )
        expected = "{} OB".format( nationalities[player_id]["display_name"] )
        assert ob_tabs[player_no].text.strip() == expected

    # load the OB tabs
    SCENARIO_PARAMS = {
        "ob1": {
            "OB_SETUPS_1": [ { "caption": "an ob setup", "width": "" } ],
            "OB_NOTES_1": [ { "caption": "an ob note", "width": "" } ],
            "VEHICLES_1": [ "a german vehicle" ],
            "VEHICLES_WIDTH_1": "101",
            "ORDNANCE_1": [ "a german ordnance" ],
            "ORDNANCE_WIDTH_1": "102",
        },
        "ob2": {
            "OB_SETUPS_2": [ { "caption": "another ob setup", "width": "" } ],
            "OB_NOTES_2": [ { "caption": "another ob note", "width": "" } ],
            "VEHICLES_2": [ "a russian vehicle" ],
            "VEHICLES_WIDTH_2": "201",
            "ORDNANCE_2": [ "a russian ordnance" ],
            "ORDNANCE_WIDTH_2": "202",
        },
    }
    load_scenario_params( SCENARIO_PARAMS )

    def is_ob_tab_empty( player_no ):
        """Check if an OB tab is empty."""
        select_tab( "ob{}".format( player_no ) )
        sortables = [
            find_child( "#{}-sortable_{}".format( key, player_no ) )
            for key in ["ob_setups","ob_notes","vehicles","ordnance"]
        ]
        if any( get_sortable_entry_count(s) > 0 for s in sortables ):
            return False
        widths = [
            find_child( "input[name='{}_WIDTH_{}']".format( key, player_no ) )
            for key in ["VEHICLES","ORDNANCE"]
        ]
        if any( w.get_attribute("value") for w in widths ):
            return False
        return True

    # change player 1
    select_tab( "scenario" )
    select_droplist_val( player_sel[1], "finnish" )
    assert ob_tabs[1].text.strip() == "{} OB".format( nationalities["finnish"]["display_name"] )
    assert is_ob_tab_empty( 1 )

    # change player 2
    select_tab( "scenario" )
    select_droplist_val( player_sel[2], "japanese" )
    assert ob_tabs[2].text.strip() == "{} OB".format( nationalities["japanese"]["display_name"] )
    assert is_ob_tab_empty( 2 )
