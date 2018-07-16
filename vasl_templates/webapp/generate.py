""" Webapp handlers. """

import os
import json
import zipfile

from flask import jsonify, abort

from vasl_templates.webapp import app
from vasl_templates.webapp.config.constants import DATA_DIR

autoload_template_pack = None

# ---------------------------------------------------------------------

@app.route( "/templates/default" )
def get_default_templates():
    """Get the default templates."""

    # return the default templates
    dname = os.path.join( DATA_DIR, "default-templates" )
    return jsonify( _do_get_templates( dname ) )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@app.route( "/templates/autoload" )
def get_autoload_templates():
    """Get the templates to auto-load at startup.

    We would like the user to be able to specify a template pack to auto-load
    when starting the desktop app, but it's a little tricky to programatically
    get the frontend Javascript to accept an upload. We could possibly do it
    by using QWebChannel, but this would only work if the webapp was running
    inside PyQt. Instead, we get the frontend to call this endpoint when it
    starts up, to get the (optional) autoload templates.
    """

    # check if an autoload template pack has been configured
    if not autoload_template_pack:
        # nope - return an empty response
        return jsonify( {} )

    # check if the template pack is a directory
    if os.path.isdir( autoload_template_pack ):
        # yup - return the template files in it
        templates = _do_get_templates( autoload_template_pack )
        templates["_path_"] = autoload_template_pack
        return jsonify( templates )

    # return the template files in the specified ZIP file
    if not os.path.isfile( autoload_template_pack ):
        return jsonify( { "error": "Can't find template pack: {}".format(autoload_template_pack) } )
    templates = {}
    with zipfile.ZipFile( autoload_template_pack, "r" ) as zip_file:
        for fname in zip_file.namelist():
            if fname.endswith( "/" ):
                continue
            fname2 = os.path.split(fname)[1]
            templates[os.path.splitext(fname2)[0]] = zip_file.read( fname ).decode( "utf-8" )
    templates["_path_"] = autoload_template_pack
    return jsonify( templates )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _do_get_templates( dname ):
    """Get the specified templates."""
    if not os.path.isdir( dname ):
        abort( 404 )
    templates = {}
    for root,_,fnames in os.walk(dname):
        for fname in fnames:
            fname = os.path.join( root, fname )
            if os.path.splitext(fname)[1] != ".j2":
                continue
            with open(fname,"r") as fp:
                fname = os.path.split(fname)[1]
                templates[os.path.splitext(fname)[0]] = fp.read()
    return templates

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
