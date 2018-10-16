""" Check the vehicle/ordnance reports. """

import os
import io
import shutil
import re

import lxml.html
import lxml.etree
import tabulate

import vasl_templates.webapp.tests.utils as test_utils
from vasl_templates.webapp.tests.utils import find_child, wait_for

# ---------------------------------------------------------------------

def test_vo_reports( webapp, webdriver ): #pylint: disable=too-many-locals
    """Check the vehicle/ordnance reports."""

    # initialize
    check_dir = os.path.join( os.path.split(__file__)[0], "fixtures/vo-reports/" )
    save_dir = None # nb: define this to save the generated reports

    # initialize
    if save_dir and os.path.isdir(save_dir):
        shutil.rmtree( save_dir )

    def fixup_capabilities( col, caption ):
        """Convert capability HTML to something a bit more readable."""
        assert results[0][col] == caption
        for i in range(1,len(results)):
            results[i][col] = re.sub(
                r"<sup>(.*?)</sup>",
                lambda mo: "[{}]".format( mo.group(1) ),
                results[i][col]
            )
            results[i][col] = results[i][col].replace( " <small><i>(brew up)</i></small>", "[brewup]" )

    # check each vehicle/ordnance report
    nationalities = [
        "german", "russian", "american", "british", "italian", "japanese", "chinese", "french", "finnish",
        "polish", "belgian","yugoslavian","danish","dutch","greek", "allied-minor-common",
        "romanian", "hungarian","slovakian","croatian","bulgarian", "axis-minor-common"
    ]
    for nat in nationalities:
        for vo_type in ["vehicles","ordnance"]:
            for year in range(1940,1945+1):

                # get the next report
                results = get_vo_report( webapp, webdriver, "ETO", nat, vo_type, year, 1 )

                # FUDGE! The "capabilities" and "notes" columns span 2 columns each,
                # so we add dummy header columns to stop tabulate from getting confused :-/
                assert results[0][-1] == "Notes"
                results[0].insert( len(results[0])-1, "#" )
                assert results[0][-3] == "Capabilities"
                results[0].insert( len(results[0])-2, "(effective)" )

                # fix up date-based capabilities
                fixup_capabilities( -4, "Capabilities" )
                fixup_capabilities( -3, "(effective)" )
                fixup_capabilities( -2, "#" )

                # convert the report to plain-text
                buf = io.StringIO()
                print( "=== {}/{}/{} ===".format( vo_type, nat, year ), file=buf )
                print( "", file=buf )
                print(
                    tabulate.tabulate( results, headers="firstrow" ),
                    file = buf
                )
                report = buf.getvalue()

                # check if we should save the report
                fname = "{}/{}/{}.txt".format( vo_type, nat, year )
                if save_dir:
                    fname2 = os.path.join( save_dir, fname )
                    os.makedirs( os.path.split(fname2)[0], exist_ok=True )
                    with open( os.path.join(save_dir,fname2), "w" ) as fp:
                        fp.write( report )

                # check the report
                fname = os.path.join( check_dir, fname )
                assert open(fname,"r",encoding="utf-8").read() == report

    # get the landing craft report
    url = webapp.url_for( "get_lc_report" )
    webdriver.get( url )
    wait_for( 2, lambda: find_child("#results").is_displayed() )
    results = _parse_report( webdriver.page_source )

    # convert the report to plain-text
    assert results[0][-1] == "Notes"
    results[0].insert( len(results[0])-1, "#" )
    assert results[0][-3] == "Capabilities"
    results[0].insert( len(results[0])-2, "(effective)" )
    buf = io.StringIO()
    print( "=== landing craft ===", file=buf )
    print( "", file=buf )
    print(
        tabulate.tabulate( results, headers="firstrow" ),
        file = buf
    )
    report = buf.getvalue()

    # check if we should save the report
    if save_dir:
        with open( os.path.join(save_dir,"landing-craft.txt"), "w" ) as fp:
            fp.write( report )

    # check the report
    fname = os.path.join( check_dir, "landing-craft.txt" )
    assert open(fname,"r",encoding="utf-8").read() == report

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def get_vo_report( webapp, webdriver,
    theater, nat, vo_type, year, month,
    name=None, merge_common=False
): #pylint: disable=too-many-arguments,too-many-locals
    """Get a vehicle/ordnance report.

    NOTE: We can't get the V/O report to return its results as, say, plain-text, for easy checking,
    since it's all done in Javascript, asynchronously i.e. we need something that will wait until
    the results are ready i.e. Selenium, not wget :-/
    """

    # nb: in case the caller hasn't called init_webapp()
    test_utils._webdriver = webdriver #pylint: disable=protected-access

    # initialize
    url = webapp.url_for( "get_vo_report", theater=theater, nat=nat, vo_type=vo_type, year=year, month=month )
    assert "?" in url
    if name:
        url += "&name={}".format( name )
    if merge_common:
        url += "&merge_common=1"
    webdriver.get( url )
    wait_for( 2, lambda: find_child("#results").is_displayed() )

    # parse the report
    results = _parse_report( webdriver.page_source )

    return results

def _parse_report( buf ):
    """Parse a vehicle/ordnance report."""

    def tidy( cell ):
        """Tidy up a cell value."""
        val = lxml.etree.tostring( cell ).decode( "utf-8" ) #pylint: disable=c-extension-no-member
        if val in ("<td/>","<th/>"):
            return ""
        mo = re.search( r"^<(th|td).*?>(.*)</\1>$", val )
        val = mo.group(2)
        if val == "<small><em>n/a</em></small>":
            return "n/a"
        val = val.replace( '<span class="val">', "" ).replace( "</span>", "" )
        val = val.replace( "&#8224;", "\u2020" ).replace( "&#174;", "\u00ae" )
        val = val.replace( "&#10003;", "yes" )
        return val

    # unload the results
    # NOTE: Getting each table cell via Selenium is insanely slow - we parse the HTML manually :-/
    results = []
    doc = lxml.html.fromstring( buf )
    for row in doc.xpath( "//div[@id='results']//table//tr" ):
        tag = "td" if results else "th"
        cells = row.xpath( ".//{}".format( tag ) )
        results.append( list( tidy(c) for c in cells ) )

    return results
