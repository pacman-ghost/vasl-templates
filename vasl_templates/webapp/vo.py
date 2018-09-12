""" Main webapp handlers. """

import os
import json

from flask import request, render_template, jsonify, abort

from vasl_templates.webapp import app
from vasl_templates.webapp.config.constants import DATA_DIR

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

def _do_get_listings( listings_type ): #pylint: disable=too-many-branches
    """Load the vehicle/ordnance listings."""

    # locate the data directory
    if request.args.get( "report" ):
        dname = DATA_DIR # nb: always use the real data for reports, not the test fixtures
    else:
        dname = app.config.get( "DATA_DIR", DATA_DIR )
    dname = os.path.join( dname, listings_type )
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

    # merge the common entries into each Allied/Axis Minor listing
    if request.args.get( "merge_common" ) == "1":
        for minor_type in ("allied-minor","axis-minor"):
            if minor_type+"-common" not in listings:
                continue
            for nat in minor_nats[minor_type]:
                listings[nat].extend( listings[minor_type+"-common"] )
            del listings[ minor_type+"-common" ]

    return jsonify( listings )

# ---------------------------------------------------------------------

@app.route( "/<vo_type>/<theater>/<nat>/<int:year>", defaults={"month":1}  )
@app.route( "/<vo_type>/<theater>/<nat>/<int:year>/<int:month>" )
def get_vo_report( theater, nat, vo_type, year, month ):
    """Get a vehicle/ordnance report."""

    # generate the vehicle/ordnance report
    if vo_type not in ("vehicles","ordnance"):
        abort( 404 )
    return render_template( "vo-report.html",
        THEATER = theater,
        NATIONALITY = nat,
        VO_TYPE = vo_type,
        VO_TYPE0 = vo_type[:-1] if vo_type.endswith("s") else vo_type,
        YEAR = year,
        MONTH = month,
    )
