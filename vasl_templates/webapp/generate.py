""" Webapp handlers. """

import os

from flask import jsonify

from vasl_templates.webapp import app
from vasl_templates.webapp.config.constants import DATA_DIR

# ---------------------------------------------------------------------

@app.route( "/templates" )
def get_templates():
    """Get the specified templates."""

    # load the default templates
    templates = {}
    dname = os.path.join( DATA_DIR, "default-templates" )
    for fname in os.listdir(dname):
        if os.path.splitext(fname)[1] != ".j2":
            continue
        fname2 = os.path.join( dname, fname )
        with open(fname2,"r") as fp:
            templates[os.path.splitext(fname)[0]] = fp.read()

    return jsonify( templates )
