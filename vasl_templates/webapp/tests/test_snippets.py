""" Test HTML snippet generation. """

from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.tests.test_ob import add_ob_setup, add_ob_note
from vasl_templates.webapp.tests.utils import select_tab, set_template_params, get_clipboard
from vasl_templates.webapp.tests.utils import get_stored_msg, dismiss_notifications, find_child
from vasl_templates.webapp.tests.utils import for_each_template, wait_for

# ---------------------------------------------------------------------

def test_scenario_snippets( webapp, webdriver ):
    """Test HTML snippet generation."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1 ) )
    select_tab( "scenario" )

    # generate a SCENARIO snippet
    _test_snippet( webdriver, "scenario", {
        "SCENARIO_NAME": "my <i>cool</i> scenario",
        "SCENARIO_LOCATION": "right <u>here</u>",
        "SCENARIO_DATE": "01/02/1942",
    },
        'name = [my <i>cool</i> scenario] | loc = [right <u>here</u>] | date = [01/02/1942] aka "2 January, 1942"',
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

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_vc_snippets( webapp, webdriver ):
    """Test HTML snippet generation."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1 ) )
    select_tab( "scenario" )

    # generate a VC snippet
    _test_snippet( webdriver, "victory_conditions", {
        "VICTORY_CONDITIONS": "Kill 'Em <i>All</i>!",
    },
        "VC: [Kill 'Em <i>All</i>!]",
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

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_players_snippets( webapp, webdriver ):
    """Test HTML snippet generation."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1 ) )
    select_tab( "scenario" )

    # generate a PLAYERS snippet
    _test_snippet( webdriver, "players", {
        "PLAYER_1": "french",
        "PLAYER_1_ELR": "1",
        "PLAYER_1_SAN": "2",
        "PLAYER_2": "british",
        "PLAYER_2_ELR": "3",
        "PLAYER_2_SAN": "4",
    },
        "player1=[french:French] ; ELR=[1] ; SAN=[2] | player2=[british:British] ; ELR=[3] ; SAN=[4]",
        None
    )

    # generate a PLAYERS snippet with both players the same nationality
    _test_snippet( webdriver, "players", {
        "PLAYER_1": "british",
        },
        "player1=[british:British] ; ELR=[1] ; SAN=[2] | player2=[british:British] ; ELR=[3] ; SAN=[4]",
        [ "Both players have the same nationality!" ],
    )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

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

def test_edit_templates( webapp, webdriver ):
    """Test editing templates."""

    # initialize
    webdriver.get( webapp.url_for( "main", edit_template_links=1 ) )

    # try uploading a customized version of each template
    def edit_template( template_id ):
        """Edit a template."""
        elem = find_child( "#edit-template textarea" )
        elem.clear()
        elem.send_keys( "EDITED TEMPLATE: {}".format( template_id ) )
        elem.send_keys( Keys.ESCAPE )
    def test_template( template_id, orig_template_id ):
        """Test editing a template."""
        if template_id in("ob_setup","ob_note"):
            return # nb: these require special handling (done below)
        # edit the template
        elem = find_child( "a.edit-template-link[data-id='{}']".format( template_id ) )
        webdriver.execute_script( "$(arguments[0]).click();", elem )
        edit_template( orig_template_id )
        # check that the new template is being used
        dismiss_notifications()
        elem = find_child( "input.generate[data-id='{}']".format( orig_template_id ) )
        elem.click()
        wait_for( 5, # FUDGE! Work-around a weird timing problem on Linux :shrug:
            lambda: get_clipboard() == "EDITED TEMPLATE: {}".format( orig_template_id )
        )
    for_each_template( test_template )

    # customize the OB SETUP template
    select_tab( "ob1" )
    elem = find_child( "#tabs-ob1 input[type='button'][data-id='ob_setup']" )
    elem.click()
    edit_template( "ob_setup" )

    # check that the new template is being used
    for player_id in range(1,2+1):
        add_ob_setup( webdriver, player_id, "ob setup (ignored)", None )
        elem = find_child( "#ob_setups-sortable_{} li input[type='button']".format( player_id ) )
        elem.click()
        assert get_clipboard() == "EDITED TEMPLATE: ob_setup"

    # customize the OB NOTE template
    select_tab( "ob2" )
    elem = find_child( "#tabs-ob2 input[type='button'][data-id='ob_note']" )
    elem.click()
    edit_template( "ob_note" )

    # check that the new template is being used
    for player_id in range(1,2+1):
        add_ob_note( webdriver, player_id, "ob note (ignored)", None )
        elem = find_child( "#ob_notes-sortable_{} li input[type='button']".format( player_id ) )
        elem.click()
        assert get_clipboard() == "EDITED TEMPLATE: ob_note"
