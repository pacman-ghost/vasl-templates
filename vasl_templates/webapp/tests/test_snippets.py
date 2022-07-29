""" Test HTML snippet generation. """

import re
import base64
import time

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.tests import pytest_options
from vasl_templates.webapp.tests.test_user_settings import set_user_settings, SCENARIO_IMAGES_SOURCE_THIS_PROGRAM
from vasl_templates.webapp.tests.utils import \
    init_webapp, select_tab, find_snippet_buttons, set_template_params, wait_for, wait_for_clipboard, wait_for_elem, \
    get_stored_msg, set_stored_msg_marker, find_child, find_children, find_sortable_helper, \
    for_each_template, add_simple_note, edit_simple_note, click_dialog_button, \
    load_trumbowyg, unload_trumbowyg, get_trumbowyg_editor, \
    get_sortable_entry_count, generate_sortable_entry_snippet, drag_sortable_entry_to_trash, \
    new_scenario, set_scenario_date, set_player
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario

# ---------------------------------------------------------------------

def test_snippet_ids( webapp, webdriver ):
    """Check that snippet ID's are generated correctly."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # load a scenario (so that we get some sortable's)
    load_scenario( {
        "COMPASS": "left",
        "SCENARIO_NOTES": [ { "caption": "Scenario note #1"  } ],
        "OB_SETUPS_1": [ { "caption": "OB setup note #1" } ],
        "OB_NOTES_1": [ { "caption": "OB note #1" } ],
        "OB_SETUPS_2": [ { "caption": "OB setup note #2" } ],
        "OB_NOTES_2": [ { "caption": "OB note #2" } ],
    } )

    def check_snippet( btn ):
        """Generate a snippet and check that it has an ID."""
        btn.click()
        wait_for_clipboard( 2, "<!-- vasl-templates:id ", contains=True )

    def do_test( scenario_date ):
        """Check each generated snippet has an ID."""

        # configure the scenario
        set_scenario_date( scenario_date )

        # check each snippet
        for tab_id,btns in snippet_btns.items():
            select_tab( tab_id )
            for btn in btns:
                check_snippet( btn )

    # test snippets with German/Russian
    snippet_btns = find_snippet_buttons()
    do_test( "" )
    do_test( "10/01/1943" )
    do_test( "01/01/1944" )

    # test snippets with British/American
    new_scenario()
    load_scenario( {
        "PLAYER_1": "british", "PLAYER_2": "american",
        "COMPASS": "right",
    } )
    snippet_btns = find_snippet_buttons()
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
        "SCENARIO_NAME": "& > <",
        "SCENARIO_LOCATION": "japan (\u65e5\u672c)",
        "SCENARIO_DATE": "01/02/1942",
        "SCENARIO_WIDTH": "",
    },
        'name = [&amp; &gt; &lt;] | loc = [japan (\u65e5\u672c)] | date = [01/02/1942] aka "2 January, 1942"',
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
    assert generate_sortable_entry_snippet( sortable, 0 ) == "[scenario <i>note</i> #1]"
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
    assert generate_sortable_entry_snippet( sortable, 0 ) == "[japan &lt;\u65e5\u672c&gt;]"

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
        "PLAYER_1_DESCRIPTION": "Froggy Army",
        "PLAYER_2": "british",
        "PLAYER_2_ELR": "3",
        "PLAYER_2_SAN": "4",
        "PLAYER_2_DESCRIPTION": "Barmy Army",
    },
        "player1=[french:French] ; ELR=[1] ; SAN=[2] ; description=[Froggy Army]" \
            " | player2=[british:British] ; ELR=[3] ; SAN=[4] ; description=[Barmy Army]",
        None
    )

    # generate a PLAYERS snippet with both players the same nationality
    _test_snippet( btn, {
        "PLAYER_1": "british",
        },
        "player1=[british:British] ; ELR=[1] ; SAN=[2] ; description=[]" \
            " | player2=[british:British] ; ELR=[3] ; SAN=[4] ; description=[Barmy Army]",
        [ "Both players have the same nationality!" ],
    )

# ---------------------------------------------------------------------

def test_simple_snippets_from_dialog( webapp, webdriver ):
    """Test generating snippets from the "add/edit simple note" dialog."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver, scenario_persistence=1 )
    load_scenario( {
        "SCENARIO_NOTES": [
            { "id": 1, "caption": "scenario note 1", "width": "111px" },
            { "id": 2, "caption": "scenario note 2" }
            ],
        "SSR": [ "SSR #1", "SSR #2" ],
        "SSR_WIDTH": "222px",
        "OB_SETUPS_1": [
            { "id": 1, "caption": "german ob setup #1", "width": "991px" },
            { "id": 2, "caption": "german ob setup #2" }
        ],
        "OB_NOTES_2": [
            { "id": 1, "caption": "russian setup note #1", "width": "992px" },
            { "id": 2, "caption": "russian setup note #2" }
        ]
    } )

    def test_existing_simple_note( sortable, entry_no, expected ):
        # edit the simple note
        elems = find_children( "li", sortable )
        ActionChains(webdriver).double_click( elems[entry_no] ).perform()
        # change the snippet content
        elem = find_child( ".ui-dialog.edit-simple_note .trumbowyg-editor" )
        load_trumbowyg( elem, "modified content" )
        # change the snippet width
        elem = find_child( ".ui-dialog.edit-simple_note input[name='width']" )
        if elem.is_displayed():
            elem.clear()
            elem.send_keys( "123px" )
        # generate the snippet
        click_dialog_button( "Snippet", contains=True )
        if isinstance( expected, str ):
            # NOTE: We also check that the snippet ID is correct.
            expected = re.compile( ".*".join( [
                "<!-- vasl-templates:id {} -->".format( expected ),
                "width: 123px",
                "modified content",
            ] ), re.DOTALL )
        wait_for_clipboard( 2, expected )
        click_dialog_button( "Cancel" )
        click_dialog_button( "OK" )

    def test_new_simple_note( sortable, expected ) :
        # add a new simple note
        find_sortable_helper( sortable, "add" ).click()
        elem = find_child( ".ui-dialog.edit-simple_note .trumbowyg-editor" )
        load_trumbowyg( elem, "new content" )
        elem = find_child( ".ui-dialog.edit-simple_note input[name='width']" )
        if elem.is_displayed():
            elem.clear()
            elem.send_keys( "789px" )
        # generate the snippet
        click_dialog_button( "Snippet", contains=True )
        if isinstance( expected, str ):
            # NOTE: We also check that the snippet ID is correct.
            expected = re.compile( ".*".join( [
                "<!-- vasl-templates:id {} -->".format( expected ),
                "width: 789px",
                "new content",
                ] ), re.DOTALL )
        wait_for_clipboard( 2, expected )
        click_dialog_button( "Cancel" )
        click_dialog_button( "OK" )

    # test scenario notes
    sortable = find_child( "#scenario_notes-sortable" )
    test_existing_simple_note( sortable, 1, "scenario_note.2" )
    test_new_simple_note( sortable, "scenario_note.3" )

    # test SSR's
    sortable = find_child( "#ssr-sortable" )
    test_existing_simple_note( sortable, 1, re.compile( ".*".join( [
        "<!-- vasl-templates:id ssr -->",
        "width: 222px",
        r'<ul id="ssr">\s*<li>\s*SSR #1\s*<li>\s*modified content\s*</ul>',
    ] ), re.DOTALL ) )
    test_new_simple_note( sortable, re.compile( ".*".join( [
        "<!-- vasl-templates:id ssr -->",
        "width: 222px",
        r'<ul id="ssr">\s*<li>\s*SSR #1\s*<li>\s*SSR #2\s*<li>\s*new content\s*</ul>',
    ] ), re.DOTALL ) )

    # test OB setups
    select_tab( "ob1" )
    sortable = find_child( "#ob_setups-sortable_1" )
    test_existing_simple_note( sortable, 1, "german/ob_setup_1.2" )
    test_new_simple_note( sortable, "german/ob_setup_1.3" )

    # test OB setups
    select_tab( "ob2" )
    sortable = find_child( "#ob_notes-sortable_2" )
    test_existing_simple_note( sortable, 1, "russian/ob_note_2.2" )
    test_new_simple_note( sortable, "russian/ob_note_2.3" )

# ---------------------------------------------------------------------

def test_edit_templates( webapp, webdriver ):
    """Test editing templates."""

    # initialize
    webapp.control_tests.set_vo_notes_dir( "{TEST}" )
    init_webapp( webapp, webdriver, scenario_persistence=1, edit_template_links=1 )
    load_scenario( {
        "TURN_TRACK": { "NTURNS": 3 },
        "COMPASS": "down",
    } )
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

# NOTE: These tests are seeing the same problem the WebDriver stress-test was seeing: the shift-click
# on the snippet button is sometimes being interpreted as a request to edit the sortable entry.
# However, the workaround we implemented in that script (dismissing the dialog) doesn't work here,
# and I just couldn't get things to work (not even reloading the page each time helped) :-(
@pytest.mark.skipif(
    pytest_options.webdriver == "firefox",
    reason="Selenium problems (?) cause these tests to fail under Firefox."
)
def test_snippet_images( webapp, webdriver ):
    """Test generating snippet images."""

    # initialize
    webapp.control_tests.set_vo_notes_dir( "{TEST}" )
    init_webapp( webapp, webdriver, scenario_persistence=1, snippet_image_persistence=1 )

    # check if there is a webdriver configured
    remote_app_config = webapp.control_tests.get_app_config()
    if "WEBDRIVER_PATH" not in remote_app_config:
        return

    # load a test scenario
    load_scenario( {
        "PLAYER_1": "german", "PLAYER_2": "russian",
        "SCENARIO_NAME": "test scenario", "SCENARIO_DATE": "1940-01-01", "SCENARIO_LOCATION": "somewhere",
        "SCENARIO_NOTES": [ { "caption": "Scenario note #1"  } ],
        "VICTORY_CONDITIONS": "win at all costs!",
        "SSR": [ "a test ssr" ],
        "OB_SETUPS_1": [ { "caption": "OB setup note #1" } ],
        "OB_NOTES_1": [ { "caption": "OB note #1" } ],
        "OB_VEHICLES_1": [ { "name": "a german vehicle" } ],
        "OB_ORDNANCE_1": [ { "name": "a german ordnance" } ],
        "OB_SETUPS_2": [ { "caption": "OB setup note #2" } ],
        "OB_NOTES_2": [ { "caption": "OB note #2" } ],
        "OB_VEHICLES_2": [ { "name": "a russian vehicle" } ],
        "OB_ORDNANCE_2": [ { "name": "a russian ordnance" } ],
    } )

    def do_test( snippet_btn, expected_fname ): #pylint: disable=missing-docstring

        # clear the return buffer
        ret_buffer = find_child( "#_snippet-image-persistence_" )
        assert ret_buffer.tag_name == "textarea"
        webdriver.execute_script( "arguments[0].value = arguments[1]", ret_buffer, "" )

        # shift-click the snippet button
        ActionChains( webdriver ).key_down( Keys.SHIFT ).click( snippet_btn ).perform()
        ActionChains( webdriver ).key_up( Keys.SHIFT ).perform()

        # wait for the snippet image to be generated
        wait_for( 20, lambda: ret_buffer.get_attribute( "value" ) )
        fname, img_data = ret_buffer.get_attribute( "value" ).split( "|", 1 )
        img_data = base64.b64decode( img_data )

        # check the results
        assert fname == expected_fname
        last_snippet_image = webapp.control_tests.get_last_snippet_image()
        assert img_data == last_snippet_image

    def do_simple_test( template_id, expected_fname ): #pylint: disable=missing-docstring
        btn = find_child( "button.generate[data-id='{}']".format( template_id ) )
        do_test( btn, expected_fname )

    def do_sortable_test( sortable_id, expected_fname ): #pylint: disable=missing-docstring
        entries = find_children( "#{} li".format( sortable_id ) )
        assert len(entries) == 1
        btn = find_child( "img.snippet", entries[0] )
        do_test( btn, expected_fname )

    # do the tests
    do_simple_test( "scenario", "scenario.png" )
    do_simple_test( "players", "players.png" )
    do_sortable_test( "scenario_notes-sortable", "scenario note.1.png" )
    do_simple_test( "victory_conditions", "victory conditions.png" )
    do_simple_test( "ssr", "ssr.png" )

    # do the tests
    select_tab( "ob1" )
    do_sortable_test( "ob_setups-sortable_1", "ob setup 1.1.png" )
    do_sortable_test( "ob_notes-sortable_1", "ob note 1.1.png" )
    do_sortable_test( "ob_vehicles-sortable_1", "a german vehicle.png" )
    do_sortable_test( "ob_ordnance-sortable_1", "a german ordnance.png" )

    # do the tests
    select_tab( "ob2" )
    do_sortable_test( "ob_setups-sortable_2", "ob setup 2.1.png" )
    do_sortable_test( "ob_notes-sortable_2", "ob note 2.1.png" )
    do_sortable_test( "ob_vehicles-sortable_2", "a russian vehicle.png" )
    do_sortable_test( "ob_ordnance-sortable_2", "a russian ordnance.png" )

# ---------------------------------------------------------------------

def test_player_flags_in_trumbowyg( webapp, webdriver, monkeypatch ):
    """Test inserting images for player flags into Trumbowyg HTML editor controls."""

    # initialize
    monkeypatch.setitem( webapp.config, "TRUMBOWYG_BUTTONS_VICTORY_CONDITIONS" ,
        [ "flags", "viewHTML" ]
    )
    init_webapp( webapp, webdriver )

    def check_flags_dropdown( expected ):
        dropdown = find_child( "#panel-vc .trumbowyg-dropdown-flags" )
        nats = [
            img.get_attribute( "data-nat" )
            for img in find_children( "button img", dropdown )
        ]
        assert nats[ 0 : len(expected) ] == expected

    # check the initial state of the flags dropdown
    check_flags_dropdown( [ "german", "russian", "american", "british" ] )

    # change the players, check the flags dropdown
    set_player( 1, "british" )
    set_player( 2, "french" )
    check_flags_dropdown( [ "british", "french", "american", "burmese" ] )

    # load some content into the Victory Conditions and position the cursor
    editor = get_trumbowyg_editor( "VICTORY_CONDITIONS" )
    editor.send_keys( "abcxyz" )
    for _ in range( 3 ):
        editor.send_keys( Keys.LEFT )

    def insert_flag( nat ):
        find_child( "#panel-vc .trumbowyg-flags-button" ).click()
        wait_for_elem( 2, "#panel-vc .trumbowyg-dropdown-flags" )
        find_child( "button.trumbowyg-{}-dropdown-button".format( nat ) ).click()
    def wait_for_flag( expected ):
        if expected.search( unload_trumbowyg( editor ) ):
            return True
        time.sleep( 0.1 )
        return False

    # insert an online flag
    insert_flag( "japanese" )
    wait_for( 2, lambda: wait_for_flag(
        re.compile( 'abc<img src="http://vasl-templates.org/.+?/japanese.png["?].+?>xyz' )
    ) )

    # configure local images, then add another image
    # NOTE: Opening the User Settings dialog makes the cursor move to the start of the Trumboyg content.
    set_user_settings( { "scenario-images-source": SCENARIO_IMAGES_SOURCE_THIS_PROGRAM } )
    insert_flag( "american" )
    wait_for( 2, lambda: wait_for_flag(
        re.compile( r'<img src="http://localhost:\d+/flags/american["?].+?>abc<img src="http://vasl-templates.org/' )
    ) )

# ---------------------------------------------------------------------

@pytest.mark.skipif( pytest_options.short_tests, reason="--short-tests specified" )
def test_jinja_in( webapp, webdriver ):
    """Test the "in" operator in Jinja templates."""

    # initialize
    init_webapp( webapp, webdriver, edit_template_links=1 )

    def do_test( search_for, search_in, expected ):
        """Test the IN operator."""
        # install a new template
        elem = find_child( "a._edit-template-link_[data-id='victory_conditions']" )
        webdriver.execute_script( "$(arguments[0]).click();", elem )
        elem = find_child( "#edit-template textarea" )
        elem.clear()
        buf = [
            "{%set HELLO_WORLD = \"Hello, world!\"%}",
            "{%set HELLO = \"hello\"%}",
            "{%if " + search_for + " in " + search_in + "%} YES {%else%} NO {%endif%}"
        ]
        template = "\n".join( buf )
        elem.send_keys( template )
        elem.send_keys( Keys.ESCAPE )
        # process the template
        elem = find_child( "button.generate[data-id='victory_conditions']" )
        elem.click()
        wait_for_clipboard( 2, "YES" if expected else "NO" )

    # do th tests
    do_test( '"foo"', "HELLO_WORLD", False )
    do_test( '"O, W"', "HELLO_WORLD", True )
    do_test( "HELLO", "HELLO_WORLD", True )
    do_test( "HELLO", '"hello, big guy!"', True )

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
