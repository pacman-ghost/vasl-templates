""" Test National Capabilities snippet generation. """

import os
import shutil
import io
import itertools

import lxml.html

from vasl_templates.webapp.tests.utils import init_webapp, get_nationalities, SwitchFrame

# ---------------------------------------------------------------------

def test_national_capabilities_reports( webapp, webdriver ):
    """Check the national capabilities reports."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver )

    # initialize
    check_dir = os.path.join( os.path.split(__file__)[0], "fixtures/nat-caps/" )
    save_dir = os.environ.get( "NATCAPS_SAVEDIR" ) # nb: define this to save the generated reports
    if save_dir and os.path.isdir(save_dir):
        shutil.rmtree( save_dir )

    def do_test( nats, theater, years ): #pylint: disable=missing-docstring

        # initialize
        failed = False

        # check each nationality
        for nat in nats:

            # check each year
            for year in range( years[0], years[1]+1 ):

                # get the next snippet
                nat_caps = _get_nat_caps( webapp, webdriver, nat, theater, year, 1 )
                if nat in ("filipino",):
                    assert nat_caps is None
                    continue
                report = _make_report( nat, theater, year, nat_caps )

                # check if we should save the report
                fname = os.path.join(
                    os.path.join("kfw",nat) if theater == "Korea" else nat,
                    "{}.txt".format( year )
                )
                if save_dir:
                    fname2 = os.path.join( save_dir, fname )
                    os.makedirs( os.path.split(fname2)[0], exist_ok=True )
                    with open( os.path.join(save_dir,fname2), "w", encoding="utf-8" ) as fp:
                        fp.write( report )

                # check the report
                fname = os.path.join( check_dir, fname )
                with open( fname, "r", encoding="utf-8" ) as fp:
                    if fp.read() != report:
                        if save_dir:
                            print( "FAILED:", fname )
                            failed = True
                        else:
                            assert False, "Report mismatch: {}".format( fname )

        assert not failed

    # check each nationality
    nationalities = list( get_nationalities( webapp ).keys() )
    do_test(
        [ nat for nat in nationalities if not nat.startswith("kfw-") ],
        "ETO", (1940,1945)
    )
    do_test(
        [ "american", "kfw-rok", "british", "kfw-ounc", "kfw-kpa", "kfw-cpva" ],
        "Korea", (1950,1953)
    )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _get_nat_caps( webapp, webdriver, nat, theater, year, month ): #pylint: disable=too-many-locals
    """Get a national capabilities snippet."""

    # get the snippet
    url = webapp.url_for( "get_national_capabilities", nat=nat, theater=theater, year=year, month=month )
    webdriver.get( url )
    with SwitchFrame( webdriver, "#results" ):
        buf = webdriver.page_source

    # check if there is anything
    if "Not available." in buf:
        return None

    def to_text( elem ):
        """Convert an HTML element to text (tags are stripped, we don't descend into child nodes)."""
        vals = [ elem.text ]
        for c in elem.iterchildren():
            if c.tag == "ul":
                continue
            vals.extend( [ c.text, c.tail ] )
        vals.append( elem.tail )
        vals = [ v for v in vals if v ]
        return "".join( vals ).strip()

    # parse the basic details
    report = {}
    doc = lxml.html.fromstring( buf )
    fields = [ "grenades", "hob-drm", "th-color", "oba-black", "oba-red", "oba-access" ]
    for field in fields:
        elems = doc.xpath(  "//*[@class='{}']".format( field ) )
        if len(elems) == 0:
            report[ field ] = "-"
        else:
            assert len(elems) == 1
            report[ field ] = to_text( elems[0] )
    if report["hob-drm"] != "-":
        assert report["hob-drm"].startswith( "Heat of Battle: " )
        report["hob-drm"] = report["hob-drm"][16:]

    # parse the OBA comments
    report["oba-comments"] = []
    for elem in doc.xpath( "//ul[@class='oba-comments']/li" ):
        report["oba-comments"].append( elem.text.strip() )

    def parse_list( root, items ):
        """Parse a list of items (and their child items)."""
        for elem in root.xpath( "./li" ):
            val = to_text( elem )
            elems = elem.xpath( "./ul" )
            if not elems:
                items.append( val )
            else:
                assert len(elems) == 1
                items.append( [
                    val, parse_list( elems[0], [] )
                ] )
        return items

    # parse the notes
    report[ "note-groups" ] = []
    for group in doc.xpath( "//div[@class='note-group']" ):
        caption = group.xpath( "./div[@class='caption']" )
        notes = group.xpath( "./ul" )
        report["note-groups"].append( [
            to_text( caption[0] ) if caption else None,
            parse_list( notes[0], [] ) if notes else None
        ] )

    return report

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _make_report( nat, theater, year, nat_caps ):
    """Generate a report for the national capabilities."""

    def dump_list_items( items, depth ):
        """Dump a list of items (and their child items)."""
        tab = "  " * depth
        for item in items:
            if isinstance( item, str ):
                print( "{}* {}".format( tab, item ), file=buf )
            else:
                assert isinstance( item, list ) and len(item) == 2
                print( "{}* {}".format( tab, item[0] ), file=buf )
                dump_list_items( item[1], depth+1 )

    # generate the report
    buf = io.StringIO()
    print( "=== {} ({} {}) ===".format( nat, theater, year ), file=buf )
    print( "", file=buf )
    print( nat_caps["grenades"], file=buf )
    print( "HoB: {}".format( nat_caps["hob-drm"] ), file=buf )
    print( nat_caps["th-color"], file=buf )
    print( "OBA: {} {}".format( nat_caps["oba-black"], nat_caps["oba-red"] ), end="", file=buf )
    if nat_caps["oba-access"]:
        print( " {}".format( nat_caps["oba-access"] ), end="", file=buf )
    print( "", file=buf )
    for cmt in nat_caps["oba-comments"]:
        print( "- {}".format( cmt ), file=buf )
    for group in nat_caps.get( "note-groups", [] ):
        print( "", file=buf )
        if group[0]:
            print( group[0], file=buf )
        if group[1]:
            dump_list_items( group[1], 0 )

    return buf.getvalue()

# ---------------------------------------------------------------------

def test_time_based_national_capabilities( webapp, webdriver ):
    """Check time-based national capabilities.

    Capabilities that change according to the year are checked in the reports,
    these tests check those capabilities that change in the middle of a year.
    """

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver )

    def check_notes( nat, theater, month, year, expected ):
        """Check the national capabilities notes."""
        nat_caps = _get_nat_caps( webapp, webdriver, nat, theater, year, month )
        for e in expected:
            notes = [
                g[1] or []
                for g in nat_caps.get( "note-groups", [] )
            ]
            notes = [
                n if isinstance(n,str) else n[0]
                for n in itertools.chain( *notes )
            ]
            if e.startswith( "!" ):
                assert e[1:] not in notes
            else:
                assert e in notes

    def check_oba( nat, theater, month, year, expected_black, expected_red, comments=None, plentiful=None ):
        """Check the OBA national capabilities."""
        nat_caps = _get_nat_caps( webapp, webdriver, nat, theater, year, month )
        assert nat_caps["oba-black"] == expected_black
        assert nat_caps["oba-red"] == expected_red
        if plentiful:
            assert comments is None
            comments = [ "Plentiful Ammo included" ]
        if comments:
            assert nat_caps["oba-comments"] == comments
        else:
            assert not nat_caps["oba-comments"]

    def check_th_color( nat, theater, month, year, expected ):
        """Check the TH# color."""
        nat_caps = _get_nat_caps( webapp, webdriver, nat, theater, year, month )
        assert nat_caps["th-color"] == expected

    # test the German national capabilities
    check_notes( "german", "ETO", 12, 1942, [
        "No Inherent PF", "No Inherent ATMM"
    ] )
    check_notes( "german", "ETO", 9, 1943, [
        "No Inherent PF", "No Inherent ATMM"
    ] )
    check_notes( "german", "ETO", 10, 1943, [
        "Inherent PF", "No Inherent ATMM"
    ] )

    # test the Russian national capabilities
    check_notes( "russian", "ETO", 12, 1941, [
        "Commissars", "Riders NA"
    ] )
    check_notes( "russian", "ETO", 10, 1942, [
        "Commissars", "Riders OK"
    ] )
    check_notes( "russian", "ETO", 11, 1942, [
        "Commissars NA", "Riders OK"
    ] )
    check_notes( "russian", "ETO", 1, 1943, [
        "Commissars NA", "Riders OK"
    ] )

    # test the Free French national capabilities
    check_notes( "free-french", "ETO", 11, 1943, [
        "No Assault Fire",
        "British (f) vehicles/Guns/SW", "!British/French (a)/(f) SW",
        "!Inherent Crews as British for Morale"
    ] )
    check_notes( "free-french", "ETO", 12, 1943, [
        "Assault Fire",
        "!British (f) vehicles/Guns/SW", "British/French (a)/(f) SW",
        "Inherent Crews as British for Morale"
    ] )

    # test the Finnish national capabilities
    # NOTE: We should test for Inherent PF here, but it's in a nested sub-list (more trouble than it's worth).
    check_oba( "finnish", "ETO", 12, 1943, "8B", "3R", plentiful=True )
    check_oba( "finnish", "ETO", 1, 1944, "8B", "3R", plentiful=True )
    check_oba( "finnish", "ETO", 9, 1944, "8B", "3R", plentiful=True )
    check_oba( "finnish", "ETO", 10, 1944, "7B", "3R", plentiful=True )
    check_oba( "finnish", "ETO", 1, 1945, "7B", "3R", plentiful=True )

    # test the Axis Minor national capabilities
    check_notes( "romanian", "ETO", 6, 1943, [
        "No Inherent PF", "No Inherent ATMM"
    ] )
    check_notes( "romanian", "ETO", 7, 1943, [
        "No Inherent PF", "Inherent ATMM in non-Crew Elite  and 1st Line MMC (-2 CC DRM)"
    ] )
    check_notes( "romanian", "ETO", 3, 1944, [
        "Inherent PF  in non-Crew MMC", "Inherent ATMM in non-Crew Elite  and 1st Line MMC (-2 CC DRM)"
    ] )
    # FUDGE! Because the "Inherent PF" note appears in the "Romanian + Hungarian" or "Romanian" group,
    # depending on the data, we distinguish between the two by having an extra space in the note,
    # which won't make any different when it's rendered as HTML, but can be detected here... :-/
    check_notes( "romanian", "ETO", 7, 1944, [
        "Inherent PF in non-Crew MMC", "Inherent ATMM in non-Crew Elite  and 1st Line MMC (-2 CC DRM)"
    ] )

    # test the KFW American national Capabilities
    # NOTE: We should test for early war Katusa here, but it's in a nested sub-list (more trouble than it's worth).
    check_oba( "american", "Korea", 12, 1949, "???", "3R" )
    check_oba( "american", "Korea", 5, 1950, "???", "3R" )
    check_oba( "american", "Korea", 6, 1950, "9B", "3R" )
    check_oba( "american", "Korea", 8, 1950, "9B", "3R" )
    check_oba( "american", "Korea", 9, 1950, "10B", "3R", plentiful=True )
    check_oba( "american", "Korea", 1, 1951, "10B", "3R", plentiful=True )
    check_th_color( "american", "Korea", 12, 1949, "??? TH#" )
    check_th_color( "american", "Korea", 5, 1950, "??? TH#" )
    check_th_color( "american", "Korea", 6, 1950, "Red TH#" )
    check_th_color( "american", "Korea", 8, 1950, "Red TH#" )
    check_th_color( "american", "Korea", 9, 1950, "Black TH#" )
    check_th_color( "american", "Korea", 1, 1951, "Black TH#" )
    check_notes( "american", "Korea", 5, 1950, [
        "!Early KW U.S. Army rules:"
    ] )
    check_notes( "american", "Korea", 6, 1950, [
        "Early KW U.S. Army rules:"
    ] )
    check_notes( "american", "Korea", 9, 1950, [
        "!Early KW U.S. Army rules:"
    ] )

    # test the South Korean national Capabilities
    check_oba( "kfw-rok", "Korea", 5, 1950, "???", "3R",
        comments = [ "Plentiful Ammo included (KMC)" ]
    )
    check_oba( "kfw-rok", "Korea", 6, 1950, "10B", "3R",
        comments = [ "Plentiful Ammo included (KMC)", "ROK: 6B/3R" ]
    )
    check_oba( "kfw-rok", "Korea", 10, 1950, "10B", "3R", plentiful=True )
    check_th_color( "kfw-rok", "Korea", 8, 1950, "Red TH#" )
    check_th_color( "kfw-rok", "Korea", 9, 1950, "Red TH# (ROK) ; Black (KMC)" )
    check_th_color( "kfw-rok", "Korea", 5, 1951, "Black TH#" )

    # test the CPVA national Capabilities
    check_notes( "kfw-cpva", "Korea", 9, 1950, [
        "!Early KW CPVA rules"
    ] )
    check_notes( "kfw-cpva", "Korea", 10, 1950, [
        "Early KW CPVA rules"
    ] )
    check_notes( "kfw-cpva", "Korea", 4, 1951, [
        "!Early KW CPVA rules"
    ] )
    check_oba( "kfw-cpva", "Korea", 3, 1951, "-", "-" )
    check_oba( "kfw-cpva", "Korea", 4, 1951, "7B", "3R" )
    check_oba( "kfw-cpva", "Korea", 11, 1952, "7B", "2R" )
