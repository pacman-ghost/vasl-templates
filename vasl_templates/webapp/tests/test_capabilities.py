""" Test snippet generation for capabilities. """

from vasl_templates.webapp.tests.utils import \
    init_webapp, select_tab, new_scenario, load_scenario_params, \
    find_child, wait_for_clipboard

# ---------------------------------------------------------------------

def test_scenario_theater( webapp, webdriver ):
    """Test ETO/PTO-only capabilities."""

    # initialize
    init_webapp( webapp, webdriver )

    def do_test( scenario_theater, scenario_date, expected ):
        """Test snippet generation."""
        load_scenario_params( {
            "scenario": {
                "SCENARIO_THEATER": scenario_theater,
                "SCENARIO_DATE": scenario_date,
            }
        } )
        select_tab( "ob1" )
        btn = find_child( "button.generate[data-id='ob_ordnance_1']" )
        btn.click()
        wait_for_clipboard( 2, "capabilities: {}".format(expected), contains=True )

    # M2A1 105mm Howitzer: C7(4+P)†1
    load_scenario_params( {
        "scenario": {
            "PLAYER_1": "american",
        },
        "ob1": {
            "OB_ORDNANCE_1": [ "M2A1 105mm Howitzer" ],
        }
    } )
    do_test( "ETO", "01/01/1940", '"NT" "H6" "WP8" "s7"')
    do_test( "ETO", "01/01/1944", '"NT" "H6" "WP8" "s7"')
    do_test( "ETO", "01/01/1945", '"NT" "H6" "WP8" "s7"')
    do_test( "PTO", "01/01/1940", '"NT" "H6" "WP8" "s7"')
    do_test( "PTO", "01/01/1944", '"NT" "C7" "H6" "WP8" "s7"')
    do_test( "PTO", "01/01/1945", '"NT" "C7" "H6" "WP8" "s7"')

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
    do_test( "ETO", "01/01/1940", '"NT" "H7" "WP8" "s7"')
    do_test( "PTO", "01/01/1940", '"NT" "C7" "H7" "WP8" "s7"')
