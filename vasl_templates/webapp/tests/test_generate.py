""" Test HTML snippet generation. """

from vasl_templates.webapp.tests.utils import set_template_params, get_clipboard, get_stored_msg, find_child

# ---------------------------------------------------------------------

def _test_snippet( webdriver, template_id, params, expected, expected2 ): #pylint: disable=unused-argument
    """Do a single test."""

    # set the template parameters
    set_template_params( params )

    # generate the snippet
    submit = find_child( "input.generate[data-id='{}']".format(template_id) )
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
        "SCENARIO_NAME": "my scenario",
        "SCENARIO_LOCATION": "here",
        "SCENARIO_DATE": "01/02/1942",
    },
        'name = [my scenario] | loc = [here] | date = [01/02/1942] aka "2 January, 1942"',
        None
    )

    # generate a SCENARIO snippet with some fields missing
    _test_snippet( webdriver, "scenario", {
        "SCENARIO_NAME": "my scenario",
        "SCENARIO_LOCATION": None,
        "SCENARIO_DATE": None,
    },
        "name = [my scenario] | loc = [] | date = []",
        [ "scenario date" ],
    )

    # generate a SCENARIO snippet with all fields missing
    _test_snippet( webdriver, "scenario", {
        "SCENARIO_NAME": None,
        "SCENARIO_LOCATION": None,
        "SCENARIO_DATE": None,
    },
        "name = [] | loc = [] | date = []",
        [ "scenario name", "scenario date" ],
    )

    # generate a SCENARIO snippet with a snippet width
    _test_snippet( webdriver, "scenario", {
        "SCENARIO_NAME": "test",
        "SCENARIO_LOCATION": "here",
        "SCENARIO_DATE": "01/02/1942",
        "SCENARIO_WIDTH": "20em",
    },
        'name = [test] | loc = [here] | date = [01/02/1942] aka "2 January, 1942" | width = [20em]',
        None
    )

# ---------------------------------------------------------------------

def test_vc_snippets( webapp, webdriver ):
    """Test HTML snippet generation."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1 ) )

    # generate a VC snippet
    _test_snippet( webdriver, "victory_conditions", {
        "VICTORY_CONDITIONS": "Kill 'Em All!",
    },
        "VC: [Kill 'Em All!]",
        None
    )

    # generate an empty VC snippet
    _test_snippet( webdriver, "victory_conditions", {
        "VICTORY_CONDITIONS": "",
    },
        "VC: []",
        None
    )

    # generate a VC snippet with a width
    _test_snippet( webdriver, "victory_conditions", {
        "VICTORY_CONDITIONS": "Kill 'Em All!",
        "VICTORY_CONDITIONS_WIDTH": "100px",
    },
        "VC: [Kill 'Em All!] ; width=[100px]",
        None
    )

# ---------------------------------------------------------------------

def test_players_snippets( webapp, webdriver ):
    """Test HTML snippet generation."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1 ) )

    # generate a PLAYERS snippet
    _test_snippet( webdriver, "players", {
        "PLAYER_1": "french",
        "PLAYER_1_ELR": "1",
        "PLAYER_1_SAN": "2",
        "PLAYER_2": "british",
        "PLAYER_2_ELR": "3",
        "PLAYER_2_SAN": "4",
    },
        "player1=[french] ; ELR=[1] ; SAN=[2] | player2=[british] ; ELR=[3] ; SAN=[4]",
        None
    )

    # generate a PLAYERS snippet with both players the same nationality
    _test_snippet( webdriver, "players", {
        "PLAYER_1": "british",
        },
        "player1=[british] ; ELR=[1] ; SAN=[2] | player2=[british] ; ELR=[3] ; SAN=[4]",
        [ "Both players have the same nationality!" ],
    )
