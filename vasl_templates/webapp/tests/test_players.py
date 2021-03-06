""" Test how players are handled. """

from vasl_templates.webapp.tests.utils import get_nationality_display_name, select_tab, find_child, \
    init_webapp, load_scenario_params, set_player, get_player_nat, \
    wait_for, get_sortable_entry_count, click_dialog_button

# ---------------------------------------------------------------------

def test_player_change( webapp, webdriver ):
    """Test changing players."""

    # initialize
    init_webapp( webapp, webdriver )
    select_tab( "scenario" )
    ob_tabs = {
        1: find_child( "#tabs .ui-tabs-nav a[href='#tabs-ob1']" ),
        2: find_child( "#tabs .ui-tabs-nav a[href='#tabs-ob2']" )
    }

    # make sure that the UI was updated correctly for the initial players
    for player_no in [1,2]:
        player_nat = get_player_nat( player_no )
        expected = "{} OB".format( get_nationality_display_name( player_nat ) )
        assert ob_tabs[ player_no ].text.strip() == expected

    # check that we can change the player nationalities without being asked to confirm
    # nb: the frontend ignores the vehicle/ordnance snippet widths when deciding if to ask for confirmation
    VO_WIDTHS = {
        "ob1": { "OB_VEHICLES_WIDTH_1": 123 },
        "ob2": { "OB_ORDNANCE_WIDTH_2": 456 },
    }
    load_scenario_params( VO_WIDTHS )
    set_player( 1, "russian" )
    assert ob_tabs[1].text.strip() == "{} OB".format( get_nationality_display_name("russian") )
    set_player( 2, "german" )
    assert ob_tabs[2].text.strip() == "{} OB".format( get_nationality_display_name("german") )

    # load the OB tabs
    SCENARIO_PARAMS = {
        "ob1": {
            "OB_SETUPS_1": [ { "caption": "an ob setup", "width": "" } ],
        },
        "ob2": {
            "OB_VEHICLES_2": [ "a german vehicle" ],
        },
    }
    load_scenario_params( SCENARIO_PARAMS )

    def get_sortable_counts( player_no ):
        """Get the contents of the player's OB tab."""
        sortables = [
            find_child( "#{}-sortable_{}".format( key, player_no ) )
            for key in ["ob_setups","ob_notes","ob_vehicles","ob_ordnance"]
        ]
        return [ get_sortable_entry_count(s) for s in sortables ]

    for player_no in [1,2]:

        # try to change the player's nationality
        set_player( player_no, "finnish" )
        wait_for( 2, lambda: find_child("#ask") )

        # cancel the confirmation request and make sure nothing changed
        click_dialog_button( "Cancel" )
        nat_id = "russian" if player_no == 1 else "german"
        assert ob_tabs[player_no].text.strip() == "{} OB".format( get_nationality_display_name(nat_id) )
        assert get_sortable_counts( player_no ) == \
            [1,0,0,0] if player_no == 1 else [0,0,1,0]

        # try to change the player's nationality
        set_player( player_no, "finnish" )
        wait_for( 2, lambda: find_child("#ask") )

        # confirm the request and make sure the OB tab was cleared
        click_dialog_button( "OK" )
        assert ob_tabs[player_no].text.strip() == "{} OB".format( get_nationality_display_name("finnish") )
        assert get_sortable_counts( player_no ) == [0,0,0,0]
