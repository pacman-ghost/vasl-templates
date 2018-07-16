""" Helper utilities. """

import urllib.request
import json
import time

from PyQt5.QtWidgets import QApplication
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException

_webdriver = None

# ---------------------------------------------------------------------

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
                    time.sleep( 0.25 )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def get_nationalities( webapp ):
    """Get the nationalities table."""
    url = webapp.url_for( "get_nationalities" )
    return json.load( urllib.request.urlopen( url ) )

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
