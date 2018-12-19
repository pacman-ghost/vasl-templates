""" Test HTML snippet generation. """

from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.tests.utils import \
    init_webapp, select_tab, select_tab_for_elem, set_template_params, wait_for_clipboard, \
    get_stored_msg, set_stored_msg_marker, find_child, find_children, adjust_html, \
    for_each_template, add_simple_note, edit_simple_note, \
    get_sortable_entry_count, generate_sortable_entry_snippet, drag_sortable_entry_to_trash, \
    new_scenario, set_scenario_date
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario, load_scenario_params

# ---------------------------------------------------------------------

def test_snippet_ids( webapp, webdriver ):
    """Check that snippet ID's are generated correctly."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct: ct.set_data_dir( dtype="real" )
    )

    # load a scenario (so that we get some sortable's)
    scenario_data = {
        "SCENARIO_NOTES": [ { "caption": "Scenario note #1"  } ],
        "OB_SETUPS_1": [ { "caption": "OB setup note #1" } ],
        "OB_NOTES_1": [ { "caption": "OB note #1" } ],
        "OB_SETUPS_2": [ { "caption": "OB setup note #2" } ],
        "OB_NOTES_2": [ { "caption": "OB note #2" } ],
    }
    load_scenario( scenario_data )

    def check_snippet( btn ):
        """Generate a snippet and check that it has an ID."""
        select_tab_for_elem( btn )
        if not btn.is_displayed():
            # FUDGE! All nationality-specific buttons are created on each OB tab, and the ones not relevant
            # to each player are just hidden. This is not real good since we have multiple elements with the same ID :-/
            # but we work around this by checking if the button is visible. Sigh...
            return
        btn.click()
        wait_for_clipboard( 2, "<!-- vasl-templates:id ", contains=True )

    def do_test( scenario_date ):
        """Check each generated snippet has an ID."""

        # configure the scenario
        set_scenario_date( scenario_date )

        # check each snippet
        for btn in find_children( "button.generate" ):
            check_snippet( btn )
        for btn in find_children( "img.snippet" ):
            check_snippet( btn )

    # test snippets with German/Russian
    do_test( "" )
    do_test( "10/01/1943" )
    do_test( "01/01/1944" )

    # test snippets with British/American
    new_scenario()
    load_scenario_params( { "scenario": { "PLAYER_1": "british", "PLAYER_2": "american" } } )
    do_test( "" )
    do_test( "11/01/1942" )

# ---------------------------------------------------------------------

def test_scenario_snippets( webapp, webdriver ):
    """Test HTML snippet generation."""

    # initialize
    init_webapp( webapp, webdriver )
    select_tab( "scenario" )
    btn = find_child( "button.generate[data-id='scenario']" )

    # generate a SCENARIO snippet
    _test_snippet( btn, {
        "SCENARIO_NAME": "my <i>cool</i> scenario",
        "SCENARIO_LOCATION": "right <u>here</u>",
        "SCENARIO_DATE": "01/02/1942",
    },
        'name = [my <i>cool</i> scenario] | loc = [right <u>here</u>] | date = [01/02/1942] aka "2 January, 1942"',
        None
    )

    # generate a SCENARIO snippet with some fields missing
    _test_snippet( btn, {
        "SCENARIO_NAME": "my scenario",
        "SCENARIO_LOCATION": None,
        "SCENARIO_DATE": None,
    },
        "name = [my scenario] | loc = [] | date = []",
        [ "scenario date" ],
    )

    # generate a SCENARIO snippet with all fields missing
    _test_snippet( btn, {
        "SCENARIO_NAME": None,
        "SCENARIO_LOCATION": None,
        "SCENARIO_DATE": None,
    },
        "name = [] | loc = [] | date = []",
        [ "scenario name", "scenario date" ],
    )

    # generate a SCENARIO snippet with a snippet width
    _test_snippet( btn, {
        "SCENARIO_NAME": "test",
        "SCENARIO_LOCATION": "here",
        "SCENARIO_DATE": "01/02/1942",
        "SCENARIO_WIDTH": "20em",
    },
        'name = [test] | loc = [here] | date = [01/02/1942] aka "2 January, 1942" | width = [20em]',
        None
    )

    # generate a SCENARIO snippet with non-English content and HTML special characters
    _test_snippet( btn, {
        "SCENARIO_NAME": "<foo> & <bar>",
        "SCENARIO_LOCATION": "japan (\u65e5\u672c)",
        "SCENARIO_DATE": "01/02/1942",
        "SCENARIO_WIDTH": "",
    },
        'name = [<foo> & <bar>] | loc = [japan (\u65e5\u672c)] | date = [01/02/1942] aka "2 January, 1942"',
        None
    )

# ---------------------------------------------------------------------

def test_vc_snippets( webapp, webdriver ):
    """Test HTML snippet generation."""

    # initialize
    init_webapp( webapp, webdriver )
    select_tab( "scenario" )
    btn = find_child( "button.generate[data-id='victory_conditions']" )

    # generate a VC snippet
    _test_snippet( btn, {
        "VICTORY_CONDITIONS": "Kill 'Em <i>All</i>!",
    },
        "VC: [Kill 'Em <i>All</i>!]",
        None
    )

    # generate an empty VC snippet
    _test_snippet( btn, {
        "VICTORY_CONDITIONS": "",
    },
        "VC: []",
        None
    )

    # generate a VC snippet with a width
    _test_snippet( btn, {
        "VICTORY_CONDITIONS": "Kill 'Em All!",
        "VICTORY_CONDITIONS_WIDTH": "100px",
    },
        "VC: [Kill 'Em All!] ; width=[100px]",
        None
    )

# ---------------------------------------------------------------------

def test_scenario_notes_snippets( webapp, webdriver ):
    """Test HTML snippet generation."""

    # initialize
    init_webapp( webapp, webdriver )
    select_tab( "scenario" )

    sortable = find_child( "#scenario_notes-sortable" )
    add_simple_note( sortable, "scenario <i>note</i> #1", None )
    add_simple_note( sortable, "scenario note #2", "100px" )
    assert generate_sortable_entry_snippet( sortable, 0 ) == adjust_html( "[scenario <i>note</i> #1]" )
    assert generate_sortable_entry_snippet( sortable, 1 ) == "[scenario note #2] (width=[100px])"

    # delete a scenario note by dragging it into the trash
    assert get_sortable_entry_count( sortable ) == 2
    drag_sortable_entry_to_trash( sortable, 0 )
    assert get_sortable_entry_count( sortable ) == 1

    # delete scenario note by emptying its caption
    edit_simple_note( sortable, 0, "", None )
    assert get_sortable_entry_count( sortable ) == 0

    # add a scenario note with non-English content and HTML special characters
    sortable = find_child( "#scenario_notes-sortable" )
    add_simple_note( sortable, "japan <\u65e5\u672c>", None )
    assert generate_sortable_entry_snippet( sortable, 0 ) == "[japan <\u65e5\u672c>]"

# ---------------------------------------------------------------------

def test_players_snippets( webapp, webdriver ):
    """Test HTML snippet generation."""

    # initialize
    init_webapp( webapp, webdriver )
    select_tab( "scenario" )
    btn = find_child( "button.generate[data-id='players']" )

    # generate a PLAYERS snippet
    _test_snippet( btn, {
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
    _test_snippet( btn, {
        "PLAYER_1": "british",
        },
        "player1=[british:British] ; ELR=[1] ; SAN=[2] | player2=[british:British] ; ELR=[3] ; SAN=[4]",
        [ "Both players have the same nationality!" ],
    )

# ---------------------------------------------------------------------

def test_edit_templates( webapp, webdriver ):
    """Test editing templates."""

    # initialize
    init_webapp( webapp, webdriver, edit_template_links=1,
        reset = lambda ct: ct.set_vo_notes_dir( dtype="test" )
    )
    ob_setups = {
        1: find_child( "#ob_setups-sortable_1" ),
        2: find_child( "#ob_setups-sortable_2" )
    }
    ob_notes = {
        1: find_child( "#ob_notes-sortable_1" ),
        2: find_child( "#ob_notes-sortable_2" )
    }

    # try uploading a customized version of each template
    def edit_template( template_id ):
        """Edit a template."""
        elem = find_child( "#edit-template textarea" )
        elem.clear()
        elem.send_keys( "EDITED TEMPLATE: {}".format( template_id ) )
        elem.send_keys( Keys.ESCAPE )
    def test_template( template_id, orig_template_id ):
        """Test editing a template."""
        if template_id in ("scenario_note","ob_setup","ob_note"):
            return # nb: these require special handling (done below)
        if template_id in ("ob_vehicle_note","ob_ordnance_note"):
            return # nb: we currently don't support editing these in the UI
        # edit the template
        elem = find_child( "a._edit-template-link_[data-id='{}']".format( template_id ) )
        webdriver.execute_script( "$(arguments[0]).click();", elem )
        edit_template( orig_template_id )
        # check that the new template is being used
        elem = find_child( "button.generate[data-id='{}']".format( orig_template_id ) )
        elem.click()
        wait_for_clipboard( 2, "EDITED TEMPLATE: {}".format( orig_template_id ) )
    for_each_template( test_template )

    # customize the SCENARIO NOTE template
    select_tab( "scenario" )
    elem = find_child( "button[data-id='scenario_note']" )
    elem.click()
    edit_template( "scenario_note" )

    # check that the new template is being used
    sortable = find_child( "#scenario_notes-sortable" )
    add_simple_note( sortable, "scenario note (ignored)", None )
    elem = find_child( "li img.snippet", sortable )
    elem.click()
    wait_for_clipboard( 2, "EDITED TEMPLATE: scenario_note" )

    # customize the OB SETUP template
    select_tab( "ob1" )
    elem = find_child( "#tabs-ob1 button[data-id='ob_setup']" )
    elem.click()
    edit_template( "ob_setup" )

    # check that the new template is being used
    for player_no in range(1,2+1):
        select_tab( "ob{}".format( player_no ) )
        sortable = ob_setups[ player_no ]
        add_simple_note( sortable, "ob setup (ignored)", None )
        elem = find_child( "li img.snippet", sortable )
        elem.click()
        wait_for_clipboard( 2, "EDITED TEMPLATE: ob_setup" )

    # customize the OB NOTE template
    select_tab( "ob2" )
    elem = find_child( "#tabs-ob2 button[data-id='ob_note']" )
    elem.click()
    edit_template( "ob_note" )

    # check that the new template is being used
    for player_no in range(1,2+1):
        select_tab( "ob{}".format( player_no ) )
        sortable = ob_notes[ player_no ]
        add_simple_note( sortable, "ob note (ignored)", None )
        elem = find_child( "li img.snippet", sortable )
        elem.click()
        wait_for_clipboard( 2, "EDITED TEMPLATE: ob_note" )

# ---------------------------------------------------------------------

def _test_snippet( btn, params, expected, expected2 ):
    """Do a single test."""

    # set the template parameters and generate the snippet
    set_template_params( params )
    marker = set_stored_msg_marker( "_last-warning_" )
    btn.click()
    def reformat( clipboard ): #pylint: disable=missing-docstring
        lines = [ l.strip() for l in clipboard.split("\n") ]
        return " | ".join( l for l in lines if l )
    wait_for_clipboard( 2, expected, transform=reformat )

    # check warnings for mandatory parameters
    last_warning = get_stored_msg( "_last-warning_" )
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
        assert last_warning == marker
