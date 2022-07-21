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

from vasl_templates.webapp import app, globvars
from vasl_templates.webapp.config.constants import DATA_DIR
from vasl_templates.webapp.vo import get_vo_listings
from vasl_templates.webapp.utils import compare_version_strings

SUPPORTED_VASL_MOD_VERSIONS = [ "6.6.0", "6.6.1", "6.6.2", "6.6.3", "6.6.3.1", "6.6.4" ]
SUPPORTED_VASL_MOD_VERSIONS_DISPLAY = "6.6.0-.3, 6.6.3.1, 6.6.4"

_zip_file_lock = threading.Lock()

_warnings = [] # nb: for the test suite

# ---------------------------------------------------------------------

def set_vasl_mod( vmod_fname, msg_store ):
    """Install a new global VaslMod object."""
    globvars.vasl_mod = None
    global _warnings
    _warnings = []
    if vmod_fname:
        # load and install the specified VASL module
        extns_dir = app.config.get( "VASL_EXTNS_DIR" )
        extns = _load_vasl_extns( extns_dir, msg_store )
        try:
            vasl_mod = VaslMod( vmod_fname, DATA_DIR, extns )
        except Exception as ex: #pylint: disable=broad-except
            msg = "Can't load the VASL module: {}".format( ex )
            _logger.error( "%s", msg )
            if msg_store:
                msg_store.error( msg )
            return
        globvars.vasl_mod = vasl_mod
        # make sure the VASL version is one we support
        if globvars.vasl_mod.vasl_version not in SUPPORTED_VASL_MOD_VERSIONS:
            if msg_store:
                msg_store.warning(
                    "This program has not been tested with VASL {}.<p>Things might work, but they might not...".format(
                        globvars.vasl_mod.vasl_real_version
                    )
                )

def _load_vasl_extns( extn_dir, msg_store ): #pylint: disable=too-many-locals,too-many-statements,too-many-branches
    """Locate VASL extensions and their corresponding vehicle/ordnance info files."""

    if not extn_dir:
        return []
    if not os.path.isdir( extn_dir ):
        msg = "Can't find the VASL extensions directory: {}".format( extn_dir )
        _logger.error( "%s", msg )
        if msg_store:
            msg_store.error( msg )
        return []

    def log_warning( fmt, *args, **kwargs ): #pylint: disable=missing-docstring
        soft = kwargs.pop( "soft", False )
        msg = fmt.format( *args, **kwargs )
        _warnings.append( msg )
        if soft:
            _logger.info( "%s", msg )
        else:
            _logger.warning( "%s", msg )

    # load our extension info files
    all_extn_info = {}
    dname = app.config.get( "_VASL_EXTN_INFO_DIR_" ) # nb: this is set by the test suite
    if not dname:
        dname = os.path.join( DATA_DIR, "extensions" )
    # NOTE: We sort the filenames so that the test results are stable.
    for fname in sorted( glob.glob( os.path.join(dname,"*.json") ) ):
        _logger.debug( "Loading VASL extension info: %s", fname )
        with open( fname, "r", encoding="utf-8" ) as fp:
            extn_info = json.load( fp )
        all_extn_info[ ( extn_info["extensionId"], extn_info["version"] ) ] = extn_info
        _logger.debug( "- id=%s ; version=%s", extn_info["extensionId"], extn_info["version"] )

    # figure out what filename extensions we will recognize
    valid_fname_extns = app.config.get( "VASL_EXTENSION_FILENAME_EXTNS", ".mdx .vmdx .zip" )
    valid_fname_extns = valid_fname_extns.replace( ";", " " ).replace( ",", " " ).split()

    # process each VASL extension
    extns = []
    # NOTE: We sort the filenames so that the test results are stable.
    for extn_fname in sorted( os.listdir( extn_dir ) ):

        # check if this is a file we're interested in
        if os.path.splitext(extn_fname)[1] not in valid_fname_extns:
            continue
        extn_fname = os.path.join( extn_dir, extn_fname )

        # try to load the extension
        _logger.debug( "Checking VASL extension: %s", extn_fname )
        try:
            with zipfile.ZipFile( extn_fname, "r" ) as zf:
                build_info = zf.read( "buildFile" )
        except zipfile.BadZipFile:
            log_warning( "Can't check VASL extension (not a ZIP file): {}", extn_fname )
            continue
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
            log_warning( "Can't find ID for VASL extension: {}", extn_fname, soft=True )
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
                os.path.split(extn_fname)[1], extn_id, extn_version,
                soft = True
            )
            continue

        # yup - add the extension to the list
        _logger.info( "Accepting VASL extension: %s (%s/%s)", os.path.split(extn_fname)[1], extn_id, extn_version )
        extns.append( ( extn_fname, extn_info ) )

        # add any child extensions
        for extn_info2 in all_extn_info.values():
            if extn_info2.get( "parentExtensionId" ) == extn_info["extensionId"] \
               and extn_info2["version"] == extn_info["version"]:
                extns.append( ( extn_fname, extn_info2 ) )

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
        self._files = [ ( zipfile.ZipFile(fname,"r"), None ) ] #pylint: disable=consider-using-with
        if extns:
            for extn in extns:
                self._files.append(
                    ( zipfile.ZipFile(extn[0],"r"), extn[1] ) #pylint: disable=consider-using-with
                )

        # load the VASL module and any extensions
        self._load_vmod( data_dir )
        if self.vasl_version not in SUPPORTED_VASL_MOD_VERSIONS:
            _logger.warning( "Unsupported VASL version: %s", self.vasl_real_version )

    def __del__( self ):
        # clean up
        # NOTE: We keep our module and extension ZIP files open for the duration (so we can
        # read images out of them on demand), so we need to make sure we close them here.
        if hasattr( self, "_files" ):
            for f in self._files:
                f[0].close()

    def get_piece_image( self, gpid, side, index ):
        """Get the image for the specified piece."""

        # get the image path
        gpid = get_remapped_gpid( self, gpid )
        if gpid not in self._pieces:
            return None, None
        piece = self._pieces[ gpid ]
        assert side in ("front","back")
        image_paths = piece[ side + "_images" ]
        if not image_paths:
            return None, None
        if not isinstance( image_paths, list ):
            image_paths = [ image_paths ]
        image_path = image_paths[ index ]

        # load the image data
        image_path = os.path.join( "images", image_path )
        image_path = re.sub( r"[\\/]+", "/", image_path ) # nb: in case we're on Windows :-/
        # FUDGE! Reading ZIP file should be thread-safe, but there appears to be a bug in Python 3.7 and 3.8
        # that causes intermittent decompression errors:
        #   https://bugs.python.org/issue42369
        # We work around this by only allowing 1 thread to read from a ZIP file at any time. Strictly speaking,
        # we should do this everywhere we read from a ZIP file, but this is the only place where multiple threads
        # come into play. It's also overkill to have a single lock for *all* ZIP files, but it won't kill us
        # to do things this way, and trying to do things "properly" is problematic (i.e. when do we clean up
        # these locks?).
        with _zip_file_lock:
            image_data = piece[ "zip_file" ].read( image_path )

        return image_path, image_data

    def get_piece_info( self ):
        """Get information about each piece."""
        def image_count( piece, key ):
            """Return the number of images the specified piece has."""
            if not piece[key]:
                return 0
            return len(piece[key]) if isinstance( piece[key], list ) else 1
        def get_image_paths( piece ):
            """Return the piece's image paths."""
            paths = piece[ "front_images" ]
            return paths if isinstance(paths,list) else [paths]
        piece_info_table = {}
        for gpid, piece in self._pieces.items():
            piece_info = {
                "name": piece["name"],
                "front_images": image_count( piece, "front_images" ),
                "back_images": image_count( piece, "back_images" ),
                "paths": get_image_paths( piece ),
                "is_small": piece["is_small"],
            }
            piece_info_table[ gpid ] = piece_info
            reverse_gpid = get_reverse_remapped_gpid( self, gpid )
            if reverse_gpid != gpid:
                piece_info_table[ reverse_gpid ] = piece_info
        return piece_info_table

    def get_extns( self ):
        """Return the loaded VASL extensions."""
        return [
            ( files[0].filename, files[1] )
            for files in self._files
            if files[1]
        ]

    def _load_vmod( self, data_dir ): #pylint: disable=too-many-branches,too-many-locals
        """Load a VASL module file and any extensions."""

        # get the VASL version
        build_info = self._files[0][0].read( "buildFile" )
        doc = xml.etree.ElementTree.fromstring( build_info )
        # NOTE: We have data files for each version of VASL, mostly for tracking things like changed GPID's,
        # expected image URL problems, etc. These don't always change between releases, so to avoid
        # having to create a new set of identical data files, we allow VASL versions to be aliased.
        # This also helps in the case of emergency releases e.g. 6.6.3.1 is treated the same as 6.6.3,
        # and beta releases (e.g. 6.6.4-beta5 = 6.6.3).
        self.vasl_real_version = doc.attrib.get( "version" )
        fname = os.path.join( data_dir, "vasl-version-aliases.json" )
        with open( fname, "r", encoding="utf-8" ) as fp:
            aliases = json.load( fp )
        self.vasl_version = aliases.get( self.vasl_real_version, self.vasl_real_version )

        # load our overrides
        fname = os.path.join( data_dir, "vasl-"+self.vasl_version, "vasl-overrides.json" )
        with open( fname, "r", encoding="utf-8" ) as fp:
            vasl_overrides = json.load( fp )
        fname = os.path.join( data_dir, "vasl-"+self.vasl_version, "expected-multiple-images.json" )
        with open( fname, "r", encoding="utf-8" ) as fp:
            expected_multiple_images = json.load( fp )

        # figure out which pieces we're interested in
        target_gpids = get_vo_gpids( self )

        # parse the VASL module and any extensions
        fname = os.path.join( data_dir, "vasl-"+self.vasl_version, "piece-info.json" )
        with open( fname, "r", encoding="utf-8" ) as fp:
            piece_info = json.load( fp )
        for i,files in enumerate( self._files ):
            _logger.info( "Loading VASL %s: %s", ("module" if i == 0 else "extension"), files[0].filename )
            self._parse_zip_file( files[0], target_gpids, piece_info, vasl_overrides, expected_multiple_images )

        # NOTE: The code below may log warnings if we're using an older version of VASL (because we know
        # about pieces that were added in a later version, but, of course, aren't in the older version).
        # However, we don't disable these log messages, since they might be useful if somebody reports
        # a problem, and it turns out they have an older version of VASL configured :-/

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

    def _parse_zip_file( self, zip_file, target_gpids, piece_info, vasl_overrides, expected_multiple_images ): #pylint: disable=too-many-locals
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
                "name": node.attrib["entryName"].strip(),
                "front_images": front_images,
                "back_images": back_images,
                "is_small": piece_info.get( gpid, {} ).get( "is_small", False ),
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
            for attr in ("front_images","back_images"):
                if isinstance( piece[attr], list ) and not piece[attr]:
                    piece[attr] = None
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
            if "-malf-" in val:
                return False
            if val.endswith( (".gif",".png") ):
                return True
            if val.startswith( "," ):
                val = val[1:]
            if val.startswith( (
                "ru/", "ge/", "am/", "br/", "it/", "ja/", "ch/", "sh/", "fr/", "al/", "ax/", "hu/", "fi/", "nk/", "sv/"
              ) ):
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
            front_images, back_images = split_fields(fields[1]), split_fields(fields[0])

        def check_pair( pair ):
            """Check if the front/back images end with the specified strings."""
            return front_images[-1].endswith( pair[0] ) and back_images[-1].endswith( pair[1] )

        # ignore dismantled ordnance
        if len(front_images) > 1:
            for pair in [
              ("dm","dmb"), ("dm.png","dmm.png"), ("-dm.png","-dm-malf.png"),
              ("(KFW)dm.png","(KFW)dmx.png"), ("amrcl75-malf.png","dm-75rcl.gif")
            ]:
                if check_pair( pair ):
                    _logger.debug( "Ignoring dismantled images: gpid=%s, front=%s, back=%s",
                        gpid, front_images, back_images
                    )
                    front_images.pop()
                    back_images.pop()

        # ignore limbered ordnance
        if len(front_images) > 1:
            for pair in [ ("l","lb"), ("l","l-b"),
              ("(KFW)l.png","(KFW)lx.png"), ("(KFW)-limbered.png","(KFW)-limbered-malf.png"),
              ("l(KFW).png","lm(KFW).png")
            ]:
                if check_pair( pair ):
                    # nb: this is for some K:FW ordnance
                    _logger.debug( "Ignoring limbered images: gpid=%s, front=%s, back=%s",
                        gpid, front_images, back_images
                    )
                    front_images.pop()
                    back_images.pop()
            if front_images[-1].endswith( "B.png" ) and front_images[0] == front_images[-1][:-5]+".png":
                # nb: this is for Finnish Guns
                _logger.debug( "Ignoring limbered images: gpid=%s, front=%s, back=%s",
                    gpid, front_images, back_images
                )
                front_images.pop()
                assert not back_images
            elif front_images[-1].endswith( "-BFPb.png" ) and front_images[0] == front_images[-1][:-9]+"-BFP.png":
                # nb: this is for Polish Guns (Poland In Flames)
                _logger.debug( "Ignoring limbered images: gpid=%s, front=%s, back=%s",
                    gpid, front_images, back_images
                )
                front_images.pop()
                assert not back_images

        def tidy_paths( paths ):
            """Tidy up image paths."""
            if paths is None:
                return None
            assert isinstance( paths, list )
            # ensure every path has an extension
            for i,path in enumerate(paths):
                if not os.path.splitext( path )[1]:
                    paths[i] += ".gif"
            # de-listify the paths
            return paths[0] if len(paths) == 1 else paths
        return tidy_paths(front_images), tidy_paths(back_images)

# ---------------------------------------------------------------------

def get_vo_gpids( vasl_mod ):
    """Get the GPID's for the vehicles/ordnance."""

    # initialize
    listings = get_vo_listings( vasl_mod, None )

    # figure out which GPID's we know about
    gpids = set()
    for vo_type in ("vehicles","ordnance"):
        for vo_entries in listings[ vo_type ].values():
            for vo_entry in vo_entries:
                vo_gpids = vo_entry.get( "gpid" )
                if not vo_gpids:
                    continue
                gpids.update(
                    get_remapped_gpid( vasl_mod, str(gpid) )
                    for gpid in (vo_gpids if isinstance(vo_gpids,list) else [vo_gpids])
                )

    return gpids

# ---------------------------------------------------------------------

# VASL 6.4.3 removed several PieceSlot's. There's no comment for the commmit (0a27c24)
# but I suspect it's because they're duplicates. Our data files have the following mappings:
#   SdKfz 10/5: 7140, 2775
#   SdKfz 10/4: 7146, 2772
# but we can't just remove the now-missing GPID's, since any scenarios that use them
# will break. This kind of thing is going to happen again, so we provide a generic mechanism
# for dealing with this kind of thing...
# VASL 6.5.0 introduced a bunch of changes, where pieces were mysteriously assigned a new GPID :-/
GPID_REMAPPINGS = [
    [ "6.4.3", {
        "7140": "2775", # SdKfz 10/5
        "7146": "2772", # SdKfz 10/4
    } ],
    [ "6.5.0", {
        "879": "12483", # 81* MTR M1 (American)
        "900": "3b5:3741", # 12.7 AA M51 (American)
        "1002": "11340", # M8 AC (American)
        "1380": "3b5:7681", # Churchill Bridgelayer (British)
        "3741": "11500", # 45L AT PTP obr. 32 (Axis Minor)
        "3756": "11501", # 150L ART Skoda M28(NOa) (Axis Minor)
        "3766": "11502", # 47L AA Skoda 47L40(t) (Axis Minor)
        "3772": "11503", # 65* INF Cannone da 65/17 (Axis Minor)
        "3896": "11504", # L6/40(i) (Axis Minor)
        "3898": "11506", # wz. 34-I (Axis Minor)
        "4059": "11524", # 40M Nimrod (Hungarian)
        "4065": "11532", # 39M Csaba (Hungarian)
        "6873": "7461", # T-26C (r) nb: also 7463 (Finnish)
        # NOTE: Doug Rimmer confirms that the "FT-17 730m(f)" and "FT-17 730(f)" were probably incorrectly renamed
        # to "FT-17 730(f)" and "FT-17 730(m)". However, the 7124 -> 11479 GPID change is still probably correct.
        # He also suggests that 7124 and 7128 are incorrectly-added duplicates, and the correct ones
        # are 2542 and 2544.
        "7124": "11479", # FT-17 730m(f) (German)
    } ],
    [ "6.5.1", {
        "1527": "12730" # IP Carrier AOV (British)
    } ]
]

REVERSE_GPID_REMAPPINGS = [
    [ row[0], { v: k for k,v in row[1].items() } ]
    for row in GPID_REMAPPINGS
]

def get_remapped_gpid( vasl_mod, gpid ):
    """Check if a GPID has been remapped."""
    if not vasl_mod:
        return gpid
    for remappings in GPID_REMAPPINGS:
        # FUDGE! Early versions of this code (pre-6.5.0) always applied the remappings for 6.4.3,
        # even for versions of VASL earlier than that. For simplicity, we preserve that behavior.
        if compare_version_strings( remappings[0], "6.5.0" ) < 0 \
           or compare_version_strings( vasl_mod.vasl_version, remappings[0] ) >= 0:
            gpid = remappings[1].get( gpid, gpid )
    return gpid

def get_reverse_remapped_gpid( vasl_mod, gpid ):
    """Check if a GPID has been remapped."""
    if not vasl_mod:
        return gpid
    for remappings in REVERSE_GPID_REMAPPINGS:
        if compare_version_strings( vasl_mod.vasl_version, remappings[0] ) >= 0:
            gpid = remappings[1].get( gpid, gpid )
    return gpid
