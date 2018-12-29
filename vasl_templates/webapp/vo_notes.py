""" Main webapp handlers. """
# Pokhara, Nepal (DEC/18).

import os
import threading
import logging
from collections import defaultdict

from flask import render_template, jsonify, abort

from vasl_templates.webapp import app
from vasl_templates.webapp.files import FileServer
from vasl_templates.webapp.utils import resize_image_response, is_image_file, is_empty_file

_vo_notes_lock = threading.RLock() # nb: this controls the cached V/O notes and the FileServer
_cached_vo_notes = None
_vo_notes_file_server = None

# ---------------------------------------------------------------------

@app.route( "/vehicles/notes" )
def get_vehicle_notes():
    """Return the Chapter H vehicle notes."""
    vo_notes = _do_get_vo_notes( "vehicles" )
    return jsonify( vo_notes )

@app.route( "/ordnance/notes" )
def get_ordnance_notes():
    """Return the Chapter H ordnance notes."""
    vo_notes = _do_get_vo_notes( "ordnance" )
    return jsonify( vo_notes )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _do_get_vo_notes( vo_type ): #pylint: disable=too-many-locals,too-many-branches
    """Load the Chapter H notes."""

    # check if we already have the vehicle/ordnance notes
    with _vo_notes_lock:
        global _cached_vo_notes
        if _cached_vo_notes:
            return _cached_vo_notes[ vo_type ]

    # locate the data directory
    dname = app.config.get( "CHAPTER_H_NOTES_DIR" )
    if not dname:
        return {}
    dname = os.path.abspath( dname )
    if not os.path.isdir( dname ):
        abort( 404 )
    with _vo_notes_lock:
        global _vo_notes_file_server
        _vo_notes_file_server = FileServer( dname )

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

    # load the vehicle/ordnance notes
    vo_notes = { "vehicles": defaultdict(dict), "ordnance": defaultdict(dict) }
    for root,_,fnames in os.walk( dname, followlinks=True ):
        dname2, vo_type2 = os.path.split( root )
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
                    vo_notes[vo_type2][nat2][key] = fname[len(prefix)+1:]
                else:
                    logging.warning( "Unexpected vehicle/ordnance note path: %s", fname )
            elif extn == ".html":
                key = get_ma_note_key( nat2, fname )
                with open( os.path.join(root,fname), "r" ) as fp:
                    buf = fp.read().strip()
                    if not buf:
                        continue # nb: ignore placeholder files
                    if buf.startswith( "<p>" ):
                        buf = buf[3:].strip()
                    ma_notes[key] = buf
        vo_notes[vo_type2][nat2]["multi-applicable"] = ma_notes

    with _vo_notes_lock:
        # install the new vehicle/ordnance notes
        _cached_vo_notes = { k: dict(v) for k,v in vo_notes.items() }

        return _cached_vo_notes[ vo_type ]

# ---------------------------------------------------------------------

@app.route( "/<vo_type>/<nat>/note/<key>" )
def get_vo_note( vo_type, nat, key ):
    """Return a Chapter H vehicle/ordnance note."""

    # locate the file
    with _vo_notes_lock:
        # NOTE: We assume that the client has already loaded the vehicle/ordnance notes.
        if not _vo_notes_file_server:
            abort( 404 )
        vo_notes = _do_get_vo_notes( vo_type )
        fname = vo_notes.get( nat, {} ).get( key )
        if not fname:
            abort( 404 )
        # nb: we ignore placeholder files (return 404 for empty files)
        resp = _vo_notes_file_server.serve_file( fname, ignore_empty=True )
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
