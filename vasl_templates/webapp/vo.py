""" Main webapp handlers. """

import os
import json
import copy
import logging

from flask import request, render_template, jsonify, abort

from vasl_templates.webapp import app, globvars
from vasl_templates.webapp.config.constants import DATA_DIR

# ---------------------------------------------------------------------

@app.route( "/vehicles" )
def get_vehicle_listings():
    """Return the vehicle listings."""
    return jsonify( _do_get_listings( "vehicles" ) )

@app.route( "/ordnance" )
def get_ordnance_listings():
    """Return the ordnance listings."""
    return jsonify( _do_get_listings( "ordnance" ) )

def _do_get_listings( vo_type ):
    """Return the vehicle/ordnance listings."""
    if request.args.get("merge_common") == "1" and request.args.get("report") != "1":
        # nb: this is the normal case
        return globvars.vo_listings[ vo_type ]
    else:
        # nb: we should only get here during tests
        return _do_load_vo_listings(
            vo_type,
            request.args.get("merge_common") == "1", request.args.get("report") == "1"
        )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def load_vo_listings():
    """Load the vehicle/ordnance listings."""
    globvars.vo_listings = {
        "vehicles": _do_load_vo_listings( "vehicles", True, False ),
        "ordnance": _do_load_vo_listings( "ordnance", True, False )
    }

def _do_load_vo_listings( vo_type, merge_common, report ): #pylint: disable=too-many-locals,too-many-branches
    """Load the vehicle/ordnance listings."""

    # locate the data directory
    if report:
        dname = DATA_DIR # nb: always use the real data for reports, not the test fixtures
    else:
        dname = app.config.get( "DATA_DIR", DATA_DIR )
    dname = os.path.join( dname, vo_type )
    if not os.path.isdir( dname ):
        raise RuntimeError( "Missing vehicles/ordnance directory: {}".format( dname ) )

    # load the listings
    listings = {}
    minor_nats = { "allied-minor": set(), "axis-minor": set() }
    for root,_,fnames in os.walk(dname):
        for fname in fnames:
            fname_stem, extn = os.path.splitext( fname )
            if extn != ".json" or fname_stem.endswith( ".lend-lease" ):
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
            fname2 = os.path.join( root, "{}.lend-lease.json".format( fname_stem ) )
            if os.path.isfile( fname2 ):
                with open( fname2, "r" ) as fp:
                    listings[nat].extend( json.load( fp ) )

    # fixup any vehicle/ordnance references
    vo_index = _make_vo_index( listings )
    for nat,vo_entries in listings.items():
        for i,vo_entry in enumerate(vo_entries):
            vo_id = vo_entry.get( "copy_from" )
            if vo_id:
                vo_entries[i] = _copy_vo_entry( vo_entry, vo_index[vo_id] )

    # add in any common vehicles/ordnance and landing craft
    if merge_common:
        # add in any common Allied/Axis Minor vehicles/ordnance
        for minor_type in ("allied-minor","axis-minor"):
            if minor_type+"-common" not in listings:
                continue
            for nat in minor_nats[minor_type]:
                listings[nat].extend( listings[minor_type+"-common"] )
            del listings[ minor_type+"-common" ]
        # add in any landing craft
        if vo_type == "vehicles":
            for lc in listings.get("landing-craft",[]):
                if lc["name"] in ("Daihatsu","Shohatsu"):
                    listings["japanese"].append( lc )
                else:
                    listings["american"].append( lc )
                    listings["british"].append( lc )

    # apply any changes for VASL extensions
    # NOTE: We do this here, rather than in VaslMod, because VaslMod is a wrapper around a VASL module, and so
    # only knows about GPID's and counter images, rather than Chapter H pieces and piece ID's (e.g. "ge/v:001").
    if globvars.vasl_mod:
        # process each VASL extension
        vo_index = _make_vo_index( listings )
        for extn in globvars.vasl_mod.get_extns():
            _apply_extn_info( listings, extn[0], extn[1], vo_index, vo_type )

    # update nationality variants with the listings from their base nationality
    for nat in listings:
        if "~" not in nat:
            continue
        base_nat = nat.split( "~" )[0]
        listings[nat] = listings[base_nat] + listings[nat]

    return listings

def _copy_vo_entry( placeholder_vo_entry, src_vo_entry ):
    """Create a new vehicle/ordnance entry by copying an existing one."""
    # Anjuna, India (FEB/19)
    # create the new vehicle/ordnance entry
    new_vo_entry = copy.deepcopy( src_vo_entry )
    new_vo_entry["id"] = placeholder_vo_entry["id"]
    if "note_number" in placeholder_vo_entry:
        new_vo_entry["note_number"] = placeholder_vo_entry["note_number"]
    if "name" in placeholder_vo_entry:
        new_vo_entry["name"] = placeholder_vo_entry["name"]
    if "gpid" in placeholder_vo_entry:
        new_vo_entry["gpid"] = placeholder_vo_entry["gpid"]
    elif "extra_gpids" in placeholder_vo_entry:
        if not isinstance( new_vo_entry["gpid"], list ):
            new_vo_entry["gpid"] = [ new_vo_entry["gpid"] ]
        new_vo_entry["gpid"].extend( placeholder_vo_entry["extra_gpids"] )
    # fixup any multi-applicable notes
    if "notes" in new_vo_entry:
        vo_id = placeholder_vo_entry[ "copy_from" ]
        if vo_id.startswith( "br/" ):
            prefix = "Br"
        elif vo_id.startswith( "am/" ):
            prefix = "US"
        else:
            logging.warning( "Unexpected vehicle/ordnance reference nationality: %s", vo_id )
            prefix = ""
        new_vo_entry["notes"] = [ "{} {}".format( prefix, n ) for n in new_vo_entry["notes"] ]
        if "extra_notes" in placeholder_vo_entry:
            new_vo_entry["notes"].extend( placeholder_vo_entry["extra_notes"] )
    return new_vo_entry

def _apply_extn_info( listings, extn_fname, extn_info, vo_index, vo_type ):
    """Update the vehicle/ordnance listings for the specified VASL extension."""

    # initialize
    logger = logging.getLogger( "vasl_mod" )
    logger.info( "Updating %s for VASL extension '%s': %s",
        vo_type, extn_info["extensionId"], os.path.split(extn_fname)[1]
    )

    # process each entry
    for nat in extn_info:
        if not isinstance( extn_info[nat], dict ):
            continue
        for entry in extn_info[nat].get( vo_type, [] ):
            vo_entry = vo_index.get( entry["id"] )
            if vo_entry:
                # update an existing vehicle/ordnance
                logger.debug( "- Updating GPID's for %s: %s", entry["id"], entry["gpid"] )
                if vo_entry["gpid"]:
                    prev_gpids = vo_entry["gpid"]
                    if not isinstance( vo_entry["gpid"], list ):
                        vo_entry["gpid"] = [ vo_entry["gpid"] ]
                    vo_entry["gpid"].extend( entry["gpid"] )
                else:
                    prev_gpids = "(none)"
                    vo_entry["gpid"] = entry["gpid"]
                logger.debug( "  - %s => %s", prev_gpids, vo_entry["gpid"] )
            else:
                # add a new vehicle/ordnance
                if nat not in listings:
                    listings[ nat ] = []
                entry[ "extn_id" ] = extn_info[ "extensionId" ]
                listings[ nat ].append( entry )

def _make_vo_index( vo_entries ):
    """Generate an index of each vehicle/ordnance entry."""
    vo_index = {}
    for nat in vo_entries:
        for vo_entry in vo_entries[nat]:
            vo_index[ vo_entry["id"] ] = vo_entry
    return vo_index

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
