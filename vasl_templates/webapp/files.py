""" Serve static files. """

import os
import io
import urllib.request
import urllib.parse
import mimetypes

from flask import send_file, send_from_directory, jsonify, redirect, url_for, abort

from vasl_templates.webapp import app
from vasl_templates.webapp.file_server.vasl_mod import get_vasl_mod
from vasl_templates.webapp.utils import resize_image_response, is_empty_file

# ---------------------------------------------------------------------

class FileServer:
    """Serve static files."""

    def __init__( self, base_dir ):
        if FileServer.is_remote_path( base_dir ):
            self.base_dir = base_dir
        else:
            self.base_dir = os.path.abspath( base_dir )

    def serve_file( self, path, ignore_empty=False ):
        """Serve a file."""
        # NOTE: We return a Flask Response object, instead of the file data, so that (1) we can use
        # send_from_directory() and (2) if we have to download a file from a URL, we can include
        # the MIME type in what we return.
        if FileServer.is_remote_path( self.base_dir ):
            url = "{}/{}".format( self.base_dir, path )
            # NOTE: We download the target file and serve it ourself (instead of just redirecting)
            # since VASSAL can't handle SSL :-/
            resp = urllib.request.urlopen( url )
            buf = io.BytesIO()
            buf.write( resp.read() )
            buf.seek( 0 )
            mime_type = mimetypes.guess_type( url )[0]
            if not mime_type:
                # FUDGE! send_file() requires a MIME type, so we take a guess and hope the browser
                # can figure it out if we're wrong :-/
                mime_type = "image/png"
            return send_file( buf, mimetype=mime_type )
        else:
            path = path.replace( "\\", "/" ) # nb: for Windows :-/
            if ignore_empty and is_empty_file( os.path.join( self.base_dir, path ) ):
                return None
            return send_from_directory( self.base_dir, path )

    @staticmethod
    def is_remote_path( path ):
        """Check if a path is referring to a remote server."""
        return path.startswith( ("http://","https://") )

# ---------------------------------------------------------------------

@app.route( "/user/<path:path>" )
def get_user_file( path ):
    """Get a static file."""
    dname = app.config.get( "USER_FILES_DIR" )
    if not dname:
        abort( 404 )
    resp = FileServer( dname ).serve_file( path )
    if not resp:
        abort( 404 )
    return resize_image_response( resp )

# ---------------------------------------------------------------------

@app.route( "/counter/<gpid>/<side>/<int:index>" )
@app.route( "/counter/<gpid>/<side>", defaults={"index":0} )
def get_counter_image( gpid, side, index ):
    """Get a counter image."""

    # check if a VASL module has been configured
    vasl_mod = get_vasl_mod()
    if not vasl_mod:
        return redirect( url_for( "static", filename="images/missing-image.png" ), code=302 )

    # return the specified counter image
    image_path, image_data = vasl_mod.get_piece_image( gpid, side, int(index) )
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
    vasl_mod = get_vasl_mod()
    if not vasl_mod:
        return jsonify( {} )

    # return the VASL piece info
    return jsonify( vasl_mod.get_piece_info() )
