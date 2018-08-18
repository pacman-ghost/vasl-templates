""" Main webapp handlers. """

import os
import json
import glob

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

def _do_get_listings( listings_type ):
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
    for fname in glob.glob( os.path.join( dname, "*.json" ) ):
        nat = os.path.splitext( os.path.split(fname)[1] )[ 0 ]
        with open( fname, "r" ) as fp:
            listings[nat] = json.load( fp )

    return jsonify( listings )

# ---------------------------------------------------------------------

@app.route( "/<vo_type>/<nat>/<int:year>", defaults={"month":1}  )
@app.route( "/<vo_type>/<nat>/<int:year>/<int:month>" )
def get_vo_report( nat, vo_type, year, month ):
    """Get a vehicle/ordnance report."""

    # generate the vehicle/ordnance report
    if vo_type not in ("vehicles","ordnance"):
        abort( 404 )
    return render_template( "vo-report.html",
        NATIONALITY = nat,
        VO_TYPE = vo_type,
        VO_TYPE0 = vo_type[:-1] if vo_type.endswith("s") else vo_type,
        YEAR = year,
        MONTH = month
    )
