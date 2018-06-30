""" Main webapp handlers. """

from flask import request, render_template

from vasl_templates.webapp import app

# ---------------------------------------------------------------------

@app.route( "/main" )
def main():
    """Return the main page."""
    return render_template( "main.html" )

# ---------------------------------------------------------------------

@app.route( "/shutdown" )
def shutdown():
    """Shutdown the webapp (for testing porpoises)."""
    request.environ.get( "werkzeug.server.shutdown" )()
    return ""
