""" Test the user settings. """

import json
import re

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.tests.utils import \
    init_webapp, find_child, find_children, find_snippet_buttons, wait_for_clipboard, \
    select_tab, select_menu_option, select_droplist_val, set_player, click_dialog_button, add_simple_note
from vasl_templates.webapp.tests.test_vehicles_ordnance import add_vo
from vasl_templates.webapp.tests.test_scenario_persistence import save_scenario, load_scenario
from vasl_templates.webapp.tests.test_template_packs import upload_template_pack_file
from vasl_templates.webapp.tests.test_vo_notes import extract_ma_notes

# nb: these are taken from user_settings.js
SCENARIO_IMAGES_SOURCE_THIS_PROGRAM = 1
SCENARIO_IMAGES_SOURCE_INTERNET = 2

# ---------------------------------------------------------------------

def test_include_vasl_images_in_snippets( webapp, webdriver ):
    """Test including VASL counter images in snippets."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver )
    set_user_settings( { "scenario-images-source": SCENARIO_IMAGES_SOURCE_THIS_PROGRAM } )

    # add a vehicle
    set_player( 1, "german" )
    add_vo( webdriver, "vehicles", 1, "PzKpfw IB" )

    # disable "show VASL images in snippets"
    select_menu_option( "user_settings" )
    elem = find_child( ".ui-dialog.user-settings input[name='include-vasl-images-in-snippets']" )
    assert elem.is_selected()
    elem.click()
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "include-vasl-images-in-snippets", False )

    # make sure that it took effect
    snippet_btn = find_child( "button[data-id='ob_vehicles_1']" )
    snippet_btn.click()
    wait_for_clipboard( 2, "/counter/2524/front", contains=False )

    # enable "show VASL images in snippets"
    select_menu_option( "user_settings" )
    elem = find_child( ".ui-dialog.user-settings input[name='include-vasl-images-in-snippets']" )
    assert not elem.is_selected()
    elem.click()
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "include-vasl-images-in-snippets", True )

    # make sure that it took effect
    snippet_btn.click()
    wait_for_clipboard( 2, "/counter/2524/front", contains=True )

# ---------------------------------------------------------------------

def test_include_flags_in_snippets( webapp, webdriver ):
    """Test including flags in snippets."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver )

    # prepare the scenario
    set_player( 1, "german" )
    select_tab( "ob1" )
    sortable = find_child( "#ob_setups-sortable_1" )
    add_simple_note( sortable, "OB setup note", None )

    # disable "show flags in snippets"
    select_menu_option( "user_settings" )
    elem = find_child( ".ui-dialog.user-settings input[name='include-flags-in-snippets']" )
    assert elem.is_selected()
    elem.click()
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "include-flags-in-snippets", False )

    # make sure that it took effect
    ob_setup_snippet_btn = find_child( "li img.snippet", sortable )
    ob_setup_snippet_btn.click()
    wait_for_clipboard( 2, "/flags/german", contains=False )

    # make sure it also affects vehicle/ordnance snippets
    ob_vehicles_snippet_btn = find_child( "button.generate[data-id='ob_vehicles_1']" )
    ob_vehicles_snippet_btn.click()
    wait_for_clipboard( 2, "/flags/german", contains=False )
    ob_ordnance_snippet_btn = find_child( "button.generate[data-id='ob_ordnance_1']" )
    ob_ordnance_snippet_btn.click()
    wait_for_clipboard( 2, "/flags/german", contains=False )

    # enable "show flags in snippets"
    select_menu_option( "user_settings" )
    elem = find_child( ".ui-dialog.user-settings input[name='include-flags-in-snippets']" )
    assert not elem.is_selected()
    elem.click()
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "include-flags-in-snippets", True )

    # make sure that it took effect
    ob_setup_snippet_btn.click()
    wait_for_clipboard( 2, "/flags/german", contains=True )

    # make sure it also affects vehicle/ordnance snippets
    ob_vehicles_snippet_btn.click()
    wait_for_clipboard( 2, "/flags/german", contains=True )
    ob_ordnance_snippet_btn.click()
    wait_for_clipboard( 2, "/flags/german", contains=True )

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
    select_droplist_val( date_format_sel, "yy-mm-dd" )
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "date-format", "yy-mm-dd" )

    # make sure that it took effect
    assert scenario_date.get_attribute( "value" ) == "1940-01-02"
    check_scenario_date( (1,2,1940) )

    # clear the scenario date, set the date format to DD-MM-YYY
    set_scenario_date( "" )
    select_menu_option( "user_settings" )
    select_droplist_val( date_format_sel, "dd/mm/yy" )
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "date-format", "dd/mm/yy" )

    # set the scenario date
    set_scenario_date( "03/04/1945" ) # nb: this will be interpreted as DD/MM/YYYY
    check_scenario_date( (4,3,1945) )

    # load the scenario we saved before and check the date
    load_scenario( saved_scenario )
    check_scenario_date( (1,2,1940) )
    assert scenario_date.get_attribute( "value" ) == "02/01/1940"

# ---------------------------------------------------------------------

def test_hide_unavailable_ma_notes( webapp, webdriver ):
    """Test showing/hiding unavailable multi-applicable notes."""

    # initialize
    webapp.control_tests.set_vo_notes_dir( "{TEST}" )
    init_webapp( webapp, webdriver, scenario_persistence=1 )

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
    webapp.control_tests.set_vo_notes_dir( "{TEST}" )
    init_webapp( webapp, webdriver, scenario_persistence=1 )

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

def test_alternate_webapp_base_url( webapp, webdriver ):
    """Test changing the webapp base URL."""

    def do_test( expected ): #pylint: disable=missing-docstring

        # initialize
        webapp.control_tests.set_data_dir( "{REAL}" )
        init_webapp( webapp, webdriver, scenario_persistence=1 )

        # enable images
        set_user_settings( {
            "scenario-images-source": SCENARIO_IMAGES_SOURCE_THIS_PROGRAM,
            "include-vasl-images-in-snippets": True,
            "include-flags-in-snippets": True,
            "custom-list-bullets": True,
            "vo-notes-as-images": True,
        } )

        # load the scenario
        load_scenario( {
            "SCENARIO_NAME": "test scenario",
            "SCENARIO_DATE": "01/01/1940",
            "COMPASS": "north",
            "VICTORY_CONDITIONS": "Just do it!",
            "SCENARIO_NOTES": [ { "caption": "Scenario note #1" } ],
            "SSR": [ "SSR #1", "SSR #2", "SSR #3" ],
            "PLAYER_1": "german",
            "OB_SETUPS_1": [ { "caption": "OB setup note 1" } ],
            "OB_NOTES_1": [ { "caption": "OB note 1" } ],
            "OB_VEHICLES_1": [ { "name": "PzKpfw VG" } ],
            "OB_ORDNANCE_1": [ { "name": "8.8cm PaK 43" } ],
            "PLAYER_2": "russian",
            "OB_SETUPS_2": [ { "caption": "OB setup note 2" } ],
            "OB_NOTES_2": [ { "caption": "OB note 2" } ],
            "OB_VEHICLES_2": [ { "name": "T-34/85" } ],
            "OB_ORDNANCE_2": [ { "name": "82mm BM obr. 37" } ],
        } )

        # generate each snippet
        snippet_btns = find_snippet_buttons()
        for tab_id,btns in snippet_btns.items():
            select_tab( tab_id )
            for btn in btns:
                snippet_id = btn.get_attribute( "data-id" )
                btn.click()
                buf = wait_for_clipboard( 2, re.compile( "<!-- vasl-templates:id (german/|russian/)?"+snippet_id ) )
                # check each URL
                for mo in re.finditer( r"<img .*?src=[\"'](.*?)[\"']", buf ):
                    url = mo.group(1)
                    assert url.startswith( expected )

    # test with the default base URL
    do_test( webapp.base_url + "/" )

    # test with a custom base URL
    webapp.control_tests.set_app_config_val(
        key="ALTERNATE_WEBAPP_BASE_URL", val="http://ALT-BASE-URL"
    )
    do_test( "http://ALT-BASE-URL/" )

# ---------------------------------------------------------------------

def set_user_settings( opts ):
    """Configure the user settings."""
    select_menu_option( "user_settings" )
    for key,val in opts.items():
        if isinstance( val, bool ):
            elem = find_child( ".ui-dialog.user-settings input[name='{}']".format( key ) )
            if (val and not elem.is_selected()) or (not val and elem.is_selected()):
                elem.click()
        elif isinstance( val, int ):
            elem = find_child( ".ui-dialog.user-settings select[name='{}']".format( key ) )
            select_droplist_val( Select(elem), val )
        else:
            assert False
    click_dialog_button( "OK" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _check_cookies( webdriver, name, expected ):
    """Check that a user setting was stored in the cookies correctly."""
    cookies = [ c for c in webdriver.get_cookies() if c["name"] == "user-settings" ]
    assert len(cookies) == 1
    val = cookies[0]["value"].replace( "%22", '"' ).replace( "%2C", "," )
    user_settings = json.loads( val )
    assert user_settings[name] == expected
