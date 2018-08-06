""" Helper utilities. """

import os
import urllib.request
import json
import time

from PyQt5.QtWidgets import QApplication
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

# standard templates
_STD_TEMPLATES = {
    "scenario": [ "scenario", "players", "victory_conditions", "ssr" ],
    "ob1": [ "ob_setup_1", "vehicles_1", "ordnance_1" ],
    "ob2": [ "ob_setup_2", "vehicles_2", "ordnance_2" ],
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

def for_each_template( func ):
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
        select_tab( tab_id )
        for template_id in template_ids:
            if template_id.startswith( "ob_setup_" ):
                template_id2 = "ob_setup"
            elif template_id.startswith( "vehicles_" ):
                template_id2 = "vehicles"
            elif template_id.startswith( "ordnance_" ):
                template_id2 = "ordnance"
            else:
                template_id2 = template_id
            func( template_id2, template_id )
            if template_id not in ("ob_setup_2","vehicles_2","ordnance_2"):
                templates_to_test.remove( template_id2 )

    # test the nationality-specific templates
    # NOTE: The buttons are the same on the OB1 and OB2 tabs, so we only test for player 1.
    for nat,template_ids in _NAT_TEMPLATES.items():
        select_tab( "scenario" )
        sel = Select( find_child( "select[name='PLAYER_1']" ) )
        sel.select_by_value( nat )
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
    wait_for( 5, lambda: find_child("#menu .PopMenu-Container") is None ) # nb: wait for the menu to go away

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def set_template_params( params ):
    """Set template parameters."""

    for key,val in params.items():

        # check for SSR's (these require special handling)
        if key == "SSR":
            # add them in (nb: we don't consider any existing SSR's)
            from vasl_templates.webapp.tests.test_ssr import add_ssr #pylint: disable=cyclic-import
            for ssr in val:
                add_ssr( _webdriver, ssr )
            continue

        # check for vehicles/ordnance (these require special handling)
        if key in ("VEHICLES_1","ORDNANCE_1","VEHICLES_2","ORDNANCE_2"):
            # add them in (nb: we don't consider any existing vehicles/ordnance)
            vo_type = "vehicle" if key.startswith("VEHICLES_") else "ordnance"
            from vasl_templates.webapp.tests.test_vehicles_ordnance import add_vo #pylint: disable=cyclic-import
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
            Select(elem).select_by_value( val )
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

def get_stored_msg( msg_id ):
    """Get a message stored for us by the front-end."""
    elem = find_child( "#"+msg_id )
    if not elem:
        return None
    if elem.tag_name == "div":
        return elem.text
    assert elem.tag_name == "textarea"
    return elem.get_attribute( "value" )

def set_stored_msg( msg_id, val ):
    """Set a message for the front-end."""
    elem = find_child( "#"+msg_id )
    assert elem.tag_name == "textarea"
    _webdriver.execute_script( "arguments[0].value = arguments[1]", elem, val )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def find_child( sel, parent=None ):
    """Find a single child element."""
    try:
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

def dismiss_notifications():
    """Dismiss all notifications."""
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

def get_clipboard() :
    """Get the contents of the clipboard."""
    app = QApplication( [] ) #pylint: disable=unused-variable
    clipboard = QApplication.clipboard()
    return clipboard.text()

def wait_for( timeout, func ):
    """Wait for a condition to become true."""
    start_time = time.time()
    while True:
        if func():
            break
        assert time.time() - start_time < timeout
        time.sleep( 0.1 )
