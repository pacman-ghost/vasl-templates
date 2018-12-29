""" Wrapper around a VASL module file and extensions. """

import os
import threading
import json
import glob
import zipfile
import re
import xml.etree.ElementTree

import logging
_logger = logging.getLogger( "vasl_mod" )

from vasl_templates.webapp import app
from vasl_templates.webapp.config.constants import DATA_DIR
from vasl_templates.webapp.file_server.utils import get_vo_gpids, get_effective_gpid

SUPPORTED_VASL_MOD_VERSIONS = [ "6.4.0", "6.4.1", "6.4.2", "6.4.3" ]
SUPPORTED_VASL_MOD_VERSIONS_DISPLAY = "6.4.0-6.4.3"

warnings = [] # nb: for the test suite

# ---------------------------------------------------------------------

# NOTE: The lock only controls access to the _vasl_mod variable, not the VaslMod object it points to.
# In practice this doesn't really matter, since it will be loaded once at startup, then never changes;
# it's only the tests that are constantly changing the underlying object.
_vasl_mod_lock = threading.RLock()
_vasl_mod = None

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def get_vasl_mod():
    """Return the global VaslMod object."""
    with _vasl_mod_lock:
        global _vasl_mod
        if _vasl_mod is None:
            # check if a VASL module has been configured
            # NOTE: We will be doing this check every time someone wants the global VaslMod object,
            # even if one hasn't been configured, but in all likelihood, everyone will have it configured,
            # in which case, the check will only be done once, and the global _vasl_mod variable set.
            fname = app.config.get( "VASL_MOD" )
            if fname:
                # yup - load it
                from vasl_templates.webapp.main import startup_msg_store #pylint: disable=cyclic-import
                set_vasl_mod( fname, startup_msg_store )
        return _vasl_mod

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def set_vasl_mod( vmod_fname, msg_store ):
    """Install a new global VaslMod object."""
    with _vasl_mod_lock:
        global _vasl_mod
        if vmod_fname:
            extns_dir = app.config.get( "VASL_EXTNS_DIR" )
            extns = _load_vasl_extns( extns_dir )
            _vasl_mod = VaslMod( vmod_fname, DATA_DIR, extns )
            if _vasl_mod.vasl_version not in SUPPORTED_VASL_MOD_VERSIONS:
                msg_store.warning(
                    "VASL {} is unsupported.<p>Things might work, but they might not...".format(
                        _vasl_mod.vasl_version
                    )
                )
        else:
            _vasl_mod = None

def _load_vasl_extns( extn_dir ): #pylint: disable=too-many-locals,too-many-statements
    """Locate VASL extensions and their corresponding vehicle/ordnance info files."""

    if not extn_dir:
        return []

    def log_warning( fmt, *args, **kwargs ): #pylint: disable=missing-docstring
        msg = fmt.format( *args, **kwargs )
        warnings.append( msg )
        _logger.warning( msg )

    # load our extension info files
    all_extn_info = {}
    if "_VASL_EXTN_INFO_DIR_" in app.config:
        dname = app.config["_VASL_EXTN_INFO_DIR_"] # nb: for the test suite
    else:
        dname = os.path.join( DATA_DIR, "extensions" )
    for fname in glob.glob( os.path.join(dname,"*.json") ):
        _logger.debug( "Loading VASL extension info: %s", fname )
        with open( fname, "r" ) as fp:
            extn_info = json.load( fp )
        all_extn_info[ ( extn_info["extensionId"], extn_info["version"] ) ] = extn_info
        _logger.debug( "- id=%s ; version=%s", extn_info["extensionId"], extn_info["version"] )

    # figure out what filename extensions we will recognize
    valid_fname_extns = app.config.get( "VASL_EXTENSION_FILENAME_EXTNS", ".mdx .zip" )
    valid_fname_extns = valid_fname_extns.replace( ";", " " ).replace( ",", " " ).split()

    # process each VASL extension
    extns = []
    for extn_fname in os.listdir( extn_dir ):

        # check if this is a file we're interested in
        if os.path.splitext(extn_fname)[1] not in valid_fname_extns:
            continue
        extn_fname = os.path.join( extn_dir, extn_fname )

        # try to load the extension
        _logger.debug( "Checking VASL extension: %s", extn_fname )
        try:
            zip_file = zipfile.ZipFile( extn_fname, "r" )
        except zipfile.BadZipFile:
            log_warning( "Can't check VASL extension (not a ZIP file): {}", extn_fname )
            continue
        try:
            build_info = zip_file.read( "buildFile" )
        except KeyError:
            log_warning( "Missing buildFile: {}", extn_fname )
            continue
        doc = xml.etree.ElementTree.fromstring( build_info )
        node = doc.findall( "." )[0]
        if node.tag != "VASSAL.build.module.ModuleExtension":
            log_warning( "Unexpected root node ({}) for VASL extension: {}", node.tag, extn_fname )
            continue

        # get the extension's ID and version string
        extn_id = node.attrib.get( "extensionId" )
        if not extn_id:
            log_warning( "Can't find ID for VASL extension: {}", extn_fname )
            continue
        extn_version = node.attrib.get( "version" )
        if not extn_version:
            log_warning( "Can't find version for VASL extension: {}", extn_fname )
            continue
        _logger.debug( "- id=%s ; version=%s", extn_id, extn_version )

        # check if we have a corresponding info file
        extn_info = all_extn_info.get( ( extn_id, extn_version ) )
        if not extn_info:
            log_warning( "Not accepting {}: no extension info for {}/{}.",
                os.path.split(extn_fname)[1], extn_id, extn_version
            )
            continue

        # yup - add the extension to the list
        _logger.info( "Accepting VASL extension: %s (%s/%s)", os.path.split(extn_fname)[1], extn_id, extn_version )
        extns.append( ( extn_fname, extn_info ) )

    return extns

# ---------------------------------------------------------------------

class VaslMod:
    """Wrapper around a VASL module file and extensions."""

    def __init__( self, fname, data_dir, extns ) :

        # initialize
        self.filename = fname
        self.extns = extns

        # initialize
        self._pieces = {}
        self._files = [ ( zipfile.ZipFile(fname,"r"), None ) ]
        if extns:
            for extn in extns:
                self._files.append(
                    ( zipfile.ZipFile(extn[0],"r"), extn[1] )
                )

        # load the VASL module and any extensions
        self.vasl_version = self._load_vmod( data_dir )
        if self.vasl_version not in SUPPORTED_VASL_MOD_VERSIONS:
            _logger.warning( "Unsupported VASL version: %s", self.vasl_version )

    def get_piece_image( self, gpid, side, index ):
        """Get the image for the specified piece."""

        # get the image path
        gpid = get_effective_gpid( gpid )
        if gpid not in self._pieces:
            return None, None
        piece = self._pieces[ get_effective_gpid( gpid ) ]
        assert side in ("front","back")
        image_paths = piece[ side + "_images" ]
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
        image_data = piece[ "zip_file" ].read( image_path )

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
            for p in self._pieces.values()
        }

    def get_extns( self ):
        """Return the loaded VASL extensions."""
        return [
            ( files[0].filename, files[1] )
            for files in self._files
            if files[1]
        ]

    def _load_vmod( self, data_dir ): #pylint: disable=too-many-branches,too-many-locals
        """Load a VASL module file and any extensions."""

        # load our overrides
        fname = os.path.join( data_dir, "vasl-overrides.json" )
        vasl_overrides = json.load( open( fname, "r" ) )
        fname = os.path.join( data_dir, "expected-multiple-images.json" )
        expected_multiple_images = json.load( open( fname, "r" ) )

        # figure out which pieces we're interested in
        target_gpids = get_vo_gpids( data_dir, self.get_extns() )

        # parse the VASL module and any extensions
        for i,files in enumerate( self._files ):
            _logger.info( "Loading VASL %s: %s", ("module" if i == 0 else "extension"), files[0].filename )
            version = self._parse_zip_file( files[0], target_gpids, vasl_overrides, expected_multiple_images )
            if i == 0:
                vasl_version = version

        # make sure we found all the pieces we need
        _logger.info( "Loaded %d pieces.", len(self._pieces) )
        if target_gpids:
            _logger.warning( "Couldn't find pieces: %s", target_gpids )

        # make sure all the overrides defined were used
        if vasl_overrides:
            gpids = ", ".join( vasl_overrides.keys() )
            _logger.warning( "Unused VASL overrides: %s", gpids )
        if expected_multiple_images:
            gpids = ", ".join( expected_multiple_images.keys() )
            _logger.warning( "Expected multiple images but didn't find them: %s", gpids )

        return vasl_version

    def _parse_zip_file( self, zip_file, target_gpids, vasl_overrides, expected_multiple_images ): #pylint: disable=too-many-locals
        """Parse a VASL module or extension."""

        # load the build file
        build_info = zip_file.read( "buildFile" )
        doc = xml.etree.ElementTree.fromstring( build_info )

        def check_override( gpid, piece, override ):
            """Check that the values in an override entry match what we have."""
            for key in override:
                if piece[key] != override[key]:
                    _logger.warning( "Unexpected value in VASL override for '%s' (gpid=%s): %s", key, gpid, piece[key] )
                    return False
            return True

        # iterate over each PieceSlot in the build file
        for node in doc.iter( "VASSAL.build.widget.PieceSlot" ):

            # load the next entry
            gpid = node.attrib[ "gpid" ]
            if gpid not in target_gpids:
                continue
            if gpid in self._pieces:
                _logger.warning( "Found duplicate GPID: %s", gpid )
            front_images, back_images = self._get_image_paths( gpid, node.text )
            piece = {
                "gpid": gpid,
                "name": node.attrib["entryName"],
                "front_images": front_images,
                "back_images": back_images,
                "is_small": int(node.attrib["height"]) <= 48,
                "zip_file": zip_file,
            }

            # check if we want to override any values
            override = vasl_overrides.get( gpid )
            if override:
                if check_override( gpid, piece, override["expected"] ):
                    for key in override["updated"]:
                        piece[key] = override["updated"][key]
                del vasl_overrides[ gpid ]

            # save the loaded entry
            self._pieces[ gpid ] = piece
            target_gpids.remove( gpid )
            _logger.debug( "- Loaded piece: %s", piece )

            # check for multiple images
            if isinstance(piece["front_images"],list) or isinstance(piece["back_images"],list):
                expected = expected_multiple_images.get( gpid )
                if expected:
                    check_override( gpid, piece, expected )
                    del expected_multiple_images[ gpid ]
                else:
                    _logger.warning( "Found multiple images: %s", piece )

        return doc.attrib.get( "version" )

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
            _logger.warning( "Couldn't find any image paths for gpid=%s.", gpid )
            return None, None
        if len(fields) == 1:
            # the piece only has front image(s)
            front_images, back_images = split_fields(fields[0]), None
        else:
            # the piece has front and back image(s)
            if len(fields) > 2:
                _logger.warning( "Found > 2 image paths for gpid=%s", gpid )
            front_images, back_images = split_fields(fields[1]), split_fields(fields[0])

        # ignore dismantled ordnance
        if len(front_images) > 1:
            if front_images[-1].endswith( "dm" ):
                if back_images[-1].endswith( "dmb" ):
                    _logger.debug( "Ignoring dismantled images: gpid=%s, front=%s, back=%s",
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
                    _logger.debug( "Ignoring limbered images: gpid=%s, front=%s, back=%s",
                        gpid, front_images, back_images
                    )
                    front_images.pop()
                    back_images.pop()
                else:
                    _logger.warning( "Unexpected limbered images: %s %s", front_images, back_images )
            elif front_images[-1].endswith( "B.png" ) and front_images[0] == front_images[-1][:-5]+".png":
                # nb: this is for Finnish Guns
                _logger.debug( "Ignoring limbered images: gpid=%s, front=%s, back=%s",
                    gpid, front_images, back_images
                )
                front_images.pop()
                assert not back_images

        def delistify( val ): #pylint: disable=missing-docstring
            if val is None:
                return None
            return val[0] if len(val) == 1 else val
        return delistify(front_images), delistify(back_images)
