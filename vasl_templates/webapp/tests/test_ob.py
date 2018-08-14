""" Test generating OB SETUP snippets. """

import re
import types

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.tests.utils import \
    get_nationalities, get_clipboard, get_stored_msg, set_stored_msg_marker, select_tab, find_child, find_children, \
    add_simple_note, edit_simple_note, get_sortable_entry_count, drag_sortable_entry_to_trash, \
    select_droplist_val

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
    sortable1 = find_child( "#{}-sortable_1".format( ob_type ) )
    sortable2 = find_child( "#{}-sortable_2".format( ob_type ) )

    # generate OB setup/note snippets for both players
    select_tab( "ob1" )
    add_simple_note( sortable1, "{} #1".format(ob_type), None )
    add_simple_note( sortable1, "{} #2".format(ob_type), "2px" )
    select_tab( "ob2" )
    add_simple_note( sortable2, "<i>{}</i> #3".format(ob_type), "3px" )

    # check that snippets are generated correctly
    def check_snippet( sortable, entry_no, expected ):
        """Generate the snippet for an OB setup/note."""
        elems = find_children( "li img.snippet", sortable )
        elems[entry_no].click()
        if ob_type == "ob_notes":
            expected = re.sub( r" \(col=.*?\)", "", expected )
        assert get_clipboard() == expected
    select_tab( "ob1" )
    check_snippet( sortable1, 0,
        "[German] [{} #1] (col=[OBCOL:german/OBCOL2:german])".format( ob_type )
    )
    check_snippet( sortable1, 1,
        "[German] [{} #2] (col=[OBCOL:german/OBCOL2:german]) (width=[2px])".format( ob_type )
    )
    select_tab( "ob2" )
    check_snippet( sortable2, 0,
        "[Russian] [<i>{}</i> #3] (col=[OBCOL:russian/OBCOL2:russian]) (width=[3px])".format( ob_type )
    )

    # make some changes and check the snippets again
    edit_simple_note( sortable2, 0, "updated {} #3".format(ob_type), "" )
    select_tab( "ob1" )
    edit_simple_note( sortable1, 1, "<i>updated {} #2</i>".format(ob_type), "200px" )
    edit_simple_note( sortable1, 0, None, "100px" )
    select_tab( "ob2" )
    check_snippet( sortable2, 0,
        "[Russian] [updated {} #3] (col=[OBCOL:russian/OBCOL2:russian])".format( ob_type )
    )
    select_tab( "ob1" )
    check_snippet( sortable1, 1,
        "[German] [<i>updated {} #2</i>] (col=[OBCOL:german/OBCOL2:german]) (width=[200px])".format( ob_type )
    )
    check_snippet( sortable1, 0,
        "[German] [{} #1] (col=[OBCOL:german/OBCOL2:german]) (width=[100px])".format( ob_type )
    )

    # delete an OB setup/note by dragging it into the trash
    assert get_sortable_entry_count( sortable1 ) == 2
    drag_sortable_entry_to_trash( sortable1, 1 )
    assert get_sortable_entry_count( sortable1 ) == 1

    # delete an OB setup/note by emptying its caption
    edit_simple_note( sortable1, 0, "", None )
    assert get_sortable_entry_count( sortable1 ) == 0

# ---------------------------------------------------------------------

def test_nationality_specific( webapp, webdriver ): #pylint: disable=too-many-locals
    """Check that nationality-specific buttons are shown/hidden correctly."""

    # initialize
    webdriver.get( webapp.url_for( "main" ) )
    nationalities = get_nationalities( webapp )

    # initialize
    scenario_date = find_child( "#panel-scenario input[name='SCENARIO_DATE']" )
    def set_scenario_date( date ):
        """Set the scenario date."""
        select_tab( "scenario" )
        scenario_date.clear()
        scenario_date.send_keys( "{:02}/01/{:04}".format( date[1], date[0] ) )

    def do_check_snippets( btn, date, expected, warning ):
        """Check that snippets are being generated correctly."""
        # test snippet generation
        set_scenario_date( date )
        select_tab( "ob1" )
        marker = set_stored_msg_marker( "_last-warning_" )
        btn.click()
        assert get_clipboard() == expected
        # check if a warning was issued
        last_warning = get_stored_msg( "_last-warning_" )
        image_url = find_child( "img", btn ).get_attribute( "src" )
        if warning:
            assert "are only available" in last_warning
            assert "snippet-disabled.png" in image_url
        else:
            assert last_warning == marker
            assert "snippet.png" in image_url

    # initialize
    def check_pf_snippets():
        """Check that the PF snippets are generated correctly."""
        btn = find_child( "button[data-id='pf']" )
        col = "[OBCOL:german]/[OBCOL2:german]"
        do_check_snippets( btn, (1942,1), "PF: range=[1] ; check=[2] (drm=[+1]) ; col={}".format(col), True )
        do_check_snippets( btn, (1943,9), "PF: range=[1] ; check=[2] (drm=[+1]) ; col={}".format(col), True )
        do_check_snippets( btn, (1943,10), "PF: range=[1] ; check=[3] ; col={}".format(col), False )
        do_check_snippets( btn, (1944,5), "PF: range=[1] ; check=[3] ; col={}".format(col), False )
        do_check_snippets( btn, (1944,6), "PF: range=[2] ; check=[3] ; col={}".format(col), False )
        do_check_snippets( btn, (1944,12), "PF: range=[2] ; check=[3] ; col={}".format(col), False )
        do_check_snippets( btn, (1945,1), "PF: range=[3] ; check=[4] (drm=[-1]) ; col={}".format(col), False )
        do_check_snippets( btn, (1946,1), "PF: range=[3] ; check=[4] (drm=[-1]) ; col={}".format(col), False )

    # initialize
    def check_psk_snippets():
        """Check that the PSK snippets are generated correctly."""
        btn = find_child( "button[data-id='psk']" )
        expected = "====> whoosh! ; col=[OBCOL:german]/[OBCOL2:german]"
        do_check_snippets( btn, (1942,1), expected, True )
        do_check_snippets( btn, (1943,9), expected, True )
        do_check_snippets( btn, (1943,10), expected, False )
        do_check_snippets( btn, (1944,1), expected, False )

    # initialize
    def check_baz_snippets():
        """Check that the BAZ snippets are generated correctly."""
        btn = find_child( "button[data-id='baz']" )
        do_check_snippets( btn, (1941,1), "BAZ: none", True )
        do_check_snippets( btn, (1942,10), "BAZ: none", True )
        col = "[OBCOL:american]/[OBCOL2:american]"
        do_check_snippets( btn, (1942,11), "BAZ: '43 ; range=[4] ; X#=[10] ; TK#=[13] ; col={}".format(col), False )
        do_check_snippets( btn, (1943,1), "BAZ: '43 ; range=[4] ; X#=[10] ; TK#=[13] ; col={}".format(col), False )
        do_check_snippets( btn, (1944,1), "BAZ: '44 ; range=[4] ; X#=[11] ; TK#=[16] ; col={}".format(col), False )
        do_check_snippets( btn, (1945,1),
            "BAZ: '45 ; range=[5] ; X#=[11] ; TK#=[16] ; WP#=[6] ; col={}".format(col),
            False
        )
        do_check_snippets( btn, (1946,1),
            "BAZ: '45 ; range=[5] ; X#=[11] ; TK#=[16] ; WP#=[6] ; col={}".format(col),
            False
        )

    # initialize
    def check_atmm_snippets():
        """Check that the ATMM snippets are generated correctly."""
        btn = find_child( "button[data-id='atmm']" )
        expected = "Kaboom!!! ; col=[OBCOL:german]/[OBCOL2:german]"
        do_check_snippets( btn, (1943,12), expected, True )
        do_check_snippets( btn, (1944,1), expected, False )
        do_check_snippets( btn, (1944,12), expected, False )
        do_check_snippets( btn, (1945,1), expected, False )

    # initialize
    nationality_specific_buttons = {
        "mol": [ "russian", "Burn, baby, burn! ; col=[OBCOL:russian]/[OBCOL2:russian]" ],
        "mol-p": [ "russian", "mol-p template ; col=[OBCOL:russian]/[OBCOL2:russian]" ],
        "pf": [ "german", check_pf_snippets ],
        "psk": [ "german", check_psk_snippets ],
        "atmm": [ "german", check_atmm_snippets ],
        "baz": [ "american", check_baz_snippets ],
        "piat": [ "british", "piat template ; col=[OBCOL:british]/[OBCOL2:british]" ],
    }
    btn_elems = {
        btn: find_child( "button[data-id='{}']".format( btn ) )
        for btn in nationality_specific_buttons
    }

    # iterate through each nationality
    player1_sel = Select( find_child( "select[name='PLAYER_1']" ) )
    for nat in nationalities:

        # change the nationality for player 1
        select_tab( "scenario" )
        select_droplist_val( player1_sel, nat )

        # check the nationality-specific buttons
        select_tab( "ob1" )
        for button_id,expected in nationality_specific_buttons.items():
            elem = btn_elems[ button_id ]
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
