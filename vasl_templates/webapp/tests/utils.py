""" Helper utilities. """

from selenium.common.exceptions import NoSuchElementException

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
