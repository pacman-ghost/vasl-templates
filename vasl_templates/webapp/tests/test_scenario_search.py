"""" Test scenario search. """

import os
import base64
import time

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import StaleElementReferenceException

from vasl_templates.webapp.tests import pytest_options
from vasl_templates.webapp.tests.test_scenario_persistence import save_scenario, load_scenario
from vasl_templates.webapp.tests.test_vassal import run_vassal_tests
from vasl_templates.webapp.tests.utils import init_webapp, select_tab, new_scenario, \
    set_player, set_template_params, set_scenario_date, get_player_nat, get_theater, set_theater, \
    get_turn_track_nturns, \
    wait_for, wait_for_elem, find_child, find_children, get_css_classes, set_stored_msg, click_dialog_button

# ---------------------------------------------------------------------

def test_scenario_cards( webapp, webdriver ):
    """Test showing scenario cards."""

    # initialize
    init_webapp( webapp, webdriver )

    # search for the "full" scenario and check the scenario card
    _do_scenario_search( "full", [1], webdriver )
    card = _unload_scenario_card()
    assert card == {
        "scenario_name": "Full content scenario", "scenario_id": "FCS-1",
        "scenario_url": "https://aslscenarioarchive.com/scenario.php?id=1",
        "scenario_location": "Some place", "scenario_date": "31st December, 1945",
        "theater": "PTO", "turn_count": "4-5", "playing_time": "1\u00bc hours",
        "icons": [ "aslsk.png", "deluxe.png", "night.png", "oba.png" ],
        "designer": "Joe Author",
        "publication": "ASL Journal",
        "publication_url": "https://aslscenarioarchive.com/viewPub.php?id=PUB-1",
        "publication_date": "3rd February, 2001",
        "publisher": "Avalon Hill",
        "publisher_url": "https://aslscenarioarchive.com/viewPublisher.php?id=42",
        "prev_publication": "Prior version", "revised_publication": "Revised version",
        "overview": "This is a really good scenario.",
        "map_url": "MAP:[1.23,4.56]",
        "defender_name": "Dutch", "defender_desc": "1st Dutch Army",
        "attacker_name": "Romanian", "attacker_desc": "1st Romanian Army",
        "balances": { "asa": [
            { "name": "Dutch", "wins": 3, "percentage": 30 }, { "name": "Romanian", "wins": 7, "percentage": 70 }
        ] },
        "oba": [
            [ "Dutch", "1B", "1R" ], [ "Romanian", "-", "-" ]
        ],
        "boards": "1, 2, RB (4)", # n: the (4) is the number of map previews
        "map_previews": [
            "chuck:1600000000|screenshot3.png",
            "bob:1500000000|screenshot2.png",
            "alice:1400000000|screenshot1.png",
            "asl-scenario-archive.png"
        ],
        "overlays": "1, 2, OG1",
        "extra_rules": "Some extra rules",
        "errata": [
            [ "Errata #1", "over there" ],
            [ "Errata #2", "right here" ]
        ]
    }

    # search for the "empty" scenario and check the scenario card
    _do_scenario_search( "Untitled", ["no-content"], webdriver )
    card = _unload_scenario_card()
    assert card == {
        "scenario_name": "Untitled scenario (#no-content)",
        "scenario_url": "https://aslscenarioarchive.com/scenario.php?id=no-content",
    }

# ---------------------------------------------------------------------

def test_import_scenario( webapp, webdriver ):
    """Test importing a scenario."""

    # initialize
    init_webapp( webapp, webdriver )

    # import the "full" scenario
    dlg = _do_scenario_search( "full", [1], webdriver )
    find_child( "button.import", dlg ).click()
    wait_for( 2, lambda: _check_scenario(
        SCENARIO_NAME="Full content scenario", SCENARIO_ID="FCS-1",
        SCENARIO_LOCATION="Some place",
        SCENARIO_TURNS="5",
        PLAYER_1="dutch", PLAYER_1_DESCRIPTION="1st Dutch Army",
        PLAYER_2="romanian", PLAYER_2_DESCRIPTION="1st Romanian Army",
        THEATER="PTO"
    ) )

    # import the "empty" scenario
    _unlink_scenario()
    dlg = _do_scenario_search( "Untitled", ["no-content"], webdriver )
    _import_scenario_and_confirm( dlg )
    # NOTE: Since there are no players defined in the scenario, what's on-screen will be left unchanged.
    wait_for( 2, lambda: _check_scenario(
        SCENARIO_NAME="Untitled scenario (#no-content)", SCENARIO_ID="",
        SCENARIO_LOCATION="",
        SCENARIO_TURNS="",
        PLAYER_1="dutch", PLAYER_1_DESCRIPTION="",
        PLAYER_2="romanian", PLAYER_2_DESCRIPTION="",
        THEATER="ETO"
    ) )

def _check_scenario( **kwargs ):
    """Check the scenario import."""
    for key in ["SCENARIO_NAME","SCENARIO_ID","SCENARIO_LOCATION","PLAYER_1_DESCRIPTION","PLAYER_2_DESCRIPTION"]:
        elem = find_child( "input[name='{}']".format( key ) )
        if elem.get_attribute( "value" ) != kwargs[ key ]:
            return False
    if get_player_nat( 1 ) != kwargs["PLAYER_1"] or get_player_nat( 2 ) != kwargs["PLAYER_2"]:
        return False
    if get_theater() != kwargs[ "THEATER" ]:
        return False
    if get_turn_track_nturns() != kwargs["SCENARIO_TURNS"]:
        return False
    return True

# ---------------------------------------------------------------------

def test_import_warnings( webapp, webdriver ): #pylint: disable=too-many-statements
    """Test warnings when importing a scenario."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # import a scenario on top of an empty scenario
    dlg = _do_scenario_search( "full", [1], webdriver )
    find_child( "button.import", dlg ).click()
    wait_for( 2, lambda: not dlg.is_displayed() )

    def check_warnings( expected ): #pylint: disable=missing-docstring
        warnings = find_children( ".warnings input[type='checkbox']", dlg )
        return [ w.get_attribute( "name" ) for w in warnings ] == expected

    def do_test( param_name, expected_warning, expected_val, curr_val="CURR-VAL" ): #pylint: disable=missing-docstring

        # start with a new scenario
        new_scenario()

        # set the scenario parameter
        set_template_params( { param_name: curr_val } )

        # import a scenario
        _do_scenario_search( "full", [1], webdriver )
        _click_import_button( find_child( "#scenario-search" ) )

        # check if any warnings were expected
        elem = find_child( "[name='{}']".format( param_name ) )
        if expected_warning:
            # yup - make sure they are being shown
            wait_for( 2, lambda: check_warnings( [expected_warning] ) )
            # cancel the import
            find_child( "button.cancel-import", dlg ).click()
            wait_for( 2, lambda: not find_child( ".warnings", dlg ).is_displayed() )
            # do the import again, and accept it
            _import_scenario_and_confirm( dlg )
            assert elem.get_attribute( "value" ) == expected_val
        else:
            # nope - check that the import was done
            wait_for( 2, lambda: not dlg.is_displayed() )
            # assert not dlg.is_displayed()
            assert elem.get_attribute( "value" ) == expected_val

    # do the tests
    do_test( "SCENARIO_NAME", "scenario_name", "Full content scenario" )
    do_test( "SCENARIO_ID", "scenario_display_id", "FCS-1" )
    do_test( "SCENARIO_LOCATION", "scenario_location", "Some place" )
    do_test( "SCENARIO_DATE", "scenario_date_iso", "12/31/1945", curr_val="01/02/1940" )
    do_test( "SCENARIO_THEATER", None, "PTO", curr_val="Burma" )
    do_test( "PLAYER_1", None, "dutch", curr_val="german" )
    do_test( "PLAYER_1_DESCRIPTION", "defender_desc", "1st Dutch Army" )
    do_test( "PLAYER_2", None, "romanian", curr_val="german" )
    do_test( "PLAYER_2_DESCRIPTION", "attacker_desc", "1st Romanian Army" )

    # test importing a scenario on top of existing OB owned by the same nationality
    new_scenario()
    load_scenario( {
        "PLAYER_1": "dutch",
    } )
    dlg = _do_scenario_search( "full", [1], webdriver )
    find_child( "button.import", dlg ).click()
    check_warnings( [] )
    wait_for( 2, lambda: not dlg.is_displayed() )

    # test importing a scenario on top of existing OB owned by the same nationality
    new_scenario()
    load_scenario( {
        "PLAYER_1": "dutch",
        "OB_SETUPS_1": [ { "caption": "Dutch setup note" } ]
    } )
    dlg = _do_scenario_search( "full", [1], webdriver )
    find_child( "button.import", dlg ).click()
    wait_for( 2, lambda: not dlg.is_displayed() )

    # test importing a scenario on top of existing OB owned by the different nationality
    new_scenario()
    load_scenario( {
        "PLAYER_1": "german",
        "OB_SETUPS_1": [ { "caption": "German setup note" } ]
    } )
    dlg = _do_scenario_search( "full", [1], webdriver )
    find_child( "button.import", dlg ).click()
    warnings = wait_for( 2, lambda: find_children( ".warnings input[type='checkbox']", dlg ) )
    assert [ w.get_attribute( "name" ) for w in warnings ] == [ "defender_name" ]
    assert not warnings[0].is_selected()
    wait_for( 2, lambda: warnings[0].is_displayed )
    time.sleep( 0.1 ) # nb: wait for the slide to finish :-/
    warnings[0].click()
    find_child( "button.confirm-import", dlg ).click()
    assert not dlg.is_displayed()
    assert get_player_nat( 1 ) == "dutch"

# ---------------------------------------------------------------------

def test_oba_info( webapp, webdriver ):
    """Test showing OBA info in the scenario card."""

    # initialize
    init_webapp( webapp, webdriver )

    def check_oba_info( card, expected ):
        """Check the OBA info."""
        assert card["oba"] == expected
        assert "oba.png" in card["icons"]

    # search for the "OBA test" scenario
    dlg = _do_scenario_search( "OBA test", ["5a"], webdriver )
    expected = [
        [ "Finnish", "6B", "3R", "Plentiful Ammo included" ],
        [ "German", "1B", "2R", "a comment", "another comment" ]
    ]
    check_oba_info( _unload_scenario_card(), expected )

    # import the scenario and check the OBA info
    find_child( "button.import", dlg ).click()
    wait_for( 2, lambda: not dlg.is_displayed() )
    check_oba_info( _get_scenario_info(), expected )

    # change the scenario date and check the OBA info
    set_scenario_date( "01/02/1943" )
    check_oba_info( _get_scenario_info(), [
        [ "Finnish", "8B", "3R", "Plentiful Ammo included" ],
        [ "German", "1B", "2R", "a comment", "another comment" ],
        "Based on a scenario date of 1/43."
    ] )

    # change the scenario date and check the OBA info
    set_scenario_date( "" )
    check_oba_info( _get_scenario_info(), expected )

    # check a scenario where only the defender has OBA
    _do_scenario_search( "Defender OBA", ["5b"], webdriver )
    check_oba_info( _unload_scenario_card(), [
        [ "Burmese", "-", "-" ],
        None
    ] )

    # check a scenario where the attacker has OBA, the defender is an unknwon nationality
    _do_scenario_search( "Attacker OBA", ["5c"], webdriver )
    check_oba_info( _unload_scenario_card(), [
        [ "The Other Guy", "?", "?" ],
        [ "Russian", "3B", "4R" ]
    ] )

# ---------------------------------------------------------------------

def test_asa_theater_mappings( webapp, webdriver ):
    """Test mapping ASA theaters."""

    # initialize
    init_webapp( webapp, webdriver )

    def do_test( query, scenario_id, expected, warning=None ):
        new_scenario()
        set_theater( "DTO" )
        dlg = _do_scenario_search( query, [scenario_id], webdriver )
        _click_import_button( dlg )
        if warning:
            _check_warnings( [], [warning] )
            find_child( "button.confirm-import", dlg ).click()
        wait_for( 2, lambda: not dlg.is_displayed() )
        assert get_theater() == expected

    # test some basic theater mappings
    do_test( "WTO", "3a", "ETO" )
    do_test( "MTO", "3b", "ETO" )
    do_test( "KFW", "3c", "Korea" )

    # test mapping CBI scenarios
    do_test( "China", "3d1", "PTO" )
    do_test( "Burma", "3d2", "Burma" )
    do_test( "India", "3d3", "PTO" )

    # test a theater that has no mapping
    do_test( "Africa", "3e", "other", warning="Unknown theater: Africa" )

# ---------------------------------------------------------------------

def test_unknown_nats( webapp, webdriver ):
    """Test importing scenarios with unknown player nationalities."""

    # initialize
    init_webapp( webapp, webdriver )

    # test importing a scenario with 2 completely unknown player nationalities
    set_player( 1, "french" )
    set_player( 2, "italian" )
    dlg = _do_scenario_search( "Unknown players", ["4a"], webdriver )
    _click_import_button( dlg )
    _check_warnings( [], ["Unknown player: Eastasia","Unknown player: Oceania"] )
    expected_bgraphs = { "asa": [
        { "name": "Eastasia", "wins": 2, "percentage": 67 },
        { "name": "Oceania", "wins": 1, "percentage": 33 }
    ] }
    assert _unload_balance_graphs( dlg ) == expected_bgraphs
    find_child( "button.confirm-import", dlg ).click()
    wait_for( 2, lambda: not find_child( "#scenario-search" ).is_displayed() )
    assert get_player_nat( 1 ) == "french"
    assert get_player_nat( 2 ) == "italian"

    # test matching nationalities (partial name matches)
    new_scenario()
    dlg = _do_scenario_search( "partial nationality matches", ["4b"], webdriver )
    find_child( "button.import", dlg ).click()
    wait_for( 2, lambda: not find_child( "#scenario-search" ).is_displayed() )
    assert get_player_nat( 1 ) == "russian"
    assert get_player_nat( 2 ) == "japanese"

    # test nationality mapping
    new_scenario()
    dlg = _do_scenario_search( "nationality mapping", ["4c"], webdriver )
    find_child( "button.import", dlg ).click()
    wait_for( 2, lambda: not find_child( "#scenario-search" ).is_displayed() )
    assert get_player_nat( 1 ) == "british"
    assert get_player_nat( 2 ) == "british~canadian"

# ---------------------------------------------------------------------

def test_roar_matching( webapp, webdriver ):
    """Test matching scenarios with ROAR scenarios."""

    # initialize
    init_webapp( webapp, webdriver )

    # search for the "full" scenario
    _do_scenario_search( "full", [1], webdriver )
    card = _unload_scenario_card()
    assert card["balances"] == { "asa": [
        { "name": "Dutch", "wins": 3, "percentage": 30 },
        { "name": "Romanian", "wins": 7, "percentage": 70 }
    ] }

    # search for the "empty" scenario
    _do_scenario_search( "Untitled", ["no-content"], webdriver )
    card = _unload_scenario_card()
    assert "balances" not in card

    # search for "Fighting Withdrawal"
    _do_scenario_search( "Withdrawal", ["2"], webdriver )
    card = _unload_scenario_card()
    assert card["balances"] == {
        # NOTE: The 2 sides in the ROAR balance graph should have been swapped around
        # to match what's in the ASL Scenario Archive.
        "roar": [
            { "name": "Russian", "wins": 325, "percentage": 54 },
            { "name": "Finnish", "wins": 279, "percentage": 46 }
        ],
        "asa": [
            { "name": "Russians", "wins": 78, "percentage": 58 }, # nb: the player nationality has a trailing "s"
            { "name": "Finnish", "wins": 56, "percentage": 42 }
        ]
    }

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@pytest.mark.skipif(
    pytest_options.webapp_url is not None,
    reason = "Can't test against a remote webapp server."
)
def test_roar_matching2( webapp, webdriver ):
    """Test matching scenarios with ROAR scenarios."""

    # initialize
    init_webapp( webapp, webdriver )

    from vasl_templates.webapp.scenarios import _asa_scenarios, _match_roar_scenario
    def do_test( scenario_name, expected ): #pylint: disable=missing-docstring
        scenarios = [
            s for s in _asa_scenarios.index.values() #pylint: disable=no-member
            if s.get( "title" ) == scenario_name
        ]
        assert len(scenarios) == 1
        matches = _match_roar_scenario( scenarios[0] )
        if not isinstance( expected, list ):
            expected = [ expected ]
        assert [ ( m["roar_id"], m["name"] ) for m in matches ] == expected

    with _asa_scenarios:

        # check for no match
        do_test( "Full content scenario", [] )

        # check for an exact match
        do_test( "ROAR Exact Match", ("200","!! ROAR exact-match !!") )

        # check for multiple matches, resolved by the scenario ID
        do_test( "ROAR Exact Match 2", ("211","ROAR Exact Match 2") )

        # check for multiple matches
        # NOTE: These should be sorted in descending order of number of playings.
        do_test( "ROAR Multiple Matches", [
            ("222","ROAR Multiple Matches"), ("220","ROAR Multiple Matches"), ("221","ROAR Multiple Matches")
        ] )

# ---------------------------------------------------------------------

def test_roar_linking( webapp, webdriver ):
    """Test linking scenarios with ROAR scenarios."""

    # initialize
    init_webapp( webapp, webdriver )

    def check( bgraph, connect, disconnect ):
        """Check the scenario card."""

        # check if the balance graph is shown
        try:
            card = _unload_scenario_card()
        except StaleElementReferenceException:
            # NOTE: We can get here if the scenario card is reloaded while we're reading it.
            return False
        if bgraph:
            balance = card["balances"].get( "roar" )
            if not balance:
                return False
            if balance[0]["name"] != bgraph[0] or balance[1]["name"] != bgraph[1]:
                return False
        else:
            if "roar" in card["balances"]:
                return False

        # check if the "connect to ROAR" button is shown
        elem = find_child( "#scenario-info-dialog .connect-roar" )
        if connect:
            if not elem.is_displayed():
                return False
        else:
            if elem and elem.is_displayed():
                return False

        # check if the "disconnect from ROAR" is shown
        elem = find_child( "#scenario-info-dialog .disconnect-roar" )
        if disconnect:
            if not elem.is_displayed():
                return False
        else:
            if elem and elem.is_displayed():
                return False

        return True

    def disconnect_roar():
        """Disconnect the scenario from ROAR."""
        btn = find_child( "#scenario-info-dialog .disconnect-roar" )
        btn.click()
        wait_for( 2, lambda: not btn.is_displayed() )
        wait_for( 2, lambda: check( None, True, False ) )

    # import the "Fighting Withdrawal" scenario
    dlg = _do_scenario_search( "withdrawal", [2], webdriver )
    wait_for( 2, lambda: check( ["Russian","Finnish"], False, False ) )
    find_child( "#scenario-search button.import" ).click()
    wait_for( 2, lambda: not dlg.is_displayed() )

    # connect to another ROAR scenario
    find_child( "button.scenario-search" ).click()
    wait_for( 2, lambda: check( ["Russian","Finnish"], False, True ) )
    disconnect_roar()
    find_child( "#scenario-info-dialog .connect-roar" ).click()
    dlg = wait_for_elem( 2, ".ui-dialog.select-roar-scenario" )
    find_child( ".select2-search__field", dlg ).send_keys( "another" )
    find_child( ".select2-search__field", dlg ).send_keys( Keys.RETURN )
    wait_for( 2, lambda: check( ["British","French"], False, True ) )
    find_child( ".ui-dialog.scenario-info button.ok" ).click()

    # disconnect from the ROAR scenario
    find_child( "button.scenario-search" ).click()
    wait_for( 2, lambda: check( ["British","French"], False, True ) )
    disconnect_roar()
    find_child( ".ui-dialog.scenario-info button.ok" ).click()

    # connect to a ROAR scenario
    find_child( "button.scenario-search" ).click()
    wait_for( 2, lambda: check( None, True, False ) )
    find_child( "#scenario-info-dialog .connect-roar" ).click()
    dlg = wait_for_elem( 2, ".ui-dialog.select-roar-scenario" )
    elem = find_child( ".select2-search__field", dlg )
    elem.send_keys( "withdrawal" )
    elem.send_keys( Keys.RETURN )
    wait_for( 2, lambda: check( ["Russian","Finnish"], False, True ) )
    find_child( ".ui-dialog.scenario-info button.ok" ).click()

# ---------------------------------------------------------------------

def test_scenario_linking( webapp, webdriver ):
    """Test linking scenarios with the ASL Scenario Archive."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    def get_asa_id():
        """Get the ASL Scenario Archive scenario ID."""
        return find_child( "input[name='ASA_ID']" ).get_attribute( "value" )

    def check( asa_id ):
        """Check the current state of the scenario."""

        # check that the ASL Scenario Archive scenario ID has been set
        wait_for( 2, lambda: get_asa_id() == asa_id )

        # check that the ASL Scenario Archive scenario ID is saved correctly
        saved_scenario = save_scenario()
        assert saved_scenario[ "ASA_ID" ] == asa_id

        # reset the scenario
        new_scenario()
        assert get_asa_id() == ""

        # check that the ASL Scenario Archive scenario ID is loaded correctly
        load_scenario( saved_scenario )
        assert get_asa_id() == asa_id

    # import the "full" scenario
    _do_scenario_search( "full", [1], webdriver )
    find_child( "#scenario-search button.import" ).click()
    check( "1" )

    # import the "empty" scenario (on top of the current scenario)
    dlg = _do_scenario_search( "Untitled", ["no-content"], webdriver )
    _import_scenario_and_confirm( dlg )
    check( "no-content" )

    # import the "Fighting Withdrawal" scenario (on top of the current scenario)
    dlg = _do_scenario_search( "Fighting Withdrawal", [2], webdriver )
    _import_scenario_and_confirm( dlg )
    check( "2" )

    # unlink the scenario
    _unlink_scenario()
    check( "" )

# ---------------------------------------------------------------------

def test_scenario_upload( webapp, webdriver ):
    """Test uploading scenarios to the ASL Scenario Archive."""

    # initialize
    init_webapp( webapp, webdriver, vsav_persistence=1, scenario_persistence=1 )

    def do_upload( prep_upload, expect_ask ):
        """Upload the scenario to our test endpoint."""

        # show the scenario card
        find_child( "button.scenario-search" ).click()
        wait_for( 2, _find_scenario_card )

        # open the upload dialog
        find_child( ".ui-dialog.scenario-info button.upload" ).click()
        dlg = wait_for_elem( 2, ".ui-dialog.scenario-upload" )
        if prep_upload:
            prep_upload( dlg )

        # start the upload
        webapp.control_tests.reset_last_asa_upload()
        find_child( "button.upload", dlg ).click()
        if expect_ask:
            dlg = wait_for_elem( 2, ".ui-dialog.ask" )
            find_child( "button.ok", dlg ).click()

        # wait for the upload to be processed
        last_asa_upload = wait_for( 5, webapp.control_tests.get_last_asa_upload )
        assert last_asa_upload["user"] == user_name
        assert last_asa_upload["token"] == api_token
        return last_asa_upload

    user_name, api_token = "joe", "xyz123"
    def prep_upload( dlg ):
        """Prepare the upload."""
        assert find_child( ".scenario-name", dlg ).text == "Full content scenario"
        assert find_child( ".scenario-id", dlg ).text == "(FCS-1)"
        assert find_child( ".asa-id", dlg ).text == "(#1)"
        # NOTE: We only set the auth details once, then they should be remembered.
        find_child( "input.user", dlg ).send_keys( user_name )
        find_child( "input.token", dlg ).send_keys( api_token )

    # test uploading just a vasl-templates setup
    dlg = _do_scenario_search( "full", [1], webdriver )
    find_child( "button.import", dlg ).click()
    asa_upload = do_upload( prep_upload, True )
    assert asa_upload["user"] == user_name
    assert asa_upload["token"] == api_token
    assert "vasl_setup" not in asa_upload
    assert "screenshot" not in asa_upload

    # compare the vasl-templates setup
    saved_scenario = save_scenario()
    keys = [ k for k in saved_scenario if k.startswith("_") ]
    for key in keys:
        del saved_scenario[ key ]
        del asa_upload["vt_setup"][ key ]
    del saved_scenario[ "VICTORY_CONDITIONS" ]
    del saved_scenario[ "SSR" ]
    assert asa_upload["vt_setup"] == saved_scenario

    def prep_upload2( dlg ):
        """Prepare the upload."""
        assert asa_upload["user"] == user_name
        assert asa_upload["token"] == api_token
        # send the VSAV data to the front-end
        fname = os.path.join( os.path.dirname(__file__), "fixtures/update-vsav/full.vsav" )
        with open( fname, "rb" ) as fp:
            vsav_data = fp.read()
        set_stored_msg( "_vsav-persistence_", base64.b64encode( vsav_data ).decode( "utf-8" ) )
        find_child( ".vsav-container", dlg ).click()
        # wait for the files to be prepared
        wait_for( 60,
            lambda: "loader.gif" not in find_child( ".screenshot-container .preview img" ).get_attribute( "src" )
        )

    # test uploading a VASL save file
    def do_test(): #pylint: disable=missing-docstring
        init_webapp( webapp, webdriver, vsav_persistence=1, scenario_persistence=1 )
        dlg = _do_scenario_search( "full", [1], webdriver )
        find_child( "button.import", dlg ).click()
        last_asa_upload = do_upload( prep_upload2, False )
        assert isinstance( last_asa_upload["vt_setup"], dict )
        assert last_asa_upload["vasl_setup"][:2] == b"PK"
        assert last_asa_upload["screenshot"][:2] == b"\xff\xd8" \
          and last_asa_upload["screenshot"][-2:] == b"\xff\xd9" # nb: these are the magic numbers for JPEG's
    run_vassal_tests( webapp, do_test )

# ---------------------------------------------------------------------

def test_scenario_downloads( webapp, webdriver ):
    """Test downloading files from the ASL Scenario Archive."""

    # initialize
    init_webapp( webapp, webdriver )

    def unload_downloads():
        """Unload the available downloads."""
        btn = find_child( ".ui-dialog.scenario-search .import-control button.downloads" )
        if not btn.is_enabled():
            return None
        btn.click()
        dlg = wait_for_elem( 2, "#scenario-downloads-dialog" )
        # unload the file groups
        fgroups = []
        for elem in find_children( ".fgroup", dlg ):
            fgroup = {
                "screenshot": fixup( find_child( ".screenshot img", elem ).get_attribute( "src" ) ),
                "user": fixup( find_child( ".user", elem ).text ),
                "timestamp": fixup( find_child( ".timestamp", elem ).text ),
            }
            add_download_url( fgroup, "vt_setup", elem )
            add_download_url( fgroup, "vasl_setup", elem )
            fgroups.append( fgroup )
        return fgroups
    def add_download_url( fgroup, key, parent ): #pylint: disable=missing-docstring
        btn = find_child( "."+key, parent )
        if btn:
            fgroup[ key ] = fixup( btn.get_attribute( "data-url" ) )
    def fixup( val ): #pylint: disable=missing-docstring
        val = val.replace( webapp.base_url, "{WEBAPP-BASE-URL}" )
        val = val.replace( "%7C", "|" )
        return val

    # check the downloads for a scenario that doesn't have any
    _do_scenario_search( "fighting", [2], webdriver )
    assert unload_downloads() is None

    # check the downloads for a scenario that has some
    _do_scenario_search( "full", [1], webdriver )
    assert unload_downloads() == [ {
        "screenshot": "{WEBAPP-BASE-URL}/static/images/missing-image.png",
        "timestamp": "November 14, 2023",
        "user": "dave",
        "vasl_setup": "http://test.com/dave:1700000000|vt_setup4.vsav",
        "vt_setup": "http://test.com/dave:1700000000|vt_setup4.json"
    }, {
        "screenshot": "http://test.com/chuck:1600000000|screenshot3.png",
        "timestamp": "September 13, 2020",
        "user": "chuck",
        "vasl_setup": "http://test.com/chuck:1600000000|vt_setup3.vsav"
    }, {
        "screenshot": "http://test.com/bob:1500000000|screenshot2.png",
        "timestamp": "July 14, 2017",
        "user": "bob",
        "vt_setup": "http://test.com/bob:1500000000|vt_setup2.json"
    }, {
        "screenshot": "http://test.com/alice:1400000000|screenshot1.png",
        "timestamp": "May 13, 2014",
        "user": "alice",
        "vasl_setup": "http://test.com/alice:1400000000|vt_setup1.vsav",
        "vt_setup": "http://test.com/alice:1400000000|vt_setup1.json"
    } ]

# ---------------------------------------------------------------------

def _do_scenario_search( query, expected, webdriver ):
    """Do a scenario search."""

    # find the dialog
    dlg = find_child( "#scenario-search" )
    if not dlg.is_displayed():
        select_tab( "scenario" )
        btn = find_child( "button.scenario-search" )
        ActionChains( webdriver ).key_down( Keys.SHIFT ).click( btn ).perform()
        dlg = wait_for_elem( 2, "#scenario-search" )
        ActionChains( webdriver ).key_up( Keys.SHIFT ).perform()

    # initialize
    card = find_child( ".scenario-card", dlg )
    seq_no = card.get_attribute( "data-seqNo" )

    # do the search and check the results
    elem = find_child( "input.select2-search__field", dlg )
    elem.clear()
    # IMPORTANT: We can't use send_keys() here because it simulates a key-press for each character in the query,
    # and the incremental search feature means that we will constantly be loading scenario cards as the results
    # change, which makes it difficult for us to be able to tell when everything's stopped and it's safe to unload
    # the scenario card. Instead, we manually load the text box and trigger an event to update the UI.
    webdriver.execute_script(
        "arguments[0].value = arguments[1] ; $(arguments[0]).trigger('input')",
        elem, query
    )
    def check_search_results(): #pylint: disable=missing-docstring
        results = _unload_search_results()
        return [ r[0] for r in results ] == [ str(e) for e in expected ]
    wait_for( 2, check_search_results )

    # wait for the scenario card to finish loading
    # NOTE: We do this here since the typical use case is to search for something, then check what was found.
    wait_for( 2, lambda: card.get_attribute( "data-seqNo" ) != seq_no )

    return dlg

def _unload_search_results():
    """Unload the current search results."""
    results = []
    for sr in find_children( "#scenario-search .select2-results .search-result" ):
        results.append( ( sr.get_attribute("data-id"), sr ) )
    return results

def _unload_scenario_card(): #pylint: disable=too-many-branches,too-many-locals
    """Unload the scenario card."""

    # initialize
    card = wait_for( 2, _find_scenario_card )
    results = {}

    # unload the basic text content
    def unload_text_field( key, sel, trim_prefix=None, trim_postfix=None, trim_parens=False ):
        """Unload a text field from the scenario card."""
        elem = find_child( sel, card )
        if not elem:
            return
        val = elem.text.strip()
        if val:
            if trim_parens:
                assert val.startswith( "(" ) and val.endswith( ")" )
                val = val[1:-1]
            if trim_prefix:
                assert val.startswith( trim_prefix )
                val = val[ len(trim_prefix) : ]
            if trim_postfix:
                assert val.endswith( trim_postfix )
                val = val[ : -len(trim_postfix) ]
            val = val.strip()
            if val:
                results[ key ] = val
    def unload_attr( key, sel, attr ):
        """Unload a element's attribute from the scenario card."""
        elem = find_child( sel, card )
        if not elem:
            return
        results[ key ] = elem.get_attribute( attr )
    unload_text_field( "scenario_name", ".scenario-name" )
    unload_attr( "scenario_url", ".scenario-name a", "href" )
    unload_text_field( "scenario_id", ".scenario-id", trim_parens=True )
    unload_text_field( "scenario_location", ".scenario-location" )
    unload_text_field( "scenario_date", ".scenario-date", trim_parens=True )
    unload_text_field( "theater", ".info .theater" )
    unload_text_field( "turn_count", ".info .turn-count", trim_postfix="turns" )
    unload_text_field( "playing_time", ".info .playing-time" )
    unload_text_field( "designer", ".designer", trim_prefix="Designer:" )
    unload_text_field( "publication", ".publication" )
    unload_attr( "publication_url", ".publication a", "href" )
    unload_text_field( "publication_date", ".publication-date", trim_parens=True )
    unload_text_field( "publisher", ".publisher", trim_parens=True )
    unload_attr( "publisher_url", ".publisher a", "href" )
    unload_text_field( "prev_publication", ".prev-publication", trim_prefix="Previously:" )
    unload_text_field( "revised_publication", ".revised-publication", trim_prefix="Revised:" )
    unload_text_field( "map_url", ".map" ) # nb: we don't show a real map in test mode
    unload_text_field( "overview", ".overview" )
    unload_text_field( "defender_name", ".defender .name" )
    unload_text_field( "defender_desc", ".defender .desc"  )
    unload_text_field( "attacker_name", ".attacker .name" )
    unload_text_field( "attacker_desc", ".attacker .desc" )
    unload_text_field( "boards", ".boards", trim_prefix="Boards:" )
    unload_text_field( "overlays", ".overlays", trim_prefix="Overlays:" )
    unload_text_field( "extra_rules", ".extra-rules", trim_prefix="Rules:" )

    # unload the balance graphs
    balances = _unload_balance_graphs( card )
    if balances:
        results[ "balances" ] = balances

    # FUDGE! We just show the lat/long in test mode, not a real map, so we have to remove it
    # from the overview content.
    if "overview" in results and "map_url" in results:
        results["overview"] = results["overview"].replace( results["map_url"], "" ).strip()

    # unload the icons
    icons = set(
        c.get_attribute( "src" )
        for c in find_children( ".info .icons img", card )
    )
    if icons:
        results[ "icons" ] = sorted( os.path.split(i)[1] for i in icons )

    # unload the OBA info
    oba = find_child( ".player-info .oba", card )
    if oba and oba.is_displayed():
        oba_info = []
        for player in ["defender","attacker"]:
            row = find_child( ".{}".format( player ), oba )
            if not row:
                oba_info.append( None )
                continue
            oba_info.append( [
                find_child( ".name", row ).text,
                find_child( ".black", row ).text,
                find_child( ".red", row ).text
            ] )
            comments = find_child( ".{} .comments".format(player), oba ).text
            if comments:
                oba_info[-1].extend( comments.split( "\n" ) )
        elem = find_child( ".date-warning", oba )
        if elem.is_displayed():
            oba_info.append( elem.text )
        results[ "oba" ] = oba_info

    # unload any map preview images
    btn = find_child( ".map-previews", card )
    if btn and btn.is_displayed():
        btn.click()
        imgs = find_children( ".lg .lg-thumb-item img" )
        if not imgs:
            # NOTE: If there is only one image, no thumbnails are shown - just use the main image
            imgs = [ find_child( ".lg .lg-image" ) ]
        urls = [ e.get_attribute( "src" ) for e in imgs ]
        results[ "map_previews" ] = [
            os.path.basename( u ).replace( "%7C", "|" )
            for u in urls
        ]
        find_child( ".lg .lg-close" ).click()

    # unload any errata
    def get_source( val ): #pylint: disable=missing-docstring
        assert val.startswith( "[" ) and val.endswith( "]" )
        return val[1:-1]
    elems1 = find_children( ".errata .text", card )
    elems2 = find_children( ".errata .source", card )
    assert len(elems1) == len(elems2)
    if len(elems1) > 0:
        results[ "errata" ] = [
            [ e1.text, get_source(e2.text) ]
            for e1,e2 in zip(elems1,elems2)
        ]

    return results

def _unload_balance_graphs( parent ):
    """Unload balance graph(s)."""

    def get_player_no( elem ):
        """Figure out what player an element belongs to."""
        # FUDGE! Selenium doesn't seem to let us select elements using things like ".wins.player1",
        # so we have to iterate over all ".wins" elements, and figure out which player each one belongs to :-/
        classes = elem.get_attribute( "class" )
        if "player1" in classes:
            return 0
        elif "player2" in classes:
            return 1
        else:
            assert False
            return -1

    # unload the balance graphs
    balances = {}
    balance_graphs = find_children( ".balance-graph", parent ) or []
    for bgraph in balance_graphs:
        if not bgraph.is_displayed():
            continue
        balance = [ {}, {} ]
        for elem in find_children( ".player", bgraph ):
            balance[ get_player_no(elem) ][ "name" ] = elem.text
        for elem in find_children( ".wins", bgraph ):
            wins = elem.text
            assert wins.startswith( "(" ) and wins.endswith( ")" )
            balance[ get_player_no(elem) ][ "wins" ] = int( wins[1:-1] )
        for elem in find_children( ".progressbar", bgraph ):
            percentage = int( elem.get_attribute( "aria-valuenow" ) )
            player_no = get_player_no( elem )
            if player_no == 0:
                percentage = 100 - percentage
            balance[ player_no ][ "percentage" ] = percentage
        classes = [ c for c in get_css_classes(bgraph) if c != "balance-graph" ]
        assert len(classes) == 1
        balances[ classes[0] ] = balance

    return balances

def _check_warnings( expected, expected2 ):
    """Check any import warnings being shown."""
    def do_check_warnings(): #pylint:
        """Get import warnings."""
        warnings = [
            c.get_attribute( "name" )
            for c in find_children( "#scenario-search .warnings input[type='checkbox']" )
        ]
        warnings2 = [
            c.text
            for c in find_children( "#scenario-search .warnings .warning2" )
        ]
        return warnings == expected and warnings2 == expected2
    wait_for( 2, do_check_warnings )

def _get_scenario_info():
    """Open the scenario info and unload the information."""
    btn = find_child( "button.scenario-search" )
    assert find_child( "img", btn ).get_attribute( "src" ).endswith( "/info.gif" )
    btn.click()
    wait_for_elem( 2, "#scenario-info-dialog" )
    card = _unload_scenario_card()
    btn = find_children( ".ui-dialog .ui-dialog-buttonpane button" )[0]
    assert btn.text == "OK"
    btn.click()
    return card

def _unlink_scenario():
    """Unlink the scenario from the ASL Scenario Archive."""
    find_child( "button.scenario-search" ).click()
    wait_for_elem( 2, "#scenario-info-dialog" )
    btn = find_children( ".ui-dialog .ui-dialog-buttonpane button" )[1]
    assert btn.text == "Unlink"
    btn.click()

def _import_scenario_and_confirm( dlg ):
    """Import a scenario, confirming any warnings."""
    _click_import_button( dlg )
    btn = wait_for_elem( 2, "button.confirm-import", dlg )
    btn.click()
    wait_for( 2, lambda: not dlg.is_displayed() )

def _find_scenario_card():
    """Find the currently-displayed scenario card."""
    if find_child( "#scenario-search" ).is_displayed():
        return find_child( "#scenario-search .scenario-card" )
    if find_child( "#scenario-info-dialog" ).is_displayed():
        return find_child( "#scenario-info-dialog .scenario-card" )
    return None

def _click_import_button( dlg ):
    """Click the "import scenario" button, and confirm the action (if necessary)."""
    find_child( "button.import", dlg ).click()
    if find_child( "#ask" ).is_displayed():
        click_dialog_button( "OK" )
