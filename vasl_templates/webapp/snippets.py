""" Webapp handlers. """

import os
import json
import re
import zipfile
import io
import base64
import threading

from flask import request, jsonify, send_file, abort
from PIL import Image

from vasl_templates.webapp import app
from vasl_templates.webapp.utils import SimpleError
from vasl_templates.webapp.config.constants import DATA_DIR
from vasl_templates.webapp.webdriver import WebDriver

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

    # NOTE: Similarly, we always load the default extras templates, and user-defined template packs
    # can add to them, or modify existing ones, but not remove them.
    dname = os.path.join( base_dir, "extras" )
    if os.path.isdir( dname ):
        _, extra_templates = _do_get_template_pack( dname )
        for key,val in extra_templates.items():
            data["templates"]["extras/"+key] = val

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
                fname2 = os.path.split(fname)[1]
                if fname2.lower() == "nationalities.json":
                    data["nationalities"].update( json.loads( fdata ) )
                    continue
                if fname.startswith( "extras" + os.sep ):
                    fname2 = "extras/" + fname2
                data["templates"][ fname2 ] = fdata

    return jsonify( data )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _do_get_template_pack( dname ):
    """Get the specified template pack."""
    dname = os.path.abspath( dname )
    if not os.path.isdir( dname ):
        abort( 404 )
    nationalities, templates = {}, {}
    for root,_,fnames in os.walk(dname):
        for fname in fnames:
            # add the next file to the results
            words = os.path.splitext( fname )
            fname = os.path.join( root, fname )
            with open( fname, "r" ) as fp:
                if fname.lower() == "nationalities.json":
                    nationalities = json.load( fp )
                    continue
                if words[1] == ".j2":
                    fname2 = words[0]
                    relpath = os.path.relpath( os.path.abspath(fname), dname )
                    if relpath.startswith( "extras" + os.sep ):
                        fname2 = "extras/" + fname2
                    templates[fname2] = fp.read()
    return nationalities, templates

# ---------------------------------------------------------------------

last_snippet_image = None # nb: for the test suite

@app.route( "/snippet-image", methods=["POST"] )
def make_snippet_image():
    """Generate an image for a snippet."""
    # Kathmandu, Nepal (DEC/18)

    # generate an image for the snippet
    snippet = request.data.decode( "utf-8" )
    try:
        with WebDriver.get_instance() as webdriver:
            img = webdriver.get_snippet_screenshot( None, snippet )
    except SimpleError as ex:
        return "ERROR: {}".format( ex )

    # get the image data
    buf = io.BytesIO()
    img.save( buf, format="PNG" )
    buf.seek( 0 )
    img_data = buf.read()
    global last_snippet_image
    last_snippet_image = img_data

    return base64.b64encode( img_data )

# ---------------------------------------------------------------------

@app.route( "/flags/<nat>" )
def get_flag( nat ):
    """Get a flag image."""
    return _get_small_image(
        "static/images/flags/", nat,
        app.config.get( "DEFAULT_FLAG_HEIGHT", 11 )
    )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

_small_image_cache = {}
_small_image_cache_lock = threading.Lock()

def _get_small_image( base_dir, key, default_height ):
    """Get a small image (cached)."""

    # locate the image file
    if not re.search( "^[-a-z~]+$", key ):
        abort( 404 )
    fname = os.path.join( base_dir, key+".png" )

    # check how we should resize the image
    # NOTE: Resizing images in the HTML snippets looks dreadful (presumably
    # because VASSAL's HTML engine is so ancient), so we do it ourself :-/
    height = int( request.args.get( "height", default_height ) )
    if height <= 0:
        abort( 400 )

    with _small_image_cache_lock:

        # check if we have the image in the cache
        cache_key = ( key, height )
        if cache_key not in _small_image_cache:

            # nope - load it
            with app.open_resource( fname, "rb" ) as fp:
                img = Image.open( fp )
                # resize the image
                height = int( height )
                if height > 0:
                    width = img.size[0] / ( float(img.size[1]) / height )
                    width = int( width + 0.5 )
                    img = img.resize( (width,height), Image.ANTIALIAS )
                # add the image to the cache
                buf = io.BytesIO()
                img.save( buf, format="PNG" )
                buf.seek( 0 )
                _small_image_cache[ cache_key ] = buf.read()

        # return the flag image
        img_data =_small_image_cache[ cache_key ]
        return send_file( io.BytesIO(img_data), mimetype="image/png" )
