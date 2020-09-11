"""" Test scenario search. """

import os
import time

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import ElementClickInterceptedException, ElementNotInteractableException

from vasl_templates.webapp.tests.test_scenario_persistence import save_scenario, load_scenario
from vasl_templates.webapp.tests.utils import init_webapp, select_tab, new_scenario, \
    set_player, set_template_params, set_scenario_date, get_player_nat, get_theater, set_theater, \
    wait_for, wait_for_elem, find_child, find_children, get_css_classes

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
        "theater": "PTO", "turn_count": "6", "playing_time": "1\u00bc hours",
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
        "boards": "1, 2, RB",
        "map_previews": [ "asl-scenario-archive.png" ],
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
    _check_scenario(
        SCENARIO_NAME="Full content scenario", SCENARIO_ID="FCS-1",
        SCENARIO_LOCATION="Some place",
        PLAYER_1="dutch", PLAYER_1_DESCRIPTION="1st Dutch Army",
        PLAYER_2="romanian", PLAYER_2_DESCRIPTION="1st Romanian Army",
        THEATER="PTO"
    )

    # import the "empty" scenario
    _unlink_scenario()
    dlg = _do_scenario_search( "Untitled", ["no-content"], webdriver )
    find_child( "button.import", dlg ).click()
    find_child( "button.confirm-import", dlg ).click()
    # NOTE: Since there are no players defined in the scenario, what's on-screen will be left unchanged.
    _check_scenario(
        SCENARIO_NAME="Untitled scenario (#no-content)", SCENARIO_ID="",
        SCENARIO_LOCATION="",
        PLAYER_1="dutch", PLAYER_1_DESCRIPTION="",
        PLAYER_2="romanian", PLAYER_2_DESCRIPTION="",
        THEATER="ETO"
    )

def _check_scenario( **kwargs ):
    """Check the scenario import."""
    keys = [ "SCENARIO_NAME", "SCENARIO_ID", "SCENARIO_LOCATION", "PLAYER_1_DESCRIPTION", "PLAYER_2_DESCRIPTION" ]
    for key in keys:
        elem = find_child( "input[name='{}']".format( key ) )
        assert elem.get_attribute( "value" ) == kwargs[ key ]
    assert get_player_nat( 1 ) == kwargs[ "PLAYER_1" ]
    assert get_player_nat( 2 ) == kwargs[ "PLAYER_2" ]
    assert get_theater() == kwargs[ "THEATER" ]

# ---------------------------------------------------------------------

def test_import_warnings( webapp, webdriver ): #pylint: disable=too-many-statements
    """Test warnings when importing a scenario."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # import a scenario on top of an empty scenario
    dlg = _do_scenario_search( "full", [1], webdriver )
    find_child( "button.import", dlg ).click()
    wait_for( 2, lambda: not dlg.is_displayed() )

    def do_test( param_name, expected_warning, expected_val, curr_val="CURR-VAL" ): #pylint: disable=missing-docstring

        # start with a new scenario
        new_scenario()

        # set the scenario parameter
        set_template_params( { param_name: curr_val } )

        # import a scenario
        _do_scenario_search( "full", [1], webdriver )
        find_child( "#scenario-search button.import" ).click()

        # check if any warnings were expected
        elem = find_child( "[name='{}']".format( param_name ) )
        if expected_warning:
            # yup - make sure they are being shown
            warnings = find_children( ".warnings input[type='checkbox']", dlg )
            if expected_warning:
                assert [ w.get_attribute( "name" ) for w in warnings ] == [ expected_warning ]
            else:
                assert not warnings
            # cancel the import
            find_child( "button.cancel-import", dlg ).click()
            wait_for( 2, lambda: not find_child( ".warnings", dlg ).is_displayed() )
            # do the import again, and accept it
            find_child( "#scenario-search button.import" ).click()
            find_child( "button.confirm-import", dlg ).click()
            assert not dlg.is_displayed()
            assert elem.get_attribute( "value" ) == expected_val
        else:
            # nope - check that the import was done
            assert not dlg.is_displayed()
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
    _do_scenario_search( "full", [1], webdriver )
    find_child( "#scenario-search button.import" ).click()
    warnings = find_children( ".warnings input[type='checkbox']", dlg )
    assert [ w.get_attribute( "name" ) for w in warnings ] == []

    # test importing a scenario on top of existing OB owned by the same nationality
    new_scenario()
    load_scenario( {
        "PLAYER_1": "dutch",
        "OB_SETUPS_1": [ { "caption": "Dutch setup note" } ]
    } )
    _do_scenario_search( "full", [1], webdriver )
    find_child( "#scenario-search button.import" ).click()
    wait_for( 2, lambda: not dlg.is_displayed() )

    # test importing a scenario on top of existing OB owned by the different nationality
    new_scenario()
    load_scenario( {
        "PLAYER_1": "german",
        "OB_SETUPS_1": [ { "caption": "German setup note" } ]
    } )
    _do_scenario_search( "full", [1], webdriver )
    find_child( "#scenario-search button.import", dlg ).click()
    warnings = wait_for( 2, lambda: find_children( ".warnings input[type='checkbox']", dlg ) )
    assert [ w.get_attribute( "name" ) for w in warnings ] == [ "defender_name" ]
    assert not warnings[0].is_selected()
    try:
        warnings[0].click()
    except (ElementClickInterceptedException, ElementNotInteractableException):
        # FUDGE! We sometimes get a "Other element would receive the click" (div.warning) error,
        # I suspect because the warnings panel is still sliding up.
        time.sleep( 0.5 )
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
    find_child( "button.import" ).click()
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
    dlg = _do_scenario_search( "Defender OBA", ["5b"], webdriver )
    check_oba_info( _unload_scenario_card(), [
        [ "Burmese", "-", "-" ],
        None
    ] )

    # check a scenario where the attacker has OBA, the defender is an unknwon nationality
    dlg = _do_scenario_search( "Attacker OBA", ["5c"], webdriver )
    check_oba_info( _unload_scenario_card(), [
        [ "The Other Guy", "?", "?" ],
        [ "Russian", "3B", "4R" ]
    ] )

# ---------------------------------------------------------------------

def test_unknown_theaters( webapp, webdriver ):
    """Test importing scenarios with unknown theaters."""

    # initialize
    init_webapp( webapp, webdriver )

    # search for the "MTO" scenario (this has a theater mapping)
    set_theater( "Korea" )
    dlg = _do_scenario_search( "MTO", ["3a"], webdriver )
    find_child( "button.import", dlg ).click()
    wait_for( 2, lambda: not dlg.is_displayed() )
    assert get_theater() == "ETO"

    # search for the "Africa" scenario (this has no theater mapping)
    new_scenario()
    set_theater( "Korea" )
    dlg = _do_scenario_search( "Africa", ["3b"], webdriver )
    find_child( "button.import", dlg ).click()
    _check_warnings( [], ["Unknown theater: Africa"] )
    find_child( "button.confirm-import", dlg ).click()
    assert get_theater() == "other"

# ---------------------------------------------------------------------

def test_unknown_nats( webapp, webdriver ):
    """Test importing scenarios with unknown player nationalities."""

    # initialize
    init_webapp( webapp, webdriver )

    # test importing a scenario with 2 completely unknown player nationalities
    set_player( 1, "french" )
    set_player( 2, "italian" )
    dlg = _do_scenario_search( "Unknown players", ["4a"], webdriver )
    find_child( "button.import", dlg ).click()
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

@pytest.mark.skipif( pytest.config.option.server_url is not None, reason="--server-url specified" ) #pylint: disable=no-member
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

        # unload the scenario card
        if find_child( "#scenario-search" ).is_displayed():
            parent = find_child( "#scenario-search .scenario-card" )
        elif find_child( "#scenario-info-dialog" ).is_displayed():
            parent = find_child( "#scenario-info-dialog .scenario-card" )
        else:
            assert False
        card = _unload_scenario_card()

        # check if the balance graph is shown
        if bgraph:
            balance = card["balances"]["roar"]
            assert balance[0]["name"] == bgraph[0]
            assert balance[1]["name"] == bgraph[1]
        else:
            assert "roar" not in card["balances"]

        # check if the "connect to ROAR" button is shown
        elem = find_child( ".connect-roar", parent )
        if connect:
            assert elem.is_displayed()
        else:
            assert not elem.is_displayed()

        # check if the "disconnect from ROAR" is shown
        elem = find_child( ".disconnect-roar", parent )
        if disconnect:
            assert elem.is_displayed()
        else:
            assert not elem or not elem.is_displayed()

    # import the "Fighting Withdrawal" scenario
    _do_scenario_search( "withdrawal", [2], webdriver )
    check( ["Russian","Finnish"], False, False )
    find_child( "#scenario-search button.import" ).click()

    # connect to another ROAR scenario
    find_child( "button.scenario-search" ).click()
    check( ["Russian","Finnish"], False, True )
    find_child( "#scenario-info-dialog .disconnect-roar" ).click()
    check( None, True, False )
    find_child( "#scenario-info-dialog .connect-roar" ).click()
    dlg = wait_for_elem( 2, ".ui-dialog.select-roar-scenario" )
    find_child( ".select2-search__field", dlg ).send_keys( "another" )
    find_child( ".select2-search__field", dlg ).send_keys( Keys.RETURN )
    check( ["British","French"], False, True )
    find_child( ".ui-dialog.scenario-info button.ok" ).click()

    # disconnect from the ROAR scenario
    find_child( "button.scenario-search" ).click()
    check( ["British","French"], False, True )
    find_child( "#scenario-info-dialog .disconnect-roar" ).click()
    check( None, True, False )
    find_child( ".ui-dialog.scenario-info button.ok" ).click()

    # connect to a ROAR scenario
    find_child( "button.scenario-search" ).click()
    check( None, True, False )
    find_child( "#scenario-info-dialog .connect-roar" ).click()
    dlg = wait_for_elem( 2, ".ui-dialog.select-roar-scenario" )
    elem = find_child( ".select2-search__field", dlg )
    elem.send_keys( "withdrawal" )
    elem.send_keys( Keys.RETURN )
    check( ["Russian","Finnish"], False, True )
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
    _do_scenario_search( "Untitled", ["no-content"], webdriver )
    find_child( "#scenario-search button.import" ).click()
    find_child( "#scenario-search button.confirm-import" ).click()
    check( "no-content" )

    # import the "Fighting Withdrawal" scenario (on top of the current scenario)
    _do_scenario_search( "Fighting Withdrawal", [2], webdriver )
    find_child( "#scenario-search button.import" ).click()
    find_child( "#scenario-search button.confirm-import" ).click()
    check( "2" )

    # unlink the scenario
    _unlink_scenario()
    check( "" )

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

    # do the search and check the results
    elem = find_child( "input.select2-search__field", dlg )
    elem.clear()
    elem.send_keys( query )
    results = _unload_search_results()
    assert [ r[0] for r in results ] == [ str(e) for e in expected ]

    return dlg

def _unload_search_results():
    """Unload the current search results."""
    results = []
    for sr in find_children( "#scenario-search .select2-results .search-result" ):
        results.append( ( sr.get_attribute("data-id"), sr ) )
    return results

def _unload_scenario_card(): #pylint: disable=too-many-branches,too-many-locals
    """Unload the scenario card."""

    if find_child( "#scenario-search" ).is_displayed():
        card = find_child( "#scenario-search .scenario-card" )
    elif find_child( "#scenario-info-dialog" ).is_displayed():
        card = find_child( "#scenario-info-dialog .scenario-card" )
    else:
        assert False
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
            results[ key ] = val.strip()
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
        elem =  find_child( ".date-warning", oba )
        if elem.is_displayed():
            oba_info.append( elem.text )
        results[ "oba" ] = oba_info

    # unload any map preview images
    elems = find_children( ".map-preview", card )
    if elems:
        urls = [ e.get_attribute("href") for e in elems ]
        results[ "map_previews" ] = [ os.path.basename(u) for u in urls ]

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