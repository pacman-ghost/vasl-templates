""" Webapp handlers. """

import os
import json

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

# ---------------------------------------------------------------------

@app.route( "/nationalities" )
def get_nationalities():
    """Get the nationalities table."""

    # load the nationalities table
    fname = os.path.join( DATA_DIR, "nationalities.json" )
    with open(fname,"r") as fp:
        nationalities = json.load( fp )

    # auto-generate ID's for those entries that don't already have one
    for nat in nationalities:
        if "id" not in nat:
            nat["id"] = nat["display_name"].lower()

    return jsonify( { n["id"]: n for n in nationalities } )
