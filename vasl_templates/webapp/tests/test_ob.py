""" Test generating OB SETUP snippets. """

import re
import types

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains

from vasl_templates.webapp.tests.utils import get_nationalities, get_clipboard, get_stored_msg
from vasl_templates.webapp.tests.utils import select_tab, find_child, find_children, click_dialog_button

# ---------------------------------------------------------------------

# NOTE: Handling of OB setups and OB notes is identical (the only difference
# is in the template files, where OB setups have a colored header).

def test_ob_setup( webapp, webdriver ):
    """Test generating OB setup snippets."""
    _do_test_ob_entries( webapp, webdriver, "ob_setups" )

def test_ob_notes( webapp, webdriver ):
    """Test generating OB note snippets."""
    _do_test_ob_entries( webapp, webdriver, "ob_notes" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _do_test_ob_entries( webapp, webdriver, ob_type ):
    """Test generating OB setup/notes."""

    # initialize
    webdriver.get( webapp.url_for( "main" ) )
    colors = {
        "german": "col=[OBCOL:german/OBCOL2:german]", #.format( ob_type ) ,
        "russian": "col=[OBCOL:russian/OBCOL2:russian]" #.format( ob_type )
    }

    # generate OB setup/note snippets for both players
    def check_snippet( player_id, entry_no, expected ):
        """Generate the snippet for an OB setup/note."""
        select_tab( "ob{}".format( player_id ) )
        elems = find_children( "#{}-sortable_{} li input[type='button']".format( ob_type, player_id ) )
        elems[entry_no].click()
        if ob_type == "ob_notes":
            expected = re.sub( r" \(col=.*?\)", "", expected )
        assert get_clipboard() == expected
    _do_add_ob_entry( webdriver, 1, ob_type, "{} #1".format(ob_type), None )
    _do_add_ob_entry( webdriver, 1, ob_type, "{} #2".format(ob_type), "2px" )
    _do_add_ob_entry( webdriver, 2, ob_type, "<i>{}</i> #3".format(ob_type), "3px" )
    check_snippet( 1, 0, "[German] [{} #1] ({})".format( ob_type, colors["german"] ) )
    check_snippet( 1, 1, "[German] [{} #2] ({}) (width=[2px])".format( ob_type, colors["german"] ) )
    check_snippet( 2, 0, "[Russian] [<i>{}</i> #3] ({}) (width=[3px])".format( ob_type, colors["russian"] ) )

    # make some changes and check the snippets again
    _do_edit_ob_entry( webdriver, 2, ob_type, 0, "updated {} #3".format(ob_type), "" )
    _do_edit_ob_entry( webdriver, 1, ob_type, 1, "<i>updated {} #2</i>".format(ob_type), "200px" )
    _do_edit_ob_entry( webdriver, 1, ob_type, 0, None, "100px" )
    check_snippet( 2, 0, "[Russian] [updated {} #3] ({})".format( ob_type, colors["russian"] ) )
    check_snippet( 1, 1, "[German] [<i>updated {} #2</i>] ({}) (width=[200px])".format( ob_type, colors["german"] ) )
    check_snippet( 1, 0, "[German] [{} #1] ({}) (width=[100px])".format( ob_type, colors["german"] ) )

    # delete an OB setup/note by dragging it into the trash
    def count_entries( player_id ):
        """Count the number of OB setup/notes."""
        elems = find_children( "#{}-sortable_{} li".format( ob_type, player_id ) )
        return len(elems)
    select_tab( "ob1" )
    assert count_entries(1) == 2
    elem = find_child( "#{}-sortable_1 li[2]".format( ob_type ) )
    trash = find_child( "#{}-trash_1".format( ob_type ) )
    ActionChains(webdriver).drag_and_drop( elem, trash ).perform()
    assert count_entries(1) == 1

    # delete an OB setup/note by emptying its caption
    _do_edit_ob_entry( webdriver, 1, ob_type, 0, "", None )
    click_dialog_button( "OK" ) # nb: confirm the deletion
    assert count_entries(1) == 0

# ---------------------------------------------------------------------

def test_nationality_specific( webapp, webdriver ):
    """Check that nationality-specific buttons are shown/hidden correctly."""

    # initialize
    webdriver.get( webapp.url_for( "main", store_msgs=1 ) )
    nationalities = get_nationalities( webapp )

    # initialize
    def set_scenario_date( date ):
        """Set the scenario date."""
        select_tab( "scenario" )
        elem = find_child( "#panel-scenario input[name='SCENARIO_DATE']" )
        elem.clear()
        elem.send_keys( "{:02}/01/{:04}".format( date[1], date[0] ) )

    # initialize
    def check_pf_snippets():
        """Check that the PF snippets are generated correctly."""
        def do_test( date, expected, warning ): #pylint: disable=missing-docstring
            # test snippet generation
            set_scenario_date( date )
            select_tab( "ob1" )
            elem = find_child( "input[type='button'][data-id='pf']" )
            elem.click()
            assert get_clipboard() == expected
            # check if a warning was issued
            last_warning = get_stored_msg( "_last-warning_" ) or ""
            if warning:
                assert last_warning.startswith( "PF are only available" )
            else:
                assert last_warning == ""
        do_test( (1942,1), "PF: range=[1] ; check=[2] (drm=[+1]) ; col=[OBCOL:german]/[OBCOL2:german]", True )
        do_test( (1943,9), "PF: range=[1] ; check=[2] (drm=[+1]) ; col=[OBCOL:german]/[OBCOL2:german]", True )
        do_test( (1943,10), "PF: range=[1] ; check=[3] ; col=[OBCOL:german]/[OBCOL2:german]", False )
        do_test( (1944,5), "PF: range=[1] ; check=[3] ; col=[OBCOL:german]/[OBCOL2:german]", False )
        do_test( (1944,6), "PF: range=[2] ; check=[3] ; col=[OBCOL:german]/[OBCOL2:german]", False )
        do_test( (1944,12), "PF: range=[2] ; check=[3] ; col=[OBCOL:german]/[OBCOL2:german]", False )
        do_test( (1945,1), "PF: range=[3] ; check=[4] (drm=[-1]) ; col=[OBCOL:german]/[OBCOL2:german]", False )
        do_test( (1946,1), "PF: range=[3] ; check=[4] (drm=[-1]) ; col=[OBCOL:german]/[OBCOL2:german]", False )

    # initialize
    def check_baz_snippets():
        """Check that the BAZ snippets are generated correctly."""
        def do_test( date, expected ): #pylint: disable=missing-docstring
            # test snippet generation
            set_scenario_date( date )
            select_tab( "ob1" )
            elem = find_child( "input[type='button'][data-id='baz']" )
            elem.click()
            assert get_clipboard() == expected
            # check if a warning was issued
            last_warning = get_stored_msg( "_last-warning_" ) or ""
            if expected == "BAZ: none":
                assert last_warning.startswith( "BAZ are only available" )
            else:
                assert last_warning == ""
        do_test( (1941,1), "BAZ: none" )
        do_test( (1942,10), "BAZ: none" )
        do_test( (1942,11), "BAZ: '43 ; range=[4] ; X#=[10] ; TK#=[13] ; col=[OBCOL:american]/[OBCOL2:american]" )
        do_test( (1943,1), "BAZ: '43 ; range=[4] ; X#=[10] ; TK#=[13] ; col=[OBCOL:american]/[OBCOL2:american]" )
        do_test( (1944,1), "BAZ: '44 ; range=[4] ; X#=[11] ; TK#=[16] ; col=[OBCOL:american]/[OBCOL2:american]" )
        do_test( (1945,1),
            "BAZ: '45 ; range=[5] ; X#=[11] ; TK#=[16] ; WP#=[6] ; col=[OBCOL:american]/[OBCOL2:american]"
        )
        do_test( (1946,1),
            "BAZ: '45 ; range=[5] ; X#=[11] ; TK#=[16] ; WP#=[6] ; col=[OBCOL:american]/[OBCOL2:american]"
        )

    # initialize
    nationality_specific_buttons = {
        "mol": [ "russian", "Burn, baby, burn! ; col=[OBCOL:russian]/[OBCOL2:russian]" ],
        "mol-p": [ "russian", "mol-p template ; col=[OBCOL:russian]/[OBCOL2:russian]" ],
        "pf": [ "german", check_pf_snippets ],
        "psk": [ "german", "====> whoosh! ; col=[OBCOL:german]/[OBCOL2:german]" ],
        "atmm": [ "german", "Kaboom!!! ; col=[OBCOL:german]/[OBCOL2:german]" ],
        "baz": [ "american", check_baz_snippets ],
        "piat": [ "british", "piat template ; col=[OBCOL:british]/[OBCOL2:british]" ],
    }

    # iterate through each nationality
    for nat in nationalities:

        # change the nationality for player 1
        select_tab( "scenario" )
        sel = Select(
            find_child( "select[name='PLAYER_1']" )
        )
        sel.select_by_value( nat )
        select_tab( "ob1" )

        # check the nationality-specific buttons
        for button_id,expected in nationality_specific_buttons.items():
            elem = find_child( "input[type='button'][data-id='{}']".format( button_id ) )
            if nat == expected[0]:
                # the button should be shown for this nationality
                assert elem.is_displayed()
                # make sure that the template works
                elem.click()
                if isinstance( expected[1], str ):
                    assert get_clipboard() == expected[1]
                elif isinstance( expected[1], types.FunctionType ):
                    expected[1]() #pylint: disable=not-callable
                else:
                    assert False
            else:
                # it should be hidden for all other nationalities
                assert not elem.is_displayed()

# ---------------------------------------------------------------------

def add_ob_setup( webdriver, player_id, caption, width ):
    """Add a new OB setup."""
    _do_add_ob_entry( webdriver, player_id, "ob_setups", caption, width )

def add_ob_note( webdriver, player_id, caption, width ):
    """Add a new OB note."""
    _do_add_ob_entry( webdriver, player_id, "ob_notes", caption, width )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _do_add_ob_entry( webdriver, player_id, ob_type, caption, width ):
    """Add a new OB setup/note."""
    select_tab( "ob{}".format( player_id ) )
    elem = find_child( "#{}-add_{}".format( ob_type, player_id ) )
    elem.click()
    _do_edit_ob_entry( webdriver, player_id, ob_type, None, caption, width )

# ---------------------------------------------------------------------

def edit_ob_setup( webdriver, player_id, entry_no, caption, width ):
    """Edit an OB setup."""
    _do_edit_ob_entry( webdriver, player_id, "ob_setups", entry_no, caption, width )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _do_edit_ob_entry( webdriver, player_id, ob_type, entry_no, caption, width ):
    """Edit an OB setup/note."""
    # locate the requested entry and start editing it
    if entry_no is not None:
        select_tab( "ob{}".format( player_id ) )
        elems = find_children( "#{}-sortable_{} li".format( ob_type, player_id ) )
        elem = elems[ entry_no ]
        ActionChains(webdriver).double_click( elem ).perform()

    # edit the OB setup/note
    if caption is not None:
        elem = find_child( "#edit-simple_note textarea" )
        elem.clear()
        elem.send_keys( caption )
    if width is not None:
        elem = find_child( "#edit-simple_note input[type='text']" )
        elem.clear()
        elem.send_keys( width )
    click_dialog_button( "OK" )
