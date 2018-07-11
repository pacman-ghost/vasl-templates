""" Test generating SSR snippets. """

import html

from selenium.webdriver.common.action_chains import ActionChains

from vasl_templates.webapp.tests.utils import get_clipboard, find_child, find_children

# ---------------------------------------------------------------------

def test_ssr( webapp, webdriver ):
    """Test generating SSR snippets."""

    # initialize
    webdriver.get( webapp.url_for( "main" ) )

    # initialize
    expected = []
    def add_ssr( val ):
        """Add a new SSR, and check that the SSR snippet is generated correctly."""
        # add the SSR
        expected.append( val )
        elem = find_child( webdriver, "#add-ssr" )
        elem.click()
        edit_ssr( val )
    def edit_ssr( val ):
        """Edit an SSR's content, and check that the SSR snippet is generated correctly."""
        # edit the SSR content
        textarea = find_child( webdriver, "#edit-ssr textarea" )
        textarea.clear()
        textarea.send_keys( val )
        btn = next(
            elem for elem in find_children(webdriver,".ui-dialog.edit-ssr button")
            if elem.text == "OK"
        )
        btn.click()
        # check the generated snippet
        check_snippet()
    def check_snippet():
        """Check the generated SSR snippet."""
        btn = find_child( webdriver, "input[type='button'][data-id='ssr']" )
        btn.click()
        val = "\n".join( "(*) [{}]".format(e) for e in expected )
        assert html.unescape(get_clipboard()) == val

    # add an SSR and generate the SSR snippet
    add_ssr( "This is my first SSR." )

    # add an SSR that contains HTML
    add_ssr( "This snippet contains <b>bold</b> and <i>italic</i> text." )

    # add a multi-line SSR
    add_ssr( "line 1\nline 2\nline 3" )

    # edit one of the SSR's
    elems = find_children( webdriver, "#ssr-sortable li" )
    assert len(elems) == 3
    elem = elems[1]
    ActionChains(webdriver).double_click( elem ).perform()
    expected[1] = "This SSR was <i>modified</i>."
    edit_ssr( expected[1] )

    # delete one of the SSR's
    elems = find_children( webdriver, "#ssr-sortable li" )
    assert len(elems) == 3
    elem = elems[1]
    trash = find_child( webdriver, "#ssr-trash" )
    ActionChains(webdriver).drag_and_drop( elem, trash ).perform()
    del expected[1]
    check_snippet()
