""" Main webapp handlers. """

import os
import json
import copy

from flask import request, render_template, jsonify, abort

from vasl_templates.webapp import app, globvars
from vasl_templates.webapp.config.constants import DATA_DIR
from vasl_templates.webapp.vo_utils import copy_vo_entry, add_vo_comments, apply_extn_info,  make_vo_index
from vasl_templates.webapp import vo_utils as webapp_vo_utils

_kfw_listings = { "vehicles": {}, "ordnance": {} }

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
            globvars.vasl_mod, vo_type,
            request.args.get("merge_common") == "1", request.args.get("report") == "1",
            None
        )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def load_vo_listings( msg_store ):
    """Load and install the vehicle/ordnance listings."""
    globvars.vo_listings = get_vo_listings( globvars.vasl_mod, msg_store )

def get_vo_listings( vasl_mod, msg_store ):
    """Get the vehicle/ordnance listings."""
    return {
        "vehicles": _do_load_vo_listings( vasl_mod, "vehicles", True, False, msg_store ),
        "ordnance": _do_load_vo_listings( vasl_mod, "ordnance", True, False, msg_store )
    }

def _do_load_vo_listings( vasl_mod, vo_type, merge_common, real_data_dir, msg_store ): #pylint: disable=too-many-locals,too-many-branches,too-many-statements
    """Load the vehicle/ordnance listings."""

    # locate the data directory
    if real_data_dir:
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
            is_kfw = os.path.split( root )[1] == "kfw"
            if is_kfw:
                nat = "kfw-" + ("uro" if nat == "us-rok-ounc" else nat)
            if os.path.split(root)[1] in ("allied-minor","axis-minor"):
                minor_type = os.path.split( root )[1]
                if nat == "common":
                    nat = minor_type + "-common"
                else:
                    minor_nats[minor_type].add( nat )
            with open( os.path.join(root,fname), "r" ) as fp:
                ( _kfw_listings[vo_type] if is_kfw else listings )[ nat ] = json.load( fp )
            fname2 = os.path.join( root, "{}.lend-lease.json".format( fname_stem ) )
            if os.path.isfile( fname2 ):
                with open( fname2, "r" ) as fp:
                    listings[nat].extend( json.load( fp ) )

    # apply any changes for VASL extensions
    # NOTE: We do this here, rather than in VaslMod, because VaslMod is a wrapper around a VASL module, and so
    # only knows about GPID's and counter images, rather than Chapter H pieces and piece ID's (e.g. "ge/v:001").
    if vasl_mod:
        # process each VASL extension
        vo_index = make_vo_index( listings )
        for extn in vasl_mod.get_extns():
            apply_extn_info( listings, extn[0], extn[1], vo_index, vo_type )

    # add in the common Allied/Axis Minor vehicles/ordnance
    if merge_common:
        for minor_type in ( "allied-minor", "axis-minor" ):
            if minor_type+"-common" not in listings:
                continue
            for nat in minor_nats[minor_type]:
                listings[nat].extend( copy.deepcopy( listings[minor_type+"-common"] ) )
            del listings[ minor_type+"-common" ]

    # add vehicle/ordnance comments (based on what notes they have)
    webapp_vo_utils._vo_comments = None #pylint: disable=protected-access
    add_vo_comments( listings, vo_type, msg_store )
    add_vo_comments( _kfw_listings[vo_type], vo_type, msg_store )

    # fixup any vehicle/ordnance references
    # NOTE: We do this after adding comments to vehicles/ordnance, so that those comments
    # are included when we copy vehicle/ordnance entries.
    vo_index = make_vo_index( listings )
    for nat,vo_entries in listings.items():
        for i,vo_entry in enumerate(vo_entries):
            vo_id = vo_entry.get( "copy_from" )
            if vo_id:
                vo_entries[i] = copy_vo_entry( vo_entry, vo_index[vo_id], nat, vo_type, msg_store )

    # update nationality variants with the listings from their base nationality
    for nat in listings:
        if "~" not in nat:
            continue
        base_nat = nat.split( "~" )[0]
        listings[nat] = listings[base_nat] + listings[nat]

    # add in the Landing Craft
    if merge_common:
        if vo_type == "vehicles":
            for lc in listings.get( "landing-craft", [] ):
                # FUDGE! Landing Craft get appended to the vehicles for the Japanese/American/British,
                # so we need to tag the note numbers so that they refer to the *Landing Craft* note,
                # not the Japanese/American/British vehicle note.
                lc = copy.deepcopy( lc )
                if "note_number" in lc:
                    lc["note_number"] = "LC {}".format( lc["note_number"] )
                if lc["name"] in ("Daihatsu","Shohatsu"):
                    listings["japanese"].append( lc )
                else:
                    listings["american"].append( lc )
                    listings["british"].append( lc )

    # install the K:FW entries
    # NOTE: We do this after updating the nationality variants so that e.g. the British Canadians
    # don't get the BCFK vehicles/ordnance.
    def extend_listings( key, kfw_key ):
        """Extend the listings with new entries."""
        if key in listings and kfw_key in _kfw_listings[vo_type]:
            listings[ key ].extend( _kfw_listings[vo_type][ kfw_key ] )
    if vo_type == "vehicles":
        for nat in ( "american", "kfw-rok", "kfw-ounc", "british" ):
            extend_listings( nat, "kfw-bcfk" if nat == "british" else "kfw-uro" )
            extend_listings( nat, "kfw-un-common" )
        extend_listings( "kfw-kpa", "kfw-kpa" )
    elif vo_type == "ordnance":
        # NOTE: Appending the common ordnance to each of the American, ROK and OUNC ordnance lists isn't
        # quite the right thing to do, since it will cause incorrect behavior when analyzing a scenario.
        # For example, the M2 60* Mortar has variants for each nationality, each with its own GPID,
        # which should really only be imported if the owning player's nationality matches the counter.
        # However, this shouldn't really be a problem since these nationalities will never be playing
        # against each other.
        for nat in ( "american", "kfw-rok", "kfw-ounc" ):
            extend_listings( nat, "kfw-uro" )
            extend_listings( nat, "kfw-un-common" )
        for pair in [ ("british","kfw-bcfk"), ("kfw-kpa","kfw-kpa"), ("kfw-cpva","kfw-cpva") ]:
            extend_listings( pair[0],  pair[1] )
        extend_listings( "british", "kfw-un-common" )
    else:
        assert False, "Unknown V/O type: {}".format( vo_type )

    return listings

# ---------------------------------------------------------------------

@app.route( "/<vo_type>/<nat>/<theater>/<int:year>", defaults={"month":1} )
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
