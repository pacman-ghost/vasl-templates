""" Test snippet generation for capabilities. """

import re

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.tests.utils import \
    init_webapp, select_menu_option, select_tab, click_dialog_button, \
    find_child, find_children, wait_for_clipboard, \
    set_scenario_date
from vasl_templates.webapp.tests import pytest_options
from vasl_templates.webapp.tests.test_vo_reports import get_vo_report
from vasl_templates.webapp.tests.test_vehicles_ordnance import add_vo
from vasl_templates.webapp.tests.test_scenario_persistence import save_scenario, load_scenario

_IGNORE_CAPABILITIES = [ "T", "NT", "ST" ]

# ---------------------------------------------------------------------

@pytest.mark.skipif( pytest_options.short_tests, reason="--short-tests specified" )
def test_month_capabilities( webapp, webdriver ): #pylint: disable=too-many-statements
    """Test date-based capabilities that change in the middle of a year."""

    # Sherman III(a): WP6(J4+)† s8
    vehicle = [ "russian", "vehicles", "Sherman III(a)" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "s8 CS 5 [brewup]" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "05/1944", "s8 CS 5 [brewup]" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "06/1944", "WP6[!] s8 CS 5 [brewup]" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "WP6[!] s8 CS 5 [brewup]" )

    # Churchill III(b): D6(J4)/7(5)† ; HE7(F3)/8(4+)† ; sD6(4+) ; sM8†
    vehicle = [ "russian", "vehicles", "Churchill III(b)" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1942", "sM8[!] CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1943", "sM8[!] CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "02/1943", "HE7[!] sM8[!] CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "05/1944", "HE8[!] sD6 sM8[!] CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "06/1944", "D6[!] HE8[!] sD6 sM8[!] CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "D7[!] HE8[!] sD6 sM8[!] CS 7" )

    # M3A1 37mm AT Gun: NT, C7(A2+)†1
    ordnance = [ "american", "ordnance", "M3A1 37mm AT Gun" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1941", "NT", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "07/1942", "NT", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "08/1942", "NT C7[!1]", (1,2) )

    # M1 57mm AT Gun: NT, HE7(J4E)/7(5)†, D4(J4+E)†
    ordnance = [ "american", "ordnance", "M1 57mm AT Gun" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1943", "NT", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "05/1944", "NT", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "06/1944", "NT D4[!] HE7[!]", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "06/1944", "NT", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1945", "NT D4[!] HE7[!]", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "01/1945", "NT HE7[!]", (1,2) )

    # M3: C7(A2+)†2
    vehicle = [ "american", "vehicles", "M3" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1941", "CS 4", (1,4) )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "07/1942", "CS 4", (1,4) )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "08/1942", "C7[!2] CS 4", (1,4) )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1943", "C7[!2] CS 4", (1,4) )

    # M4/M4A1/M4A2/M4A3: WP7(J4+)†3 s5(J4+) sM5(4+)
    for vo_name in ("M4","M4A1","M4A2","M4A3"):
        vehicle = [ "american", "vehicles", vo_name ]
        ref = "[!{}]".format( 2 if vo_name == "M4A2" else 3 )
        sM = 4 if vo_name == "M4A3" else 5
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "CS 5 [brewup]" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "05/1944", "sM{} CS 5 [brewup]".format(sM) )
        _check_capabilities( webdriver, webapp, *vehicle,
            "ETO", "06/1944", "WP7{} s5 sM{} CS 5 [brewup]".format(ref,sM)
        )
        _check_capabilities( webdriver, webapp, *vehicle,
            "ETO", "01/1945", "WP7{} s5 sM{} CS 5 [brewup]".format(ref,sM)
        )

    # M4A3E2 (L): A4(4)/5(5), s5(5)
    vehicle = [ "american", "vehicles", "M4A3E2 (L)" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "sM8 CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1944", "A4 sM8 CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1944", "A4 sM8 CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "A5 s5 sM8 CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1946", "sM8 CS 6" )

    # M4A1(76)W & M4A3(76)W: A4(A4)/5(5)†2, s5(5)
    for vo_name in ("M4A1(76)W","M4A3(76)W"):
        vehicle = [ "american", "vehicles", vo_name ]
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "sM8 CS 6" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "07/1944", "sM8 CS 6" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "08/1944", "A4[!2] sM8 CS 6" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "A5[!2] s5 sM8 CS 6" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1946", "sM8 CS 6" )

    # Sherman Crab: s5(J4+); WP7(J4+)†2
    vehicle = [ "american", "vehicles", "Sherman Crab" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "sM4 CS 5 [brewup]" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "05/1944", "sM4 CS 5 [brewup]" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "06/1944", "WP7[!2] s5 sM4 CS 5 [brewup]" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "WP7[!2] s5 sM4 CS 5 [brewup]" )

    # M8 HMC: C4(4+)†1
    vehicle = [ "american", "vehicles", "M8 HMC" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "H9 WP9 CS 5" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1944", "C4[!1] H9 WP9 CS 5" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "C4[!1] H9 WP9 CS 5" )

    # OML 2-in. Mortar: IR(2)+†
    ordnance = [ "british", "ordnance", "OML 2-in. Mortar" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1941", "s7", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1942", "IR[!] s7", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1943", "IR[!] s7", (1,2) )

    # OML 3-in. Mortar: IR(2)+†1
    ordnance = [ "british", "ordnance", "OML 3-in. Mortar" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1941", "NT WP7 s8[!]", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1942", "NT IR[!1] WP7 s8[!]", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1943", "NT IR[!1] WP7 s8[!]", (1,2) )

    # OQF 6-Pounder 7-cwt: D6(J4E)7(5)† HE7(F3)8(4+)†
    ordnance = [ "british", "ordnance", "OQF 6-Pounder 7-cwt" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1942", "NT" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1943", "NT" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "02/1943", "NT HE7[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "05/1944", "NT HE8[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "06/1944", "NT D6[!] HE8[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "06/1944", "NT HE8[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1945", "NT D7[!] HE8[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "01/1945", "NT D7[!] HE8[!]" )

    # OQF 17-Pounder: D5(S4)6(5)† HE8(J4+)†
    ordnance = [ "british", "ordnance", "OQF 17-Pounder" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1943", "NT", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "05/1944", "NT", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "06/1944", "NT HE8[!]", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "09/1944", "NT D5[!] HE8[!]", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1945", "NT D6[!] HE8[!]", (1,2) )

    # Crusader III: HE7(F3+)†1
    vehicle = [ "british", "vehicles", "Crusader III" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1942", "sD7 sM8[!2] CS 3 [brewup]" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1943", "sD7 sM8[!2] CS 3 [brewup]" )
    _check_capabilities( webdriver, webapp, *vehicle,
        "ETO", "02/1943", "HE7[!1] sD7 sM8[!2] CS 3 [brewup]"
    )
    _check_capabilities( webdriver, webapp, *vehicle,
        "ETO", "01/1944", "HE7[!1] sD7 sM8[!2] CS 3 [brewup]"
    )

    # Sherman II(a)/III(a)/V(a): WP6(J4+)†3
    for vo_name in ("Sherman II(a)","Sherman III(a)","Sherman V(a)"):
        vehicle = [ "british", "vehicles", vo_name ]
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "s8 sD6 CS 5 [brewup]" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "05/1944", "s8 sD6 CS 5 [brewup]" )
        _check_capabilities( webdriver, webapp, *vehicle,
            "ETO", "06/1944", "WP6[!3] s8 sD6 CS 5 [brewup]"
        )
        _check_capabilities( webdriver, webapp, *vehicle,
            "ETO", "01/1945", "WP6[!3] s8 sD6 CS 5 [brewup]"
        )

    # Sherman IIC(a)/VC(a): D5(S4)6(5)†2
    for vo_name in ("Sherman IIC(a)","Sherman VC(a)"):
        vehicle = [ "british", "vehicles", vo_name ]
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "HE7 sM8 CS 5 [brewup]" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "08/1944", "HE7 sM8 CS 5 [brewup]" )
        _check_capabilities( webdriver, webapp, *vehicle,
            "ETO", "09/1944", "D5[!2] HE7 sM8 CS 5 [brewup]"
        )
        _check_capabilities( webdriver, webapp, *vehicle,
            "ETO", "01/1945", "D6[!2] HE7 sM8 CS 5 [brewup]"
        )

    # Challenger: D5(S4)6(5)†1
    vehicle = [ "british", "vehicles", "Challenger" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "HE7 sD7 sM8[!2] CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "08/1944", "HE7 sD7 sM8[!2] CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle,
        "ETO", "09/1944", "D5[!1] HE7 sD7 sM8[!2] CS 6"
    )
    _check_capabilities( webdriver, webapp, *vehicle,
        "ETO", "01/1945", "D6[!1] HE7 sD7 sM8[!2] CS 6"
    )

    # Churchill IV: D6(J4)7(5)†2 HE7(F3)8(4)+†1 sD6(4+)
    vehicle = [ "british", "vehicles", "Churchill IV" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1942", "sM8[!3] CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1943", "sM8[!3] CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle,
        "ETO", "02/1943", "HE7[!1] sM8[!3] CS 7"
    )
    _check_capabilities( webdriver, webapp, *vehicle,
        "ETO", "05/1944", "HE8[!1] sD6 sM8[!3] CS 7"
    )
    _check_capabilities( webdriver, webapp, *vehicle,
        "ETO", "06/1944", "D6[!2] HE8[!1] sD6 sM8[!3] CS 7"
    )
    _check_capabilities( webdriver, webapp, *vehicle,
        "ETO", "01/1945", "D7[!2] HE8[!1] sD6 sM8[!3] CS 7"
    )

    # Churchill VI: WP6(J4+)†1
    vehicle = [ "british", "vehicles", "Churchill VI" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "s8 sD7 sM8[!2] CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "05/1944", "s8 sD7 sM8[!2] CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle,
        "ETO", "06/1944", "WP6[!1] s8 sD7 sM8[!2] CS 7"
    )
    _check_capabilities( webdriver, webapp, *vehicle,
        "ETO", "01/1945", "WP6[!1] s8 sD7 sM8[!2] CS 7"
    )

    # Deacon: HE7(F3+)†2
    vehicle = [ "british", "vehicles", "Deacon" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1942", "CS 5" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1943", "CS 5" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "02/1943", "HE7[!2] CS 5" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1944", "HE7[!2] CS 5" )

    # Wolverine(a): A5(S4)6(5)†1 s5(5)
    vehicle = [ "british", "vehicles", "Wolverine(a)" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "HE7 CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "08/1944", "HE7 CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "09/1944", "A5[!1] HE7 CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "A6[!1] HE7 s5 CS 7" )

    # Achilles(a): D6(S4)7(5)†1
    vehicle = [ "british", "vehicles", "Achilles(a)" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "HE7 CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "08/1944", "HE7 CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "09/1944", "D6[!1] HE7 CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "D7[!1] HE7 CS 7" )

    # AEC II: D6(J4)7(5)†2 HE7(3)8(4)+†1
    vehicle = [ "british", "vehicles", "AEC II" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1942", "sM8 CS 4" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1943", "HE7[!1] sM8 CS 4" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "05/1944", "HE8[!1] sM8 CS 4" )
    _check_capabilities( webdriver, webapp, *vehicle,
        "ETO", "06/1944", "D6[!2] HE8[!1] sM8 CS 4"
    )
    _check_capabilities( webdriver, webapp, *vehicle,
        "ETO", "01/1945", "D7[!2] HE8[!1] sM8 CS 4"
    )

    # M3 GMC(a): WP7(J4+)†1
    vehicle = [ "british", "vehicles", "M3 GMC(a)" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "s8 CS 4" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "05/1944", "s8 CS 4" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "06/1944", "WP7[!1] s8 CS 4" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "WP7[!1] s8 CS 4" )

    # Cannone da 65/17, 75/27, 75/32 + Obice da 75/18: H6(S2+)†1
    for vo_name in ("Cannone da 65/17", "Cannone da 75/27","Cannone da 75/32","Obice da 75/18"):
        ordnance = [ "italian", "ordnance", vo_name ]
        val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1941" )
        assert "H6" not in val
        assert _get_capabilities( webdriver, webapp, *ordnance, "ETO", "08/1942" ) == val
        val2 = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "09/1942" )
        assert "H6[!1]" in val2
        assert _get_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1943" ) == val2

    # SMV M40 75/18, SMV M41 75/18, Autocann 65/17(b): H7(S2+)†2
    for vo_name in ("SMV M40 75/18", "SMV M41 75/18", "Autocann 65/17(b)"):
        vehicle = [ "italian", "vehicles", vo_name ]
        val = _get_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1941" )
        assert "H7" not in val
        assert _get_capabilities( webdriver, webapp, *vehicle, "ETO", "08/1942" ) == val
        val2 = _get_capabilities( webdriver, webapp, *vehicle, "ETO", "09/1942" )
        assert "H7[!2]" in val2
        assert _get_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1943" ) == val2

    # M4A4(a): WP7(J4+)†
    vehicle = [ "chinese", "vehicles", "M4A4(a)" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "s8 CS 5 [brewup]" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "05/1944", "s8 CS 5 [brewup]" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "06/1944", "WP7[!] s8 CS 5 [brewup]" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "WP7[!] s8 CS 5 [brewup]" )

    # 81 Krh/32: s8(N1+)†
    ordnance = [ "finnish", "ordnance", "81 Krh/32" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1940", "NT" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "10/1941", "NT" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "11/1941", "NT s8[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1942", "NT s8[!]" )

    # 76 RK/27(r): H6J4+†
    ordnance = [ "finnish", "ordnance", "76 RK/27(r)" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1943", "NT s6" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "05/1944", "NT s6" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "06/1944", "NT H6[!] s6" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1945", "NT H6[!] s6" )

    # 105 H/33(g) ; 105 H/41(t): H6A4+†
    for vo_name in ("105 H/33(g)","105 H/41(t)"):
        ordnance = [ "finnish", "ordnance", vo_name ]
        val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1943" )
        assert "H6" not in val
        assert _get_capabilities( webdriver, webapp, *ordnance, "ETO", "07/1944" ) == val
        val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "08/1944" )
        assert "H6[!]" in val
        assert _get_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1945" ) == val

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@pytest.mark.skipif( pytest_options.short_tests, reason="--short-tests specified" )
def test_kfw( webapp, webdriver ):
    """Test date-based capabilities for K:FW vehicles/ordnance."""

    # M26A1: WP6(M51+)†2
    vehicle = [ "american", "vehicles", "M26A1" ]
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "12/1950", "A[!1] CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "02/1951", "A[!1] CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "03/1951", "A[!1] WP6[!2] CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1952", "A[!1] WP6[!2] CS 6" )

    # M46: WP6(M51+)†3
    vehicle = [ "american", "vehicles", "M46" ]
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "12/1950", "A[!2] CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "02/1951", "A[!2] CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "03/1951", "A[!2] WP6[!3] CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1952", "A[!2] WP6[!3] CS 6" )

# ---------------------------------------------------------------------

@pytest.mark.skipif( pytest_options.short_tests, reason="--short-tests specified" )
def test_theater_capabilities( webapp, webdriver ):
    """Test theater-specific capabilities."""

    # M2A1 105mm Howitzer: C7(4+P)†1
    ordnance = [ "american", "ordnance", "M2A1 105mm Howitzer" ]
    _check_capabilities( webdriver, webapp, *ordnance , "ETO", "12/1943", "NT H6 WP8 s7", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance , "ETO", "01/1944", "NT H6 WP8 s7", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance , "ETO", "01/1945", "NT H6 WP8 s7", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance , "PTO", "12/1943", "NT H6 WP8 s7", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance , "PTO", "01/1944", "NT C7[!1] H6 WP8 s7", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance , "PTO", "01/1945", "NT C7[!1] H6 WP8 s7", (1,2) )

    # M3 105mm Howitzer: C7(P)†1
    ordnance = [ "american", "ordnance", "M3 105mm Howitzer" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1940", "NT H7 WP8 s7", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "01/1940", "NT C7[!1] H7 WP8 s7", (1,2) )

    # M2A4: C10(P)†1
    vehicle = [ "american", "vehicles", "M2A4" ]
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1940", "C10[!1] CS 4" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1940", "CS 4" )

    # M4(105) & M4A3(105): C7P†1
    for vo_name in ("M4(105)","M4A3(105)"):
        vehicle = [ "american", "vehicles", vo_name ]
        _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1940", "C7[!1] H9 WP9 s7 sM8 CS 6" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1940", "H9 WP9 s7 sM8 CS 6" )

    # NOTE: We do a bit of hackery for the APCR specification for the M10 GMC and M18 GMC,
    # to flag them as ETO-only, so we make sure everything's working properly here.

    # M10 GMC: A(E)5(A4)/6(5)†1
    vehicle = [ "american", "vehicles", "M10 GMC" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "sP5 CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "07/1944", "sP5 CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "08/1944", "A5[!1] sP5 CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "A6[!1] s5 sP5 CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "other", "01/1945", "s5 sP5 CS 7" )

    # M18 GMC: A(E)5(4)/6(5)†1
    vehicle = [ "american", "vehicles", "M18 GMC" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "sP5 CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1944", "A5[!1] sP5 CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "A6[!1] s5 sP5 CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "other", "01/1945", "s5 sP5 CS 6" )

    # M7 HMC: C7(P)†1
    vehicle = [ "american", "vehicles", "M7 HMC" ]
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1940", "C7[!1] H7 WP8 s7 CS 7", (1,2) )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1940", "H7 WP8 s7 CS 7", (1,2) )

    # LVT(A)1: C10(P)†2
    vehicle = [ "american", "vehicles", "LVT(A)1" ]
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1940", "C10[!2] CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1940", "CS 6" )

    # LVT(A)4: C7(P)†3
    vehicle = [ "american", "vehicles", "LVT(A)4" ]
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1940", "C7[!3] H8 WP9 CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1940", "H8 WP9 CS 6" )

    # OQF 3.7-in. Howitzer: H6(3+P)†
    ordnance = [ "british", "ordnance", "OQF 3.7-in. Howitzer" ]
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "12/1942", "NT WP7 s8" )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "01/1943", "NT H6[!] WP7 s8" )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "01/1944", "NT H6[!] WP7 s8" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1944", "NT WP7 s8" )

    # Obice da 149/13: WP6(B)
    ordnance = [ "chinese", "ordnance", "Obice da 149/13" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1940", "NT s5" )
    _check_capabilities( webdriver, webapp, *ordnance, "Burma", "01/1940", "NT WP6[!] s5" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@pytest.mark.skipif( pytest_options.short_tests, reason="--short-tests specified" )
def test_theater_capabilities_bfp( webapp, webdriver ):
    """Test theater-specific capabilities (BFP extension)."""

    # initialize
    webapp.control_tests \
        .set_data_dir( "{REAL}" ) \
        .set_vasl_version( "random", "{REAL}" )
    init_webapp( webapp, webdriver )

    # LVT(A)1(L): C10(P)†2
    vehicle = [ "american", "vehicles", "LVT(A)1(L)" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1940", "CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1940", "C10[!2] CS 6" )

    # LVT(A)4(L): C7(P)†3
    vehicle = [ "american", "vehicles", "LVT(A)4(L)" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1940", "H8 WP9 CS 6" )
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1940", "C7[!3] H8 WP9 CS 6" )

    # M3A1F: C7(P)†
    vehicle = [ "american", "vehicles", "M3A1F" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1940", "CS 4" )
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1940", "C7[!] CS 4" )

# ---------------------------------------------------------------------

@pytest.mark.skipif( pytest_options.short_tests, reason="--short-tests specified" )
def test_american_ordnance_note_c( webapp, webdriver ):
    """Test handling of American Ordnance Note C."""

    # M3A1 37mm AT Gun: C7[A2+]†[1]
    ordnance = [ "american", "ordnance", "M3A1 37mm AT Gun" ]
    _check_capabilities( webdriver, webapp, *ordnance , "ETO", "07/1942", "", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance , "PTO", "07/1942", "", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance , "ETO", "08/1942", "C7[!1]", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance , "PTO", "08/1942", "C10[!1]", (1,2) ) # nb: C# += 3

    # M2A1 105mm Howitzer: C7[4+P]†[1] H6 WP8 s7
    ordnance = [ "american", "ordnance", "M2A1 105mm Howitzer" ]
    _check_capabilities( webdriver, webapp, *ordnance , "ETO", "12/1943", "H6 WP8 s7", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance , "PTO", "12/1943", "H6 WP8 s7", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance , "ETO", "01/1944", "H6 WP8 s7", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance , "PTO", "01/1944", "C7[!1] H6 WP8 s7", (1,2) ) # nb: no += 3

    # M3 105mm Howitzer: C7[P]†[1] H7 WP8 s7
    ordnance = [ "american", "ordnance", "M3 105mm Howitzer" ]
    _check_capabilities( webdriver, webapp, *ordnance , "ETO", "01/1940", "H7 WP8 s7", (1,2) )
    _check_capabilities( webdriver, webapp, *ordnance , "PTO", "01/1940", "C7[!1] H7 WP8 s7", (1,2) ) # nb: no += 3

# ---------------------------------------------------------------------

@pytest.mark.skipif( pytest_options.short_tests, reason="--short-tests specified" )
def test_nationality_capabilities( webapp, webdriver ):
    """Test nationality-specific capabilities."""

    # G obr. 38:  s5(1-2R)†
    ordnance = [ "romanian", "ordnance", "G obr. 38" ]
    val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1940", merge_common=True )
    assert "s5[!]" not in val
    val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1941", merge_common=True )
    assert "s5[!]" in val
    ordnance = [ "slovakian", "ordnance", "G obr. 38" ]
    val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1941", merge_common=True )
    assert "s5[!]" not in val

    # Skoda M35: C7(CS)†
    ordnance = [ "croatian", "ordnance", "Skoda M35" ]
    val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1940", merge_common=True )
    assert "C7[!]" in val
    ordnance = [ "slovakian", "ordnance", "Skoda M35" ]
    val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1940", merge_common=True )
    assert "C7[!]" in val
    ordnance = [ "bulgarian", "ordnance", "Skoda M35" ]
    val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1940", merge_common=True )
    assert "C7[!]" not in val

    # Kanon PUV vz. 37(t): A4(1S)
    ordnance = [ "slovakian", "ordnance", "Kanon PUV vz. 37(t)" ]
    val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1940", merge_common=True )
    assert "A4" not in val
    val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1941", merge_common=True )
    assert "A4" in val
    ordnance = [ "croatian", "ordnance", "Kanon PUV vz. 37(t)" ]
    val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1941", merge_common=True )
    assert "A4" not in val

# ---------------------------------------------------------------------

def test_custom_capabilities( webapp, webdriver ): #pylint: disable=too-many-statements
    """Test custom capabilities."""

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # add a vehicle
    add_vo( webdriver, "vehicles", 1, "another german vehicle" )

    snippet_btn = find_child( "button[data-id='ob_vehicles_1']" )
    def extract_capabilities( clipboard ):
        """Extract the capabilities."""
        mo = re.search( r"^- capabilities: (.*)$", clipboard, re.MULTILINE )
        return mo.group(1) if mo else ""
    def check_snippet( expected ):
        """Check the vehicle's snippet."""
        snippet_btn.click()
        wait_for_clipboard( 2, expected, transform=extract_capabilities )
    def check_capabilities_in_dialog( expected ):
        """Check the vehicle's capabilities."""
        elems = find_children( "#vo_capabilities-sortable li" )
        elems2 = [ find_child("input[type='text']",c) for c in elems ]
        assert [ e.get_attribute("value") for e in elems2 ] == expected
        return elems

    # check the vehicle's snippet
    check_snippet( '"XYZ" "<span class=\'brewup\'>cs 4</span>"' )

    # edit the vehicle's capabilities
    vehicles_sortable = find_child( "#ob_vehicles-sortable_1" )
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 1
    ActionChains( webdriver ).double_click( elems[0] ).perform()
    elems = check_capabilities_in_dialog( [ "XYZ", "<span class='brewup'>cs 4</span>" ] )

    # edit one of the capabilities
    elem = find_child( "input[type='text']", elems[0] )
    elem.clear()
    elem.send_keys( "XYZ (modified)" )

    # delete a capability
    ActionChains( webdriver ).key_down( Keys.CONTROL ).click( elems[1] ).perform()
    ActionChains( webdriver ).key_up( Keys.CONTROL ).perform()

    # add a new capability
    elem = find_child( "#vo_capabilities-add" )
    elem.click()
    elems = find_children( "#vo_capabilities-sortable input[type='text']" )
    assert len(elems) == 2
    elems[1].send_keys( "a <i>new</i> capability" )

    # save the changes and check the vehicle's snippet
    click_dialog_button( "OK" )
    check_snippet( '"XYZ (modified)" "a <i>new</i> capability"' )

    # save the scenario
    saved_scenario = save_scenario()
    assert len(saved_scenario["OB_VEHICLES_1"]) == 1
    assert saved_scenario["OB_VEHICLES_1"][0]["custom_capabilities"] == [ "XYZ (modified)", "a <i>new</i> capability" ]

    # reload the scenario, and check the vehicle's snippet
    select_menu_option( "new_scenario" )
    load_scenario( saved_scenario )
    select_tab( "ob1" )
    check_snippet( '"XYZ (modified)" "a <i>new</i> capability"' )

    # make sure the capabilities are loaded correcly when editing the vehicle
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 1
    ActionChains( webdriver ).double_click( elems[0] ).perform()
    elems = check_capabilities_in_dialog( [ "XYZ (modified)", "a <i>new</i> capability" ] )

    # delete all capabilities
    for elem in elems:
        ActionChains( webdriver ).key_down( Keys.CONTROL ).click( elem ).perform()
        ActionChains( webdriver ).key_up( Keys.CONTROL ).perform()
    click_dialog_button( "OK" )
    check_snippet( "" )

    # save the scenario
    saved_scenario2 = save_scenario()
    assert len(saved_scenario2["OB_VEHICLES_1"]) == 1
    assert saved_scenario2["OB_VEHICLES_1"][0]["custom_capabilities"] == []

    # reload the scenario, and reset the vehicle's capabilities back to the default
    load_scenario( saved_scenario )
    select_tab( "ob1" )
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 1
    ActionChains( webdriver ).double_click( elems[0] ).perform()
    btn = find_child( "#vo_capabilities-reset" )
    btn.click()
    click_dialog_button( "OK" )
    check_snippet( '"XYZ" "<span class=\'brewup\'>cs 4</span>"' )

    # make sure the custom capabilities are no longer saved in the scenario
    saved_scenario2 = save_scenario()
    assert len(saved_scenario2["OB_VEHICLES_1"]) == 1
    assert "custom_capabilities" not in saved_scenario2["OB_VEHICLES_1"][0]

    # reload the scenario, and manually set the vehicle's capabilities to be the same as the default
    load_scenario( saved_scenario )
    select_tab( "ob1" )
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 1
    ActionChains( webdriver ).double_click( elems[0] ).perform()
    elems = find_children( "#vo_capabilities-sortable input[type='text']" )
    assert len(elems) == 2
    elems[0].clear()
    elems[0].send_keys( "XYZ" )
    elems[1].clear()
    elems[1].send_keys( "<span class='brewup'>cs 4</span>" )
    click_dialog_button( "OK" )

    # make sure the custom capabilities are no longer saved in the scenario
    saved_scenario = save_scenario()
    assert len(saved_scenario["OB_VEHICLES_1"]) == 1
    assert "custom_capabilities" not in saved_scenario["OB_VEHICLES_1"][0]

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def test_custom_comments( webapp, webdriver ): #pylint: disable=too-many-statements
    """Test custom comments."""

    # NOTE: Vehicle/ordnance comments are not capabilities, but they are managed in the same place
    # and the code is virtually identical, so it makes sense to put the test code here.

    # initialize
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # add a vehicle
    add_vo( webdriver, "vehicles", 1, "a commented german vehicle" )

    snippet_btn = find_child( "button[data-id='ob_vehicles_1']" )
    def extract_comments( clipboard ):
        """Extract the comments."""
        mo = re.search( r"^- comments: (.*)$", clipboard, re.MULTILINE )
        return mo.group(1) if mo else ""
    def check_snippet( expected ):
        """Check the vehicle's snippet."""
        snippet_btn.click()
        wait_for_clipboard( 2, expected, transform=extract_comments )
    def check_comments_in_dialog( expected ):
        """Check the vehicle's comments."""
        elems = find_children( "#vo_comments-sortable li" )
        elems2 = [ find_child("input[type='text']",c) for c in elems ]
        assert [ e.get_attribute("value") for e in elems2 ] == expected
        return elems

    # check the vehicle's snippet
    check_snippet( '"a comment" "another comment"' )

    # edit the vehicle's comments
    vehicles_sortable = find_child( "#ob_vehicles-sortable_1" )
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 1
    ActionChains( webdriver ).double_click( elems[0] ).perform()
    elems = check_comments_in_dialog( [ "a comment", "another comment" ] )

    # edit one of the comments
    elem = find_child( "input[type='text']", elems[0] )
    elem.clear()
    elem.send_keys( "a comment (modified)" )

    # delete a comment
    ActionChains( webdriver ).key_down( Keys.CONTROL ).click( elems[1] ).perform()
    ActionChains( webdriver ).key_up( Keys.CONTROL ).perform()

    # add a new comment
    elem = find_child( "#vo_comments-add" )
    elem.click()
    elems = find_children( "#vo_comments-sortable input[type='text']" )
    assert len(elems) == 2
    elems[1].send_keys( "a <i>new</i> comment" )

    # save the changes and check the vehicle's snippet
    click_dialog_button( "OK" )
    check_snippet( '"a comment (modified)" "a <i>new</i> comment"' )

    # save the scenario
    saved_scenario = save_scenario()
    assert len(saved_scenario["OB_VEHICLES_1"]) == 1
    assert saved_scenario["OB_VEHICLES_1"][0]["custom_comments"] == [ "a comment (modified)", "a <i>new</i> comment" ]

    # reload the scenario, and check the vehicle's snippet
    select_menu_option( "new_scenario" )
    load_scenario( saved_scenario )
    select_tab( "ob1" )
    check_snippet( '"a comment (modified)" "a <i>new</i> comment"' )

    # make sure the comments are loaded correcly when editing the vehicle
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 1
    ActionChains( webdriver ).double_click( elems[0] ).perform()
    elems = check_comments_in_dialog( [ "a comment (modified)", "a <i>new</i> comment" ] )

    # delete all comments
    for elem in elems:
        ActionChains( webdriver ).key_down( Keys.CONTROL ).click( elem ).perform()
        ActionChains( webdriver ).key_up( Keys.CONTROL ).perform()
    click_dialog_button( "OK" )
    check_snippet( "" )

    # save the scenario
    saved_scenario2 = save_scenario()
    assert len(saved_scenario2["OB_VEHICLES_1"]) == 1
    assert saved_scenario2["OB_VEHICLES_1"][0]["custom_comments"] == []

    # reload the scenario, and reset the vehicle's comments back to the default
    load_scenario( saved_scenario )
    select_tab( "ob1" )
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 1
    ActionChains( webdriver ).double_click( elems[0] ).perform()
    btn = find_child( "#vo_comments-reset" )
    btn.click()
    click_dialog_button( "OK" )
    check_snippet( '"a comment" "another comment"' )

    # make sure the custom comments are no longer saved in the scenario
    saved_scenario2 = save_scenario()
    assert len(saved_scenario2["OB_VEHICLES_1"]) == 1
    assert "custom_comments" not in saved_scenario2["OB_VEHICLES_1"][0]

    # reload the scenario, and manually set the vehicle's comments to be the same as the default
    load_scenario( saved_scenario )
    select_tab( "ob1" )
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 1
    ActionChains( webdriver ).double_click( elems[0] ).perform()
    elems = find_children( "#vo_comments-sortable input[type='text']" )
    assert len(elems) == 2
    elems[0].clear()
    elems[0].send_keys( "a comment" )
    elems[1].clear()
    elems[1].send_keys( "another comment" )
    click_dialog_button( "OK" )

    # make sure the custom comments are no longer saved in the scenario
    saved_scenario = save_scenario()
    assert len(saved_scenario["OB_VEHICLES_1"]) == 1
    assert "custom_comments" not in saved_scenario["OB_VEHICLES_1"][0]

# ---------------------------------------------------------------------

def test_capability_updates_in_ui( webapp, webdriver ):
    """Check that capabilities are updated in the UI correctly."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # load the scenario
    scenario_data = {
        "PLAYER_1": "german",
        "OB_VEHICLES_1": [ { "name": "PzKpfw 38(t)A" } ], # A4[1]/5[2] ; sD6 ; CS 4
        "OB_ORDNANCE_1": [ { "name": "3.7cm PaK 35/36" } ], # NT ; A4[1]/5[2]/4[3]/3[4] ; H6[9]†
        "PLAYER_2": "russian",
        "OB_VEHICLES_2": [ { "name": "Churchill III(b)" } ], # D6[J4]/7[5]† ; HE7[F3]/8[4+]† ; sD6[4+] ; sM8† ; CS 7
        "OB_ORDNANCE_2": [ { "name": "45mm PTP obr. 32" } ], # NT ; A4[2]/5[3]/6[4]/7[5]
    }
    scenario_data["OB_VEHICLES_1"].append( { "name": "PzJg I" } ) # A5[1]/6[2]/5[3]; HE7 ; CS 3
    load_scenario( scenario_data )

    sortables = [
        find_child( "#ob_vehicles-sortable_1" ),
        find_child( "#ob_ordnance-sortable_1" ),
        find_child( "#ob_vehicles-sortable_2" ),
        find_child( "#ob_ordnance-sortable_2" ),
    ]
    def check_capabilities( scenario_date, expected ):
        """Get the vehicle/ordnance capabilities from the UI."""
        # set the scenario date
        set_scenario_date( scenario_date )
        # check the vehicle/ordnance capabilities
        results = []
        for sortable in sortables:
            results.append( [] )
            vo_entries = find_children( "li", sortable )
            for vo_entry in vo_entries:
                capabilities = find_children( "span.vo-capability", vo_entry )
                results[-1].append( [ c.get_attribute("innerHTML") for c in capabilities ] )
        for row in expected:
            for i,entries in enumerate(row):
                row[i] = [ e for e in entries if e not in _IGNORE_CAPABILITIES ]
        assert results == expected

    # no scenario date => we should be showing the raw capabilities
    check_capabilities( None, [
        [
            [ "A4<sup>1</sup>5<sup>2</sup>", "sD6", "CS 4" ],
            [ "A5<sup>1</sup>6<sup>2</sup>5<sup>3</sup>", "HE7", "CS 3" ]
        ],
        [ [ "NT", "A4<sup>1</sup>5<sup>2</sup>4<sup>3</sup>3<sup>4</sup>", "H6[9]\u2020" ] ],
        [ [ "D6<sup>J4</sup>7<sup>5</sup>†", "HE7<sup>F3</sup>8<sup>4+</sup>\u2020", "sD6<sup>4+</sup>", "sM8\u2020", "CS 7" ] ], #pylint: disable=line-too-long
        [ [ "NT", "A4<sup>2</sup>5<sup>3</sup>6<sup>4</sup>7<sup>5</sup>" ] ]
    ] )

    # edit the PzJg I's capabilities (nb: this locks them in, and they should not change
    # regardless of what the scenario date is set to)
    select_tab( "ob1" )
    vehicles_sortable = find_child( "#ob_vehicles-sortable_1" )
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 2
    ActionChains( webdriver ).double_click( elems[1] ).perform()
    elem = find_child( "#vo_capabilities-add" )
    elem.click()
    elems = find_children( "#vo_capabilities-sortable input[type='text']" )
    assert len(elems) == 4
    elems[3].send_keys( "foo!" )
    click_dialog_button( "OK" )

    # change the scenario date, check the capabilities
    select_tab( "scenario" )
    check_capabilities( "01/01/1940", [
        [
            [ "sD6", "CS 4" ],
            [ "A5<sup>1</sup>6<sup>2</sup>5<sup>3</sup>", "HE7", "CS 3", "foo!" ]
        ],
        [ [ "NT", "H6[9]\u2020" ] ],
        [ [ "sM8\u2020", "CS 7" ] ],
        [ [ "NT" ] ]
    ] )
    check_capabilities( "01/01/1941", [
        [
            [ "A4", "sD6", "CS 4" ] ,
            [ "A5<sup>1</sup>6<sup>2</sup>5<sup>3</sup>", "HE7", "CS 3", "foo!" ]
        ],
        [ [ "NT", "A4", "H6[9]\u2020" ] ],
        [ [ "sM8\u2020", "CS 7" ] ],
        [ [ "NT" ] ]
    ] )
    check_capabilities( "01/01/1942", [
        [
            [ "A5", "sD6", "CS 4" ],
            [ "A5<sup>1</sup>6<sup>2</sup>5<sup>3</sup>", "HE7", "CS 3", "foo!" ]
        ],
        [ [ "NT", "A5", "H6[9]\u2020" ] ],
        [ [ "sM8\u2020", "CS 7" ] ],
        [ [ "NT", "A4" ] ]
    ] )
    check_capabilities( "01/01/1943", [
        [
            [ "sD6", "CS 4" ],
            [ "A5<sup>1</sup>6<sup>2</sup>5<sup>3</sup>", "HE7", "CS 3", "foo!" ]
        ],
        [ [ "NT", "A4", "H6[9]\u2020" ] ],
        [ [ "sM8\u2020", "CS 7" ] ],
        [ [ "NT", "A5" ] ]
    ] )
    check_capabilities( "01/01/1944", [
        [
            [ "sD6", "CS 4" ],
            [ "A5<sup>1</sup>6<sup>2</sup>5<sup>3</sup>", "HE7", "CS 3", "foo!" ]
        ],
        [ [ "NT", "A3", "H6[9]\u2020" ] ],
        [ [ "HE8\u2020", "sD6", "sM8\u2020", "CS 7" ] ],
        [ [ "NT", "A6" ] ]
    ] )
    check_capabilities( "01/01/1945", [
        [
            [ "sD6", "CS 4" ],
            [ "A5<sup>1</sup>6<sup>2</sup>5<sup>3</sup>", "HE7", "CS 3", "foo!" ]
        ],
        [ [ "NT", "H6[9]\u2020" ] ],
        [ [ "D7\u2020", "HE8\u2020", "sD6", "sM8\u2020", "CS 7" ] ],
        [ [ "NT", "A7" ] ]
    ] )

# ---------------------------------------------------------------------

def test_elite( webapp, webdriver ): #pylint: disable=too-many-statements
    """Test elite vehicles/ordnance."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    def get_sortable_elem():
        """Find the sortable element for the test vehicle."""
        sortable = find_child( "#ob_vehicles-sortable_1" )
        elems = find_children( "li", sortable )
        assert len(elems) == 1
        return elems[0]
    def check_elite( expected, custom ):
        """Check the elite status of the vehicle in the main UI."""
        vo_name = find_child( ".vo-name", get_sortable_elem() ).text
        caps = [ c.text for c in find_children(".vo-capability",get_sortable_elem()) ]
        if expected:
            assert vo_name.endswith( "\u24ba" )
            expected = [ "H9", "s10", "sD7", "CS 5" ]
            if custom:
                expected.append( "HE11" )
            assert caps == expected
        else:
            assert "\u24ba" not in vo_name
            expected = [ "H8", "s9", "sD7", "CS 5" ]
            if custom:
                expected.append( "HE10" )
            assert caps == expected
    def check_elite2( expected, custom ):
        """Check the elite status of the vehicle in the edit dialog."""
        vo_name = find_child( "#edit-vo .header .vo-name" ).text
        caps = [ c.get_attribute("value") for c in find_children("#vo_capabilities-sortable input[type='text']") ]
        if expected:
            assert vo_name.endswith( "\u24ba" )
            expected = [ "H9", "s10", "sD7", "CS 5" ]
            if custom:
                expected.append( "HE11" )
            assert caps == expected
        else:
            assert "\u24ba" not in vo_name
            expected = [ "H8", "s9", "sD7", "CS 5" ]
            if custom:
                expected.append( "HE10" )
            assert caps == expected

    # load the scenario
    scenario_data = {
        "PLAYER_1": "german",
        "OB_VEHICLES_1": [ { "name": "PSW 233" } ], # H8 s9 sD7 CS 5
    }
    load_scenario( scenario_data )
    select_tab( "ob1" )

    # check that the vehicle was loaded non-elite
    check_elite( False, False )

    # add a custom capability
    ActionChains( webdriver ).double_click( get_sortable_elem() ).perform()
    elem = find_child( "#vo_capabilities-add" )
    elem.click()
    elems = find_children( "#vo_capabilities-sortable input[type='text']" )
    assert len(elems) == 5
    elems[4].send_keys( "HE10" )
    click_dialog_button( "OK" )

    # make the vehicle elite
    ActionChains( webdriver ).double_click( get_sortable_elem() ).perform()
    check_elite2( False, True )
    elem = find_child( "#edit-vo .capabilities .elite" )
    elem.click()
    check_elite2( True, True )
    click_dialog_button( "OK" )
    check_elite( True, True )

    # save the scenario, then reload it
    saved_scenario = save_scenario()
    assert len(saved_scenario["OB_VEHICLES_1"]) == 1
    assert saved_scenario["OB_VEHICLES_1"][0]["elite"]
    assert saved_scenario["OB_VEHICLES_1"][0]["custom_capabilities"] == \
        [ "H9", "s10", "sD7", "CS 5", "HE11" ]
    select_menu_option( "new_scenario" )
    load_scenario( saved_scenario )
    select_tab( "ob1" )
    check_elite( True, True )

    # make the vehicle non-elite
    ActionChains( webdriver ).double_click( get_sortable_elem() ).perform()
    check_elite2( True, True )
    elem = find_child( "#edit-vo .capabilities .elite" )
    elem.click()
    check_elite2( False, True )
    click_dialog_button( "OK" )
    check_elite( False, True )

    # save the scenario
    saved_scenario = save_scenario()
    assert len(saved_scenario["OB_VEHICLES_1"]) == 1
    assert "elite" not in saved_scenario["OB_VEHICLES_1"][0]
    assert saved_scenario["OB_VEHICLES_1"][0]["custom_capabilities"] == \
        [ "H8", "s9", "sD7", "CS 5", "HE10" ]

    # make the vehicle elite, remove the custom capability
    ActionChains( webdriver ).double_click( get_sortable_elem() ).perform()
    check_elite2( False, True )
    elem = find_child( "#edit-vo .capabilities .elite" )
    elem.click()
    check_elite2( True, True )
    elems = find_children( "#vo_capabilities-sortable li" )
    webdriver.execute_script( "arguments[0].scrollIntoView(true);", elems[4] )
    ActionChains( webdriver ).key_down( Keys.CONTROL ).click( elems[4] ).perform()
    ActionChains( webdriver ).key_up( Keys.CONTROL ).perform()
    click_dialog_button( "OK" )
    check_elite( True, False )

    # save the scenario, then reload it
    saved_scenario = save_scenario()
    assert len(saved_scenario["OB_VEHICLES_1"]) == 1
    assert saved_scenario["OB_VEHICLES_1"][0]["elite"]
    assert saved_scenario["OB_VEHICLES_1"][0]["custom_capabilities"] == [ "H9", "s10", "sD7", "CS 5" ]
    select_menu_option( "new_scenario" )
    load_scenario( saved_scenario )
    select_tab( "ob1" )
    check_elite( True, False )

    # make the vehicle non-elite
    ActionChains( webdriver ).double_click( get_sortable_elem() ).perform()
    check_elite2( True, False )
    elem = find_child( "#edit-vo .capabilities .elite" )
    elem.click()
    check_elite2( False, False )
    click_dialog_button( "OK" )
    check_elite( False, False )

    # save the scenario
    saved_scenario = save_scenario()
    assert len(saved_scenario["OB_VEHICLES_1"]) == 1
    assert "elite" not in saved_scenario["OB_VEHICLES_1"][0]
    assert "custom_capabilities" not in saved_scenario["OB_VEHICLES_1"][0]

# ---------------------------------------------------------------------

def _check_capabilities( webdriver, webapp,
    nat, vo_type, vo_name, scenario_theater, scenario_date,
    expected, row=None
): #pylint: disable=too-many-arguments
    """Check the vehicle/ordnance capabilities for the specified parameters."""
    capabilities = _get_capabilities(
        webdriver, webapp, nat, vo_type, vo_name, scenario_theater, scenario_date,
        merge_common = False,
        row = row
    )
    for cap in _IGNORE_CAPABILITIES:
        expected = re.sub( r"(^|\s+){}($|\s+)".format(cap), "", expected )
    assert capabilities == expected

def _get_capabilities( webdriver, webapp,
    nat, vo_type, vo_name, scenario_theater, scenario_date,
    merge_common=False,
    row=None
): #pylint: disable=too-many-arguments
    """Get the vehicle/ordnance capabilities for the specified parameters.

    NOTE: We're only interested in checking the generated capabilities, not testing the UI,
    so we use a V/O report to get the information out of the webapp, which is significantly faster.
    """

    # FUDGE! There are a few vehicles with the same name :-/
    if row:
        row_no, expected_rows = row
    else:
        row_no = expected_rows = 1

    # generate the V/O report
    month, year = scenario_date.split( "/" )
    results = get_vo_report( webapp, webdriver,
        vo_type, nat, scenario_theater, year, month, name=vo_name,
        merge_common = merge_common
    )
    assert len(results) == 1+expected_rows

    # check the capabilities
    assert "Capabilities" in results[0][1]
    capabilities = results[row_no][2]
    capabilities = re.sub( '<span class="brewup">(.*?)</span>', r'\1 [brewup]', capabilities )
    capabilities = re.sub( "\u2020<sup>(\\d)</sup>", lambda mo: "[!{}]".format(mo.group(1)), capabilities )
    capabilities = capabilities.replace( "\u2020", "[!]" )
    return capabilities
