""" Test the extras templates. """

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.tests.utils import init_webapp, select_tab, \
    set_template_params, get_droplist_vals, select_droplist_val, \
    find_child, find_children, wait_for, wait_for_clipboard
from vasl_templates.webapp.tests.test_template_packs import make_zip_from_files, upload_template_pack_zip

# ---------------------------------------------------------------------

def test_extras_templates( webapp, webdriver ):
    """Test the extras templates."""

    # initialize
    init_webapp( webapp, webdriver )
    select_tab( "extras" )

    # check that the extras templates were loaded correctly
    assert _get_extras_template_index() == [
        ( "extras/minimal", None ),
        ( "Full template", "This is the caption." ),
        ( "select", None ),
    ]

    # check that the "full" template was loaded correctly
    _select_extras_template( webdriver, "extras/full" )
    content = find_child( "#tabs-extras .right-panel" )
    assert find_child( "div.name", content ).text == "Full template"
    assert find_child( "div.caption", content ).text == "This is the caption."
    assert find_child( "div.description", content ).text == "This is the description."
    params = find_children( "tr", content )
    assert len(params) == 1
    assert find_child( "td.caption", params[0] ).text == "The parameter:"
    textbox = find_child( "td.value input", params[0] )
    assert textbox.get_attribute( "value" ) == "default-val"
    assert textbox.get_attribute( "size" ) == "10"
    assert textbox.get_attribute( "title" ) == "This is the parameter description."

    # generate the snippet
    snippet_btn = find_child( "button.generate", content )
    snippet_btn.click()
    clipboard = wait_for_clipboard( 2, "param = default-val", contains=True )
    assert "vasl-templates:comment" not in clipboard # nb: check that the comment was removed

    # check that the "minimal" template was loaded correctly
    _select_extras_template( webdriver, "extras/minimal" )
    assert find_child( "div.name", content ).text == "extras/minimal"
    assert find_child( "div.caption", content ) is None
    assert find_child( "div.description", content ) is None
    params = find_children( "tr", content )
    assert len(params) == 1
    assert find_child( "td.caption", params[0] ).text == "PARAM:"
    textbox = find_child( "td.value input", params[0] )
    assert textbox.get_attribute( "value" ) == ""

    # generate the snippet
    textbox.send_keys( "boo!" )
    snippet_btn = find_child( "button.generate", content )
    snippet_btn.click()
    clipboard = wait_for_clipboard( 2, "param = boo!", contains=True )

# ---------------------------------------------------------------------

def test_droplists( webapp, webdriver ):
    """Test droplist's in  extras templates."""

    # initialize
    init_webapp( webapp, webdriver )
    select_tab( "extras" )

    # load the "droplist" template
    _select_extras_template( webdriver, "extras/droplist" )
    content = find_child( "#tabs-extras .right-panel" )
    params = find_children( "tr", content )
    assert len(params) == 1
    sel = Select( find_child( "td.value select", params[0] ) )
    vals = get_droplist_vals( sel )
    assert vals == [ ("item 1","item 1"), ("item 2","item 2"), ("item 3","item 3") ]

    # generate the snippet for each droplist choice
    for i in range(1,3+1):
        select_droplist_val( sel, "item {}".format(i) )
        snippet_btn = find_child( "button.generate", content )
        snippet_btn.click()
        wait_for_clipboard( 2, "Selected: item {}".format(i) )

# ---------------------------------------------------------------------

def test_template_pack( webapp, webdriver ):
    """Test uploading a template pack that contains extras templates."""

    # initialize
    init_webapp( webapp, webdriver, template_pack_persistence=1 )
    select_tab( "extras" )

    # check that the extras templates were loaded correctly
    assert _get_extras_template_index() == [
        ( "extras/minimal", None ),
        ( "Full template", "This is the caption." ),
        ( "select", None ),
    ]

    # upload the template pack
    zip_data = make_zip_from_files( "extras" )
    upload_template_pack_zip( zip_data, False )

    # check that the templates were updated correctly
    assert _get_extras_template_index() == [
        ( "extras/minimal", None ),
        ( "Full template (modified)", "This is the caption (modified)." ),
        ( "New template", None ),
        ( "select", None ),
    ]

    # check that the modified "full" template is being used
    _select_extras_template( webdriver, "extras/full" )
    content = find_child( "#tabs-extras .right-panel" )
    assert find_child( "div.name", content ).text == "Full template (modified)"
    assert find_child( "div.caption", content ).text == "This is the caption (modified)."
    params = find_children( "tr", content )
    assert len(params) == 2
    assert find_child( "td.caption", params[0] ).text == "The modified parameter:"
    textbox = find_child( "td.value input", params[0] )
    assert textbox.get_attribute( "value" ) == "modified-default-val"
    assert textbox.get_attribute( "size" ) == "10"
    assert textbox.get_attribute( "title" ) == "This is the modified parameter description."
    assert find_child( "td.caption", params[1] ).text == "NEW-PARAM:"
    textbox = find_child( "td.value input", params[1] )

# ---------------------------------------------------------------------

def test_edit_extras_template( webapp, webdriver ):
    """Test editing an extras templates."""

    # initialize
    init_webapp( webapp, webdriver )
    select_tab( "extras" )

    # edit the "minimal" template
    _select_extras_template( webdriver, "extras/minimal" )
    content = find_child( "#tabs-extras .right-panel" )
    assert find_child( "div.caption", content ) is None
    webdriver.execute_script( "edit_template('extras/minimal')", content )
    textarea = find_child( "#edit-template textarea" )
    template = textarea.get_attribute( "value" ) \
        .replace( "<html>", "<html>\n<!-- vasl-templates:caption Modified minimal. -->" ) \
        .replace( "<div>", "<div>\nadded = {{ADDED:added-val}}" )
    textarea.clear()
    textarea.send_keys( template )
    textarea.send_keys( Keys.ESCAPE )

    # generate the template (we should still be using the old template)
    snippet_btn = find_child( "button.generate", content )
    snippet_btn.click()
    wait_for_clipboard( 2, "param =", contains=True )

    # switch to another template, then back again
    _select_extras_template( webdriver, "extras/full" )
    _select_extras_template( webdriver, "extras/minimal" )

    # make sure the new template was loaded
    assert find_child( "div.caption", content ).text == "Modified minimal."
    params = find_children( "tr", content )
    assert len(params) == 2
    assert find_child( "td.caption", params[0] ).text == "ADDED:"
    textbox = find_child( "td.value input", params[0] )
    assert textbox.get_attribute( "value" ) == "added-val"

    # generate the template (we should be using the new template)
    snippet_btn = find_child( "button.generate", content )
    snippet_btn.click()
    wait_for_clipboard( 2, "added = added-val\nparam =", contains=True )

# ---------------------------------------------------------------------

def test_count_remaining_hilites( webapp, webdriver ):
    """Test highlighting in the "count remaining" extras template."""

    # initialize
    init_webapp( webapp, webdriver,
        reset = lambda ct: ct.set_data_dir( dtype="real" )
    )

    def do_test( year, expected ): #pylint: disable=missing-docstring

        # set the specified year
        set_template_params( {
            "SCENARIO_DATE": "01/01/{}".format( year ) if year else ""
        } )

        # select the "count remaining" template and check what's been highlighted
        select_tab( "extras" )
        _select_extras_template( webdriver, "extras/count-remaining" )
        for count_type in expected:
            table = find_child( "table.{}".format( count_type ) )
            cells = []
            for row in find_children( "tr", table ):
                row = list( find_children( "td", row ) )
                assert len(row) == 2
                bgd_col = row[1].value_of_css_property( "background-color" )
                assert bgd_col.startswith( ( "rgb(", "rgba(" ) )
                cells.append( bgd_col != "rgba(0, 0, 0, 0)" )
            assert cells == expected[count_type]

    # do the tests
    do_test( None, {
        "pf": [ False, False, False ],
        "thh": [ False, False, False, False ]
    } )
    do_test( 1940, {
        "pf": [ True, False, False ],
        "thh": [ True, False, False, False ]
    } )
    do_test( 1941, {
        "pf": [ True, False, False ],
        "thh": [ True, False, False, False ]
    } )
    do_test( 1942, {
        "pf": [ True, False, False ],
        "thh": [ True, False, False, False ]
    } )
    do_test( 1943, {
        "pf": [ True, False, False ],
        "thh": [ False, True, False, False ]
    } )
    do_test( 1944, {
        "pf": [ False, True, False ],
        "thh": [ False, False, True, False ]
    } )
    do_test( 1945, {
        "pf": [ False, False, True ],
        "thh": [ False, False, False, True ]
    } )
    do_test( 1946, {
        "pf": [ False, False, False ],
        "thh": [ False, False, False, False ]
    } )

# ---------------------------------------------------------------------

def _get_extras_template_index():
    """Get the list of extras templates from the sidebar."""
    def get_child_text( child_class, elem ): #pylint: disable=missing-docstring
        elem = find_child( child_class, elem )
        return elem.text if elem else None
    return [
        ( get_child_text(".name",elem), get_child_text(".caption",elem) )
        for elem in _get_extras_templates()
    ]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _get_extras_templates():
    """Get the available extras templates."""
    return find_children( "#tabs-extras .left-panel li" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _select_extras_template( webdriver, template_id ):
    """Select the specified extras template."""

    # find the specified template in the index
    elems = [
        e for e in _get_extras_templates()
        if webdriver.execute_script( "return $(arguments[0]).data('template_id')", e ) == template_id
    ]
    assert len(elems) == 1
    template_name = find_child( ".name", elems[0] ).text

    # select the template and wait for it to load
    elems[0].click()
    def is_template_loaded(): #pylint: disable=missing-docstring
        elem = find_child( "#tabs-extras .right-panel .name" )
        return elem and elem.text == template_name
    wait_for( 2, is_template_loaded )
