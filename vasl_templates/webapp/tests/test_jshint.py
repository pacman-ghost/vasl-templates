"""Run JSHint over the Javascript files."""

import os.path
import subprocess
import pytest

# ---------------------------------------------------------------------

@pytest.mark.skipif( not os.environ.get("JSHINT_RHINO"), reason="JSHint not configured." )
def test_jshint():
    """Run JSHint over the Javascript files.

    To set up JSHint:
    - install Rhino (Mozilla's Java-based (!) Javascript):
        sudo dnf install rhino
    - download and unpack JSHint:
        https://github.com/jshint/jshint
    - set JSHINT_RHINO to point to $/dist/jshint-rhino.js"

    IMPORTANT: Rhino + JSHint has been broken for some time:
        https://github.com/jshint/jshint/issues/2308
    For now, use JSHint 2.6.3 :-/
    """

    # initialize
    jshint = os.environ[ "JSHINT_RHINO" ]

    # check each Javascript file
    dname = os.path.join( os.path.split(__file__)[0], "../static/" )
    for fname in os.listdir(dname):
        if os.path.splitext(fname)[1] != ".js":
            continue
        # run JSHint for the next file
        proc = subprocess.run(
            [ jshint, os.path.join(dname,fname) ],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf-8"
        )
        if proc.stdout or proc.stderr:
            print( "=== JSHint failed: {} ===".format( fname ) )
            if proc.stdout:
                print( proc.stdout )
            if proc.stderr:
                print( proc.stderr )
            assert False
