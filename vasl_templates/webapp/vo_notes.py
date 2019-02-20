""" Main webapp handlers. """
# Pokhara, Nepal (DEC/18).

import os
import logging
from collections import defaultdict

from flask import render_template, jsonify, abort

from vasl_templates.webapp import app, globvars
from vasl_templates.webapp.files import FileServer
from vasl_templates.webapp.utils import resize_image_response, is_image_file, is_empty_file

# ---------------------------------------------------------------------

@app.route( "/vehicles/notes" )
def get_vehicle_notes():
    """Return the Chapter H vehicle notes."""
    return jsonify( globvars.vo_notes[ "vehicles" ] )

@app.route( "/ordnance/notes" )
def get_ordnance_notes():
    """Return the Chapter H ordnance notes."""
    return jsonify( globvars.vo_notes[ "ordnance" ] )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def load_vo_notes(): #pylint: disable=too-many-statements,too-many-locals,too-many-branches
    """Load the Chapter H vehicle/ordnance notes."""

    # locate the data directory
    dname = app.config.get( "CHAPTER_H_NOTES_DIR" )
    if not dname:
        globvars.vo_notes = { "vehicles": {}, "ordnance": {} }
        globvars.file_server = None
        return
    dname = os.path.abspath( dname )
    if not os.path.isdir( dname ):
        raise RuntimeError( "Missing Chapter H directory: {}".format( dname ) )
    file_server = FileServer( dname )

    # generate a list of extension ID's
    extn_ids = {}
    if globvars.vasl_mod:
        extns = globvars.vasl_mod.get_extns()
        extn_ids = set( e[1]["extensionId"] for e in extns )

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

    # load the vehicle/ordnance notes
    for root,_,fnames in os.walk( dname, followlinks=True ):
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
        ma_notes = {}
        for fname in fnames:
            extn = os.path.splitext( fname )[1].lower()
            if is_image_file( extn ):
                key = os.path.splitext(fname)[0]
                if not all( ch.isdigit() or ch in (".") for ch in key ):
                    logging.warning( "Unexpected vehicle/ordnance note key: %s", key )
                fname = os.path.join( root, fname )
                if is_empty_file( fname ):
                    continue # nb: ignore placeholder files
                prefix = os.path.commonpath( [ dname, fname ] )
                if prefix:
                    if extn_id:
                        key = "{}:{}".format( extn_id, key )
                    vo_notes[vo_type2][nat2][key] = fname[len(prefix)+1:]
                else:
                    logging.warning( "Unexpected vehicle/ordnance note path: %s", fname )
            elif extn == ".html":
                key = get_ma_note_key( nat2, fname )
                if extn_id:
                    key = "{}:{}".format( extn_id, key )
                fname = os.path.join( root, fname )
                with open( fname, "r" ) as fp:
                    buf = fp.read().strip()
                    if not buf:
                        continue # nb: ignore placeholder files
                    if buf.startswith( "<p>" ):
                        buf = buf[3:].strip()
                    if "&half;" in buf:
                        # NOTE: VASSAL doesn't like this, use "frac12;" :-/
                        logging.warning( "Found &half; in HTML: %s", fname )
                    ma_notes[key] = buf
        if "multi-applicable" in vo_notes[ vo_type2 ][ nat2 ]:
            vo_notes[ vo_type2 ][ nat2 ][ "multi-applicable" ].update( ma_notes )
        else:
            vo_notes[ vo_type2 ][ nat2 ][ "multi-applicable" ] = ma_notes

    # update nationality variants with the notes from their base nationality
    for vo_type2 in vo_notes:
        # FUDGE! The Chinese GMD don't have any vehicles/ordnance of their own, so we have to do this manually.
        if "chinese" in vo_notes[vo_type2]:
            vo_notes[vo_type2]["chinese~gmd"] = vo_notes[vo_type2]["chinese"]

    # install the vehicle/ordnance notes
    globvars.vo_notes = { k: dict(v) for k,v in vo_notes.items() }
    globvars.file_server = file_server

# ---------------------------------------------------------------------

@app.route( "/<vo_type>/<nat>/note/<key>" )
def get_vo_note( vo_type, nat, key ):
    """Return a Chapter H vehicle/ordnance note."""

    # locate the file
    vo_notes = globvars.vo_notes[ vo_type ]
    fname = vo_notes.get( nat, {} ).get( key )
    if not fname:
        abort( 404 )
    if not globvars.file_server:
        abort( 404 )
    resp = globvars.file_server.serve_file( fname, ignore_empty=True )
    if not resp:
        abort( 404 )

    default_scaling = app.config.get( "CHAPTER_H_IMAGE_SCALING", 100 )
    return resize_image_response( resp, default_scaling=default_scaling )

# ---------------------------------------------------------------------

@app.route( "/<vo_type>/<nat>/notes" )
def get_vo_notes_report( nat, vo_type ):
    """Get a Chapter H vehicles/ordnance notes report."""

    # generate the report
    return render_template( "vo-notes-report.html",
        NATIONALITY = nat,
        VO_TYPE = vo_type
    )
