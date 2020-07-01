""" Test comment generation. """

import re

from vasl_templates.webapp.tests.utils import init_webapp, new_scenario, select_tab, \
    find_child, wait_for_clipboard, set_scenario_date
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario

# ---------------------------------------------------------------------

def test_time_based_comments( webapp, webdriver ):
    """Test time-based comments."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct: ct.set_data_dir( dtype="real" )
    )

    # test a "START-" time-range
    _test_comments( "german", "vehicles", "SPW 251/10", [
        ( None, "PSK, else ATR" ),
        ( "12/31/1942", "| ATR |" ),
        ( "08/31/1943", "| ATR |" ),
        ( "09/01/1943", "| PSK |" ),
        ( "01/01/1944", "| PSK |" ),
    ] )

    # test a "-END" time-range
    _test_comments( "french", "ordnance", "Canon AC de 47 SA mle 37 APX", [
        ( None, "En Portee<sup>41+</sup>" ),
        ( "12/31/1940", "En Portee NA" ),
        ( "01/01/1941", "En Portee (Renault AGR2)" ),
    ] )

    # test a "START-END" time-range
    _test_comments( "british", "ordnance", "OQF 6-Pounder 7-cwt", [
        ( None, "En Portee<sup>41-8/43</sup>" ),
        ( "12/31/1940", "En Portee NA" ),
        ( "01/01/1941", "En Portee (3-ton lorry)" ),
        ( "08/01/1943", "En Portee (3-ton lorry)" ),
        ( "09/01/1943", "En Portee NA" ),
        ( "01/01/1944", "En Portee NA" ),
    ] )

# ---------------------------------------------------------------------

def test_french_veh_f( webapp, webdriver ):
    """Test French Vehicle Note F."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct: ct.set_data_dir( dtype="real" )
    )

    # test an "(a)" vehicle
    _test_comments( "french", "vehicles", "Ac de 40 CA(a)", [
        ( None, "American ESB+" ),
        ( None, "Black TH#" ),
        ( None, "Captured Use (unless Free French or US)" ),
    ] )
    _test_comments( "french", "vehicles", "AM Dodge(a)", [
        ( None, "Captured Use (unless Vichy French)" ),
    ] )

    # test a "(b)" vehicle
    _test_comments( "french", "vehicles", "Valentine V(b)", [
        ( None, "British ESB+" ),
        ( None, "Black TH#" ),
        ( None, "Captured Use (unless Vichy French or British)" ),
    ] )

    # test an "(f)" vehicle
    _test_comments( "free-french", "vehicles", "H39(f)", [
        ( None, "French ESB+" ),
        ( None, "Red TH#" ),
        ( None, "Captured Use (unless Free/Vichy French)" ),
    ] )

# ---------------------------------------------------------------------

def test_axis_minor_veh_e( webapp, webdriver ):
    """Test Axis Minor Vehicle Note E."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct: ct.set_data_dir( dtype="real" )
    )

    # test an "(f)" vehicle
    _test_comments( "romanian", "vehicles", "R-35(f)", [
        ( None, "| French ESB |" ),
        ( None, "! Black TH#" ),
    ] )

    # test a "(g)" vehicle
    _test_comments( "croatian", "vehicles", "LT vz 35(g)", [
        ( None, "| German ESB |" ),
        ( None, "! Black TH#" ),
    ] )
    _test_comments( "hungarian", "vehicles", "LT vz 35(g)", [
        ( None, "| German ESB |" ),
        ( None, "Black TH#" ),
    ] )

    # test an "(i)" vehicle
    _test_comments( "croatian", "vehicles", "L3/35(i)", [
        ( None, "| Italian ESB |" ),
        ( None, "! Black TH#" ),
    ] )

    # test an "(r)" vehicle
    _test_comments( "croatian", "vehicles", "Komsomolet(r)", [
        ( None, "| Russian ESB |" ),
        ( None, "! Black TH#" ),
    ] )

    # test an "(t)" vehicle
    _test_comments( "croatian", "vehicles", "LT vz 38(t)A", [
        ( None, "| Czech ESB |" ),
        ( None, "! Black TH#" ),
    ] )
    _test_comments( "slovakian", "vehicles", "LT vz 38(t)A", [
        ( None, "| Czech ESB |" ),
        ( None, "Black TH#" ),
    ] )

# ---------------------------------------------------------------------

def test_axis_minor_ord_e( webapp, webdriver ):
    """Test Axis Minor Ordnance Note E."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1,
        reset = lambda ct: ct.set_data_dir( dtype="real" )
    )

    # test a "(g)" gun
    _test_comments( "romanian", "ordnance", "leFH 18(g)", [
        ( None, "Black TH#" ),
    ] )
    _test_comments( "croatian", "ordnance", "leFH 18(g)", [
        ( None, "! Black TH#" ),
    ] )

    # test a "(t)" gun
    _test_comments( "romanian", "ordnance", "Kanon PUV vz. 37(t)", [
        ( None, "Black TH#" ),
    ] )
    _test_comments( "bulgarian", "ordnance", "Kanon PUV vz. 37(t)", [
        ( None, "! Black TH#" ),
    ] )

# ---------------------------------------------------------------------

def _test_comments( nat, vo_type, vo_name, vals ):
    """ Generate and check comments for a series of dates. """

    # load the specified vehicle/ordnance
    new_scenario()
    load_scenario( {
        "PLAYER_1": nat,
        "OB_{}_1".format( vo_type.upper() ): [ { "name": vo_name } ]
    } )

    # check the generated comments for each specified date
    for date,expected in vals:
        set_scenario_date( date )
        select_tab( "ob1" )
        btn = find_child( "button[data-id='ob_{}_1']".format( vo_type ) )
        btn.click()
        if expected.startswith( "!" ):
            expected, contains = expected[1:].strip(), False
        else:
            contains = True
        wait_for_clipboard( 2, expected, transform=_extract_comments, contains=contains )

def _extract_comments( snippet ):
    """Extract comments from a snippet."""
    vals = [
        mo.group( 1 ).strip()
        for mo in re.finditer( r'<div class="comment">\s*?<nobr>\s*?(.*?)</nobr>\s*</div>', snippet )
    ]
    if not vals:
        return vals
    return "| {} |".format( " | ".join( vals ) )
