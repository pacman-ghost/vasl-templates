""" Test generating OB SETUP snippets. """

import types

from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.tests.utils import select_tab, get_nationalities, get_clipboard, get_stored_msg, find_child

# ---------------------------------------------------------------------

def test_ob_setup( webapp, webdriver ):
    """Test generating OB SETUP snippets."""

    # initialize
    webdriver.get( webapp.url_for( "main" ) )

    # generate OB SETUP snippets for both players
    select_tab( "ob1" )
    textarea1 = find_child( "textarea[name='OB_SETUP_1']" )
    textarea1.clear()
    textarea1.send_keys( "setup <i>here</i>." )
    btn1 = find_child( "input[type='button'][data-id='ob_setup_1']" )
    select_tab( "ob2" )
    textarea2 = find_child( "textarea[name='OB_SETUP_2']" )
    textarea2.clear()
    textarea2.send_keys( "setup <b>there</b>." )
    btn2 = find_child( "input[type='button'][data-id='ob_setup_2']" )
    btn2.click()
    assert get_clipboard() == "[setup <b>there</b>.] (col=[OBCOL:russian/OBCOL2:russian])"
    select_tab( "ob1" )
    btn1.click()
    assert get_clipboard() == "[setup <i>here</i>.] (col=[OBCOL:german/OBCOL2:german])"

    # change the player nationalities and generate the OB SETUP snippets again
    select_tab( "scenario" )
    sel = Select(
        find_child( "select[name='PLAYER_1']" )
    )
    sel.select_by_value( "british" )
    sel = Select(
        find_child( "select[name='PLAYER_2']" )
    )
    sel.select_by_value( "french" )
    select_tab( "ob1" )
    btn1.click()
    assert get_clipboard() == "[setup <i>here</i>.] (col=[OBCOL:british/OBCOL2:british])"
    select_tab( "ob2" )
    btn2.click()
    assert get_clipboard() == "[setup <b>there</b>.] (col=[OBCOL:french/OBCOL2:french])"

    # set the snippet widths and generate the snippets again
    select_tab( "ob1" )
    elem = find_child( "input[name='OB_SETUP_WIDTH_1']" )
    elem.send_keys( "100px" )
    btn1.click()
    assert get_clipboard() == "[setup <i>here</i>.] (col=[OBCOL:british/OBCOL2:british]) (width=[100px])"
    select_tab( "ob2" )
    elem = find_child( "input[name='OB_SETUP_WIDTH_2']" )
    elem.send_keys( "200px" )
    btn2.click()
    assert get_clipboard() == "[setup <b>there</b>.] (col=[OBCOL:french/OBCOL2:french]) (width=[200px])"

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
        do_test( (1942,1), "PF: range=[1] ; check=[4] (drm=[+1])", True )
        do_test( (1943,9), "PF: range=[1] ; check=[4] (drm=[+1])", True )
        do_test( (1943,10), "PF: range=[1] ; check=[3]", False )
        do_test( (1944,5), "PF: range=[1] ; check=[3]", False )
        do_test( (1944,6), "PF: range=[2] ; check=[3]", False )
        do_test( (1944,12), "PF: range=[2] ; check=[3]", False )
        do_test( (1945,1), "PF: range=[3] ; check=[4] (drm=[-1])", False )
        do_test( (1946,1), "PF: range=[3] ; check=[4] (drm=[-1])", False )

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
        do_test( (1942,11), "BAZ: '43 ; range=[4] ; X#=[10] ; TK#=[13]" )
        do_test( (1943,1), "BAZ: '43 ; range=[4] ; X#=[10] ; TK#=[13]" )
        do_test( (1944,1), "BAZ: '44 ; range=[4] ; X#=[11] ; TK#=[16]" )
        do_test( (1945,1), "BAZ: '45 ; range=[5] ; X#=[11] ; TK#=[16] ; WP#=[6]" )
        do_test( (1946,1), "BAZ: '45 ; range=[5] ; X#=[11] ; TK#=[16] ; WP#=[6]" )

    # initialize
    nationality_specific_buttons = {
        "mol": [ "russian", "Burn, baby, burn!" ],
        "mol-p": [ "russian", "mol-p template" ],
        "pf": [ "german", check_pf_snippets ],
        "psk": [ "german", "====> whoosh!" ],
        "atmm": [ "german", "Kaboom!!!" ],
        "baz": [ "american", check_baz_snippets ],
        "piat": [ "british", "piat template" ],
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
