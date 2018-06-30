""" Webapp handlers. """

from flask import request

from vasl_templates.webapp import app

# ---------------------------------------------------------------------

@app.route( "/generate", methods=["POST"] )
def generate_html():
    """Generate a response"""
    val = request.form.get( "val" )
    if val:
        val = val.strip()
    return "You said: {}".format( '"{}"'.format(val) if val else "nothing!" )
