""" Helper utilities. """

import os
import urllib.request
import json
import time
import re
import uuid

import pytest
from PyQt5.QtWidgets import QApplication
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

# standard templates
_STD_TEMPLATES = {
    "scenario": [ "scenario", "players", "victory_conditions", "scenario_notes", "ssr" ],
    "ob1": [ "ob_setup_1", "ob_note_1", "ob_vehicles_1", "ob_ordnance_1" ],
    "ob2": [ "ob_setup_2", "ob_note_2", "ob_vehicles_2", "ob_ordnance_2" ],
}

# nationality-specific templates
_NAT_TEMPLATES = {
    "german": [ "pf", "psk", "atmm" ],
    "russian": [ "mol", "mol-p" ],
    "american": [ "baz" ],
    "british": [ "piat" ],
}

_webdriver = None

# ---------------------------------------------------------------------

def init_webapp( webapp, webdriver, **options ):
    """Initialize the webapp."""
    webdriver.get( webapp.url_for( "main", **options ) )
    wait_for( 5, lambda: find_child("#_page-loaded_") is not None )

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
        templates_to_test.add( fname )

    # test the standard templates
    for tab_id,template_ids in _STD_TEMPLATES.items():
        for template_id in template_ids:
            select_tab( tab_id )
            orig_template_id = template_id
            if template_id == "scenario_notes":
                template_id = "scenario_note"
            elif template_id.startswith( "ob_setup_" ):
                template_id = "ob_setup"
            elif template_id.startswith( "ob_note_" ):
                template_id = "ob_note"
            elif template_id.startswith( "ob_vehicles_" ):
                template_id = "ob_vehicles"
            elif template_id.startswith( "ob_ordnance_" ):
                template_id = "ob_ordnance"
            func( template_id, orig_template_id )
            if orig_template_id not in ("ob_setup_2","ob_note_2","ob_vehicles_2","ob_ordnance_2"):
                templates_to_test.remove( template_id )

    # test the nationality-specific templates
    # NOTE: The buttons are the same on the OB1 and OB2 tabs, so we only test for player 1.
    player1_sel = Select( find_child( "select[name='PLAYER_1']" ) )
    for nat,template_ids in _NAT_TEMPLATES.items():
        select_tab( "scenario" )
        select_droplist_val( player1_sel, nat )
        ask = find_child( "#ask" )
        if ask and ask.is_displayed():
            click_dialog_button( "OK" ) # nb: if the front-end is asking to confirm the player nationality change
        select_tab( "ob1" )
        for template_id in template_ids:
            func( template_id, template_id )
            templates_to_test.remove( template_id )

    # make sure we tested everything
    assert not templates_to_test

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def select_tab( tab_id ):
    """Select a tab in the main page."""
    elem = find_child( "#tabs .ui-tabs-nav a[href='#tabs-{}']".format( tab_id ) )
    elem.click()

def select_menu_option( menu_id ):
    """Select a menu option."""
    elem = find_child( "#menu" )
    elem.click()
    elem = find_child( "a.PopMenu-Link[data-name='{}']".format( menu_id ) )
    elem.click()
    wait_for( 2, lambda: find_child("#menu .PopMenu-Container") is None ) # nb: wait for the menu to go away
    if pytest.config.option.webdriver == "chrome": #pylint: disable=no-member
        # FUDGE! Work-around weird "is not clickable" errors because the PopMenu is still around :-/
        time.sleep( 0.25 )

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
                add_vo( vo_type, int(key[-1]), vo_name )
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
            elem.clear()
            if val:
                elem.send_keys( val )
                if key == "SCENARIO_DATE":
                    elem.send_keys( Keys.ESCAPE ) # nb: force the calendar popup to close :-/
                    wait_for( 5, lambda: find_child("#ui-datepicker-div").value_of_css_property("display") == "none" )
                    time.sleep( 0.25 )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

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

def generate_sortable_entry_snippet( sortable, entry_no ):
    """Generate the snippet for a sortable entry."""
    elems = find_children( "li img.snippet", sortable )
    elems[entry_no].click()
    return get_clipboard()

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

def get_stored_msg( msg_type ):
    """Get a message stored for us by the front-end."""
    elem = find_child( "#" + msg_type )
    assert elem.tag_name == "textarea"
    return elem.get_attribute( "value" )

def set_stored_msg( msg_type, val ):
    """Set a message for the front-end."""
    elem = find_child( "#" + msg_type )
    assert elem.tag_name == "textarea"
    _webdriver.execute_script( "arguments[0].value = arguments[1]", elem, val )

def set_stored_msg_marker( msg_type ):
    """Store marker text in the message buffer (so we can tell if the front-end changes it)."""
    marker = "marker:{}:{}".format( msg_type, uuid.uuid4() )
    set_stored_msg( msg_type, marker )
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

def select_droplist_val( sel, val ):
    """Select a droplist option by value."""
    options = get_droplist_vals_index( sel )
    _do_select_droplist( sel, options[val] )

def select_droplist_index( sel, index ):
    """Select a droplist option by index."""
    options = get_droplist_vals( sel )
    _do_select_droplist( sel, options[index][1] )

def _do_select_droplist( sel, val ):
    """Select a droplist option."""

    # open the jQuery droplist
    sel_id = sel._el.get_attribute( "id" ) #pylint: disable=protected-access
    elem = find_child( "#{}-button .ui-selectmenu-icon".format( sel_id ) )
    elem.click()

    # select the requested option (nb: clicking on the child option doesn't work :shrug:)
    elem = find_child( "#{}-button".format( sel_id ) )
    elem.send_keys( val )
    elem.send_keys( Keys.RETURN )

def get_droplist_vals_index( sel ):
    """Get the value/text for each option in a droplist."""
    return { k: v for k,v in get_droplist_vals(sel) }

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

def click_dialog_button( caption ):
    """Click a dialog button."""
    btn = next(
        elem for elem in find_children(".ui-dialog button")
        if elem.text == caption
    )
    btn.click()

# ---------------------------------------------------------------------

_pyqt_app = None

def get_clipboard() :
    """Get the contents of the clipboard."""
    if pytest.config.option.no_clipboard: #pylint: disable=no-member
        return get_stored_msg( "_clipboard_" )
    else:
        global _pyqt_app
        if _pyqt_app is None:
            _pyqt_app = QApplication( [] )
        clipboard = QApplication.clipboard()
        return clipboard.text()

def wait_for( timeout, func ):
    """Wait for a condition to become true."""
    if os.name == "nt":
        timeout *= 2 # Selenium runs pretty slow on Windows :-/
    start_time = time.time()
    while True:
        if func():
            break
        assert time.time() - start_time < timeout
        time.sleep( 0.1 )
