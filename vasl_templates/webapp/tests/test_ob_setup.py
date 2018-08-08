""" Test generating OB SETUP snippets. """

import types

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains

from vasl_templates.webapp.tests.utils import get_nationalities, get_clipboard, get_stored_msg
from vasl_templates.webapp.tests.utils import select_tab, find_child, find_children, click_dialog_button

# ---------------------------------------------------------------------

def test_ob_setup( webapp, webdriver ):
    """Test generating OB SETUP snippets."""

    # initialize
    webdriver.get( webapp.url_for( "main" ) )

    # generate OB SETUP snippets for both players
    def check_snippet( player_id, entry_no, expected ):
        """Generate the snippet for an OB setup."""
        select_tab( "ob{}".format( player_id ) )
        elems = find_children( "#ob_setup-sortable_{} li input[type='button']".format( player_id ) )
        elems[entry_no].click()
        assert get_clipboard() == expected
    add_ob_setup( webdriver, 1, "ob setup #1" )
    add_ob_setup( webdriver, 1, "ob setup #2", "2px" )
    add_ob_setup( webdriver, 2, "ob <i>setup</i> #3", "3px" )
    check_snippet( 1, 0, "[German] [ob setup #1] (col=[OBCOL:german/OBCOL2:german])" )
    check_snippet( 1, 1, "[German] [ob setup #2] (col=[OBCOL:german/OBCOL2:german]) (width=[2px])" )
    check_snippet( 2, 0, "[Russian] [ob <i>setup</i> #3] (col=[OBCOL:russian/OBCOL2:russian]) (width=[3px])" )

    # make some changes and check the snippets again
    edit_ob_setup( webdriver, 2, 0, "updated ob setup #3", "" )
    edit_ob_setup( webdriver, 1, 1, "<i>updated ob setup #2</i>", "200px" )
    edit_ob_setup( webdriver, 1, 0, None, "100px" )
    check_snippet( 2, 0, "[Russian] [updated ob setup #3] (col=[OBCOL:russian/OBCOL2:russian])" )
    check_snippet( 1, 1, "[German] [<i>updated ob setup #2</i>] (col=[OBCOL:german/OBCOL2:german]) (width=[200px])" )
    check_snippet( 1, 0, "[German] [ob setup #1] (col=[OBCOL:german/OBCOL2:german]) (width=[100px])" )

    # delete an OB setup by dragging it into the trash
    def count_entries( player_id ):
        """Count the number of OB setup's."""
        elems = find_children( "#ob_setup-sortable_{} li".format( player_id ) )
        return len(elems)
    select_tab( "ob1" )
    assert count_entries(1) == 2
    elem = find_child( "#ob_setup-sortable_1 li[2]" )
    trash = find_child( "#ob_setup-trash_1" )
    ActionChains(webdriver).drag_and_drop( elem, trash ).perform()
    assert count_entries(1) == 1

    # delete an OB setup by emptying its caption
    edit_ob_setup( webdriver, 1, 0, "", None )
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

def add_ob_setup( webdriver, player_id, caption, width=None ):
    """Add a new OB setup."""
    select_tab( "ob{}".format( player_id ) )
    elem = find_child( "#ob_setup-add_{}".format( player_id ) )
    elem.click()
    edit_ob_setup( webdriver, player_id, None, caption, width )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def edit_ob_setup( webdriver, player_id, entry_no, caption, width ):
    """Edit an OB setup."""

    # locate the requested entry and start editing it
    if entry_no is not None:
        select_tab( "ob{}".format( player_id ) )
        elems = find_children( "#ob_setup-sortable_{} li".format( player_id ) )
        elem = elems[ entry_no ]
        ActionChains(webdriver).double_click( elem ).perform()

    # edit the OB setup
    if caption is not None:
        elem = find_child( "#edit-ob_setup textarea" )
        elem.clear()
        elem.send_keys( caption )
    if width is not None:
        elem = find_child( "#edit-ob_setup input[type='text']" )
        elem.clear()
        elem.send_keys( width )
    click_dialog_button( "OK" )
