""" Main webapp handlers. """
# Pokhara, Nepal (DEC/18).

import os
import io
import re
import copy
import logging
from collections import defaultdict

from flask import request, render_template, jsonify, send_file, abort, Response, url_for

from vasl_templates.webapp import app, globvars
from vasl_templates.webapp.files import FileServer
from vasl_templates.webapp.webdriver import WebDriver
from vasl_templates.webapp.utils import read_text_file, resize_image_response, is_image_file, is_empty_file

# ---------------------------------------------------------------------

@app.route( "/vehicles/notes" )
def get_vehicle_notes():
    """Return the Chapter H vehicle notes."""
    if not globvars.vo_notes:
        abort( 404 )
    return jsonify( globvars.vo_notes[ "vehicles" ] )

@app.route( "/ordnance/notes" )
def get_ordnance_notes():
    """Return the Chapter H ordnance notes."""
    if not globvars.vo_notes:
        abort( 404 )
    return jsonify( globvars.vo_notes[ "ordnance" ] )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def load_vo_notes( msg_store ): #pylint: disable=too-many-statements,too-many-locals,too-many-branches
    """Load the Chapter H vehicle/ordnance notes."""

    # locate the data directory
    dname = app.config.get( "CHAPTER_H_NOTES_DIR" )
    if dname:
        # NOTE: If the Chapter H directory has been configured but is incorrect, we want to keep going,
        # since this may well happen when running in a container (the directory has to be always configured,
        # but the user may not have mapped it to a directory outside the container).
        dname = os.path.abspath( dname )
        if not os.path.isdir( dname ):
            error_msg = "Missing Chapter H directory: {}".format( dname )
            logging.error( "%s", error_msg )
            if msg_store:
                msg_store.error( error_msg )
            dname = None
    if not dname:
        globvars.vo_notes = { "vehicles": {}, "ordnance": {} }
        globvars.vo_notes_file_server = None
        return
    file_server = FileServer( dname )

    # generate a list of extension ID's
    extn_ids = set()
    if globvars.vasl_mod:
        extns = globvars.vasl_mod.get_extns()
        extn_ids = set( e[1]["extensionId"] for e in extns )
    extn_ids.update( [ "kfw-un", "kfw-comm" ] )

    def get_ma_note_key( nat, fname ):
        """Get the key for a multi-applicable note."""
        # NOTE: Windows has a case-insensitive file system, so we adopt the following convention:
        # - filenames are assumed to be upper-case e.g. "a.html" holds Multi-Applicable Note "A"
        # - unless it has a trailing underscore, in which it is interpreted as lower-case
        #   e.g. "a_.html" holds Multi-Applicable Note "a".
        fname = os.path.splitext( fname )[0]
        if fname.endswith( "_" ):
            return fname[:-1].lower()
        else:
            fname = fname.upper()
            # NOTE: Allied/Axis Minor multi-applicable notes have keys like "Gr" and "Da",
            # but we need to be careful we don't transform keys like "AA" and "BB".
            if nat in ("allied-minor","axis-minor") and len(fname) == 2 and fname[0] != fname[1]:
                fname = fname[0] + fname[1].lower()
            return fname

    # initialize
    vo_notes = { "vehicles": defaultdict(dict), "ordnance": defaultdict(dict) }
    # NOTE: We don't have any data files for these vehicles/ordnance, but they have
    # multi-applicable notes, so we force them to appear in the final results.
    vo_notes["vehicles"]["anzac"] = {}
    vo_notes["ordnance"]["indonesian"] = {}
    vo_note_layout_width = app.config.get( "VO_NOTE_LAYOUT_WIDTH", 500 )

    # load the vehicle/ordnance notes
    for root,_,fnames in os.walk( dname, followlinks=True ):

        # initialize
        dname2, vo_type2 = os.path.split( root )
        if vo_type2 in extn_ids:
            extn_id = vo_type2
            dname2, vo_type2 = os.path.split( dname2 )
        else:
            extn_id = None
        if vo_type2 not in ("vehicles","ordnance","landing-craft"):
            continue
        if os.path.split( dname2 )[1] == "tests":
            continue
        nat = os.path.split( dname2 )[1]
        if vo_type2 == "landing-craft":
            vo_type2, nat2 = "vehicles", "landing-craft"
        else:
            nat2 = nat

        # process each file in the next directory
        ma_notes = {}
        for fname in fnames:

            # ignore placeholder files
            fname = os.path.join( root, fname )
            if is_empty_file( fname ):
                continue

            # figure out what kind of file we have
            extn = os.path.splitext( fname )[1].lower()
            if is_image_file( extn ):

                # image file - check if this looks like a vehicle/ordnance note
                key = os.path.splitext( os.path.split( fname )[1] )[0]
                if not all( ch.isdigit() or ch == "." for ch in key ):
                    # nope (this could be e.g. an image that's part of an HTML vehicle/ordnance note)
                    continue

                # yup - save it as a vehicle/ordnance note
                if extn_id:
                    key = "{}:{}".format( extn_id, key )
                # NOTE: We only do this if we don't already have an HTML version.
                if not vo_notes.get( vo_type2, {} ).get( nat2, {} ).get( key ):
                    rel_path = os.path.relpath( fname, dname )
                    vo_notes[vo_type2][nat2][key] = rel_path.replace( "\\", "/" )

            elif extn == ".html":

                # HTML file - read the content
                fname = os.path.join( root, fname )
                html_content = read_text_file( fname ).strip()
                if "&half;" in html_content:
                    # NOTE: VASSAL doesn't like this, use "frac12;" :-/
                    logging.warning( "Found &half; in HTML: %s", fname )

                # check what kind of file we have
                key = get_ma_note_key( nat2, os.path.split(fname)[1] )
                if re.search( r"^\d+(\.\d+)?$", key ):

                    # FUDGE! The HTML version of the Chapter H content contain a lot of notes
                    # that start with "<p> &dagger;". We detect these and add a CSS class.
                    # Larger blocks of content need to be wrapped in a <div>.
                    html_content = re.sub( r"^<(p|div)>\s*&dagger;", r"<\1 class='dagger-note'> &dagger;",
                        html_content,
                        flags=re.MULTILINE
                    )

                    # check if the content is specifying its own layout
                    if "<!-- vasl-templates:manual-layout -->" not in html_content:
                        # nope - use the default one
                        html_content = "<table width='{}'><tr><td>\n{}\n</table>".format(
                            vo_note_layout_width, html_content
                        )

                    # save it as a vehicle/ordnance note
                    if extn_id:
                        key = "{}:{}".format( extn_id, key )
                    rel_path = os.path.relpath( os.path.split(fname)[0], dname )
                    vo_notes[ vo_type2 ][ nat2 ][ key ] = _fixup_urls(
                        html_content,
                        "{{CHAPTER_H}}/" + rel_path.replace( "\\", "/" ) + "/"
                    )

                else:

                    # save it as a multi-applicable note
                    if extn_id:
                        key = "{}:{}".format( extn_id, key )
                    if html_content.startswith( "<p>" ):
                        html_content = html_content[3:].strip()
                    rel_path = os.path.relpath( os.path.split(fname)[0], dname )
                    ma_notes[ key ] = _fixup_urls(
                        html_content,
                        "{{CHAPTER_H}}/" + rel_path.replace( "\\", "/" ) + "/"
                    )

        if "multi-applicable" in vo_notes[ vo_type2 ][ nat2 ]:
            vo_notes[ vo_type2 ][ nat2 ][ "multi-applicable" ].update( ma_notes )
        else:
            vo_notes[ vo_type2 ][ nat2 ][ "multi-applicable" ] = ma_notes

    # update nationality variants with the notes from their base nationality
    for vo_type2 in vo_notes:
        # FUDGE! Some nationalities don't have any vehicles/ordnance of their own, so we have to do this manually.
        # NOTE: We do a deep copy so that these new nationalities don't get affected by changes we make
        # to the base nationality later (e.g. adding K:FW counters to the British).
        if "chinese" in vo_notes[vo_type2]:
            vo_notes[vo_type2]["chinese~gmd"] = copy.deepcopy( vo_notes[vo_type2]["chinese"] )
        if "british" in vo_notes[vo_type2]:
            vo_notes[vo_type2]["british~canadian"] = copy.deepcopy( vo_notes[vo_type2]["british"] )
            vo_notes[vo_type2]["british~newzealand"] = copy.deepcopy( vo_notes[vo_type2]["british"] )
            vo_notes[vo_type2]["british~australian"] = copy.deepcopy( vo_notes[vo_type2]["british"] )

    def install_kfw_vo_notes( nat, vo_type, extn_id, include ):
        """Install the K:FW vehicle/ordnance notes into the specified nationality."""
        target_vo_notes = vo_notes[vo_type].get( nat )
        if not target_vo_notes:
            return
        kfw_vo_notes = vo_notes[vo_type].get( extn_id )
        if not kfw_vo_notes:
            return
        target_vo_notes.update( {
            "{}:{}".format( extn_id, key ): val
            for key,val in kfw_vo_notes.items()
            if not include or include( int(key) )
        } )
    def install_kfw_ma_notes( nat, vo_type, kfw_ma_notes, extn_id ):
        """Install the K:FW vehicle/ordnance multi-applicable notes into the specified nationality."""
        if not kfw_ma_notes:
            return
        if nat not in vo_notes[vo_type]:
            vo_notes[vo_type][nat] = {}
        ma_notes = vo_notes[vo_type][nat].get( "multi-applicable" )
        if not ma_notes:
            ma_notes = vo_notes[vo_type][nat]["multi-applicable"] = {}
        ma_notes.update( {
            "{}:{}".format( extn_id, key ): val
            for key,val in kfw_ma_notes.items()
        } )

    # install the UN vehicle/ordnance notes and multi-applicable notes
    kfw_ma_notes = vo_notes["vehicles"].get( "kfw-un", {} ).pop( "multi-applicable", None )
    for nat in ("american","kfw-rok","kfw-ounc"):
        install_kfw_ma_notes( nat, "vehicles", kfw_ma_notes, "kfw-un" )
        install_kfw_vo_notes( nat, "vehicles", "kfw-un", lambda key: key <= 33 or key >= 54 )
    install_kfw_ma_notes( "british", "vehicles", kfw_ma_notes, "kfw-un" )
    install_kfw_vo_notes( "british", "vehicles", "kfw-un", lambda key: key >= 34 )
    kfw_ma_notes = vo_notes["ordnance"].get( "kfw-un", {} ).pop( "multi-applicable", None )
    for nat in ("american","kfw-rok","kfw-ounc"):
        install_kfw_ma_notes( nat, "ordnance", kfw_ma_notes, "kfw-un" )
        install_kfw_vo_notes( nat, "ordnance", "kfw-un", lambda key: key <= 13 or key >= 21 )
    install_kfw_ma_notes( "british", "ordnance", kfw_ma_notes, "kfw-un" )
    install_kfw_vo_notes( "british", "ordnance", "kfw-un", lambda key: key >= 14 )

    # install the Communist vehicle/ordnance notes and multi-applicable notes
    kfw_ma_notes = vo_notes["vehicles"].get( "kfw-comm", {} ).pop( "multi-applicable", None )
    install_kfw_ma_notes( "kfw-kpa", "vehicles", kfw_ma_notes, "kfw-comm" )
    install_kfw_vo_notes( "kfw-kpa", "vehicles", "kfw-comm", None )
    kfw_ma_notes = vo_notes["ordnance"].get( "kfw-comm", {} ).pop( "multi-applicable", None )
    for nat in ("kfw-kpa","kfw-cpva"):
        install_kfw_ma_notes( nat, "ordnance", kfw_ma_notes, "kfw-comm" )
    install_kfw_vo_notes( "kfw-kpa", "ordnance", "kfw-comm", lambda key: key <= 15 )
    install_kfw_vo_notes( "kfw-cpva", "ordnance", "kfw-comm", lambda key: key >= 16 )

    # install the vehicle/ordnance notes
    globvars.vo_notes = { k: dict(v) for k,v in vo_notes.items() }
    globvars.vo_notes_file_server = file_server

def _fixup_urls( html, url_stem ):
    """Fixup URL's to Chapter H files."""
    matches = list( re.finditer( r"<img [^>]*src=(['\"])(.*?)\1", html ) )
    for mo in reversed(matches):
        before, after = html[:mo.start(2)], html[mo.start(2):]
        if after.startswith( ( "http://", "https://", "file://" ) ):
            continue
        html = before + url_stem + after
    return html

# ---------------------------------------------------------------------

@app.route( "/<vo_type>/<nat>/note/<key>" )
def get_vo_note( vo_type, nat, key ):
    """Return a Chapter H vehicle/ordnance note."""

    # get the vehicle/ordnance note
    vo_notes = globvars.vo_notes[ vo_type ]
    vo_note = vo_notes.get( nat, {} ).get( key )
    if not vo_note:
        abort( 404 )
    if not globvars.vo_notes_file_server:
        abort( 404 )

    # serve the file
    if is_image_file( vo_note ):
        resp = globvars.vo_notes_file_server.serve_file( vo_note, ignore_empty=True )
        if not resp:
            abort( 404 )
        default_scaling = app.config.get( "CHAPTER_H_IMAGE_SCALING", 100 )
        return resize_image_response( resp, default_scaling=default_scaling )
    else:
        buf = _make_vo_note_html( vo_note )
        if request.args.get( "f" ) == "html":
            # return the content as HTML
            return Response( buf, mimetype="text/html" )
        else:
            # return the content as an image
            # NOTE: We offer this option since VASSAL's HTML engine is so ancient, it doesn't support
            # floating images (which we really need), either via CSS "float", or the HTML "align" attribute.
            # NOTE: We need our own WebDriver instance in case the user is trying to generate a snippet image,
            # which will use the shared instance (thus locking it), but vehicle/ordnance notes can contain
            # a link that calls us here to generate the Chapter H content as an image, and if this 2nd request
            # gets handled in a different thread (which it certainly will, since the 1st request is still
            # in progress), we will deadlock waiting for the shared instance to become available.
            with WebDriver.get_instance( "vo_note" ) as webdriver:
                img = webdriver.get_snippet_screenshot( None, buf )
            buf = io.BytesIO()
            img.save( buf, format="PNG" )
            buf.seek( 0 )
            return send_file( buf, mimetype="image/png" )

def _make_vo_note_html( vo_note ):
    """Generate the HTML for a vehicle/ordnance note."""

    # initialize
    url_root = request.url_root
    if url_root.endswith( "/" ):
        url_root = url_root[:-1]

    # inject the CSS (we do it like this since VASSAL doesn't support <link> :-/)
    css = [
        globvars.template_pack.get( "css", {} ).get( "common", "" ),
        globvars.template_pack.get( "css", {} ).get( "ob_vo_note", "" ),
    ]
    if any( css ):
        vo_note = "<head>\n<style>\n{}\n</style>\n</head>\n\n{}".format( "\n".join(css), vo_note )

    # update any parameters
    vo_note = vo_note.replace( "{{CHAPTER_H}}", url_root+"/chapter-h" )
    vo_note = vo_note.replace( "{{IMAGES_BASE_URL}}", url_root+url_for("static",filename="images") )

    return vo_note

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@app.route( "/chapter-h/<path:path>" )
def get_chapter_h_file( path ):
    """Return a Chapter H file."""
    if not globvars.vo_notes_file_server:
        abort( 404 )
    return globvars.vo_notes_file_server.serve_file( path, ignore_empty=True )

# ---------------------------------------------------------------------

@app.route( "/<vo_type>/<nat>/notes" )
def get_vo_notes_report( nat, vo_type ):
    """Get a Chapter H vehicles/ordnance notes report."""

    # generate the report
    return render_template( "vo-notes-report.html",
        NATIONALITY = nat,
        VO_TYPE = vo_type
    )
