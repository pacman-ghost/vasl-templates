""" Webapp handlers. """

import os
import json
import zipfile

from flask import jsonify, abort

from vasl_templates.webapp import app
from vasl_templates.webapp.config.constants import DATA_DIR

default_template_pack = None

# ---------------------------------------------------------------------

@app.route( "/template-pack" )
def get_template_pack():
    """Return a template pack.

    Loading template packs is currently handled in the front-end, but we need
    this entry point for the webapp to get the *default* template pack.
    If, in the future, we support loading other template packs from the backend,
    we can add a parameter here to specify which one to return.
    """

    # initialize
    # NOTE: We always start with the default nationalities data. Unlike template files,
    # user-defined template packs can add to it, or modify existing entries, but not replace it.
    base_dir = os.path.join(
        app.config.get( "DATA_DIR", DATA_DIR ),
        "default-template-pack/"
    )
    data = { "templates": {} }
    fname = os.path.join( base_dir, "nationalities.json" )
    with open(fname,"r") as fp:
        data["nationalities"] = json.load( fp )

    # check if a default template pack has been configured
    if default_template_pack:
        dname = default_template_pack
        data["_path_"] = dname
    else:
        # nope - use our default template pack
        dname = base_dir

    # check if we're loading the template pack from a directory
    if os.path.isdir( dname ):
        # yup - return the files in it
        nat, templates =_do_get_template_pack( dname )
        data["nationalities"].update( nat )
        data["templates"] = templates
    else:
        # extract the template pack files from the specified ZIP file
        if not os.path.isfile( dname ):
            return jsonify( { "error": "Can't find template pack: {}".format(dname) } )
        data["templates"] = {}
        with zipfile.ZipFile( dname, "r" ) as zip_file:
            for fname in zip_file.namelist():
                if fname.endswith( "/" ):
                    continue
                fdata = zip_file.read( fname ).decode( "utf-8" )
                fname = os.path.split(fname)[1]
                if fname.lower() == "nationalities.json":
                    data["nationalities"].update( json.loads( fdata ) )
                    continue
                data["templates"][ os.path.splitext(fname)[0] ] = fdata

    return jsonify( data )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _do_get_template_pack( dname ):
    """Get the specified template pack."""
    if not os.path.isdir( dname ):
        abort( 404 )
    nationalities, templates = {}, {}
    for root,_,fnames in os.walk(dname):
        for fname in fnames:
            # add the next file to the results
            with open( os.path.join(root,fname), "r" ) as fp:
                if fname.lower() == "nationalities.json":
                    nationalities = json.load( fp )
                    continue
                words = os.path.splitext( fname )
                if words[1] == ".j2":
                    templates[words[0]] = fp.read()
    return nationalities, templates
