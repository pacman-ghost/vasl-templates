""" Test the user settings. """

import json
import re

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.tests.utils import \
    init_webapp, find_child, find_children, wait_for_clipboard, \
    select_tab, select_menu_option, set_player, click_dialog_button, add_simple_note
from vasl_templates.webapp.tests.test_vehicles_ordnance import add_vo
from vasl_templates.webapp.tests.test_scenario_persistence import save_scenario, load_scenario
from vasl_templates.webapp.tests.test_template_packs import upload_template_pack_file
from vasl_templates.webapp.tests.test_vo_notes import extract_ma_notes

# ---------------------------------------------------------------------

def test_include_vasl_images_in_snippets( webapp, webdriver ):
    """Test including VASL counter images in snippets."""

    # initialize
    init_webapp( webapp, webdriver,
        reset = lambda ct: ct.set_data_dir( dtype="real" )
    )

    # add a vehicle
    set_player( 1, "german" )
    add_vo( webdriver, "vehicles", 1, "PzKpfw IB (Tt)" )

    # enable "show VASL images in snippets"
    select_menu_option( "user_settings" )
    elem = find_child( ".ui-dialog.user-settings input[name='include-vasl-images-in-snippets']" )
    assert not elem.is_selected()
    elem.click()
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "include-vasl-images-in-snippets", True )

    # make sure that it took effect
    snippet_btn = find_child( "button[data-id='ob_vehicles_1']" )
    snippet_btn.click()
    wait_for_clipboard( 2, "/counter/2524/front", contains=True )

    # disable "show VASL images in snippets"
    select_menu_option( "user_settings" )
    elem = find_child( ".ui-dialog.user-settings input[name='include-vasl-images-in-snippets']" )
    assert elem.is_selected()
    elem.click()
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "include-vasl-images-in-snippets", False )

    # make sure that it took effect
    snippet_btn.click()
    wait_for_clipboard( 2, "/counter/2524/front", contains=False )

# ---------------------------------------------------------------------

def test_include_flags_in_snippets( webapp, webdriver ):
    """Test including flags in snippets."""

    # initialize
    init_webapp( webapp, webdriver,
        reset = lambda ct: ct.set_data_dir( dtype="real" )
    )

    # prepare the scenario
    set_player( 1, "german" )
    select_tab( "ob1" )
    sortable = find_child( "#ob_setups-sortable_1" )
    add_simple_note( sortable, "OB setup note", None )

    # enable "show flags in snippets"
    select_menu_option( "user_settings" )
    elem = find_child( ".ui-dialog.user-settings input[name='include-flags-in-snippets']" )
    assert not elem.is_selected()
    elem.click()
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "include-flags-in-snippets", True )

    # make sure that it took effect
    ob_setup_snippet_btn = find_child( "li img.snippet", sortable )
    ob_setup_snippet_btn.click()
    wait_for_clipboard( 2, "/flags/german", contains=True )

    # make sure it also affects vehicle/ordnance snippets
    ob_vehicles_snippet_btn = find_child( "button.generate[data-id='ob_vehicles_1']" )
    ob_vehicles_snippet_btn.click()
    wait_for_clipboard( 2, "/flags/german", contains=True )
    ob_ordnance_snippet_btn = find_child( "button.generate[data-id='ob_ordnance_1']" )
    ob_ordnance_snippet_btn.click()
    wait_for_clipboard( 2, "/flags/german", contains=True )

    # disable "show flags in snippets"
    select_menu_option( "user_settings" )
    elem = find_child( ".ui-dialog.user-settings input[name='include-flags-in-snippets']" )
    assert elem.is_selected()
    elem.click()
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "include-flags-in-snippets", False )

    # make sure that it took effect
    ob_setup_snippet_btn.click()
    wait_for_clipboard( 2, "/flags/german", contains=False )

    # make sure it also affects vehicle/ordnance snippets
    ob_vehicles_snippet_btn.click()
    wait_for_clipboard( 2, "/flags/german", contains=False )
    ob_ordnance_snippet_btn.click()
    wait_for_clipboard( 2, "/flags/german", contains=False )

# ---------------------------------------------------------------------

def test_date_format( webapp, webdriver ):
    """Test changing the date format."""

    # initialize
    init_webapp( webapp, webdriver, template_pack_persistence=1, scenario_persistence=1 )

    # customize the SCENARIO template
    upload_template_pack_file( "scenario.j2",
        "{{SCENARIO_YEAR}}-{{SCENARIO_MONTH}}-{{SCENARIO_DAY_OF_MONTH}}",
        False
    )

    scenario_date = find_child( "input[name='SCENARIO_DATE']" )
    snippet_btn = find_child( "button.generate[data-id='scenario']" )
    def set_scenario_date( date_string ):
        """Set the scenario date."""
        scenario_date.clear()
        scenario_date.send_keys( date_string )
        scenario_date.send_keys( Keys.TAB )
        assert scenario_date.get_attribute( "value" ) == date_string
    def check_scenario_date( expected ):
        """Check the scenario date is being interpreted correctly."""
        assert isinstance(expected,tuple) and len(expected) == 3
        assert 1 <= expected[0] <= 31 and 1 <= expected[1] <= 12 and 1940 <= expected[2] <= 1945
        # check the snippet
        snippet_btn.click()
        wait_for_clipboard( 2, "{}-{}-{}".format( expected[2], expected[0], expected[1] ) )
        # check the save file (should always be ISO-8601 format)
        saved_scenario = save_scenario()
        assert saved_scenario["SCENARIO_DATE"] == "{:04}-{:02}-{:02}".format( expected[2], expected[0], expected[1] )

    # check the default format (MM/DD/YYYY)
    set_scenario_date( "01/02/1940" )
    check_scenario_date( (1,2,1940) )
    saved_scenario = save_scenario()

    # change the date format to YYYY-MM-DD
    select_menu_option( "user_settings" )
    date_format_sel = Select( find_child( ".ui-dialog.user-settings select[name='date-format']" ) )
    date_format_sel.select_by_visible_text( "YYYY-MM-DD" )
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "date-format", "yy-mm-dd" )

    # make sure that it took effect
    assert scenario_date.get_attribute( "value" ) == "1940-01-02"
    check_scenario_date( (1,2,1940) )

    # clear the scenario date, set the date format to DD-MM-YYY
    set_scenario_date( "" )
    select_menu_option( "user_settings" )
    date_format_sel.select_by_visible_text( "DD/MM/YYYY" )
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "date-format", "dd/mm/yy" )

    # set the scenario date
    set_scenario_date( "03/04/1945" ) # nb: this will be interpreted as DD/MM/YYYY
    check_scenario_date( (4,3,1945) )

    # load the scenario we saved before and check the date
    load_scenario( saved_scenario )
    check_scenario_date( (1,2,1940) )
    assert scenario_date.get_attribute( "value" ) == "02/01/1940"

    # restore the date format back to default (for the rest of the tests :-/)
    select_menu_option( "user_settings" )
    date_format_sel.select_by_visible_text( "MM/DD/YYYY" )
    click_dialog_button( "OK" )

# ---------------------------------------------------------------------

def test_hide_unavailable_ma_notes( webapp, webdriver ):
    """Test showing/hiding unavailable multi-applicable notes."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct: ct.set_vo_notes_dir( dtype="test" )
    )

    # load the test vehicle
    load_scenario( {
        "PLAYER_1": "german",
        "OB_VEHICLES_1": [
            { "name": "missing multi-applicable note" }
        ]
    } )
    select_tab( "ob1" )

    def test_ma_notes( ma_note_q_present ): #pylint: disable=missing-docstring
        expected = [ ( "A", 'German Multi-Applicable Vehicle Note "A".' ) ]
        if ma_note_q_present:
            expected.append( ( "Q", "Unavailable." ) )
        btn = find_child( "button[data-id='ob_vehicles_ma_notes_1']" )
        btn.click()
        wait_for_clipboard( 2, expected, transform=extract_ma_notes )

    # generate the multi-applicable notes
    test_ma_notes( True )

    # enable "hide unavailable multi-applicable notes"
    select_menu_option( "user_settings" )
    elem = find_child( ".ui-dialog.user-settings input[name='hide-unavailable-ma-notes']" )
    assert not elem.is_selected()
    elem.click()
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "hide-unavailable-ma-notes", True )

    # generate the multi-applicable notes
    test_ma_notes( False )

    # disable "hide unavailable multi-applicable notes"
    select_menu_option( "user_settings" )
    elem = find_child( ".ui-dialog.user-settings input[name='hide-unavailable-ma-notes']" )
    assert elem.is_selected()
    elem.click()
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "hide-unavailable-ma-notes", False )

    # generate the multi-applicable notes
    test_ma_notes( True )

# ---------------------------------------------------------------------

def test_vo_notes_as_images( webapp, webdriver ):
    """Test showing vehicle/ordnance notes as HTML/images."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct: ct.set_vo_notes_dir( dtype="test" )
    )

    # load the test vehicle
    load_scenario( {
        "PLAYER_1": "greek",
        "OB_VEHICLES_1": [ { "name": "HTML note" } ],
    } )
    select_tab( "ob1" )

    def check_snippet( expected ):
        """Generate and check the vehicle note snippet."""
        sortable = find_child( "#ob_vehicles-sortable_1" )
        elems = find_children( "li", sortable )
        assert len(elems) == 1
        btn = find_child( "img.snippet", elems[0] )
        btn.click()
        contains = True if isinstance( expected, str ) else None
        wait_for_clipboard( 2, expected, contains=contains )

    # generate the vehicle snippet (should get the raw HTML)
    check_snippet( "This is an HTML vehicle note (202)." )

    # enable "show vehicle/ordnance notes as images"
    select_menu_option( "user_settings" )
    elem = find_child( ".ui-dialog.user-settings input[name='vo-notes-as-images']" )
    assert not elem.is_selected()
    elem.click()
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "vo-notes-as-images", True )

    # generate the vehicle snippet (should get a link to return an image)
    check_snippet( re.compile( r"http://.+?:\d+/vehicles/greek/note/202" ) )

    # disable "show vehicle/ordnance notes as images"
    select_menu_option( "user_settings" )
    elem = find_child( ".ui-dialog.user-settings input[name='vo-notes-as-images']" )
    assert elem.is_selected()
    elem.click()
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "vo-notes-as-images", False )

    # generate the vehicle snippet (should get the raw HTML)
    check_snippet( "This is an HTML vehicle note (202)." )

# ---------------------------------------------------------------------

def set_user_settings( opts ):
    """Configure the user settings."""
    select_menu_option( "user_settings" )
    for key,val in opts.items():
        assert isinstance( val, bool ) # nb: we currently only support checkboxes
        elem = find_child( ".ui-dialog.user-settings input[name='{}']".format( key ) )
        if (val and not elem.is_selected()) or (not val and elem.is_selected()):
            elem.click()
    click_dialog_button( "OK" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _check_cookies( webdriver, name, expected ):
    """Check that a user setting was stored in the cookies correctly."""
    cookies = [ c for c in webdriver.get_cookies() if c["name"] == "user-settings" ]
    assert len(cookies) == 1
    val = cookies[0]["value"].replace( "%22", '"' ).replace( "%2C", "," )
    user_settings = json.loads( val )
    assert user_settings[name] == expected
