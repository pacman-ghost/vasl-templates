""" Test snippet generation for capabilities. """

from vasl_templates.webapp.tests.utils import \
    init_webapp, select_tab, new_scenario, load_scenario_params, \
    find_child, wait_for_clipboard

# ---------------------------------------------------------------------

def test_month_capabilities( webapp, webdriver ):
    """Test date-based capabilities that change in the middle of a year."""

    # initialize
    init_webapp( webapp, webdriver )

    # Sherman III(a): WP6(J4+)† s8
    load_scenario_params( {
        "scenario": {
            "PLAYER_1": "russian",
        },
        "ob1": {
            "OB_VEHICLES_1": [ "Sherman III(a)" ],
        }
    } )
    _check_snippet( None, "01/01/1943", "vehicles", '"s8"' )
    _check_snippet( None, "05/31/1944", "vehicles", '"s8"' )
    _check_snippet( None, "06/01/1944", "vehicles", '"WP6\u2020" "s8"' )
    _check_snippet( None, "01/01/1945", "vehicles", '"WP6\u2020" "s8"' )

    # Churchill III(b): D6(J4)/7(5)† ; HE7(F3)/8(4+)† ; sD6(4+) ; sM8†
    new_scenario()
    load_scenario_params( {
        "scenario": {
            "PLAYER_1": "russian",
        },
        "ob1": {
            "OB_VEHICLES_1": [ "Churchill III(b)" ],
        }
    } )
    _check_snippet( None, "01/01/1942", "vehicles", '"sM8\u2020"' )
    _check_snippet( None, "01/31/1943", "vehicles", '"sM8\u2020"' )
    _check_snippet( None, "02/01/1943", "vehicles", '"HE7\u2020" "sM8\u2020"' )
    _check_snippet( None, "05/31/1944", "vehicles", '"HE8\u2020" "sD6" "sM8\u2020"' )
    _check_snippet( None, "06/01/1944", "vehicles", '"D6\u2020" "HE8\u2020" "sD6" "sM8\u2020"' )
    _check_snippet( None, "01/01/1945", "vehicles", '"D7\u2020" "HE8\u2020" "sD6" "sM8\u2020"' )

    # M3A1 37mm AT Gun: NT, QSU, C7(A2+)†1
    new_scenario()
    load_scenario_params( {
        "scenario": {
            "PLAYER_1": "american",
        },
        "ob1": {
            "OB_ORDNANCE_1": [ "M3A1 37mm AT Gun" ],
        }
    } )
    _check_snippet( None, "01/01/1941", "ordnance", '"NT" "QSU"' )
    _check_snippet( None, "07/31/1942", "ordnance", '"NT" "QSU"' )
    _check_snippet( None, "08/01/1942", "ordnance", '"NT" "QSU" "C7\u2020<sup>1</sup>"' )

    # M1 57mm AT Gun: NT, QSU, HE7(J4E)/7(5)†, D4(J4+E)†
    new_scenario()
    load_scenario_params( {
        "scenario": {
            "SCENARIO_THEATER": "ETO",
            "PLAYER_1": "american",
        },
        "ob1": {
            "OB_ORDNANCE_1": [ "M1 57mm AT Gun" ],
        }
    } )
    _check_snippet( None, "01/01/1943", "ordnance", '"NT" "QSU"' )
    _check_snippet( None, "05/31/1944", "ordnance", '"NT" "QSU"' )
    _check_snippet( None, "06/01/1944", "ordnance", '"NT" "QSU" "D4\u2020" "HE7\u2020"' )
    _check_snippet( None, "01/01/1945", "ordnance", '"NT" "QSU" "D4\u2020" "HE7\u2020"' )
    _check_snippet( "PTO", "01/01/1945", "ordnance", '"NT" "QSU"' )

# ---------------------------------------------------------------------

def test_scenario_theater( webapp, webdriver ):
    """Test ETO/PTO-only capabilities."""

    # initialize
    init_webapp( webapp, webdriver )

    # M2A1 105mm Howitzer: C7(4+P)†1
    load_scenario_params( {
        "scenario": {
            "PLAYER_1": "american",
        },
        "ob1": {
            "OB_ORDNANCE_1": [ "M2A1 105mm Howitzer" ],
        }
    } )
    _check_snippet( "ETO", "01/01/1940", "ordnance", '"NT" "H6" "WP8" "s7"' )
    _check_snippet( "ETO", "01/01/1944", "ordnance", '"NT" "H6" "WP8" "s7"' )
    _check_snippet( "ETO", "01/01/1945", "ordnance", '"NT" "H6" "WP8" "s7"' )
    _check_snippet( "PTO", "01/01/1940", "ordnance", '"NT" "H6" "WP8" "s7"' )
    _check_snippet( "PTO", "01/01/1944", "ordnance", '"NT" "C7\u2020<sup>1</sup>" "H6" "WP8" "s7"' )
    _check_snippet( "PTO", "01/01/1945", "ordnance", '"NT" "C7\u2020<sup>1</sup>" "H6" "WP8" "s7"' )

    # M3 105mm Howitzer: C7(P)†1
    new_scenario()
    load_scenario_params( {
        "scenario": {
            "PLAYER_1": "american",
        },
        "ob1": {
            "OB_ORDNANCE_1": [ "M3 105mm Howitzer" ],
        }
    } )
    _check_snippet( "ETO", "01/01/1940", "ordnance", '"NT" "H7" "WP8" "s7"' )
    _check_snippet( "PTO", "01/01/1940", "ordnance", '"NT" "C7\u2020<sup>1</sup>" "H7" "WP8" "s7"' )

    # NOTE: We do a bit of hackery for the APCR specification for the M10 GMC and M18 GMC,
    # to flag them as ETO-only, so we make sure everything's working properly here.

    # M10 GMC: A(E)5(A4)/6(5)†1
    new_scenario()
    load_scenario_params( {
        "scenario": {
            "PLAYER_1": "american",
        },
        "ob1": {
            "OB_VEHICLES_1": [ "M10 GMC" ],
        }
    } )
    _check_snippet( "ETO", "07/31/1944", "vehicles", '"sP5"' )
    _check_snippet( "ETO", "08/01/1944", "vehicles", '"A5\u2020<sup>1</sup>" "sP5"' )
    _check_snippet( "ETO", "01/01/1945", "vehicles", '"A6\u2020<sup>1</sup>" "s5" "sP5"' )
    _check_snippet( "other", "01/01/1945", "vehicles", '"s5" "sP5"' )

    # M18 GMC: A(E)5(4)/6(5)†1
    new_scenario()
    load_scenario_params( {
        "scenario": {
            "PLAYER_1": "american",
        },
        "ob1": {
            "OB_VEHICLES_1": [ "M18 GMC" ],
        }
    } )
    _check_snippet( "ETO", "12/31/1943", "vehicles", '"sP5"' )
    _check_snippet( "ETO", "01/01/1944", "vehicles", '"A5\u2020<sup>1</sup>" "sP5"' )
    _check_snippet( "ETO", "01/01/1945", "vehicles", '"A6\u2020<sup>1</sup>" "s5" "sP5"' )
    _check_snippet( "other", "01/01/1945", "vehicles", '"s5" "sP5"' )


# ---------------------------------------------------------------------

def _check_snippet( scenario_theater, scenario_date, vo_type, expected ):
    """Test snippet generation."""

    # update the scenario parameters
    params = {
        "scenario": {
            "SCENARIO_DATE": scenario_date,
        }
    }
    if scenario_theater:
        params["scenario"]["SCENARIO_THEATER"] = scenario_theater
    load_scenario_params( params )

    # generate and check the snippet
    select_tab( "ob1" )
    btn = find_child( "button.generate[data-id='ob_{}_1']".format( vo_type ) )
    btn.click()
    wait_for_clipboard( 2, "capabilities: {}".format(expected), contains=True )
