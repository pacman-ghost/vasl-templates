""" Webapp handlers. """

import os
import json
import re
import zipfile
import io
import base64
import threading
import urllib.request

from flask import request, jsonify, send_file, abort
from PIL import Image

from vasl_templates.webapp import app, globvars
from vasl_templates.webapp.config.constants import DATA_DIR
from vasl_templates.webapp.webdriver import WebDriver
from vasl_templates.webapp.utils import read_text_file

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
    if not globvars.template_pack:
        load_default_template_pack()
    return jsonify( globvars.template_pack )

def load_default_template_pack(): #pylint: disable=too-many-locals
    """Load the default template pack."""

    # initialize
    # NOTE: We always start with the default nationalities data. Unlike template files,
    # user-defined template packs can add to it, or modify existing entries, but not replace it.
    base_dir = os.path.join(
        app.config.get( "DATA_DIR", DATA_DIR ),
        "default-template-pack/"
    )
    data = { "templates": {} }
    with open( os.path.join( base_dir, "nationalities.json" ), "r", encoding="utf-8" ) as fp:
        data["nationalities"] = json.load( fp )
    with open( os.path.join( base_dir, "national-capabilities.json" ), "r", encoding="utf-8" ) as fp:
        data["national-capabilities"] = json.load( fp )

    # NOTE: Similarly, we always load the default extras templates, and user-defined template packs
    # can add to them, or modify existing ones, but not remove them.
    dname = os.path.join( base_dir, "extras" )
    if os.path.isdir( dname ):
        _, extra_templates, _, _ = _do_get_template_pack( dname )
        for key,val in extra_templates.items():
            data["templates"]["extras/"+key] = val

    # check if a default template pack has been configured
    # NOTE: The Docker container configures this setting via an environment variable.
    global default_template_pack
    default_template_pack = os.environ.get( "DEFAULT_TEMPLATE_PACK", default_template_pack )
    if default_template_pack:
        dname = default_template_pack
        data["_path_"] = dname
    else:
        # nope - use our default template pack
        dname = base_dir

    # check if we're loading the template pack from a directory
    if os.path.isdir( dname ):
        # yup - return the files in it
        nat, templates, css, includes =_do_get_template_pack( dname )
    else:
        # extract the template pack files from the specified ZIP file
        nat, templates, css, includes =_do_get_template_pack_from_zip( dname )
    data["nationalities"].update( nat )
    data["templates"] = templates
    data["css"] = css
    data["includes"] = includes

    # FUDGE! In early versions of this program, the vehicles and ordnance templates were different
    # (e.g. because only vehicles can be radioless, only ordnance can be QSU), but once everything
    # was handled via generic capabilities, they became the same. We would therefore like to have
    # a single template file handle both vehicles and ordnance, but the program had been architected
    # in such a way that vehicles and ordnance snippets are generated from their own templates,
    # so rather than re-architect the program, we maintain separate templates, that just happen
    # to be read from the same file. This causes a bit of stuffing around when the code needs to know
    # what file a template comes from (e.g. loading a template pack), but it's mostly transparent...
    templates = data.get( "templates" )
    if templates:
        if "ob_vo" in templates:
            templates["ob_vehicles"] = templates["ob_ordnance"] = templates.pop( "ob_vo" )
        if "ob_vo_note" in templates:
            templates["ob_vehicle_note"] = templates["ob_ordnance_note"] = templates.pop( "ob_vo_note" )
        if "ob_ma_notes" in templates:
            templates["ob_vehicles_ma_notes"] = templates["ob_ordnance_ma_notes"] = templates.pop( "ob_ma_notes" )

    globvars.template_pack = data

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _do_get_template_pack( dname ):
    """Get the specified template pack."""
    dname = os.path.abspath( dname )
    if not os.path.isdir( dname ):
        abort( 404 )
    nationalities, templates, css, includes = {}, {}, {}, {}
    for root,_,fnames in os.walk( dname ):
        for fname in fnames:
            # add the next file to the results
            fname_stem, extn = os.path.splitext( fname )
            fname = os.path.join( root, fname  )
            buf = read_text_file( fname )
            if (fname_stem, extn) == ("nationalities", ".json"):
                nationalities = json.loads( buf )
                continue
            if extn == ".j2":
                relpath = os.path.relpath( os.path.abspath(fname), dname )
                if relpath.startswith( "extras" + os.sep ):
                    fname_stem = "extras/" + fname_stem
                templates[ fname_stem ] = buf
            elif extn == ".css":
                css[ fname_stem ] = buf
            elif extn == ".include":
                includes[ fname_stem ] = buf
    return nationalities, templates, css, includes

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _do_get_template_pack_from_zip( fname ):
    """Get the specified template pack."""
    fname = os.path.abspath( fname )
    if not os.path.isfile( fname ):
        abort( 404 )
    nationalities, templates, css, includes = {}, {}, {}, {}
    with zipfile.ZipFile( fname, "r" ) as zip_file:
        for zip_fname in zip_file.namelist():
            if zip_fname.endswith( "/" ):
                continue
            # extract the next file
            fdata = zip_file.read( zip_fname ).decode( "utf-8" )
            fname2 = os.path.split( zip_fname )[1]
            # add the file to the results
            if fname2.lower() == "nationalities.json":
                nationalities = json.loads( fdata )
                continue
            fname2, extn = os.path.splitext( fname2 )
            if zip_fname.startswith( "extras" + os.sep ):
                fname2 = "extras/" + fname2
            if extn == ".css":
                css[ fname2 ] = fdata
            elif extn == ".include":
                includes[ fname2 ] = fdata
            else:
                templates[ fname2 ] = fdata
    return nationalities, templates, css, includes

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
    except Exception as ex: #pylint: disable=broad-except
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

    # initialize
    if not re.search( "^[-a-z~]+$", nat ):
        abort( 404 )
    key = "flags:{}".format( nat )
    # NOTE: Most of the flags are at the larger size, so we default to that size (since we get better results
    # doing that, and scaling down to the smaller size as needed, rather than the other way around).
    height = app.config.get( "DEFAULT_FLAG_HEIGHT", 13 )

    # check if a custom flag has been configured
    if globvars.template_pack:
        fname = globvars.template_pack.get( "nationalities", {} ).get( nat, {} ).get( "flag" )
        if fname:
            if fname.startswith( ("http://","https://") ):
                with urllib.request.urlopen( fname ) as resp:
                    return _get_small_image( resp, key, height )
            else:
                with open( fname, "rb" ) as fp:
                    return _get_small_image( fp, key, height )

    # serve the standard flag
    fname = os.path.join( "static/images/flags/", nat+".png" )
    try:
        with app.open_resource( fname, "rb" ) as fp:
            return _get_small_image( fp, key, height )
    except FileNotFoundError:
        abort( 404 )
        return None # stop pylint from complaining :-/

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

_small_image_cache = {}
_small_image_cache_lock = threading.Lock()

def _get_small_image( fp, key, default_height ):
    """Get a small image (cached)."""

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
