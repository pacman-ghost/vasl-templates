""" Check the vehicle/ordnance reports. """

import os
import io
import shutil
import re

import pytest
import lxml.html
import lxml.etree
import tabulate

import vasl_templates.webapp.tests.utils as test_utils
from vasl_templates.webapp.tests.utils import init_webapp, get_nationalities, find_child, wait_for

# ---------------------------------------------------------------------

# NOTE: The expected output files contain pieces from the supported extensions,
# so the VASL extensions directory must be loaded.
@pytest.mark.skipif(
    not pytest.config.option.vasl_mods, #pylint: disable=no-member
    reason = "--vasl-mods not specified"
)
@pytest.mark.skipif(
    not pytest.config.option.vasl_extensions, #pylint: disable=no-member
    reason = "--vasl-extensions not specified"
) #pylint: disable=too-many-statements,too-many-locals
def test_vo_reports( webapp, webdriver ): #pylint: disable=too-many-locals
    """Check the vehicle/ordnance reports."""

    # initialize
    init_webapp( webapp, webdriver,
        reset = lambda ct:
            ct.set_data_dir( dtype="real" ) \
              .set_vasl_mod( vmod="random", extns_dtype="real" )
    )

    # initialize
    check_dir = os.path.join( os.path.split(__file__)[0], "fixtures/vo-reports/" )
    save_dir = os.environ.get( "VO_REPORTS_SAVEDIR" ) # nb: define this to save the generated reports
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
            results[i][col] = re.sub(
                r'<span class="brewup">(.*?)(\u2020.*)?</span>',
                r"\1[brewup]\2",
                results[i][col]
            )

    # check each vehicle/ordnance report
    nationalities = list( get_nationalities( webapp ).keys() )
    nationalities.extend( [ "allied-minor-common", "axis-minor-common", "landing-craft" ] )
    failed = False
    for nat in nationalities:

        for vo_type in ["vehicles","ordnance"]:

            # figure out which years we should generate reports for
            # NOTE: The Americans and British are in K:FW, so we should really check 1950-53 for these as well,
            # but there are only a few vehicles that have date-specific capabilities, so we don't bother testing
            # for them here, and check those specific cases in test_kfw().
            years = (1950,1953) if nat.startswith( "kfw-" ) else (1940,1945)

            for year in range(years[0],years[1]+1):

                # get the next report
                if nat == "landing-craft" and vo_type == "ordnance":
                    continue
                results = get_vo_report( webapp, webdriver, vo_type, nat, "ETO", year, 1 )
                if nat in ("burmese","filipino") or (nat,vo_type) in [("anzac","ordnance"),("kfw-cpva","vehicles")]:
                    assert not results
                    continue

                # FUDGE! The "capabilities" and "notes" columns span 2 columns each,
                # so we add dummy header columns to stop tabulate from getting confused :-/
                assert results[0][-2] == "Notes"
                results[0].insert( len(results[0])-2, "#" )
                assert results[0][-4] == "Capabilities"
                results[0].insert( len(results[0])-3, "(effective)" )

                # fix up date-based capabilities
                fixup_capabilities( -5, "Capabilities" )
                fixup_capabilities( -4, "(effective)" )
                fixup_capabilities( -3, "#" )

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
                if open(fname,"r",encoding="utf-8").read() != report:
                    if save_dir:
                        print( "FAILED:", fname )
                        failed = True
                    else:
                        assert False, "Report mismatch: {}".format( fname )

    assert not failed

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def get_vo_report( webapp, webdriver,
    vo_type, nat, theater, year, month,
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
    url = webapp.url_for( "get_vo_report", vo_type=vo_type, nat=nat, theater=theater, year=year, month=month )
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
        val = re.sub( '<span class="val">(.*?)</span>', r"\1", val )
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
