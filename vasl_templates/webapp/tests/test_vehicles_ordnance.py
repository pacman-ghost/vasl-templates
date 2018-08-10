""" Test generating vehicle/ordnance snippets. """

import re

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.action_chains import ActionChains

from vasl_templates.webapp.tests.utils import \
    select_tab, set_template_params, find_child, find_children, \
    get_clipboard, click_dialog_button, dismiss_notifications

# ---------------------------------------------------------------------

def test_crud( webapp, webdriver ):
    """Test basic create/read/update/delete of vehicles/ordnance."""

    # initialize
    webdriver.get( webapp.url_for( "main" ) )

    # initialize
    _expected = {
        ("vehicles",1): [], ("ordnance",1): [],
        ("vehicles",2): [], ("ordnance",2): []
    }
    _width = {
        ("vehicles",1): None, ("ordnance",1): None,
        ("vehicles",2): None, ("ordnance",2): None
    }

    def _add_vo( vo_type, player_id, name ):
        """Add a vehicle/ordnance."""
        # check the hint
        select_tab( "ob{}".format( player_id ) )
        _check_hint( vo_type, player_id )
        # add the vehicle/ordnance
        add_vo( vo_type, player_id, name )
        _expected[ (vo_type,player_id) ].append( name )
        # check the snippet and hint
        _check_snippet( vo_type, player_id )
        _check_hint( vo_type, player_id )

    def _delete_vo( vo_type, player_id, name, webdriver ):
        """Delete a vehicle/ordnance."""
        # check the hint
        select_tab( "ob{}".format( player_id ) )
        _check_hint( vo_type, player_id )
        # delete the vehicle/ordnance
        delete_vo( vo_type, player_id, name, webdriver )
        _expected[ (vo_type,player_id) ].remove( name )
        # check the snippet and hint
        _check_snippet( vo_type, player_id )
        _check_hint( vo_type, player_id )

    def _set_width( vo_type, player_id, width ):
        """Set the snippet width."""
        select_tab( "ob{}".format( player_id ) )
        elem = find_child( "input[name='{}_WIDTH_{}']".format( vo_type.upper(), player_id ) )
        elem.clear()
        if width is not None:
            elem.send_keys( str(width) )
        _width[ (vo_type,player_id) ] = width

    def _check_snippet( vo_type, player_id ):
        """Check the generated vehicle/ordnance snippet."""
        # check the snippet
        select_tab( "ob{}".format( player_id ) )
        dismiss_notifications()
        btn = find_child( "input[type='button'][data-id='{}_{}']".format( vo_type, player_id ) )
        btn.click()
        buf = get_clipboard()
        names = [
            mo.group(1)
            for mo in re.finditer( r"^\[\*\] (.*):" , buf, re.MULTILINE )
        ]
        assert names == _expected[ (vo_type,player_id) ]
        # check the snippet width
        expected = _width[ (vo_type,player_id) ]
        mo = re.search(
            r"width={}$".format( expected if expected else "" ),
            buf,
            re.MULTILINE
        )
        assert mo

    def _check_hint( vo_type, player_id ):
        """Check the hint visibility."""
        hint = find_child( "#{}-hint_{}".format( vo_type, player_id ) )
        expected = "none" if _expected[(vo_type,player_id)] else "block"
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
    webdriver.get( webapp.url_for( "main" ) )

    def do_test( vo_type ):
        """Run the test."""
        vo_type0 = vo_type[:-1] if vo_type.endswith("s") else vo_type
        # test a full example
        add_vo( vo_type, 1, "a german {}".format(vo_type) )
        dismiss_notifications()
        btn = find_child( "input[type='button'][data-id='{}_1']".format( vo_type ) )
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
        assert get_clipboard() == "\n".join(expected)
        delete_vo( vo_type, 1, "a german {}".format(vo_type0), webdriver )

        # test a partial example
        add_vo( vo_type, 1, "another german {}".format(vo_type) )
        dismiss_notifications()
        btn = find_child( "input[type='button'][data-id='{}_1']".format( vo_type ) )
        btn.click()
        expected = [
            '[German] ; width=',
            '[*] another german {}: #=2'.format( vo_type0 ),
            '- capabilities: "QSU"',
            '- raw capabilities: "QSU"'
        ]
        if vo_type == "vehicles":
            expected.insert( 2, '- cs 4 <small><i>(brew up)</i></small>' )
        assert get_clipboard() == "\n".join(expected)
        delete_vo( vo_type, 1, "another german {}".format(vo_type0), webdriver )

        # test a minimal example
        add_vo( vo_type, 1, "name only" )
        dismiss_notifications()
        btn = find_child( "input[type='button'][data-id='{}_1']".format( vo_type ) )
        btn.click()
        assert get_clipboard() == \
'''[German] ; width=
[*] name only: #='''

    # do the test
    do_test( "vehicles" )
    do_test( "ordnance" )

# ---------------------------------------------------------------------

def test_variable_capabilities( webapp, webdriver ):
    """Test date-based variable capabilities."""

    # initialize
    webdriver.get( webapp.url_for( "main" ) )

    # add a vehicle
    add_vo( "vehicles", 2, "Churchill III(b)" )

    # change the scenario date and check the generated snippet
    vehicles2 = find_child( "input.generate[data-id='vehicles_2']" )
    def do_test( month, year, expected ):
        """Set the date and check the vehicle snippet."""
        dismiss_notifications()
        select_tab( "scenario" )
        set_template_params( { "SCENARIO_DATE": "{:02d}/01/{}".format(month,year) } )
        select_tab( "ob2" )
        vehicles2.click()
        buf = get_clipboard()
        mo = re.search( r"^- capabilities: (.*)$", buf, re.MULTILINE )
        assert mo.group(1) == expected
    do_test( 1, 1940, '"sM8\u2020"' )
    do_test( 1, 1943, '"sM8\u2020"' )
    do_test( 2, 1943, '"HE7" "sM8\u2020"' )
    do_test( 12, 1943, '"HE7" "sM8\u2020"' )
    do_test( 1, 1944, '"HE8" "sD6" "sM8\u2020"' )
    do_test( 5, 1944, '"HE8" "sD6" "sM8\u2020"' )
    do_test( 6, 1944, '"D6" "HE8" "sD6" "sM8\u2020"' )
    do_test( 12, 1944, '"D6" "HE8" "sD6" "sM8\u2020"' )
    do_test( 1, 1945, '"D7" "HE8" "sD6" "sM8\u2020"' )
    do_test( 12, 1945, '"D7" "HE8" "sD6" "sM8\u2020"' )
    do_test( 1, 1946, '"D7" "HE8" "sD6" "sM8\u2020"' )

# ---------------------------------------------------------------------

def add_vo( vo_type, player_id, name ):
    """Add a vehicle/ordnance."""

    # add the vehicle/ordnance
    select_tab( "ob{}".format( player_id ) )
    elem = find_child( "#{}-add_{}".format( vo_type, player_id ) )
    elem.click()
    sel = Select( find_child( "#select-vo select" ) )
    sel.select_by_visible_text( name[:-1] if name.endswith("s") else name )
    click_dialog_button( "OK" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def delete_vo( vo_type, player_id, name, webdriver ):
    """Delete a vehicle/ordnance."""

    # delete the vehicle/ordnance
    select_tab( "ob{}".format( player_id ) )
    elems = [
        c for c in find_children( "#{}-sortable_{} li".format( vo_type, player_id ) )
        if c.text == name
    ]
    assert len(elems) == 1
    elem = elems[0]
    trash = find_child( "#{}-trash_{}".format( vo_type, player_id ) )
    ActionChains(webdriver).drag_and_drop( elem, trash ).perform()
