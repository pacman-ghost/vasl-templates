""" Test serving counter images. """

import os
import io
import glob
import urllib.request

import pytest
import tabulate

from vasl_templates.webapp.file_server.utils import get_vo_gpids
from vasl_templates.webapp.config.constants import DATA_DIR
from vasl_templates.webapp.tests.utils import load_vasl_mod

# ---------------------------------------------------------------------

@pytest.mark.skipif(
    not pytest.config.option.vasl_mods, #pylint: disable=no-member
    reason = "--vasl-mods-tests not specified"
)
@pytest.mark.skipif(
    pytest.config.option.short_tests, #pylint: disable=no-member
    reason = "--short-tests specified"
) #pylint: disable=too-many-statements
def test_counter_images( webapp, monkeypatch ):
    """Test that counter images are served correctly."""

    # NOTE: This is ridiculously slow on Windows :-/

    # figure out which pieces we're interested in
    gpids = get_vo_gpids( DATA_DIR )

    def check_images( check_front, check_back ): #pylint: disable=unused-argument
        """Check getting the front and back images for each counter."""
        for gpid in gpids:
            for side in ("front","back"):
                url = webapp.url_for( "get_counter_image", gpid=gpid, side=side )
                try:
                    resp = urllib.request.urlopen( url )
                    resp_code = resp.code
                    resp_data = resp.read()
                except urllib.error.HTTPError as ex:
                    resp_code = ex.code
                    resp_data = None
                assert locals()["check_"+side]( resp_code, resp_data )

    # test counter images when no VASL module has been configured
    load_vasl_mod( None, monkeypatch )
    fname = os.path.join( os.path.split(__file__)[0], "../static/images/missing-image.png" )
    missing_image_data = open( fname, "rb" ).read()
    check_images(
        check_front = lambda code,data: code == 200 and data == missing_image_data,
        check_back = lambda code,data: code == 200 and data == missing_image_data
    )

    # test each VASL module file in the specified directory
    fname = os.path.join( os.path.split(__file__)[0], "fixtures/vasl-pieces.txt" )
    expected_vasl_pieces = open( fname, "r" ).read()
    fspec = os.path.join( pytest.config.option.vasl_mods, "*.vmod" ) #pylint: disable=no-member
    for fname in glob.glob(fspec):

        # install the VASL module file
        vasl_mod = load_vasl_mod( DATA_DIR, monkeypatch )

        # check the pieces loaded
        buf = io.StringIO()
        _dump_pieces( vasl_mod, buf )
        assert buf.getvalue() == expected_vasl_pieces

        # check each counter
        check_images(
            check_front = lambda code,data: code == 200 and data,
            check_back = lambda code,data: (code == 200 and data) or (code == 404 and not data)
        )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _dump_pieces( vasl_mod, out ):
    """Dump the VaslMod pieces."""

    # dump the VASL pieces
    results = [ [ "GPID", "Name", "Front images", "Back images"] ]
    for gpid in sorted(vasl_mod.pieces.keys()):
        piece = vasl_mod.pieces[ gpid ]
        assert piece["gpid"] == gpid
        results.append( [ gpid, piece["name"], piece["front_images"], piece["back_images"] ] )
    print( tabulate.tabulate( results, headers="firstrow" ), file=out )
