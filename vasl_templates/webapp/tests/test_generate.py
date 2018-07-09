""" Test HTML snippet generation. """

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.tests.utils import get_clipboard, get_stored_msg, find_child

# ---------------------------------------------------------------------

# initialize
def _test_snippet( webdriver, template_id, params, expected, expected2 ):
    """Do a single test."""

    # set the template parameters
    for key,val in params.items():
        elem = next( c for c in ( \
            find_child( webdriver, "{}[name='{}']".format(elem_type,key) ) \
            for elem_type in ["input","textarea","select"]
        ) if c )
        if elem.tag_name == "select":
            Select(elem).select_by_value( val )
        else:
            elem.clear()
            if val:
                elem.send_keys( val )

    # generate the snippet
    submit = find_child( webdriver, "input[class='generate'][data-id='{}']".format(template_id) )
    submit.click()
    snippet = get_clipboard()
    lines = [ l.strip() for l in snippet.split("\n") ]
    snippet = " | ".join( l for l in lines if l )
    assert snippet == expected

    # check warnings for mandatory parameters
    last_warning = get_stored_msg( "_last-warning_" ) or ""
    if isinstance( expected2, list):
        # check for mandatory parameters
        param_names = [ "scenario name", "scenario location", "scenario date" ]
        for pname in param_names:
            if pname in expected2:
                assert pname in last_warning
            else:
                assert pname not in last_warning
    elif isinstance(expected2, str):
        # check for a specific error message
        assert expected2 == last_warning
    else:
        # make sure there was no warning message
        assert expected2 is None
        assert not last_warning

# ---------------------------------------------------------------------

def test_scenario_snippets( webapp, webdriver ):
    """Test HTML snippet generation."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1 ) )

    # generate a SCENARIO snippet
    _test_snippet( webdriver, "scenario", {
        "scenario_name": "my scenario",
        "scenario_location": "here",
        "scenario_date": "01/02/1942",
    },
        'name = [my scenario] | loc = [here] | date = [01/02/1942] aka "2 January, 1942"',
        None
    )

    # generate a SCENARIO snippet with some fields missing
    _test_snippet( webdriver, "scenario", {
        "scenario_name": "my scenario",
        "scenario_location": None,
        "scenario_date": None,
    },
        "name = [my scenario] | loc = [] | date = []",
        [ "scenario date" ],
    )

    # generate a SCENARIO snippet with all fields missing
    _test_snippet( webdriver, "scenario", {
        "scenario_name": None,
        "scenario_location": None,
        "scenario_date": None,
    },
        "name = [] | loc = [] | date = []",
        [ "scenario name", "scenario date" ],
    )

# ---------------------------------------------------------------------

def test_vc_snippets( webapp, webdriver ):
    """Test HTML snippet generation."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1 ) )

    # generate a VC snippet
    _test_snippet( webdriver, "victory_conditions", {
        "victory_conditions": "Kill 'Em All!",
    },
        "VC: Kill 'Em All!",
        None
    )

    # generate a VC snippet
    _test_snippet( webdriver, "victory_conditions", {
        "victory_conditions": "",
    },
        "VC:",
        None
    )

# ---------------------------------------------------------------------

def test_players_snippets( webapp, webdriver ):
    """Test HTML snippet generation."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1 ) )

    # generate a PLAYERS snippet
    _test_snippet( webdriver, "players", {
        "player_1": "french",
        "player_1_elr": "1",
        "player_1_san": "2",
        "player_2": "british",
        "player_2_elr": "3",
        "player_2_san": "4",
    },
        "player1=[french] ; ELR=[1] ; SAN=[2] | player2=[british] ; ELR=[3] ; SAN=[4]",
        None
    )

    # generate a PLAYERS snippet with both players the same nationality
    _test_snippet( webdriver, "players", {
        "player_1": "british",
        },
        "player1=[british] ; ELR=[1] ; SAN=[2] | player2=[british] ; ELR=[3] ; SAN=[4]",
        [ "Both players have the same nationality!" ],
    )
