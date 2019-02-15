"""Test generating the Chapter H placeholder files."""

import os
from zipfile import ZipFile

from vasl_templates.tools.make_chapter_h_placeholders import make_chapter_h_placeholders
from vasl_templates.webapp.utils import TempFile

# ---------------------------------------------------------------------

def test_make_chapter_h_placeholders():
    """Test generating the Chapter H placeholder files."""

    with TempFile() as temp_file:

        # generate the Chapter H placeholder files
        make_chapter_h_placeholders( temp_file.name )

        # get the expected results
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/chapter-h-placeholders.txt" )
        expected = [ line.strip() for line in open(fname,"r") ]

        # check the results
        with ZipFile( temp_file.name, "r" ) as zip_file:
            zip_fnames = sorted( zip_file.namelist() )
        assert zip_fnames == expected
