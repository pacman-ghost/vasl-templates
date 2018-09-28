""" Test generating vehicle/ordnance snippets. """

import re

from selenium.webdriver.common.action_chains import ActionChains

from vasl_templates.webapp.tests.utils import \
    init_webapp, select_tab, set_template_params, find_child, find_children, \
    wait_for_clipboard, click_dialog_button

# ---------------------------------------------------------------------

def test_crud( webapp, webdriver ):
    """Test basic create/read/update/delete of vehicles/ordnance."""

    # initialize
    init_webapp( webapp, webdriver )

    # initialize
    _expected = {
        ("vehicles",1): [], ("ordnance",1): [],
        ("vehicles",2): [], ("ordnance",2): []
    }
    _width = {
        ("vehicles",1): None, ("ordnance",1): None,
        ("vehicles",2): None, ("ordnance",2): None
    }

    def _add_vo( vo_type, player_no, name ):
        """Add a vehicle/ordnance."""
        # check the hint
        select_tab( "ob{}".format( player_no ) )
        _check_hint( vo_type, player_no )
        # add the vehicle/ordnance
        add_vo( webdriver, vo_type, player_no, name )
        _expected[ (vo_type,player_no) ].append( name )
        # check the snippet and hint
        _check_snippet( vo_type, player_no )
        _check_hint( vo_type, player_no )

    def _delete_vo( vo_type, player_no, name, webdriver ):
        """Delete a vehicle/ordnance."""
        # check the hint
        select_tab( "ob{}".format( player_no ) )
        _check_hint( vo_type, player_no )
        # delete the vehicle/ordnance
        delete_vo( vo_type, player_no, name, webdriver )
        _expected[ (vo_type,player_no) ].remove( name )
        # check the snippet and hint
        _check_snippet( vo_type, player_no )
        _check_hint( vo_type, player_no )

    def _set_width( vo_type, player_no, width ):
        """Set the snippet width."""
        select_tab( "ob{}".format( player_no ) )
        elem = find_child( "input[name='OB_{}_WIDTH_{}']".format( vo_type.upper(), player_no ) )
        elem.clear()
        if width is not None:
            elem.send_keys( str(width) )
        _width[ (vo_type,player_no) ] = width

    def _check_snippet( vo_type, player_no ):
        """Check the generated vehicle/ordnance snippet."""
        # check the snippet
        select_tab( "ob{}".format( player_no ) )
        btn = find_child( "button[data-id='ob_{}_{}']".format( vo_type, player_no ) )
        btn.click()
        def reformat( clipboard ): #pylint: disable=missing-docstring
            return [
                mo.group(1)
                for mo in re.finditer( r"^\[\*\] (.*):" , clipboard, re.MULTILINE )
            ]
        clipboard = wait_for_clipboard( 2, _expected[(vo_type,player_no)], transform=reformat )
        # check the snippet width
        expected = _width[ (vo_type,player_no) ]
        mo = re.search(
            r"width={}$".format( expected if expected else "" ),
            clipboard,
            re.MULTILINE
        )
        assert mo

    def _check_hint( vo_type, player_no ):
        """Check the hint visibility."""
        hint = find_child( "#ob_{}-hint_{}".format( vo_type, player_no ) )
        expected = "none" if _expected[(vo_type,player_no)] else "block"
        assert hint.value_of_css_property("display") == expected

    def do_test( vo_type ):
        """Run the test."""
        vo_type0 = vo_type[:-1] if vo_type.endswith("s") else vo_type
        # add a German vehicle/ordnance
        _add_vo( vo_type, 1, "a german {}".format(vo_type0) )
        # generate a Russian vehicle/ordnance snippet
        _check_snippet( vo_type, 2 )
        # add a Russian vehicle/ordnance
        _add_vo( vo_type, 2, "another russian {}".format(vo_type0) )
        # go back and check the German snippet again
        _check_snippet( vo_type, 1 )
        # add another Russian vehicle/ordnance
        _set_width( vo_type, 2, "200px" )
        _add_vo( vo_type, 2, "name only" )
        # delete the German vehicle/ordnance
        _set_width( vo_type, 1, "100px" )
        _delete_vo( vo_type, 1, "a german {}".format(vo_type0), webdriver )
        _set_width( vo_type, 1, None )
        _check_snippet( vo_type, 1 )
        # go back and check the Russian snippet again
        _check_snippet( vo_type, 2 )
        # delete the Russian vehicles/ordnance
        _delete_vo( vo_type, 2, "another russian {}".format(vo_type0), webdriver )
        _set_width( vo_type, 2, None )
        _delete_vo( vo_type, 2, "name only", webdriver )
        # check the final state
        assert not _expected[ (vo_type,1) ]
        assert not _expected[ (vo_type,2) ]

    # do the test
    do_test( "vehicles" )
    do_test( "ordnance" )

# ---------------------------------------------------------------------

def test_snippets( webapp, webdriver ):
    """Test vehicle/ordnance snippet generation in detail."""

    # initialize
    init_webapp( webapp, webdriver )

    def do_test( vo_type ):
        """Run the test."""
        vo_type0 = vo_type[:-1] if vo_type.endswith("s") else vo_type
        # test a full example
        add_vo( webdriver, vo_type, 1, "a german {}".format(vo_type) )
        btn = find_child( "button[data-id='ob_{}_1']".format( vo_type ) )
        btn.click()
        expected = [
            '[German] ; width=',
            '[*] a german {}: #=1'.format( vo_type0 ),
            '- notes: "A" "B†"',
            '- capabilities: "QSU" "IR" "A1" "H2" "can do other stuff"',
            '- raw capabilities: "QSU" "IR" "A1" "H2" "can do other stuff"'
        ]
        if vo_type == "vehicles":
            expected.insert( 3, "- CS 5" )
        wait_for_clipboard( 2, "\n".join(expected) )
        delete_vo( vo_type, 1, "a german {}".format(vo_type0), webdriver )

        # test a partial example
        add_vo( webdriver, vo_type, 1, "another german {}".format(vo_type) )
        btn = find_child( "button[data-id='ob_{}_1']".format( vo_type ) )
        btn.click()
        expected = [
            '[German] ; width=',
            '[*] another german {}: #=2'.format( vo_type0 ),
            '- capabilities: "QSU"',
            '- raw capabilities: "QSU"'
        ]
        if vo_type == "vehicles":
            expected.insert( 2, '- cs 4 <small><i>(brew up)</i></small>' )
        wait_for_clipboard( 2, "\n".join(expected) )
        delete_vo( vo_type, 1, "another german {}".format(vo_type0), webdriver )

        # test a minimal example
        add_vo( webdriver, vo_type, 1, "name only" )
        btn = find_child( "button[data-id='ob_{}_1']".format( vo_type ) )
        btn.click()
        wait_for_clipboard( 2, \
'''[German] ; width=
[*] name only: #='''
        )

    # do the test
    do_test( "vehicles" )
    do_test( "ordnance" )

# ---------------------------------------------------------------------

def test_variable_capabilities( webapp, webdriver ):
    """Test date-based variable capabilities."""

    # initialize
    init_webapp( webapp, webdriver )

    # add a vehicle
    add_vo( webdriver, "vehicles", 2, "Churchill III(b)" )

    # change the scenario date and check the generated snippet
    vehicles2 = find_child( "button.generate[data-id='ob_vehicles_2']" )
    def do_test( month, year, expected ):
        """Set the date and check the vehicle snippet."""
        select_tab( "scenario" )
        set_template_params( { "SCENARIO_DATE": "{:02d}/01/{}".format(month,year) } )
        select_tab( "ob2" )
        vehicles2.click()
        def reformat( clipboard ): #pylint: disable=missing-docstring
            mo = re.search( r"^- capabilities: (.*)$", clipboard, re.MULTILINE )
            return mo.group( 1 )
        wait_for_clipboard( 2, expected, transform=reformat )
    do_test( 1, 1940, '"sM8\u2020"' )
    do_test( 1, 1943, '"sM8\u2020"' )
    do_test( 2, 1943, '"HE7\u2020" "sM8\u2020"' )
    do_test( 12, 1943, '"HE7\u2020" "sM8\u2020"' )
    do_test( 1, 1944, '"HE8\u2020" "sD6" "sM8\u2020"' )
    do_test( 5, 1944, '"HE8\u2020" "sD6" "sM8\u2020"' )
    do_test( 6, 1944, '"D6\u2020" "HE8\u2020" "sD6" "sM8\u2020"' )
    do_test( 12, 1944, '"D6\u2020" "HE8\u2020" "sD6" "sM8\u2020"' )
    do_test( 1, 1945, '"D7\u2020" "HE8\u2020" "sD6" "sM8\u2020"' )
    do_test( 12, 1945, '"D7\u2020" "HE8\u2020" "sD6" "sM8\u2020"' )
    do_test( 1, 1946, '"D7\u2020" "HE8\u2020" "sD6" "sM8\u2020"' )

# ---------------------------------------------------------------------

def add_vo( webdriver, vo_type, player_no, name ):
    """Add a vehicle/ordnance."""

    # add the vehicle/ordnance
    select_tab( "ob{}".format( player_no ) )
    elem = find_child( "#ob_{}-add_{}".format( vo_type, player_no ) )
    elem.click()
    entries = find_children( "#select-vo .select2-results li" )
    if name.endswith( "s" ):
        name = name[:-1]
    matches = [ e for e in entries if e.text == name ]
    assert len(matches) == 1
    elem = matches[0]
    webdriver.execute_script( "arguments[0].scrollIntoView()", elem )
    ActionChains( webdriver ).click( elem ).perform()
    if find_child( "#select-vo" ).is_displayed():
        # FUDGE! Clicking on the element sometimes make the dialog close :-/
        click_dialog_button( "OK" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def delete_vo( vo_type, player_no, name, webdriver ):
    """Delete a vehicle/ordnance."""

    # delete the vehicle/ordnance
    select_tab( "ob{}".format( player_no ) )
    elems = [
        c for c in find_children( "#ob_{}-sortable_{} li".format( vo_type, player_no ) )
        if c.text == name
    ]
    assert len(elems) == 1
    elem = elems[0]
    trash = find_child( "#ob_{}-trash_{}".format( vo_type, player_no ) )
    ActionChains(webdriver).drag_and_drop( elem, trash ).perform()
