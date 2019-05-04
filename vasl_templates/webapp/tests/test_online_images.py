"""Test using online images in VASL scenarios."""

import re

from selenium.webdriver.common.action_chains import ActionChains

from vasl_templates.webapp.tests.utils import init_webapp, select_tab, \
    find_child, find_children, click_dialog_button, wait_for_clipboard, wait_for_elem
from vasl_templates.webapp.tests.test_user_settings import set_user_settings
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario

# ---------------------------------------------------------------------

def test_online_images( webapp, webdriver ):
    """Test using online images in VASL scenarios."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct:
            ct.set_data_dir( dtype="real" ) \
              .set_vasl_mod( vmod="random" ) \
              .set_default_template_pack( dname="real" )
    )

    # load the test scenario
    load_scenario( {
        "PLAYER_1": "german",
        "OB_VEHICLES_1": [ { "name": "PzKpfw IVH" } ],
    } )

    # configure the user settings
    set_user_settings( {
        "include-flags-in-snippets": True,
        "custom-list-bullets": True,
        "include-vasl-images-in-snippets": True,
    } )

    def do_test( snippet_id, expected1, expected2 ): #pylint: disable=missing-docstring
        # generate the snippet with online images enabled
        set_user_settings( { "use-online-images": True } )
        btn = find_child( "button[data-id='{}']".format( snippet_id ) )
        btn.click()
        wait_for_clipboard( 2, expected1 )
        # generate the snippet with online images disabled
        set_user_settings( { "use-online-images": False } )
        btn.click()
        wait_for_clipboard( 2, expected2 )

    # test player flags
    do_test( "players",
        re.compile( r'<img src="http://vasl-templates.org/.+/flags/german.png">' ),
        re.compile( r'<img src="http://[a-z0-9.]+:\d+/flags/german">' )
    )

    # test custom list bullets
    do_test( "ssr",
        re.compile( r'url\("http://vasl-templates.org/.+/bullet.png"\)' ),
        re.compile( r'url\("http://[a-z0-9.]+:\d+/.+/bullet.png"\)')
    )

    # test VASL counter images
    select_tab( "ob1" )
    do_test( "ob_vehicles_1",
        re.compile( r'<img src="https://raw.githubusercontent.com/.+/ge/veh/pzivh.gif">' ),
        re.compile( r'<img src="http://[a-z0-9.]+:\d+/counter/2584/front">' )
    )

# ---------------------------------------------------------------------

def test_multiple_images( webapp, webdriver ):
    """Test handling of VASL counters that have multiple images."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct:
            ct.set_data_dir( dtype="real" ) \
              .set_vasl_mod( vmod="random" ) \
              .set_default_template_pack( dname="real" )
    )

    # load the test scenario
    load_scenario( {
        "PLAYER_1": "british",
        "OB_VEHICLES_1": [ { "name": "2pdr Portee" } ],
    } )

    # configure the user settings
    set_user_settings( {
        "use-online-images": True,
        "include-vasl-images-in-snippets": True,
    } )

    # generate a snippet for the vehicle (using the default image)
    select_tab( "ob1" )
    btn = find_child( "button[data-id='ob_vehicles_1']" )
    btn.click()
    wait_for_clipboard( 2,
        re.compile( r'<img src="https://raw.githubusercontent.com/.+/br/vehicles/portee.gif">')
    )

    # select the second image for the vehicle
    sortable = find_child( "#ob_vehicles-sortable_1" )
    elems = find_children( "li", sortable )
    assert len(elems) == 1
    ActionChains(webdriver).double_click( elems[0] ).perform()
    btn = wait_for_elem( 2, "#edit-vo input.select-vo-image" )
    btn.click()
    images = find_children( ".ui-dialog.select-vo-image .vo-images img" )
    assert len(images) == 2
    images[1].click()
    click_dialog_button( "OK" )

    # generate a snippet for the vehicle (using the new image)
    btn = find_child( "button[data-id='ob_vehicles_1']" )
    btn.click()
    wait_for_clipboard( 2,
        re.compile( r'<img src="https://raw.githubusercontent.com/.+/br/vehicles/portee0.gif">')
    )

# ---------------------------------------------------------------------

def test_extensions( webapp, webdriver ):
    """Test handling of VASL counters in extensions."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct:
            ct.set_data_dir( dtype="real" ) \
              .set_vasl_mod( vmod="random", extns_dtype="real" ) \
              .set_default_template_pack( dname="real" )
    )

    # load the test scenario
    load_scenario( {
        "PLAYER_1": "russian",
        "OB_VEHICLES_1": [
            { "id": "ru/v:078", "image_id": "f97:178/0" }, # Matilda II(b) (4FP variant)
            { "id": "ru/v:078", "image_id": "f97:184/0" }, # Matilda II(b) (6FP variant)
            { "id": "ru/v:004", "image_id": "547/0" }, # T-60 M40 (core module)
            { "id": "ru/v:004", "image_id": "f97:186/0" }, # T-60 M40 (KGS variant)
        ],
    } )

    # configure the user settings
    set_user_settings( {
        "use-online-images": True,
        "include-vasl-images-in-snippets": True,
    } )

    # generate a snippet for the vehicles
    select_tab( "ob1" )
    btn = find_child( "button[data-id='ob_vehicles_1']" )
    btn.click()
    wait_for_clipboard( 2, re.compile(
        '<img src="http://vasl-templates.org/.+/f97/matii2-4cmg.gif">'
        '.+'
        '<img src="http://vasl-templates.org/.+/f97/matii2-6cmg.gif">'
        '.+'
        '<img src="https://raw.githubusercontent.com/.+/ru/veh/T60M40.gif">'
        '.+'
        '<img src="http://vasl-templates.org/.+/f97/T60M40.gif">'
    , re.DOTALL ) )
