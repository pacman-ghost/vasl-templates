""" Serve static files. """

import os
import io

from flask import send_file, jsonify, abort

from vasl_templates.webapp import app
from vasl_templates.webapp.file_server.vasl_mod import VaslMod
from vasl_templates.webapp.config.constants import DATA_DIR

vasl_mod = None
if app.config.get( "VASL_MOD" ):
    vasl_mod = VaslMod( app.config["VASL_MOD"], DATA_DIR )

# ---------------------------------------------------------------------

@app.route( "/counter/<gpid>/<side>/<int:index>" )
@app.route( "/counter/<gpid>/<side>", defaults={"index":1} )
def get_counter_image( gpid, side, index ):
    """Get a counter image."""

    # check if a VASL module has been configured
    if not vasl_mod:
        return app.send_static_file( "images/missing-image.png" )

    # return the specified counter image
    image_path, image_data = vasl_mod.get_piece_image( int(gpid), side, int(index)-1 )
    if not image_data:
        abort( 404 )
    return send_file(
        io.BytesIO( image_data ),
        attachment_filename = os.path.split( image_path )[1]## nb: so Flask can figure out the MIME type
    )

# ---------------------------------------------------------------------

@app.route( "/vasl-piece-info" )
def get_vasl_piece_info():
    """Get information about the VASL pieces."""

    # check if a VASL module has been configured
    if not vasl_mod:
        return jsonify( {} )

    # return the VASL piece info
    return jsonify( vasl_mod.get_piece_info() )
