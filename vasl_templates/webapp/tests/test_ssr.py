""" Test generating SSR snippets. """

import html

from vasl_templates.webapp.tests.utils import \
    init_webapp, select_tab, find_child, get_clipboard, adjust_html, \
    add_simple_note, edit_simple_note, drag_sortable_entry_to_trash, get_sortable_entry_count

# ---------------------------------------------------------------------

def test_ssr( webapp, webdriver ):
    """Test generating SSR snippets."""

    # initialize
    init_webapp( webapp, webdriver )
    select_tab( "scenario" )
    sortable = find_child( "#ssr-sortable" )

    # initialize
    expected = []
    generate_snippet_btn = find_child( "button[data-id='ssr']" )
    def add_ssr( val ):
        """Add a new SSR."""
        expected.append( val )
        add_simple_note( sortable, val, None )
        check_snippet()
    def edit_ssr( ssr_no, val ):
        """Edit an existing SSR."""
        expected[ssr_no] = val
        edit_simple_note( sortable, ssr_no, val, None )
        check_snippet()
    def check_snippet( width=None ):
        """Check the generated SSR snippet."""
        generate_snippet_btn.click()
        val = "\n".join( "(*) [{}]".format(e) for e in expected )
        if width:
            val += "\nwidth = [{}]".format( width )
        assert html.unescape( adjust_html( get_clipboard() ) ) == val

    # add an SSR and generate the SSR snippet
    add_ssr( "This is my first SSR." )

    # add an SSR that contains HTML
    add_ssr( "This snippet contains <b>bold</b> and <i>italic</i> text." )

    # add a multi-line SSR
    add_ssr( "line 1\nline 2\nline 3" )

    # edit one of the SSR's
    edit_ssr( 1, "This SSR was <i>modified</i>." )

    # delete one of the SSR's
    assert get_sortable_entry_count(sortable) == 3
    drag_sortable_entry_to_trash( sortable, 1 )
    assert get_sortable_entry_count(sortable) == 2
    del expected[1]
    check_snippet()

    # set the snippet width
    elem = find_child( "input[name='SSR_WIDTH']" )
    elem.send_keys( "300px" )
    check_snippet( "300px" )
