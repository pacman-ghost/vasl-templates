""" Test the user settings. """

import json

from vasl_templates.webapp.tests.utils import \
    init_webapp, find_child, _get_clipboard, \
    wait_for, select_menu_option, click_dialog_button
from vasl_templates.webapp.tests.test_vehicles_ordnance import add_vo
from vasl_templates.webapp.config.constants import DATA_DIR as REAL_DATA_DIR

# ---------------------------------------------------------------------

def test_include_vasl_images_in_snippets( webapp, webdriver, monkeypatch ):
    """Test the user settings."""

    # initialize
    monkeypatch.setitem( webapp.config, "DATA_DIR", REAL_DATA_DIR )
    init_webapp( webapp, webdriver )

    # add a vehicle
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
    wait_for( 2, lambda: "/counter/2524/front" in _get_clipboard() )

    # disable "show VASL images in snippets"
    select_menu_option( "user_settings" )
    elem = find_child( ".ui-dialog.user-settings input[name='include-vasl-images-in-snippets']" )
    assert elem.is_selected()
    elem.click()
    click_dialog_button( "OK" )
    _check_cookies( webdriver, "include-vasl-images-in-snippets", False )

    # make sure that it took effect
    snippet_btn.click()
    wait_for( 2, lambda: "/counter/2524/front" not in _get_clipboard() )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _check_cookies( webdriver, name, expected ):
    """Check that a user setting was stored in the cookies correctly."""
    cookies = [ c for c in webdriver.get_cookies() if c["name"] == "user-settings" ]
    assert len(cookies) == 1
    val = cookies[0]["value"].replace( "%22", '"' )
    user_settings = json.loads( val )
    assert user_settings[name] == expected
