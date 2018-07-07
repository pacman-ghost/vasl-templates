""" Test HTML snippet generation. """

from vasl_templates.webapp.tests.utils import get_clipboard, get_stored_msg, find_child

# ---------------------------------------------------------------------

# initialize
def _test_snippet( webdriver, template_id, params, expected, expected2 ):
    """Do a single test."""

    # set the template parameters
    for key,val in params.items():
        elem = find_child( webdriver, "input[name='{}']".format(key) )
        if not elem:
            elem = find_child( webdriver, "textarea[name='{}']".format(key) )
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
    param_names = [ "scenario name", "scenario location", "scenario date" ]
    for pname in param_names:
        if pname in expected2:
            assert pname in last_warning
        else:
            assert pname not in last_warning

# ---------------------------------------------------------------------

def test_scenario_snippets( webapp, webdriver ):
    """Test HTML snippet generation."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1 ) )

    # generate a SCENARIO snippet
    _test_snippet( webdriver, "scenario", {
        "scenario_name": "my scenario",
        "scenario_location": "here",
        "scenario_date": "now",
    },
        "name = [my scenario] | loc = [here] | date = [now]",
        []
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
        []
    )

    # generate a VC snippet
    _test_snippet( webdriver, "victory_conditions", {
        "victory_conditions": "",
    },
        "VC:",
        []
    )
