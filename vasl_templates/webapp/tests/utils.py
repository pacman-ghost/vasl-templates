""" Helper utilities. """

import os
import urllib.request
import json
import time
import re
import typing
import uuid
from collections import defaultdict

import pytest
from PyQt5.QtWidgets import QApplication
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, WebDriverException

from vasl_templates.webapp.tests.remote import ControlTests

# standard templates
_STD_TEMPLATES = {
    "scenario": [
        "scenario", "players", "victory_conditions", "scenario_notes", "ssr",
        "nat_caps_1", # nb: "nat_caps_2" is functionally the same as this
    ],
    "ob1": [ "ob_setup_1", "ob_note_1",
        "ob_vehicles_1", "ob_vehicle_note_1", "ob_vehicles_ma_notes_1",
        "ob_ordnance_1", "ob_ordnance_note_1", "ob_ordnance_ma_notes_1"
    ],
    "ob2": [ "ob_setup_2", "ob_note_2",
        "ob_vehicles_2", "ob_vehicle_note_2", "ob_vehicles_ma_notes_2",
        "ob_ordnance_2", "ob_ordnance_note_2", "ob_ordnance_ma_notes_2"
    ],
}

# nationality-specific templates
_NAT_TEMPLATES = {
    "german": [ "pf", "psk", "atmm" ],
    "russian": [ "mol", "mol-p" ],
    "american": [ "baz" ],
    "british": [ "piat" ],
    "japanese": [ "thh" ],
    "kfw-cpva": [ "baz-cpva16", "baz-cpva17" ],
}

_webapp = None
_webdriver = None

# ---------------------------------------------------------------------

def init_webapp( webapp, webdriver, **options ):
    """Initialize the webapp."""

    # initialize
    global _webapp, _webdriver
    _webapp = webapp
    _webdriver = webdriver

    # reset the server
    # NOTE: We have to do this manually, since we can't use pytest's monkeypatch'ing,
    # since we could be talking to a remote server (see ControlTests for more details).
    control_tests = ControlTests( webapp )
    control_tests \
        .set_data_dir( dtype="test" ) \
        .set_default_scenario( fname=None ) \
        .set_default_template_pack( dname=None ) \
        .set_vasl_extn_info_dir( dtype=None ) \
        .set_vasl_mod( vmod=None, extns_dtype=None ) \
        .set_vassal_engine( vengine=None ) \
        .set_vo_notes_dir( dtype=None ) \
        .set_user_files_dir( dtype=None ) \
        .set_roar_scenario_index( fname="roar-scenario-index.json" )
    if "reset" in options:
        options.pop( "reset" )( control_tests )

    # force the default template pack to be reloaded (using the new settings)
    control_tests.reset_template_pack()

    # load the webapp
    webdriver.get( webapp.url_for( "main", **options ) )
    _wait_for_webapp()

    # reset the user settings
    webdriver.delete_all_cookies()

    return control_tests

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def refresh_webapp( webdriver ):
    """Refresh the webapp."""
    webdriver.refresh()
    _wait_for_webapp()

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _wait_for_webapp():
    """Wait for the webapp to finish initialization."""
    # FUDGE! The webapp sometimes takes a while to initialize (if we have a NIC active but
    # no internet connectivity? Is Chrome looking for some update, or something like that?)
    timeout = 30 if os.name == "nt" else 15
    wait_for( timeout, lambda: find_child("#_page-loaded_") is not None )

# ---------------------------------------------------------------------

def for_each_template( func ): #pylint: disable=too-many-branches
    """Test each template."""

    # generate a list of all the templates we need to test
    templates_to_test = set()
    dname = os.path.join( os.path.split(__file__)[0], "../data/default-template-pack" )
    for fname in os.listdir(dname):
        fname,extn = os.path.splitext( fname )
        if extn != ".j2":
            continue
        if fname == "ob_vo":
            templates_to_test.update( [ "ob_vehicles", "ob_ordnance" ] )
        elif fname == "ob_vo_note":
            templates_to_test.update( [ "ob_vehicle_note", "ob_ordnance_note" ] )
        elif fname == "ob_ma_notes":
            templates_to_test.update( [ "ob_vehicles_ma_notes", "ob_ordnance_ma_notes" ] )
        else:
            templates_to_test.add( fname )

    # test the standard templates
    for tab_id,template_ids in _STD_TEMPLATES.items():
        for template_id in template_ids:
            select_tab( tab_id )
            orig_template_id = template_id
            if template_id == "scenario_notes":
                template_id = "scenario_note"
            elif template_id.endswith( ("_1","_2") ):
                template_id = template_id[:-2]
            func( template_id, orig_template_id )
            if orig_template_id not in ("ob_setup_2","ob_note_2",
                "ob_vehicles_2","ob_vehicle_note_2","ob_vehicles_ma_notes_2",
                "ob_ordnance_2","ob_ordnance_note_2","ob_ordnance_ma_notes_2"
            ):
                templates_to_test.remove( template_id )

    # test the nationality-specific templates
    # NOTE: The buttons are the same on the OB1 and OB2 tabs, so we only test for player 1.
    for nat,template_ids in _NAT_TEMPLATES.items():
        set_player( 1, nat )
        ask = find_child( "#ask" )
        if ask and ask.is_displayed():
            click_dialog_button( "OK" ) # nb: if the front-end is asking to confirm the player nationality change
        select_tab( "ob1" )
        for template_id in template_ids:
            orig_template_id = template_id
            if template_id.endswith( ("_1","_2") ):
                template_id = template_id[:-2]
            func( template_id, orig_template_id )
            templates_to_test.remove( template_id )

    # test the American BAZ 45 and BAZ 50
    load_scenario_params( { "scenario": {
        "PLAYER_1": "american",
        "SCENARIO_THEATER": "Korea",
    } } )
    select_tab( "ob1" )
    for template_id in ("baz45","baz50"):
        func( template_id, template_id )
        templates_to_test.remove( template_id )

    # make sure we tested everything
    assert not templates_to_test

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def select_tab( tab_id, webdriver=None ):
    """Select a tab in the main page."""
    if not webdriver:
        webdriver = _webdriver
    elem = find_child( "#tabs .ui-tabs-nav a[href='#tabs-{}']".format( tab_id ), webdriver )
    elem.click()

def select_tab_for_elem( elem ):
    """Select the tab that contains the specified element."""
    select_tab( get_tab_for_elem( elem ) )

def get_tab_for_elem( elem ):
    """Identify the tab that contains the specified element."""
    while elem.tag_name not in ("html","body"):
        elem = elem.find_element_by_xpath( ".." )
        if elem.tag_name == "div":
            div_id = elem.get_attribute( "id" )
            if div_id.startswith( "tabs-" ):
                return div_id[5:]
    return None

def select_menu_option( menu_id, webdriver=None ):
    """Select a menu option."""

    if not webdriver:
        webdriver = _webdriver
    elem = find_child( "#menu", webdriver )
    elem.click()
    elem = wait_for_elem( 2, "a.PopMenu-Link[data-name='{}']".format( menu_id ), webdriver )
    elem.click()
    wait_for( 2, lambda: find_child("#menu .PopMenu-Container",webdriver) is None ) # nb: wait for the menu to go away

    # FUDGE! The delay above is not enough, I suspect because Selenium is deciding that the PopMenu container
    # is hidden if it has a very low opacity, but it's still blocking any clicks we want to do after we return.
    # We work around this by trying to click on a dummy button, until it works :-/
    class PopMenuHack:
        """Enable/disable the button we use to detect if PopMenu is still on-screen."""
        def __enter__( self ):
            webdriver.execute_script( "document.getElementById('popmenu-hack').style.display = 'block'" )
        def __exit__( self, *args ):
            webdriver.execute_script( "document.getElementById('popmenu-hack').style.display = 'none'" )
    btn = find_child( "button#popmenu-hack", webdriver )
    with PopMenuHack():
        for i in range(0,10): #pylint: disable=unused-variable
            try:
                btn.click()
                return
            except WebDriverException:
                time.sleep( 0.25 )
                if find_child( ".ui-dialog", webdriver ):
                    return
    assert False

def new_scenario():
    """Reset the scenario."""
    select_menu_option( "new_scenario" )
    # check if the webapp is asking for confirmation
    if find_child( "#ask" ).is_displayed():
        # yup - make it so
        click_dialog_button( "OK" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def load_scenario_params( params ):
    """Load a full set of template parameters."""
    for tab_id,fields in params.items():
        select_tab( tab_id )
        set_template_params( fields )

def set_template_params( params ): #pylint: disable=too-many-branches
    """Set template parameters."""

    def add_sortable_entries( sortable, entries ):
        """Add simple notes to a sortable."""
        for entry in entries:
            add_simple_note( sortable, entry.get("caption",""), entry.get("width","") )

    for key,val in params.items():

        # check for scenario notes (these require special handling)
        if key == "SCENARIO_NOTES":
            # add them in (nb: we don't consider any existing scenario notes)
            add_sortable_entries( find_child("#scenario_notes-sortable"), val )
            continue

        # check for SSR's (these require special handling)
        if key == "SSR":
            # add them in (nb: we don't consider any existing SSR's)
            sortable = find_child( "#ssr-sortable" )
            for ssr in val:
                add_simple_note( sortable, ssr, None )
            continue

        # check for OB setups/notes (these require special handling)
        if key in ("OB_SETUPS_1","OB_SETUPS_2","OB_NOTES_1","OB_NOTES_2"):
            # add them in (nb: we don't consider any existing OB setup/note's)
            mo = re.search( r"^(.*)_(\d)$", key )
            sortable = find_child( "#{}-sortable_{}".format( mo.group(1).lower(), mo.group(2) ) )
            add_sortable_entries( sortable, val )
            continue

        # check for vehicles/ordnance (these require special handling)
        if key in ("OB_VEHICLES_1","OB_ORDNANCE_1","OB_VEHICLES_2","OB_ORDNANCE_2"):
            # add them in (nb: we don't consider any existing vehicles/ordnance)
            from vasl_templates.webapp.tests.test_vehicles_ordnance import add_vo #pylint: disable=cyclic-import
            mo = re.search( r"^OB_(VEHICLES|ORDNANCE)_\d$", key )
            vo_type = mo.group(1).lower()
            for vo_name in val:
                add_vo( _webdriver, vo_type, int(key[-1]), vo_name )
            continue

        # locate the next parameter
        elem = next( c for c in ( \
            find_child( "{}[name='{}']".format(elem_type,key) ) \
            for elem_type in ["input","textarea","select"]
        ) if c )

        # set the parameter value
        if elem.tag_name == "select":
            select_droplist_val( Select(elem), val )
        else:
            if elem.is_displayed():
                elem.clear()
                if val:
                    elem.send_keys( val )
                    if key == "SCENARIO_DATE":
                        elem.send_keys( Keys.TAB ) # nb: force the calendar popup to close :-/
                        wait_for( 5,
                            lambda: find_child( "#ui-datepicker-div" ).value_of_css_property( "display" ) == "none"
                        )
                        time.sleep( 0.25 )
            else:
                # FUDGE! Selenium can't interact with hidden elements, so we do it like this.
                # However, we don't do this for everything since it doesn't always triggers events.
                _webdriver.execute_script( "arguments[0].value = arguments[1]", elem, val )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def set_scenario_date( scenario_date ):
    """Set the scenario date."""
    if scenario_date is None:
        return
    select_tab( "scenario" )
    elem = find_child( "input[name='SCENARIO_DATE']" )
    elem.clear()
    elem.send_keys( scenario_date )
    elem.send_keys( Keys.TAB ) # nb: force the calendar popup to close :-/

def set_player( player_no, nat ):
    """Set a player's nationality."""
    select_tab( "scenario" )
    sel = Select( find_child( "select[name='PLAYER_{}']".format( player_no ) ) )
    select_droplist_val( sel, nat )
    return sel

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

_nationalities = None

def get_nationality_display_name( nat_id ):
    """Get the nationality's display name."""
    global _nationalities
    if not _nationalities:
        _nationalities = get_nationalities( _webapp )
    return _nationalities[ nat_id ]["display_name"]

def get_nationalities( webapp ):
    """Get the nationalities table."""
    url = webapp.url_for( "get_template_pack" )
    template_pack = json.load( urllib.request.urlopen( url ) )
    return template_pack["nationalities"]

# ---------------------------------------------------------------------

def add_simple_note( sortable, caption, width ):
    """Add a new simple note to a sortable."""
    edit_simple_note( sortable, None, caption, width )

def edit_simple_note( sortable, entry_no, caption, width ):
    """Edit a simple note in a sortable."""

    # figure out if we're creating a new entry, or editing an existing one
    if entry_no is None:
        # create a new entry
        add_button = find_sortable_helper( sortable, "add" )
        add_button.click()
    else:
        # edit an existing entry
        elems = find_children( "li", sortable )
        ActionChains(_webdriver).double_click( elems[entry_no] ).perform()

    # edit the note
    if caption is not None:
        elem = find_child( "#edit-simple_note textarea" )
        elem.clear()
        elem.send_keys( caption )
    if width is not None:
        elem = find_child( ".ui-dialog-buttonpane input[name='width']" )
        elem.clear()
        elem.send_keys( width )
    click_dialog_button( "OK" )
    if caption == "":
        # an empty caption will delete the entry - confirm the deletion
        click_dialog_button( "OK" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def get_sortable_entry_text( sortable ):
    """Get the text for each entry in a sortable."""
    return [ c.text for c in find_children("li", sortable) ]

def get_sortable_entry_count( sortable ):
    """Return the number of entries in a sortable."""
    return len( find_children( "li", sortable ) )

def get_sortable_vo_names( sortable ):
    """Return the vehicle/ordnance names from a sortable."""
    return [ c.text for c in find_children("li .vo-name",sortable) ]

def generate_sortable_entry_snippet( sortable, entry_no ):
    """Generate the snippet for a sortable entry."""
    elems = find_children( "li img.snippet", sortable )
    elems[entry_no].click()
    return _get_clipboard()

def drag_sortable_entry_to_trash( sortable, entry_no ):
    """Draw a sortable entry to the trash."""
    trash = find_sortable_helper( sortable, "trash" )
    elems = find_children( "li", sortable )
    ActionChains(_webdriver).drag_and_drop( elems[entry_no], trash ).perform()

def find_sortable_helper( sortable, tag ):
    """Find a sortable's helper element."""
    sortable_id = sortable.get_attribute( "id" )
    mo = re.search( r"^(.+)-sortable(_\d)?$", sortable_id )
    helper_id = "#{}-{}".format( mo.group(1), tag )
    if mo.group(2):
        helper_id += mo.group(2)
    return find_child( helper_id )

# ---------------------------------------------------------------------

def get_stored_msg( msg_type, webdriver=None ):
    """Get a message stored for us by the front-end."""
    if not webdriver:
        webdriver = _webdriver
    elem = find_child( "#" + msg_type, webdriver )
    assert elem.tag_name == "textarea"
    return elem.get_attribute( "value" )

def set_stored_msg( msg_type, val, webdriver=None ):
    """Set a message for the front-end."""
    if not webdriver:
        webdriver = _webdriver
    elem = find_child( "#" + msg_type, webdriver )
    assert elem.tag_name == "textarea"
    webdriver.execute_script( "arguments[0].value = arguments[1]", elem, val )

def set_stored_msg_marker( msg_type, webdriver=None ):
    """Store marker text in the message buffer (so we can tell if the front-end changes it)."""
    # NOTE: Care should taken when using this function with "_clipboard_",
    # since the tests might be using the real clipboard!
    marker = "marker:{}:{}".format( msg_type, uuid.uuid4() )
    set_stored_msg( msg_type, marker, webdriver )
    return marker

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def find_child( sel, parent=None ):
    """Find a single child element."""
    try:
        # NOTE: I tried caching these results, but it didn't help the tests run any faster :-(
        return (parent if parent else _webdriver).find_element_by_css_selector( sel )
    except NoSuchElementException:
        return None

def find_children( sel, parent=None ):
    """Find child elements."""
    try:
        return (parent if parent else _webdriver).find_elements_by_css_selector( sel )
    except NoSuchElementException:
        return None

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def find_snippet_buttons( webdriver=None ):
    """Find all "generate snippet" buttons.

    NOTE: We only return the 1st snippet button in the "extras" tab.
    """
    snippet_btns = defaultdict( list )
    # find all normal "generate snippet" buttons
    for btn in find_children( "button.generate", webdriver ):
        snippet_btns[ get_tab_for_elem(btn) ].append( btn )
    # find "generate snippet" buttons in sortable lists
    for btn in find_children( "ul.sortable img.snippet", webdriver ):
        snippet_btns[ get_tab_for_elem(btn) ].append( btn )
    # FUDGE! All nationality-specific buttons are created on each OB tab, and the ones not relevant
    # to each player are just hidden. This is not real good since we have multiple elements with
    # the same ID :-/ but we work around this by checking if the button is visible. Sigh...
    snippet_btns2 = {}
    for tab_id,btns in snippet_btns.items():
        select_tab( tab_id, webdriver )
        snippet_btns2[ tab_id ] = [ btn for btn in btns if btn.is_displayed() ]
    return snippet_btns2

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def select_droplist_val( sel, val ):
    """Select a droplist option by value."""
    _do_select_droplist( sel, val )

def select_droplist_index( sel, index ):
    """Select a droplist option by index."""
    options = get_droplist_vals( sel )
    _do_select_droplist( sel, options[index][0] )

def _do_select_droplist( sel, val ):
    """Select a droplist option."""
    sel_name = sel._el.get_attribute( "name" ) #pylint: disable=protected-access
    _webdriver.execute_script(
        "$(arguments[0]).val( '{}' ).trigger( 'change' )".format( val ),
        find_child( "select[name='{}']".format( sel_name ) )
    )

def get_droplist_vals_index( sel ):
    """Get the value/text for each option in a droplist."""
    return dict( get_droplist_vals( sel ) )

def get_droplist_vals( sel ):
    """Get the value/text for each option in a droplist."""
    return [
        ( opt.get_attribute("value"), opt.get_attribute("text") )
        for opt in sel.options
    ]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def dismiss_notifications():
    """Dismiss all notifications."""
    assert False, "Shouldn't need to call this function." # nb: notifications have been disabled during tests
    while True:
        elem = find_child( ".growl-close" )
        if not elem:
            break
        try:
            elem.click()
            time.sleep( 0.25 )
        except StaleElementReferenceException:
            pass # nb: the notification had already auto-closed

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def click_dialog_button( caption, parent=None ):
    """Click a dialog button."""
    btns = [
        elem for elem in find_children( ".ui-dialog button", parent )
        if elem.text == caption
    ]
    assert len(btns) == 1
    btns[0].click()

# ---------------------------------------------------------------------

_pyqt_app = None

def _get_clipboard() :
    """Get the contents of the clipboard.

    NOTE: This used to be public, but there is sometimes a delay between doing something
    in the UI (e.g. clicking a button) and the result appearing in the clipboard, so tests
    should use wait_for_clipboard() instead.
    """
    if pytest.config.option.use_clipboard: #pylint: disable=no-member
        global _pyqt_app
        if _pyqt_app is None:
            _pyqt_app = QApplication( [] )
        clipboard = QApplication.clipboard()
        return clipboard.text()
    else:
        return get_stored_msg( "_clipboard_" )

def wait_for( timeout, func ):
    """Wait for a condition to become true."""
    if os.name == "nt":
        timeout *= 5 # Selenium runs pretty slow on Windows :-/
    else:
        timeout *= 2
    start_time = time.time()
    while True:
        if func():
            break
        assert time.time() - start_time < timeout
        time.sleep( 0.1 )

def wait_for_elem( timeout, elem_id, parent=None ):
    """Wait for an element to appear ."""
    args = { "elem": None }
    def check_elem(): #pylint: disable=missing-docstring
        args["elem"] = find_child( elem_id, parent )
        return args["elem"] is not None and args["elem"].is_displayed()
    wait_for( timeout, check_elem )
    return args["elem"]

def wait_for_clipboard( timeout, expected, contains=None, transform=None ):
    """Wait for the clipboard to hold an expected value."""
    args = { "last-clipboard": "" }
    def check_clipboard(): #pylint: disable=missing-docstring
        clipboard = _get_clipboard()
        args["last-clipboard"] = clipboard
        if transform:
            clipboard = transform( clipboard )
        if contains is None:
            if isinstance( expected, typing.re.Pattern ):
                return expected.search( clipboard ) is not None
            else:
                return expected == clipboard
        elif contains is True:
            return expected in clipboard
        elif contains is False:
            return expected not in clipboard
        assert False
        return False
    try:
        wait_for( timeout, check_clipboard )
        return args["last-clipboard"]
    except AssertionError:
        print( "Timed out waiting for the clipboard:" )
        print( "- Expecting:", expected )
        print( "- Got:", args["last-clipboard"] )
        raise

# ---------------------------------------------------------------------

_IE_HTML_TAGS = [ "<i>" ]

def adjust_html( val ):
    """Adjust HTML content for IE."""
    if pytest.config.option.webdriver != "ie": #pylint: disable=no-member
        return val
    # convert HTML tags to uppercase :-/
    for tag in _IE_HTML_TAGS:
        val = val.replace( tag, tag.upper() )
        assert tag.startswith( "<" ) and tag.endswith( ">" )
        close_tag = "</{}".format( tag[1:] )
        val = val.replace( close_tag, close_tag.upper() )
    return val

# ---------------------------------------------------------------------

def get_css_classes( elem ):
    """Get the CSS classes for the specified element."""
    classes = elem.get_attribute( "class" )
    return classes.split() if classes else []
