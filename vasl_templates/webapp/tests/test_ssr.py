""" Test generating SSR snippets. """

import html

from selenium.webdriver.common.action_chains import ActionChains

from vasl_templates.webapp.tests.utils import select_tab, find_child, find_children
from vasl_templates.webapp.tests.utils import get_clipboard, dismiss_notifications, click_dialog_button

# ---------------------------------------------------------------------

def test_ssr( webapp, webdriver ):
    """Test generating SSR snippets."""

    # initialize
    webdriver.get( webapp.url_for( "main" ) )
    select_tab( "scenario" )

    # initialize
    expected = []
    def _add_ssr( val ):
        expected.append( val )
        add_ssr( webdriver, val )
        check_snippet()
    def _edit_ssr( ssr_no, val ):
        expected[ssr_no] = val
        edit_ssr( webdriver, ssr_no, val )
        check_snippet()
    def check_snippet( width=None ):
        """Check the generated SSR snippet."""
        btn = find_child( "input[type='button'][data-id='ssr']" )
        btn.click()
        val = "\n".join( "(*) [{}]".format(e) for e in expected )
        if width:
            val += "\nwidth = [{}]".format( width )
        assert html.unescape( get_clipboard() ) == val
        dismiss_notifications()

    # add an SSR and generate the SSR snippet
    _add_ssr( "This is my first SSR." )

    # add an SSR that contains HTML
    _add_ssr( "This snippet contains <b>bold</b> and <i>italic</i> text." )

    # add a multi-line SSR
    _add_ssr( "line 1\nline 2\nline 3" )

    # edit one of the SSR's
    _edit_ssr( 1, "This SSR was <i>modified</i>." )

    # delete one of the SSR's
    elems = find_children( "#ssr-sortable li" )
    assert len(elems) == 3
    elem = elems[1]
    trash = find_child( "#ssr-trash" )
    ActionChains(webdriver).drag_and_drop( elem, trash ).perform()
    del expected[1]
    check_snippet()

    # set the snippet width
    elem = find_child( "input[name='SSR_WIDTH']" )
    elem.send_keys( "300px" )
    check_snippet( "300px" )

# ---------------------------------------------------------------------

def add_ssr( webdriver, val ):
    """Add a new SSR."""
    elem = find_child( "#add-ssr" )
    elem.click()
    edit_ssr( webdriver, None, val )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def edit_ssr( webdriver, ssr_no, val ):
    """Edit an SSR's content."""

    # locate the requested SSR and start editing it
    if ssr_no is not None:
        elems = find_children( "#ssr-sortable li" )
        elem = elems[ ssr_no ]
        ActionChains(webdriver).double_click( elem ).perform()

    # edit the SSR
    textarea = find_child( "#edit-ssr textarea" )
    textarea.clear()
    textarea.send_keys( val )
    click_dialog_button( "OK" )
