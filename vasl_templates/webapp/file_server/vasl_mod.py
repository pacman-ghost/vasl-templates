""" Serve files from a VASL module file. """

import os
import json
import zipfile
import re
import xml.etree.ElementTree

import logging
_logger = logging.getLogger( "vasl_mod" )

from vasl_templates.webapp.file_server.utils import get_vo_gpids

SUPPORTED_VASL_MOD_VERSIONS = [ "6.3.3", "6.4.0", "6.4.1", "6.4.2" ]

# ---------------------------------------------------------------------

class VaslMod:
    """Serve files from a VASL module file."""

    def __init__( self, fname, data_dir ) :
        # initialize
        self.pieces = {}
        # parse the VASL module file
        _logger.info( "Loading VASL module: %s", fname )
        self.zip_file = zipfile.ZipFile( fname, "r" )
        self._parse_vmod( data_dir )

    def get_piece_image( self, gpid, side, index ):
        """Get the image for the specified piece."""

        # get the image path
        entry = self.pieces[ gpid ]
        assert side in ("front","back")
        image_paths = entry[ side+"_images" ]
        if not image_paths:
            return None, None
        if not isinstance( image_paths, list ):
            image_paths = [ image_paths ]
        image_path = image_paths[ index ]
        if not os.path.splitext( image_path )[1]:
            image_path += ".gif"

        # load the image data
        image_path = os.path.join( "images", image_path )
        image_path = re.sub( r"[\\/]+", "/", image_path ) # nb: in case we're on Windows :-/
        image_data = self.zip_file.read( image_path )

        return image_path, image_data

    def get_piece_info( self ):
        """Get information about each piece."""
        def image_count( piece, key ):
            """Return the number of images the specified piece has."""
            if not piece[key]:
                return 0
            return len(piece[key]) if isinstance( piece[key], list ) else 1
        return {
            p["gpid"]: {
                "name": p["name"],
                "front_images": image_count( p, "front_images" ),
                "back_images": image_count( p, "back_images" ),
                "is_small": p["is_small"],
            }
            for p in self.pieces.values()
        }

    def _parse_vmod( self, data_dir ): #pylint: disable=too-many-branches,too-many-locals
        """Parse a .vmod file."""

        # load our overrides
        fname = os.path.join( data_dir, "vasl-overrides.json" )
        vasl_overrides = json.load( open( fname, "r" ) )
        fname = os.path.join( data_dir, "expected-multiple-images.json" )
        expected_multiple_images = json.load( open( fname, "r" ) )

        # figure out which pieces we're interested in
        target_gpids = get_vo_gpids( data_dir )

        def check_override( gpid, piece, override ):
            """Check that the values in an override entry match what we have."""
            for key in override:
                if piece[key] != override[key]:
                    _logger.warning( "Unexpected value in VASL override for '%s' (gpid=%d): %s", key, gpid, piece[key] )
                    return False
            return True

        # parse the VASL build info
        build_info = self.zip_file.read( "buildFile" )
        doc = xml.etree.ElementTree.fromstring( build_info )
        if doc.attrib.get( "version" ) not in SUPPORTED_VASL_MOD_VERSIONS:
            _logger.warning( "Unsupported VASL version: %s", doc.attrib.get("version") )
        for node in doc.iter( "VASSAL.build.widget.PieceSlot" ):

            # load the next entry
            gpid = int( node.attrib["gpid"] )
            if gpid not in target_gpids:
                continue
            if gpid in self.pieces:
                _logger.warning( "Found duplicate GPID: %d", gpid )
            front_images, back_images = self._get_image_paths( gpid, node.text )
            piece = {
                "gpid": gpid,
                "name": node.attrib["entryName"],
                "front_images": front_images,
                "back_images": back_images,
                "is_small": int(node.attrib["height"]) <= 48,
            }

            # check if we want to override any values
            override = vasl_overrides.get( str(gpid) )
            if override:
                if check_override( gpid, piece, override["expected"] ):
                    for key in override["updated"]:
                        piece[key] = override["updated"][key]
                del vasl_overrides[ str(gpid) ]

            # save the loaded entry
            self.pieces[gpid] = piece
            target_gpids.remove( gpid )
            _logger.debug( "- Loaded piece: %s", piece )

            # check for multiple images
            if isinstance(piece["front_images"],list) or isinstance(piece["back_images"],list):
                expected = expected_multiple_images.get( str(gpid) )
                if expected:
                    check_override( gpid, piece, expected )
                    del expected_multiple_images[ str(gpid) ]
                else:
                    _logger.warning( "Found multiple images: %s", piece )

        # make sure we found all the pieces we need
        _logger.info( "Loaded %d pieces.", len(self.pieces) )
        if target_gpids:
            _logger.warning( "Couldn't find pieces: %s", target_gpids )

        # make sure all the overrides defined were used
        if vasl_overrides:
            gpids = ", ".join( vasl_overrides.keys() )
            _logger.warning( "Unused VASL overrides: %s", gpids )
        if expected_multiple_images:
            gpids = ", ".join( expected_multiple_images.keys() )
            _logger.warning( "Expected multiple images but didn't find them: %s", gpids )

    @staticmethod
    def _get_image_paths( gpid, val ): #pylint: disable=too-many-branches
        """Get the image path(s) for a piece."""

        # FUDGE! The data in the build file looks like a serialized object, so we use
        # a bunch of heuristics to try to identify the fields we want :-/

        # split the data into fields
        val = val.replace( "\\/", "/" )
        fields = val.split( ";" )

        # identify image paths
        def is_image_path( val ): #pylint: disable=missing-docstring
            if val == "white X 60.png": # nb: a lot of Finnish pieces have this
                return False
            if val.endswith( (".gif",".png") ):
                return True
            if val.startswith( ("ru/","ge/","am/","br/","it/","ja/","ch/","sh/","fr/","al/","ax/","hu/","fi/") ):
                return True
            return False
        fields = [ f for f in fields if is_image_path(f) ]

        # figure out what we've got
        def split_fields( val ):
            """Split out individual fields in a VASL build info entry."""
            fields = [ v.strip() for v in val.split(",") ]
            fields = [ f for f in fields if f ]
            return fields
        if not fields:
            _logger.warning( "Couldn't find any image paths for gpid=%d.", gpid )
            return None, None
        if len(fields) == 1:
            # the piece only has front image(s)
            front_images, back_images = split_fields(fields[0]), None
        else:
            # the piece has front and back image(s)
            if len(fields) > 2:
                _logger.warning( "Found > 2 image paths for gpid=%d", gpid )
            front_images, back_images = split_fields(fields[1]), split_fields(fields[0])

        # ignore dismantled ordnance
        if len(front_images) > 1:
            if front_images[-1].endswith( "dm" ):
                if back_images[-1].endswith( "dmb" ):
                    _logger.debug( "Ignoring dismantled images: gpid=%d, front=%s, back=%s",
                        gpid, front_images, back_images
                    )
                    front_images.pop()
                    back_images.pop()
                else:
                    _logger.warning( "Unexpected dismantled images: %s %s", front_images, back_images )

        # ignore limbered ordnance
        if len(front_images) > 1:
            if front_images[-1].endswith( "l" ):
                if back_images[-1].endswith( ("lb","l-b") ):
                    _logger.debug( "Ignoring limbered images: gpid=%d, front=%s, back=%s",
                        gpid, front_images, back_images
                    )
                    front_images.pop()
                    back_images.pop()
                else:
                    _logger.warning( "Unexpected limbered images: %s %s", front_images, back_images )
            elif front_images[-1].endswith( "B.png" ) and front_images[0] == front_images[-1][:-5]+".png":
                # nb: this is for Finnish Guns
                _logger.debug( "Ignoring limbered images: gpid=%d, front=%s, back=%s",
                    gpid, front_images, back_images
                )
                front_images.pop()
                assert not back_images

        def delistify( val ): #pylint: disable=missing-docstring
            if val is None:
                return None
            return val[0] if len(val) == 1 else val
        return delistify(front_images), delistify(back_images)
