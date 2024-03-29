""" Test generating OB SETUP snippets. """

import re
import types

from vasl_templates.webapp.tests.utils import \
    get_nationalities, wait_for_clipboard, get_stored_msg, set_stored_msg_marker, select_tab, \
    find_child, find_children, \
    add_simple_note, edit_simple_note, get_sortable_entry_count, drag_sortable_entry_to_trash, \
    init_webapp, wait_for, adjust_html, set_scenario_date, set_player, set_theater

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
    init_webapp( webapp, webdriver )
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
        assert wait_for_clipboard( 2, expected, transform=adjust_html )
    select_tab( "ob1" )
    check_snippet( sortable1, 0,
        "[German] [{} #1] (col=[OBCOL:german/OBCOL-BORDER:german])".format( ob_type )
    )
    check_snippet( sortable1, 1,
        "[German] [{} #2] (col=[OBCOL:german/OBCOL-BORDER:german]) (width=[2px])".format( ob_type )
    )
    select_tab( "ob2" )
    check_snippet( sortable2, 0,
        "[Russian] [<i>{}</i> #3] (col=[OBCOL:russian/OBCOL-BORDER:russian]) (width=[3px])".format( ob_type )
    )

    # make some changes and check the snippets again
    edit_simple_note( sortable2, 0, "updated {} #3".format(ob_type), "" )
    select_tab( "ob1" )
    edit_simple_note( sortable1, 1, "<i>updated {} #2</i>".format(ob_type), "200px" )
    edit_simple_note( sortable1, 0, None, "100px" )
    select_tab( "ob2" )
    check_snippet( sortable2, 0,
        "[Russian] [updated {} #3] (col=[OBCOL:russian/OBCOL-BORDER:russian])".format( ob_type )
    )
    select_tab( "ob1" )
    check_snippet( sortable1, 1,
        "[German] [<i>updated {} #2</i>] (col=[OBCOL:german/OBCOL-BORDER:german]) (width=[200px])".format( ob_type )
    )
    check_snippet( sortable1, 0,
        "[German] [{} #1] (col=[OBCOL:german/OBCOL-BORDER:german]) (width=[100px])".format( ob_type )
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
    init_webapp( webapp, webdriver )
    nationalities = get_nationalities( webapp )

    def do_check_snippets( btn, date, expected, warning ):
        """Check that snippets are being generated correctly."""

        # change the scenario date, check that the button is displayed correctly
        set_scenario_date( "{:02}/01/{:04}".format( date[1], date[0] ) )
        select_tab( "ob1" )
        classes = btn.get_attribute( "class" )
        classes = classes.split() if classes else []
        if warning:
            assert "inactive" in classes
        else:
            assert "inactive" not in classes

        # test snippet generation
        marker = set_stored_msg_marker( "_last-warning_" )
        btn.click()
        wait_for_clipboard( 2, expected )

        # check if a warning was issued
        last_warning = get_stored_msg( "_last-warning_" )
        if warning:
            assert "are only available" in last_warning
            expected_image_url = "snippet-disabled.png"
        else:
            assert last_warning == marker
            expected_image_url = "snippet.png"
        wait_for( 2,
            lambda: expected_image_url in find_child( "img", btn ).get_attribute( "src" )
        )

    # initialize
    def check_pf_snippets():
        """Check that the PF snippets are generated correctly."""
        btn = find_child( "button[data-id='pf']" )
        col = "[OBCOL:german]/[OBCOL-BORDER:german]"
        do_check_snippets( btn, (1942,1), "PF: range=[1] ; check=[3] ; col={}".format(col), True )
        do_check_snippets( btn, (1943,9), "PF: range=[1] ; check=[3] ; col={}".format(col), True )
        do_check_snippets( btn, (1943,10), "PF: range=[1] ; check=[3] ; col={}".format(col), False )
        do_check_snippets( btn, (1944,5), "PF: range=[1] ; check=[3] ; col={}".format(col), False )
        do_check_snippets( btn, (1944,6), "PF: range=[2] ; check=[3] ; col={}".format(col), False )
        do_check_snippets( btn, (1944,12), "PF: range=[2] ; check=[3] ; col={}".format(col), False )
        do_check_snippets( btn, (1945,1), "PF: range=[3] ; check=[4] ; col={}".format(col), False )
        do_check_snippets( btn, (1946,1), "PF: range=[3] ; check=[4] ; col={}".format(col), False )

    # initialize
    def check_psk_snippets():
        """Check that the PSK snippets are generated correctly."""
        btn = find_child( "button[data-id='psk']" )
        expected = "====> whoosh! ; col=[OBCOL:german]/[OBCOL-BORDER:german]"
        do_check_snippets( btn, (1942,1), expected, True )
        do_check_snippets( btn, (1943,8), expected, True )
        do_check_snippets( btn, (1943,9), expected, False )
        do_check_snippets( btn, (1944,1), expected, False )

    # initialize
    def check_baz_snippets():
        """Check that the BAZ snippets are generated correctly."""
        btn = find_child( "button[data-id='baz']" )
        do_check_snippets( btn, (1941,1), "BAZ: none", True )
        do_check_snippets( btn, (1942,10), "BAZ: none", True )
        col = "[OBCOL:american]/[OBCOL-BORDER:american]"
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
        expected = "Kaboom!!! ; col=[OBCOL:german]/[OBCOL-BORDER:german]"
        do_check_snippets( btn, (1943,12), expected, True )
        do_check_snippets( btn, (1944,1), expected, False )
        do_check_snippets( btn, (1944,12), expected, False )
        do_check_snippets( btn, (1945,1), expected, False )

    # initialize
    nationality_specific_buttons = {
        "mol": [ "russian", "Burn, baby, burn! ; col=[OBCOL:russian]/[OBCOL-BORDER:russian]" ],
        "mol-p": [ "russian", "mol-p template ; col=[OBCOL:russian]/[OBCOL-BORDER:russian]" ],
        "pf": [ "german", check_pf_snippets ],
        "psk": [ "german", check_psk_snippets ],
        "atmm": [ "german", check_atmm_snippets ],
        "baz": [ "american", check_baz_snippets ],
        "baz45": [ ("american","Korea"), "BAZ 45 (from K:FW)" ],
        "baz50": [ ("american","Korea"), "BAZ 50 (from K:FW)" ],
        "baz-cpva16": [ "kfw-cpva", "BAZ 44 (from K:FW)" ],
        "baz-cpva17": [ "kfw-cpva", "BAZ Type 51 (from K:FW)" ],
        "piat": [ "british", "piat template ; col=[OBCOL:british]/[OBCOL-BORDER:british]" ],
        "thh": [ "japanese", "Banzai!!!" ],
    }
    btn_elems = {
        btn: find_child( "button[data-id='{}']".format( btn ) )
        for btn in nationality_specific_buttons
    }

    # iterate through each nationality
    for nat in nationalities:

        # change the nationality for player 1
        set_player( 1, nat )

        # check the nationality-specific buttons
        select_tab( "ob1" )
        for button_id,expected in nationality_specific_buttons.items():
            elem = btn_elems[ button_id ]
            if isinstance( expected[0], str ):
                nat2 = expected[0]
            else:
                nat2 = expected[0][0]
                set_theater( expected[0][1] )
            if nat == nat2:
                # the button should be shown for this nationality
                assert elem.is_displayed()
                # make sure that the template works
                elem.click()
                if isinstance( expected[1], str ):
                    wait_for_clipboard( 2, expected[1] )
                elif isinstance( expected[1], types.FunctionType ):
                    expected[1]() #pylint: disable=not-callable
                else:
                    assert False
            else:
                # it should be hidden for all other nationalities
                assert not elem.is_displayed()
