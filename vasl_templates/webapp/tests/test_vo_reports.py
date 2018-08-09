""" Check the vehicle/ordnance reports. """

import os
import io
import shutil
import re

import tabulate
import pytest

from vasl_templates.webapp.tests.utils import find_child, find_children, wait_for

# ---------------------------------------------------------------------

# NOTE: Running these checks is fairly slow, and once done, don't provide a great deal of value
# in the day-to-day development process, so we make them optional.
@pytest.mark.skipif(
    not pytest.config.option.check_vo_reports, #pylint: disable=no-member
    reason = "--no-reports not specified"
)
def test_vo_reports( webapp, webdriver ):
    """Check the vehicle/ordnance reports."""

    # initialize
    check_dir = os.path.join( os.path.split(__file__)[0], "fixtures/vo-reports/" )
    save_dir = None # nb: define this to save the generated reports

    # initialize
    if save_dir and os.path.isdir(save_dir):
        shutil.rmtree( save_dir )

    # check each vehicle/ordnance report
    for nat in ["german","russian"]:
        for vo_type in ["vehicles","ordnance"]:
            for year in range(1940,1945+1):

                # get the next report
                buf = io.StringIO()
                results = get_vo_report( webapp, webdriver, nat, vo_type, year )

                # FUDGE! The "capabilities" and "notes" columns span 2 columns each,
                # so we add dummy header columns to stop tabulate from getting confused :-/
                assert results[0][-1] == "Notes"
                results[0].insert( len(results[0])-1, "#" )
                assert results[0][-3] == "Capabilities"
                results[0].insert( len(results[0])-2, "(effective)" )

                # fix up date-based capabilities
                assert results[0][-4] == "Capabilities"
                for i in range(1,len(results)):
                    results[i][-4] = re.sub(
                        r"<sup>(.*?)</sup>",
                        lambda mo: "[{}]".format( mo.group(1) ),
                        results[i][-4]
                    )

                # output the report
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

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def get_vo_report( webapp, webdriver, nat, vo_type, year ):
    """Get a vehicle/ordnance report.

    NOTE: We can't get the V/O report to return its results as, say, plain-text, for easy checking,
    since it's all done in Javascript, asynchronously i.e. we need something that will wait until
    the results are ready i.e. Selenium, not wget :-/
    """

    # initialize
    webdriver.get( webapp.url_for( "get_vo_report", nat=nat, vo_type=vo_type, year=year ) )
    wait_for( 5, lambda: find_child("#results").is_displayed() )

    # unload the results
    def getval( cell ):
        """Get a table cell's value (cleaned up)."""
        val = cell.get_attribute( "innerHTML" )
        if val == "<small><em>n/a</em></small>":
            return "n/a"
        val = val.replace( '<span class="val">', "" ).replace( "</span>", "" )
        return val
    results = []
    elem = find_child( "#results" )
    for row in find_children( "tr", elem ):
        if not results:
            results.append( [ getval(c) for c in find_children("th",row) ] )
        else:
            results.append( [ getval(c) for c in find_children("td",row) ] )

    return results
