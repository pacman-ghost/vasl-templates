""" Helper utilities. """

from PyQt5.QtWidgets import QApplication
from selenium.common.exceptions import NoSuchElementException

_webdriver = None

# ---------------------------------------------------------------------

def get_stored_msg( msg_id ):
    """Get a message stored for us by the front-end."""
    elem = find_child( _webdriver, "#"+msg_id )
    if not elem:
        return None
    return elem.text

# ---------------------------------------------------------------------

def get_clipboard() :
    """Get the contents of the clipboard."""
    app = QApplication( [] ) #pylint: disable=unused-variable
    clipboard = QApplication.clipboard()
    return clipboard.text()

# ---------------------------------------------------------------------

def find_child( elem, sel ):
    """Find a single child element."""
    try:
        return elem.find_element_by_css_selector( sel )
    except NoSuchElementException:
        return None

def find_children( elem, sel ):
    """Find child elements."""
    try:
        return elem.find_elements_by_css_selector( sel )
    except NoSuchElementException:
        return None
