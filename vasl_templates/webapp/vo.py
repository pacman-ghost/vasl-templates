""" Main webapp handlers. """

import os
import json
import logging

from flask import request, render_template, jsonify, abort

from vasl_templates.webapp import app
from vasl_templates.webapp.config.constants import DATA_DIR
from vasl_templates.webapp.file_server.vasl_mod import get_vasl_mod

# ---------------------------------------------------------------------

@app.route( "/vehicles" )
def get_vehicle_listings():
    """Return the vehicle listings."""
    return _do_get_listings( "vehicles" )

@app.route( "/ordnance" )
def get_ordnance_listings():
    """Return the ordnance listings."""
    return _do_get_listings( "ordnance" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _do_get_listings( vo_type ): #pylint: disable=too-many-locals,too-many-branches
    """Load the vehicle/ordnance listings."""

    # locate the data directory
    if request.args.get( "report" ):
        dname = DATA_DIR # nb: always use the real data for reports, not the test fixtures
    else:
        dname = app.config.get( "DATA_DIR", DATA_DIR )
    dname = os.path.join( dname, vo_type )
    if not os.path.isdir( dname ):
        abort( 404 )

    # load the listings
    listings = {}
    minor_nats = { "allied-minor": set(), "axis-minor": set() }
    for root,_,fnames in os.walk(dname):
        for fname in fnames:
            if os.path.splitext(fname)[1] != ".json":
                continue
            nat = os.path.splitext( os.path.split(fname)[1] )[ 0 ]
            if os.path.split(root)[1] in ("allied-minor","axis-minor"):
                minor_type = os.path.split( root )[1]
                if nat == "common":
                    nat = minor_type + "-common"
                else:
                    minor_nats[minor_type].add( nat )
            with open( os.path.join(root,fname), "r" ) as fp:
                listings[nat] = json.load( fp )

    # merge common entries
    if request.args.get( "merge_common" ) == "1":
        # merge common Allied/Axis Minor vehicles/ordnance
        for minor_type in ("allied-minor","axis-minor"):
            if minor_type+"-common" not in listings:
                continue
            for nat in minor_nats[minor_type]:
                listings[nat].extend( listings[minor_type+"-common"] )
            del listings[ minor_type+"-common" ]
        # merge landing craft
        if vo_type == "vehicles":
            for lc in listings.get("landing-craft",[]):
                if lc["name"] in ("Daihatsu","Shohatsu"):
                    listings["japanese"].append( lc )
                else:
                    listings["american"].append( lc )
                    listings["british"].append( lc )

    # apply any changes for VASL extensions
    vasl_mod = get_vasl_mod()
    if vasl_mod:
        # build an index of the pieces
        piece_index = {}
        for nat,pieces in listings.items():
            for piece in pieces:
                piece_index[ piece["id"] ] = piece
        # process each VASL extension
        for extn in vasl_mod.get_extns():
            if vo_type not in extn[1]:
                continue
            _apply_extn_info( extn[0], extn[1], piece_index, vo_type )

    return jsonify( listings )

def _apply_extn_info( extn_fname, extn_info, piece_index, vo_type ):
    """Update the vehicle/ordnance listings for the specified VASL extension."""

    # initialize
    logger = logging.getLogger( "vasl_mod" )
    logger.info( "Updating %s for VASL extension: %s", vo_type, os.path.split(extn_fname)[1] )

    # process each entry
    for entry in extn_info[vo_type]:
        piece = piece_index.get( entry["id"] )
        if piece:
            # update an existing piece
            logger.debug( "- Updating GPID's for %s: %s", entry["id"], entry["gpid"] )
            if piece["gpid"]:
                prev_gpids = piece["gpid"]
                if not isinstance( piece["gpid"], list ):
                    piece["gpid"] = [ piece["gpid"] ]
                piece["gpid"].extend( entry["gpid"] )
            else:
                prev_gpids = "(none)"
                piece["gpid"] = entry["gpid"]
            logger.debug( "  - %s => %s", prev_gpids, piece["gpid"] )
        else:
            logger.warning( "- Updating V/O entry with extension info not supported: %s", entry["id"] )
# ---------------------------------------------------------------------

@app.route( "/<vo_type>/<nat>/<theater>/<int:year>", defaults={"month":1}  )
@app.route( "/<vo_type>/<nat>/<theater>/<int:year>/<int:month>" )
def get_vo_report( vo_type, nat, theater, year, month ):
    """Get a vehicle/ordnance report."""

    # generate the vehicle/ordnance report
    if vo_type not in ("vehicles","ordnance"):
        abort( 404 )
    return render_template( "vo-report.html",
        VO_TYPE = vo_type,
        NATIONALITY = nat,
        THEATER = theater,
        VO_TYPE0 = vo_type[:-1] if vo_type.endswith("s") else vo_type,
        YEAR = year,
        MONTH = month,
    )

@app.route( "/landing_craft" )
def get_lc_report():
    """Get a landing craft ordnance report."""
    return render_template( "vo-report.html",
        VO_TYPE = "landing-craft",
        YEAR = "null",
        MONTH = "null",
    )
