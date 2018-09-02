""" Test snippet generation for capabilities. """

import pytest

from vasl_templates.webapp.tests.test_vo_reports import get_vo_report

# ---------------------------------------------------------------------

@pytest.mark.skipif(
    pytest.config.option.short_tests, #pylint: disable=no-member
    reason = "--short-tests specified"
) #pylint: disable=too-many-statements
def test_month_capabilities( webapp, webdriver ):
    """Test date-based capabilities that change in the middle of a year."""

    # Sherman III(a): WP6(J4+)† s8
    vehicle = [ "russian", "vehicles", "Sherman III(a)" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "s8" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "05/1944", "s8" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "06/1944", "WP6\u2020 s8" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "WP6\u2020 s8" )

    # Churchill III(b): D6(J4)/7(5)† ; HE7(F3)/8(4+)† ; sD6(4+) ; sM8†
    vehicle = [ "russian", "vehicles", "Churchill III(b)" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1942", "sM8\u2020" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1943", "sM8\u2020" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "02/1943", "HE7\u2020 sM8\u2020" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "05/1944", "HE8\u2020 sD6 sM8\u2020" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "06/1944", "D6\u2020 HE8\u2020 sD6 sM8\u2020" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "D7\u2020 HE8\u2020 sD6 sM8\u2020" )

    # M3A1 37mm AT Gun: NT, QSU, C7(A2+)†1
    ordnance = [ "american", "ordnance", "M3A1 37mm AT Gun" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1941", "NT QSU" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "07/1942", "NT QSU" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "08/1942", "NT QSU C7\u2020<sup>1</sup>" )

    # M1 57mm AT Gun: NT, QSU, HE7(J4E)/7(5)†, D4(J4+E)†
    ordnance = [ "american", "ordnance", "M1 57mm AT Gun" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "12/1943", "NT QSU" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "05/1944", "NT QSU" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "06/1944", "NT QSU D4\u2020 HE7\u2020" )
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1945", "NT QSU D4\u2020 HE7\u2020" )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "01/1945", "NT QSU" )

    # M3: C7(A2+)†2
    vehicle = [ "american", "vehicles", "M3" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1941", "n/a", (1,3) )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "07/1942", "n/a", (1,3) )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "08/1942", "C7\u2020<sup>2</sup>", (1,3) )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1943", "C7\u2020<sup>2</sup>", (1,3) )

    # M4/M4A1/M4A2/M4A3: WP7(J4+)†3 s5(J4+) sM5(4+)
    for vo_name in ("M4","M4A1","M4A2","M4A3"):
        vehicle = [ "american", "vehicles", vo_name ]
        ref = "\u2020<sup>{}</sup>".format( 2 if vo_name == "M4A2" else 3 )
        sM = 4 if vo_name == "M4A3" else 5
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "n/a" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "05/1944", "sM{}".format(sM) )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "06/1944", "WP7{} s5 sM{}".format(ref,sM) )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "WP7{} s5 sM{}".format(ref,sM) )

    # M4A3E2 (L): A4(4)/5(5), s5(5)
    vehicle = [ "american", "vehicles", "M4A3E2 (L)" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "sM8" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1944", "A4 sM8" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1944", "A4 sM8" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "A5 s5 sM8" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1946", "A5 s5 sM8" )

    # M4A1(76)W & M4A3(76)W: A4(A4)/5(5)†2, s5(5)
    for vo_name in ("M4A1(76)W","M4A3(76)W"):
        vehicle = [ "american", "vehicles", vo_name ]
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "sM8" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "07/1944", "sM8" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "08/1944", "A4\u2020<sup>2</sup> sM8" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "A5\u2020<sup>2</sup> s5 sM8" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1946", "A5\u2020<sup>2</sup> s5 sM8" )

    # Sherman Crab: s5(J4+); WP7(J4+)†2
    vehicle = [ "american", "vehicles", "Sherman Crab" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "sM4" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "05/1944", "sM4" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "06/1944", "WP7\u2020<sup>2</sup> s5 sM4" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "WP7\u2020<sup>2</sup> s5 sM4" )

    # M8 HMC: C4(4+)†1
    vehicle = [ "american", "vehicles", "M8 HMC" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "H9 WP9" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1944", "C4\u2020<sup>1</sup> H9 WP9" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "C4\u2020<sup>1</sup> H9 WP9" )

# ---------------------------------------------------------------------

@pytest.mark.skipif(
    pytest.config.option.short_tests, #pylint: disable=no-member
    reason = "--short-tests specified"
)
def test_scenario_theater( webapp, webdriver ):
    """Test ETO/PTO-only capabilities."""

    # M2A1 105mm Howitzer: C7(4+P)†1
    ordnance = [ "american", "ordnance", "M2A1 105mm Howitzer" ]
    _check_capabilities( webdriver, webapp, *ordnance , "ETO", "12/1943", "NT H6 WP8 s7" )
    _check_capabilities( webdriver, webapp, *ordnance , "ETO", "01/1944", "NT H6 WP8 s7" )
    _check_capabilities( webdriver, webapp, *ordnance , "ETO", "01/1945", "NT H6 WP8 s7" )
    _check_capabilities( webdriver, webapp, *ordnance , "PTO", "12/1943", "NT H6 WP8 s7" )
    _check_capabilities( webdriver, webapp, *ordnance , "PTO", "01/1944", "NT C7\u2020<sup>1</sup> H6 WP8 s7" )
    _check_capabilities( webdriver, webapp, *ordnance , "PTO", "01/1945", "NT C7\u2020<sup>1</sup> H6 WP8 s7" )

    # M3 105mm Howitzer: C7(P)†1
    ordnance = [ "american", "ordnance", "M3 105mm Howitzer" ]
    _check_capabilities( webdriver, webapp, *ordnance, "ETO", "01/1940", "NT H7 WP8 s7" )
    _check_capabilities( webdriver, webapp, *ordnance, "PTO", "01/1940", "NT C7\u2020<sup>1</sup> H7 WP8 s7" )

    # M2A4: C10(P)†1
    vehicle = [ "american", "vehicles", "M2A4" ]
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1940", "C10\u2020<sup>1</sup>" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1940", "n/a" )

    # M4(105) & M4A3(105): C7P†1
    for vo_name in ("M4(105)","M4A3(105)"):
        vehicle = [ "american", "vehicles", vo_name ]
        _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1940", "C7\u2020<sup>1</sup> H9 WP9 s7 sM8" )
        _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1940", "H9 WP9 s7 sM8" )

    # NOTE: We do a bit of hackery for the APCR specification for the M10 GMC and M18 GMC,
    # to flag them as ETO-only, so we make sure everything's working properly here.

    # M10 GMC: A(E)5(A4)/6(5)†1
    vehicle = [ "american", "vehicles", "M10 GMC" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "sP5" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "07/1944", "sP5" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "08/1944", "A5\u2020<sup>1</sup> sP5" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "A6\u2020<sup>1</sup> s5 sP5" )
    _check_capabilities( webdriver, webapp, *vehicle, "other", "01/1945", "s5 sP5" )

    # M18 GMC: A(E)5(4)/6(5)†1
    vehicle = [ "american", "vehicles", "M18 GMC" ]
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "12/1943", "sP5" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1944", "A5\u2020<sup>1</sup> sP5" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1945", "A6\u2020<sup>1</sup> s5 sP5" )
    _check_capabilities( webdriver, webapp, *vehicle, "other", "01/1945", "s5 sP5" )

    # M7 HMC: C7(P)†1
    vehicle = [ "american", "vehicles", "M7 HMC" ]
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1940", "C7\u2020<sup>1</sup> H7 WP8 s7" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1940", "H7 WP8 s7" )

    # LVT(A)1: C10(P)†2
    vehicle = [ "american", "vehicles", "LVT(A)1" ]
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1940", "C10\u2020<sup>2</sup>" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1940", "n/a" )

    # LVT(A)4: C7(P)†3
    vehicle = [ "american", "vehicles", "LVT(A)4" ]
    _check_capabilities( webdriver, webapp, *vehicle, "PTO", "01/1940", "C7\u2020<sup>3</sup> H8 WP9" )
    _check_capabilities( webdriver, webapp, *vehicle, "ETO", "01/1940", "H8 WP9" )

# ---------------------------------------------------------------------

def _check_capabilities( webdriver, webapp,
    nat, vo_type, vo_name, scenario_theater, scenario_date,
    expected, row=None
): #pylint: disable=too-many-arguments
    """Check the vehicle/ordnance capabilities for the specified parameters.

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
    results = get_vo_report( webapp, webdriver, scenario_theater, nat, vo_type, year, month, name=vo_name )
    assert len(results) == 1+expected_rows

    # check the capabilities
    if vo_type == "vehicles":
        assert "Capabilities" in results[0][4]
        capabilities = results[row_no][5]
    elif vo_type == "ordnance":
        assert "Capabilities" in results[0][1]
        capabilities = results[row_no][2]
    else:
        assert False
    assert capabilities == expected
