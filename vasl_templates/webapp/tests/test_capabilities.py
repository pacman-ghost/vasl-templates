""" Test snippet generation for capabilities. """

import re

import pytest
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.tests.utils import \
    init_webapp, select_menu_option, select_tab, click_dialog_button, \
    load_vasl_mod, find_child, find_children, wait_for_clipboard
from vasl_templates.webapp.tests.test_vo_reports import get_vo_report
from vasl_templates.webapp.tests.test_vehicles_ordnance import add_vo
from vasl_templates.webapp.tests.test_scenario_persistence import save_scenario, load_scenario
from vasl_templates.webapp.config.constants import DATA_DIR as REAL_DATA_DIR

# ---------------------------------------------------------------------

@pytest.mark.skipif(
    pytest.config.option.short_tests, #pylint: disable=no-member
    reason = "--short-tests specified"
) #pylint: disable=too-many-statements
def test_month_capabilities( webapp, webdriver ):
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

    # M3A1 37mm AT Gun: NT, QSU, C7(A2+)†1
    ordnance = [ "american", "ordnance", "M3A1 37mm AT Gun" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1941", "NT QSU" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "07/1942", "NT QSU" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "08/1942", "NT QSU C7[!1]" )

    # M1 57mm AT Gun: NT, QSU, HE7(J4E)/7(5)†, D4(J4+E)†
    ordnance = [ "american", "ordnance", "M1 57mm AT Gun" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1943", "NT QSU" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "05/1944", "NT QSU" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "06/1944", "NT QSU D4[!] HE7[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "06/1944", "NT QSU" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1945", "NT QSU D4[!] HE7[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "01/1945", "NT QSU HE7[!]" )

    # M3: C7(A2+)†2
    vehicle = [ "american", "vehicles", "M3" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1941", "CS 4", (1,3) )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "07/1942", "CS 4", (1,3) )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "08/1942", "C7[!2] CS 4", (1,3) )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1943", "C7[!2] CS 4", (1,3) )

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
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1946", "A5 s5 sM8 CS 6" )

    # M4A1(76)W & M4A3(76)W: A4(A4)/5(5)†2, s5(5)
    for vo_name in ("M4A1(76)W","M4A3(76)W"):
        vehicle = [ "american", "vehicles", vo_name ]
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "sM8 CS 6" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "07/1944", "sM8 CS 6" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "08/1944", "A4[!2] sM8 CS 6" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "A5[!2] s5 sM8 CS 6" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1946", "A5[!2] s5 sM8 CS 6" )

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
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1941", "4PP s7" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1942", "4PP IR[!] s7" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1943", "4PP IR[!] s7" )

    # OML 3-in. Mortar: IR(2)+†1
    ordnance = [ "british", "ordnance", "OML 3-in. Mortar" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1941", "NT QSU WP7 s8[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1942", "NT QSU IR[!1] WP7 s8[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1943", "NT QSU IR[!1] WP7 s8[!]" )

    # OQF 6-Pounder 7-cwt: D6(J4E)7(5)† HE7(F3)8(4+)†
    ordnance = [ "british", "ordnance", "OQF 6-Pounder 7-cwt" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1942", "NT QSU" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1943", "NT QSU" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "02/1943", "NT QSU HE7[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "05/1944", "NT QSU HE8[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "06/1944", "NT QSU D6[!] HE8[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "06/1944", "NT QSU HE8[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1945", "NT QSU D7[!] HE8[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "01/1945", "NT QSU D7[!] HE8[!]" )

    # OQF 17-Pounder: D5(S4)6(5)† HE8(J4+)†
    ordnance = [ "british", "ordnance", "OQF 17-Pounder" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1943", "NT" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "05/1944", "NT" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "06/1944", "NT HE8[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "09/1944", "NT D5[!] HE8[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1945", "NT D6[!] HE8[!]" )

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

    # Cannone da 47/32: Towed(A1+)†
    ordnance = [ "italian", "ordnance", "Cannone da 47/32" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1940", "NT QSU no Gunshield" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "07/1941", "NT QSU no Gunshield" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "08/1941", "NT QSU no Gunshield Towed[!]" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1942", "NT QSU no Gunshield Towed[!]" )

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

    # 81 Krh/32: s8(N1)†
    ordnance = [ "finnish", "ordnance", "81 Krh/32" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1940", "NT QSU 5PP dm" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "10/1941", "NT QSU 5PP dm" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "11/1941", "NT QSU s8[!] 5PP dm" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1942", "NT QSU s8[!] 5PP dm" )

    # 76 RK/27(r): H6J4+†
    ordnance = [ "finnish", "ordnance", "76 RK/27(r)" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1943", "NT QSU s6" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "05/1944", "NT QSU s6" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "06/1944", "NT QSU H6[!] s6" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1945", "NT QSU H6[!] s6" )

    # 105 H/33(g) ; 105 H/41(t): H6A4+†
    for vo_name in ("105 H/33(g)","105 H/41(t)"):
        ordnance = [ "finnish", "ordnance", vo_name ]
        val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1943" )
        assert "H6" not in val
        assert _get_capabilities( webdriver, webapp, *ordnance, "ETO", "07/1944" ) == val
        val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "08/1944" )
        print(vo_name)
        assert "H6[!]" in val
        assert _get_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1945" ) == val

# ---------------------------------------------------------------------

@pytest.mark.skipif(
    pytest.config.option.short_tests, #pylint: disable=no-member
    reason = "--short-tests specified"
)
def test_theater_capabilities( webapp, webdriver ):
    """Test theater-specific capabilities."""

    # M2A1 105mm Howitzer: C7(4+P)†1
    ordnance = [ "american", "ordnance", "M2A1 105mm Howitzer" ]
    _check_capabilities( webdriver, webapp, *ordnance , "ETO", "12/1943", "NT H6 WP8 s7" )
    _check_capabilities( webdriver, webapp, *ordnance , "ETO", "01/1944", "NT H6 WP8 s7" )
    _check_capabilities( webdriver, webapp, *ordnance , "ETO", "01/1945", "NT H6 WP8 s7" )
    _check_capabilities( webdriver, webapp, *ordnance , "PTO", "12/1943", "NT H6 WP8 s7" )
    _check_capabilities( webdriver, webapp, *ordnance , "PTO", "01/1944", "NT C7[!1] H6 WP8 s7" )
    _check_capabilities( webdriver, webapp, *ordnance , "PTO", "01/1945", "NT C7[!1] H6 WP8 s7" )

    # M3 105mm Howitzer: C7(P)†1
    ordnance = [ "american", "ordnance", "M3 105mm Howitzer" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1940", "NT H7 WP8 s7" )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "01/1940", "NT C7[!1] H7 WP8 s7" )

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
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1940", "C7[!1] H7 WP8 s7 CS 7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1940", "H7 WP8 s7 CS 7" )

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
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "12/1942", "NT QSU WP7 s8" )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "01/1943", "NT QSU H6[!] WP7 s8" )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "01/1944", "NT QSU H6[!] WP7 s8" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1944", "NT QSU WP7 s8" )

    # Obice da 149/13: WP6(B)
    ordnance = [ "chinese", "ordnance", "Obice da 149/13" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1940", "NT h-d<sup>C</sup>[!] s5" )
    _check_capabilities( webdriver, webapp, *ordnance, "Burma", "01/1940", "NT h-d<sup>C</sup>[!] WP6[!] s5" )

# ---------------------------------------------------------------------

@pytest.mark.skipif(
    pytest.config.option.short_tests, #pylint: disable=no-member
    reason = "--short-tests specified"
)
def test_nationality_capabilities( webapp, webdriver ):
    """Test nationality-specific capabilities."""

    # G obr. 38:  s5(1-2R)†
    ordnance = [ "romanian", "ordnance", "G obr. 38" ]
    val = _get_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1940", merge_common=True )
    assert "s5[!]" not in val
    ordnance = [ "romanian", "ordnance", "G obr. 38" ]
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
    ordnance = [ "slovakian", "ordnance", "Kanon PUV vz. 37(t)" ]
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
    check_snippet( '"QSU" "cs 4 <small><i>(brew up)</i></small>"' )

    # edit the vehicle's capabilities
    vehicles_sortable = find_child( "#ob_vehicles-sortable_1" )
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 1
    ActionChains(webdriver).double_click( elems[0] ).perform()
    elems = check_capabilities_in_dialog( [ "QSU", "cs 4 <small><i>(brew up)</i></small>" ] )

    # edit one of the capabilities
    elem = find_child( "input[type='text']", elems[0] )
    elem.clear()
    elem.send_keys( "QSU (modified)" )

    # delete a capability
    ActionChains(webdriver).key_down( Keys.CONTROL ).click( elems[1] ).key_up( Keys.CONTROL ).perform()

    # add a new capability
    elem = find_child( "#vo_capabilities-add" )
    elem.click()
    elems = find_children( "#vo_capabilities-sortable input[type='text']" )
    assert len(elems) == 2
    elems[1].send_keys( "a <i>new</i> capability" )

    # save the changes and check the vehicle's snippet
    click_dialog_button( "OK" )
    check_snippet( '"QSU (modified)" "a <i>new</i> capability"' )

    # save the scenario
    saved_scenario = save_scenario()
    assert len(saved_scenario["OB_VEHICLES_1"]) == 1
    assert saved_scenario["OB_VEHICLES_1"][0]["custom_capabilities"] == [ "QSU (modified)", "a <i>new</i> capability" ]

    # reload the scenario, and check the vehicle's snippet
    select_menu_option( "new_scenario" )
    load_scenario( saved_scenario )
    select_tab( "ob1" )
    check_snippet( '"QSU (modified)" "a <i>new</i> capability"' )

    # make sure the capabilities are loaded correcly when editing the vehicle
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 1
    ActionChains(webdriver).double_click( elems[0] ).perform()
    elems = check_capabilities_in_dialog( [ "QSU (modified)", "a <i>new</i> capability" ] )

    # delete all capabilities
    for elem in elems:
        ActionChains(webdriver).key_down( Keys.CONTROL ).click( elem ).key_up( Keys.CONTROL ).perform()
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
    ActionChains(webdriver).double_click( elems[0] ).perform()
    btn = find_child( "#vo_capabilities-reset" )
    btn.click()
    click_dialog_button( "OK" )
    check_snippet( '"QSU" "cs 4 <small><i>(brew up)</i></small>"' )

    # make sure the custom capabilities are no longer saved in the scenario
    saved_scenario2 = save_scenario()
    assert len(saved_scenario2["OB_VEHICLES_1"]) == 1
    assert "custom_capabilities" not in saved_scenario2["OB_VEHICLES_1"][0]

    # reload the scenario, and manually set the vehicle's capabilities to be the same as the default
    load_scenario( saved_scenario )
    select_tab( "ob1" )
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 1
    ActionChains(webdriver).double_click( elems[0] ).perform()
    elems = find_children( "#vo_capabilities-sortable input[type='text']" )
    assert len(elems) == 2
    elems[0].clear()
    elems[0].send_keys( "QSU" )
    elems[1].clear()
    elems[1].send_keys( "cs 4 <small><i>(brew up)</i></small>" )
    click_dialog_button( "OK" )

    # make sure the custom capabilities are no longer saved in the scenario
    saved_scenario = save_scenario()
    assert len(saved_scenario["OB_VEHICLES_1"]) == 1
    assert "custom_capabilities" not in saved_scenario["OB_VEHICLES_1"][0]

# ---------------------------------------------------------------------

@pytest.mark.skipif(
    not pytest.config.option.vasl_mods, #pylint: disable=no-member
    reason = "--vasl-mods not specified"
    ) #pylint: disable=too-many-statements
def test_capability_updates_in_ui( webapp, webdriver, monkeypatch ):
    """Ensure that capabilities are updated in the UI correctly."""

    # initialize
    monkeypatch.setitem( webapp.config, "DATA_DIR", REAL_DATA_DIR )
    load_vasl_mod( REAL_DATA_DIR, monkeypatch )
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # load the scenario
    scenario_data = {
        "PLAYER_1": "german",
        "OB_VEHICLES_1": [ { "name": "PzKpfw 38(t)A" } ], # A4[1]/5[2] ; sD6 ; CS 4
        "OB_ORDNANCE_1": [ { "name": "3.7cm PaK 35/36" } ], # NT ; QSU ; A4[1]/5[2]/4[3]/3[4] ; H6[9]†
        "PLAYER_2": "russian",
        "OB_VEHICLES_2": [ { "name": "Churchill III(b)" } ], # D6[J4]/7[5]† ; HE7[F3]/8[4+]† ; sD6[4+] ; sM8† ; CS 7
        "OB_ORDNANCE_2": [ { "name": "45mm PTP obr. 32" } ], # NT ; QSU ; A4[2]/5[3]/6[4]/7[5]
    }
    scenario_data["OB_VEHICLES_1"].append( { "name": "PzJg I" } ) # A5[1]; HE7 ; CS 3
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
        if scenario_date:
            elem = find_child( "input[name='SCENARIO_DATE']" )
            elem.clear()
            elem.send_keys( scenario_date )
            elem.send_keys( Keys.TAB )
        # check the vehicle/ordnance capabilities
        results = []
        for sortable in sortables:
            results.append( [] )
            vo_entries = find_children( "li", sortable )
            for vo_entry in vo_entries:
                capabilities = find_children( "span.vo-capability", vo_entry )
                results[-1].append( [ c.get_attribute("innerHTML") for c in capabilities ] )
        assert results == expected

    # no scenario date => we should be showing the raw capabilities
    check_capabilities( None, [
        [
            [ "A4<sup>1</sup>5<sup>2</sup>", "sD6", "CS 4" ],
            [ "A5<sup>1</sup>", "HE7", "CS 3" ]
        ],
        [ [ "NT", "QSU", "A4<sup>1</sup>5<sup>2</sup>4<sup>3</sup>3<sup>4</sup>", "H6[9]\u2020" ] ],
        [ [ "D6<sup>J4</sup>7<sup>5</sup>†", "HE7<sup>F3</sup>8<sup>4+</sup>\u2020", "sD6<sup>4+</sup>", "sM8\u2020", "CS 7" ] ], #pylint: disable=line-too-long
        [ [ "NT", "QSU", "A4<sup>2</sup>5<sup>3</sup>6<sup>4</sup>7<sup>5</sup>" ] ]
    ] )

    # edit the PzJg I's capabilities (nb: this locks them in, and they should not change
    # regardless of what the scenario date is set to)
    select_tab( "ob1" )
    vehicles_sortable = find_child( "#ob_vehicles-sortable_1" )
    elems = find_children( "li", vehicles_sortable )
    assert len(elems) == 2
    ActionChains(webdriver).double_click( elems[1] ).perform()
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
            [ "A5<sup>1</sup>", "HE7", "CS 3", "foo!" ]
        ],
        [ [ "NT", "QSU", "H6[9]\u2020" ] ],
        [ [ "sM8\u2020", "CS 7" ] ],
        [ [ "NT", "QSU" ] ]
    ] )
    check_capabilities( "01/01/1941", [
        [
            [ "A4", "sD6", "CS 4" ] ,
            [ "A5<sup>1</sup>", "HE7", "CS 3", "foo!" ]
        ],
        [ [ "NT", "QSU", "A4", "H6[9]\u2020" ] ],
        [ [ "sM8\u2020", "CS 7" ] ],
        [ [ "NT", "QSU" ] ]
    ] )
    check_capabilities( "01/01/1942", [
        [
            [ "A5", "sD6", "CS 4" ],
            [ "A5<sup>1</sup>", "HE7", "CS 3", "foo!" ]
        ],
        [ [ "NT", "QSU", "A5", "H6[9]\u2020" ] ],
        [ [ "sM8\u2020", "CS 7" ] ],
        [ [ "NT", "QSU", "A4" ] ]
    ] )
    check_capabilities( "01/01/1943", [
        [
            [ "A5", "sD6", "CS 4" ],
            [ "A5<sup>1</sup>", "HE7", "CS 3", "foo!" ]
        ],
        [ [ "NT", "QSU", "A4", "H6[9]\u2020" ] ],
        [ [ "sM8\u2020", "CS 7" ] ],
        [ [ "NT", "QSU", "A5" ] ]
    ] )
    check_capabilities( "01/01/1944", [
        [
            [ "A5", "sD6", "CS 4" ],
            [ "A5<sup>1</sup>", "HE7", "CS 3", "foo!" ]
        ],
        [ [ "NT", "QSU", "A3", "H6[9]\u2020" ] ],
        [ [ "HE8\u2020", "sD6", "sM8\u2020", "CS 7" ] ],
        [ [ "NT", "QSU", "A6" ] ]
    ] )
    check_capabilities( "01/01/1945", [
        [
            [ "A5", "sD6", "CS 4" ],
            [ "A5<sup>1</sup>", "HE7", "CS 3", "foo!" ]
        ],
        [ [ "NT", "QSU", "A3", "H6[9]\u2020" ] ],
        [ [ "D7\u2020", "HE8\u2020", "sD6", "sM8\u2020", "CS 7" ] ],
        [ [ "NT", "QSU", "A7" ] ]
    ] )

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
        scenario_theater, nat, vo_type, year, month, name=vo_name,
        merge_common = merge_common
    )
    assert len(results) == 1+expected_rows

    # check the capabilities
    assert "Capabilities" in results[0][1]
    capabilities = results[row_no][2]
    capabilities = capabilities.replace( "<small><i>(brew up)</i></small>", "[brewup]" )
    capabilities = re.sub( "\u2020<sup>(\\d)</sup>", lambda mo: "[!{}]".format(mo.group(1)), capabilities )
    capabilities = capabilities.replace( "\u2020", "[!]" )
    return capabilities
