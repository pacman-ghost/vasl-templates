""" Main webapp handlers. """

from flask import render_template

from vasl_templates.webapp import app

# ---------------------------------------------------------------------

@app.route( "/national-capabilities/<nat>/<theater>/<int:year>", defaults={"month":1} )
@app.route( "/national-capabilities/<nat>/<theater>/<int:year>/<int:month>" )
def get_national_capabilities( nat, theater, year, month ):
    """Get the national capabilities snippet."""
    return render_template( "national-capabilities.html",
        NATIONALITY = nat,
        THEATER = theater,
        YEAR = year,
        MONTH = month
    )
