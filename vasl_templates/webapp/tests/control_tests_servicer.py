"""gRPC servicer that allows the webapp server to be controlled."""

import os
import json
import tempfile
import glob
import re
import logging
import io
import copy
import base64
import inspect
import random

import tabulate
from google.protobuf.empty_pb2 import Empty #pylint: disable=no-name-in-module

from vasl_templates.webapp.config.constants import DATA_DIR
from vasl_templates.webapp.vassal import VassalShim
from vasl_templates.webapp.utils import TempFile
from vasl_templates.webapp import \
    main as webapp_main, \
    vasl_mod as webapp_vasl_mod, \
    scenarios as webapp_scenarios, \
    snippets as webapp_snippets, \
    globvars as webapp_globvars

from vasl_templates.webapp.tests.proto.generated.control_tests_pb2_grpc \
    import ControlTestsServicer as BaseControlTestsServicer

from vasl_templates.webapp.tests.proto.generated.control_tests_pb2 import \
    SetVassalVersionRequest, SetVaslVersionRequest, SetVaslExtnInfoDirRequest, SetGpidRemappingsRequest, \
    SetDataDirRequest, SetDefaultScenarioRequest, SetDefaultTemplatePackRequest, \
    SetVehOrdNotesDirRequest, SetUserFilesDirRequest, \
    SetAsaScenarioIndexRequest, SetRoarScenarioIndexRequest, \
    SetAppConfigValRequest, DeleteAppConfigValRequest
from vasl_templates.webapp.tests.proto.generated.control_tests_pb2 import \
    StartTestsResponse, \
    GetVassalVersionsResponse, GetVaslVersionsResponse, GetVaslExtnsResponse, GetVaslModWarningsResponse, \
    GetLastSnippetImageResponse, GetLastAsaUploadResponse, \
    DumpVsavResponse, GetVaslPiecesResponse, GetAppConfigResponse

# nb: these are defined as a convenience
_VaslExtnsTypes_NONE = SetVaslVersionRequest.VaslExtnsType.NONE #pylint: disable=no-member
_VaslExtnsTypes_REAL = SetVaslVersionRequest.VaslExtnsType.REAL #pylint: disable=no-member
_VaslExtnsTypes_TEMP_DIR = SetVaslVersionRequest.VaslExtnsType.TEMP_DIR #pylint: disable=no-member
_TemplatePackTypes_DEFAULT = SetDefaultTemplatePackRequest.TemplatePackType.DEFAULT #pylint: disable=no-member
_TemplatePackTypes_REAL = SetDefaultTemplatePackRequest.TemplatePackType.REAL #pylint: disable=no-member

_logger = logging.getLogger( "control_tests" )

_FIXTURES_DIR = os.path.join( os.path.dirname(__file__), "fixtures" )
_ORIG_GPID_REMAPPINGS = copy.deepcopy( webapp_vasl_mod.GPID_REMAPPINGS )
_ORIG_CHAPTER_H_NOTES_DIR = None

# ---------------------------------------------------------------------

# NOTE: The API for this class should be kept in sync with ControlTests.

class ControlTestsServicer( BaseControlTestsServicer ): #pylint: disable=too-many-public-methods
    """Allows a webapp server to be controlled by a remote client."""

    def __init__( self, webapp ):

        # initialize
        self._webapp = webapp
        global _ORIG_CHAPTER_H_NOTES_DIR
        if not _ORIG_CHAPTER_H_NOTES_DIR:
            _ORIG_CHAPTER_H_NOTES_DIR = webapp.config.get( "CHAPTER_H_NOTES_DIR" )
        self._temp_dir = None

        # look for VASSAL engines
        _logger.debug( "Locating VASSAL engines:" )
        self._vassal_engines = {}
        dname = self._webapp.config.get( "TEST_VASSAL_ENGINES" )
        if dname:
            for root,_,fnames in os.walk( dname ):
                if os.sep + "_disabled_" + os.sep in root:
                    continue
                for fname in fnames:
                    if fname == "Vengine.jar":
                        if root.endswith( "/lib" ):
                            root = root[:-4]
                        # FUDGE! We assume that the version number is part of the path (we can do this
                        # since we are only used for running tests i.e. in a controlled environment).
                        mo = re.search( r"\d+\.\d+\.\d+", root )
                        self._vassal_engines[ mo.group() ] = root
                        break
            for key,val in self._vassal_engines.items():
                _logger.debug( "- %s -> %s", key, val )

        # look for VASL modules
        _logger.debug( "Locating VASL modules:" )
        self._vasl_mods = {}
        dname = self._webapp.config.get( "TEST_VASL_MODS" )
        if dname:
            fspec = os.path.join( dname, "*.vmod" )
            for fname in glob.glob( fspec ):
                # FUDGE! We assume that the version number is part of the filename (we can do this
                # since we are only used for running tests i.e. in a controlled environment).
                mo = re.search( r"\d+\.\d+\.\d+(\.\d+)?", os.path.basename(fname) )
                self._vasl_mods[ mo.group() ] = fname
            for key,val in self._vasl_mods.items():
                _logger.debug( "- %s -> %s", key, val )

    def __del__( self ):
        # clean up
        self.cleanup()

    def cleanup( self ):
        """Clean up."""
        if self._temp_dir:
            self._temp_dir.cleanup()
        self._temp_dir = None

    def startTests( self, request, context ):
        """Start a new test run."""
        _logger.info( "=== START TESTS ===" )

        # check that everything has been configured properly
        # NOTE: We do this here instead of __init__() so that we can return an error message to the client,
        # rather than having the servicer fail to start up, giving the client a "can't connect" error.
        if not self._vassal_engines:
            raise RuntimeError( "No VASSAL releases were configured (see debug.cfg.example)." )
        if not self._vasl_mods:
            raise RuntimeError( "No VASL modules were configured (see debug.cfg.example)." )

        # set up a directory for our temp files
        if self._temp_dir:
            self._temp_dir.cleanup()
        self._temp_dir = tempfile.TemporaryDirectory() #pylint: disable=consider-using-with

        # reset the webapp server
        ctx = None
        self.setDataDir(
            SetDataDirRequest( dirType = SetDataDirRequest.DirType.TEST ), ctx #pylint: disable=no-member
        )
        self.setDefaultScenario( SetDefaultScenarioRequest( fileName=None ), ctx )
        self.setDefaultTemplatePack(
            SetDefaultTemplatePackRequest( templatePackType = _TemplatePackTypes_DEFAULT ),
            ctx
        )
        self.setVehOrdNotesDir(
            SetVehOrdNotesDirRequest( dirType = SetVehOrdNotesDirRequest.DirType.NONE ), ctx #pylint: disable=no-member
        )
        self.setUserFilesDir( SetUserFilesDirRequest( dirOrUrl=None ), ctx )
        self.setVassalVersion( SetVassalVersionRequest( vassalVersion=None ), ctx )
        self.setVaslVersion( SetVaslVersionRequest( vaslVersion=None ), ctx )
        self.setGpidRemappings(
            SetGpidRemappingsRequest( gpidRemappingsJson = json.dumps(_ORIG_GPID_REMAPPINGS) ), ctx
        )
        self.setVaslExtnInfoDir( SetVaslExtnInfoDirRequest( dirName=None ), ctx )
        self.setAsaScenarioIndex( SetAsaScenarioIndexRequest( fileName="asl-scenario-archive.json" ), ctx )
        self.setRoarScenarioIndex( SetRoarScenarioIndexRequest( fileName="roar-scenario-index.json" ), ctx )
        self.setAppConfigVal( SetAppConfigValRequest( key="MAP_URL", strVal="MAP:[{LAT},{LONG}]" ), ctx )
        self.setAppConfigVal( SetAppConfigValRequest( key="DISABLE_DOWNLOADED_FILES", boolVal=True ), ctx )
        self.setAppConfigVal( SetAppConfigValRequest( key="DISABLE_LOCAL_ASA_INDEX_UPDATES", boolVal=True ), ctx )
        self.setAppConfigVal( SetAppConfigValRequest( key="DISABLE_LFA_HOTNESS_FADEIN", boolVal=True ), ctx )
        self.deleteAppConfigVal( DeleteAppConfigValRequest( key="ASL_RULEBOOK2_BASE_URL" ), ctx )
        self.deleteAppConfigVal( DeleteAppConfigValRequest( key="ALTERNATE_WEBAPP_BASE_URL" ), ctx )
        self.setAppConfigVal( SetAppConfigValRequest( key="VO_NOTES_IMAGE_CACHE_DIR", strVal="disabled" ), ctx )
        # NOTE: The webapp has been reconfigured, but the client must reloaed the home page
        # with "?force-reinit=1", to force it to re-initialize with the new settings.

        # NOTE: Dealing with landing craft is a major PITA, since it breaks the usual access pattern
        # of "nat/vo-type". For the purpose of tests, we disable them in the back-end (so that we can
        # detect problems there, as well as in the front-end), and enable them only when needed.
        self.setAppConfigVal( SetAppConfigValRequest( key="_DISABLE_LANDING_CRAFT_", boolVal=True ), ctx )

        # return our capabilities to the caller
        caps = []
        if _ORIG_CHAPTER_H_NOTES_DIR:
            # NOTE: Some tests require real Chapter H vehicle/ordnance notes. This is copyrighted material,
            # so it is kept in a private repo. For the purpose of running tests, it is considered optional
            # and tests that need it can check this capability and not run if it's not available.
            caps.append( "chapter-h" )

        return StartTestsResponse( capabilities=caps )

    def endTests( self, request, context ):
        """End a test run."""
        self._log_request( request, context )
        # end the test run
        # NOTE: If the active VaslMod has loaded any extension files from our temp directory, since they are
        # kept open for the duration, we need to clean up the VaslMod (so that it will close these files),
        # otherwise we may not be able to clean up our temp file directory.
        webapp_vasl_mod.set_vasl_mod( None, None )
        self.cleanup()
        return Empty()

    def getVassalVersions( self, request, context ):
        """Get the available VASSAL versions."""
        self._log_request( request, context )
        # get the available VASSAL versions
        vassal_versions = list( self._vassal_engines.keys() )
        _logger.debug( "- Returning VASSAL versions: %s", " ; ".join( vassal_versions ) )
        return GetVassalVersionsResponse( vassalVersions=vassal_versions )

    def setVassalVersion( self, request, context ):
        """Set the VASSAL version."""
        self._log_request( request, context )
        vassal_version = request.vassalVersion
        # set the VASSAL engine
        if vassal_version == "random":
            # NOTE: Some tests require VASSAL to be configured, and since they should all
            # should behave in the same way, it doesn't matter which one we use.
            dname = random.choice( list( self._vassal_engines.values() ) )
        elif vassal_version:
            dname = self._vassal_engines.get( vassal_version )
            if not dname:
                raise RuntimeError( "Unknown VASSAL version: {}".format( vassal_version ) )
        else:
            dname = None
        _logger.debug( "- Setting VASSAL engine: %s", dname )
        self._webapp.config[ "VASSAL_DIR" ] = dname
        return Empty()

    def getVaslVersions( self, request, context ):
        """Get the available VASL versions."""
        self._log_request( request, context )
        # get the available VASL versions
        vasl_versions = list( self._vasl_mods.keys() )
        _logger.debug( "- Returning VASL versions: %s", " ; ".join( vasl_versions ) )
        return GetVaslVersionsResponse( vaslVersions=vasl_versions )

    def setVaslVersion( self, request, context ):
        """Set the VASL version."""
        self._log_request( request, context )
        vasl_version, vasl_extns_type = request.vaslVersion, request.vaslExtnsType
        # set the VASL module
        if vasl_version == "random":
            # NOTE: Some tests require a VASL module to be loaded, and since they should all
            # should behave in the same way, it doesn't matter which one we use.
            fname = random.choice( list( self._vasl_mods.values() ) )
        elif vasl_version:
            fname = self._vasl_mods.get( vasl_version )
            if not fname:
                raise RuntimeError( "Unknown VASL version: {}".format( vasl_version ) )
        else:
            fname = None
        _logger.debug( "- Setting VASL module: %s", fname )
        self._webapp.config[ "VASL_MOD" ] = fname

        # configure the VASL extensions
        if vasl_extns_type == _VaslExtnsTypes_NONE:
            dname = None
        elif vasl_extns_type == _VaslExtnsTypes_REAL:
            dname = os.path.join( _FIXTURES_DIR, "vasl-extensions/real/" )
        elif vasl_extns_type == _VaslExtnsTypes_TEMP_DIR:
            dname = self._temp_dir.name
        else:
            raise RuntimeError( "Unknown VASL extensions type: {}".format( vasl_extns_type ) )
        _logger.debug( "- Setting VASL extensions: %s", dname )
        self._webapp.config[ "VASL_EXTNS_DIR" ] = dname

        return Empty()

    def getVaslExtns( self, request, context ):
        """Get the VASL extensions."""
        self._log_request( request, context )
        # get the VASL extensions
        vasl_extns = webapp_globvars.vasl_mod.get_extns()
        _logger.debug( "- %s", vasl_extns )
        return GetVaslExtnsResponse(
            vaslExtnsJson = json.dumps( vasl_extns )
        )

    def setVaslExtnInfoDir( self, request, context ):
        """Set the VASL extensions info directory."""
        self._log_request( request, context )
        dname = request.dirName
        # set the VASL extensions info directory
        if dname:
            dname = os.path.join( _FIXTURES_DIR, "vasl-extensions/"+dname )
        else:
            dname = None
        _logger.debug( "- Setting the default VASL extension info directory: %s", dname )
        self._webapp.config[ "_VASL_EXTN_INFO_DIR_" ] = dname
        return Empty()

    def setGpidRemappings( self, request, context ):
        """Set the GPID remappings."""
        self._log_request( request, context )
        gpid_remappings = json.loads( request.gpidRemappingsJson )
        # set the GPID remappings
        if gpid_remappings == _ORIG_GPID_REMAPPINGS:
            _logger.debug( "- Setting GPID remappings: (original)" )
        else:
            _logger.debug( "- Setting GPID remappings:" )
            for vassal_version, mappings in gpid_remappings.items():
                _logger.debug( "  - %s: %s", vassal_version, mappings )
        webapp_vasl_mod.GPID_REMAPPINGS = gpid_remappings
        return Empty()

    def getVaslModWarnings( self, request, context ):
        """Get the vasl_mod warnings."""
        self._log_request( request, context )
        # get the vasl_mod warnings
        warnings = webapp_vasl_mod._warnings #pylint: disable=protected-access
        _logger.debug( "- %s", warnings )
        return GetVaslModWarningsResponse( warnings=warnings )

    def setDataDir( self, request, context ):
        """Set the data directory."""
        self._log_request( request, context )
        dtype = request.dirType
        # set the data directory
        if dtype == SetDataDirRequest.DirType.TEST: #pylint: disable=no-member
            dname = os.path.join( _FIXTURES_DIR, "data" )
        elif dtype == SetDataDirRequest.DirType.REAL: #pylint: disable=no-member
            dname = DATA_DIR
        else:
            raise RuntimeError( "Unknown data dir type: {}".format( dtype ) )
        _logger.debug( "- Setting data directory: %s", dname )
        self._webapp.config[ "DATA_DIR" ] = dname
        return Empty()

    def setDefaultScenario( self, request, context ):
        """Set the default scenario."""
        self._log_request( request, context )
        fname = request.fileName
        # set the default scenario
        if fname:
            fname = os.path.join( _FIXTURES_DIR, fname )
        else:
            fname = None
        _logger.debug( "- Setting default scenario: %s", fname )
        webapp_main.default_scenario = fname
        return Empty()

    def setDefaultTemplatePack( self, request, context ):
        """Set the default template pack."""
        self._log_request( request, context )
        # set the default template pack
        if request.HasField( "templatePackType" ):
            if request.templatePackType == _TemplatePackTypes_DEFAULT:
                target = None
            elif request.templatePackType == _TemplatePackTypes_REAL:
                target = os.path.join( os.path.dirname(__file__), "../data/default-template-pack/" )
            else:
                raise RuntimeError( "Invalid TemplatePackType: {}".format( request.templatePackType ) )
        elif request.HasField( "dirName" ):
            target = os.path.join( _FIXTURES_DIR, "template-packs/"+request.dirName )
        elif request.HasField( "zipData" ):
            fname = os.path.join( self._temp_dir.name, "default-template-pack.zip" )
            with open( fname, "wb" ) as fp:
                fp.write( request.zipData )
            target = fname
        else:
            raise RuntimeError( "Can't find the default template pack specification." )
        _logger.debug( "- Setting default template pack: %s", target )
        webapp_snippets.default_template_pack = target
        webapp_globvars.template_pack = None # nb: force the default template pack to be reloaded
        return Empty()

    def setVehOrdNotesDir( self, request, context ):
        """Set the vehicle/ordnance notes directory."""
        self._log_request( request, context )
        dtype = request.dirType
        # set the vehicle/ordnance notes directory
        if dtype == SetVehOrdNotesDirRequest.DirType.NONE: #pylint: disable=no-member
            dname = None
        elif dtype == SetVehOrdNotesDirRequest.DirType.REAL: #pylint: disable=no-member
            dname = _ORIG_CHAPTER_H_NOTES_DIR
        elif dtype == SetVehOrdNotesDirRequest.DirType.TEST: #pylint: disable=no-member
            dname = os.path.join( _FIXTURES_DIR, "vo-notes" )
        else:
            raise RuntimeError( "Invalid vehicle/ordnance notes dir.type: {}".format( dtype ) )
        _logger.debug( "- Setting vehicle/ordnance notes: %s", dname )
        self._webapp.config[ "CHAPTER_H_NOTES_DIR" ] = dname
        return Empty()

    def setUserFilesDir( self, request, context ):
        """Set the user files directory."""
        self._log_request( request, context )
        # set the user files directory
        dname = request.dirOrUrl
        if dname:
            if not dname.startswith( ( "http://", "https://" ) ):
                dname = os.path.join( _FIXTURES_DIR, dname )
        else:
            dname = None
        _logger.debug( "- Setting user files directory: %s", dname )
        self._webapp.config[ "USER_FILES_DIR" ] = dname
        return Empty()

    def setAsaScenarioIndex( self, request, context ):
        """Set the ASL Scenario Archive scenario index."""
        self._log_request( request, context )
        fname = request.fileName
        # set the ASL Scenario Archive scenario index
        if fname:
            fname = os.path.join( _FIXTURES_DIR, fname )
        else:
            fname = None
        _logger.debug( "- Setting ASA scenario index: %s", fname )
        webapp_scenarios._asa_scenarios._set_data( fname ) #pylint: disable=protected-access
        return Empty()

    def setRoarScenarioIndex( self, request, context ):
        """Set the ROAR scenario index."""
        self._log_request( request, context )
        fname = request.fileName
        # set the ROAR scenario index
        if fname:
            fname = os.path.join( _FIXTURES_DIR, fname )
        else:
            fname = None
        _logger.debug( "- Setting ROAR scenario index: %s", fname )
        webapp_scenarios._roar_scenarios._set_data( fname ) #pylint: disable=protected-access
        return Empty()

    def getLastSnippetImage( self, request, context ):
        """Get the last snippet image."""
        self._log_request( request, context )
        # get the last snippet image
        last_snippet_image = webapp_snippets.last_snippet_image
        _logger.debug( "- Returning the last snippet image: %s",
            "#bytes={}".format( len(last_snippet_image) ) if last_snippet_image else None
        )
        return GetLastSnippetImageResponse( imageData=last_snippet_image )

    def resetLastAsaUpload( self, request, context ):
        """Reset the last ASL Scenario Archive upload."""
        self._log_request( request, context )
        # reset the last ASL Scenario Archive upload
        webapp_scenarios._last_asa_upload = None #pylint: disable=protected-access
        return Empty()

    def getLastAsaUpload( self, request, context ):
        """Get the last ASL Scenario Archive upload."""
        last_asa_upload = webapp_scenarios._last_asa_upload #pylint: disable=protected-access
        # return the last ASL Scenario Archive upload
        _logger.debug( "- Returning the last ASA upload: %s", last_asa_upload )
        if last_asa_upload:
            for key in ("vasl_setup","screenshot"):
                if last_asa_upload.get( key ):
                    last_asa_upload[key] = base64.b64encode( last_asa_upload[key] ).decode( "ascii" )
        return GetLastAsaUploadResponse( lastUploadJson = json.dumps( last_asa_upload ) )

    def dumpVsav( self, request, context ):
        """Dump a VASL save file."""
        self._log_request( request, context )
        # dump the VSAV
        with TempFile( mode="wb" ) as temp_file:
            temp_file.write( request.vsavData )
            temp_file.close( delete=False )
            vassal_shim = VassalShim()
            vsav_dump = vassal_shim.dump_scenario( temp_file.name )
        _logger.debug( "- VSAV dump: #bytes=%s", len(vsav_dump) )
        return DumpVsavResponse( vsavDump=vsav_dump )

    def getVaslPieces( self, request, context ):
        """Get the pieces for the specified VASL module."""
        self._log_request( request, context )
        vasl_version = request.vaslVersion

        # dump the VASL pieces
        fname = self._vasl_mods[ vasl_version ]
        vasl_mod = webapp_vasl_mod.VaslMod( fname, self._webapp.config["DATA_DIR"], None )
        buf = io.StringIO()
        results = [ [ "GPID", "Name", "Front images", "Back images"] ]
        pieces = vasl_mod._pieces #pylint: disable=protected-access
        # GPID's were originally int's but then changed to str's. We then started seeing non-numeric GPID's :-/
        # For back-compat, we try to maintain sort order for numeric values.
        def sort_key( val ): #pylint: disable=missing-docstring
            if val.isdigit():
                return ( "0"*10 + val )[-10:]
            else:
                # make sure that alphanumeric values appear after numeric values, even if they start with a number
                return "_" + val
        gpids = sorted( pieces.keys(), key=sort_key ) # nb: because GPID's changed from int to str :-/
        for gpid in gpids:
            piece = pieces[ gpid ]
            assert piece["gpid"] == gpid
            results.append( [ gpid, piece["name"], piece["front_images"], piece["back_images"] ] )
        print( tabulate.tabulate( results, headers="firstrow", numalign="left" ), file=buf )

        # get the piece GPID's
        gpids = webapp_vasl_mod.get_vo_gpids( vasl_mod )

        return GetVaslPiecesResponse(
            pieceDump=buf.getvalue(), gpids=gpids
        )

    def getAppConfig( self, request, context ):
        """Get the app config."""
        self._log_request( request, context )
        # get the app config
        app_config = self._webapp.config
        _logger.debug( "- %s", app_config )
        return GetAppConfigResponse(
            appConfigJson = json.dumps( app_config, default=str )
        )

    def setAppConfigVal( self, request, context ):
        """Set an app config value."""
        self._log_request( request, context )
        # get the app config setting
        for val_type in ( "strVal", "intVal", "boolVal" ):
            if request.HasField( val_type ):
                key, val = request.key, getattr(request,val_type)
                _logger.debug( "- Setting app config: %s = %s (%s)", key, str(val), type(val).__name__ )
                if isinstance( val, str ):
                    val = val.replace( "{{TEMP_DIR}}", self._temp_dir.name ) \
                             .replace( "{{FIXTURES_DIR}}", _FIXTURES_DIR )
                self._webapp.config[ key ] = val
                return Empty()
        raise RuntimeError( "Can't find app config key." )

    def deleteAppConfigVal( self, request, context ):
        """Delete an app config value."""
        self._log_request( request, context )
        key = request.key
        # delete the app config setting
        _logger.debug( "- Deleting app config: %s", key )
        if key in self._webapp.config:
            del self._webapp.config[ key ]
        return Empty()

    def saveTempFile( self, request, context ):
        """Save a temp file."""
        self._log_request( request, context )
        fname, data = request.fileName, request.data
        # save the temp file
        fname = os.path.join( self._temp_dir.name, fname )
        _logger.debug( "- Saving temp file (#bytes=%d): %s", len(data), fname )
        with open( fname, "wb" ) as fp:
            fp.write( data )
        return Empty()

    @staticmethod
    def _log_request( req, ctx ):
        """Log a request."""
        if ctx is None:
            return # nb: we don't log internal calls
        # get the entry-point name
        msg = "{}()".format( inspect.currentframe().f_back.f_code.co_name )
        # add the brief request info
        func = getattr( req, "brief", None )
        if func:
            brief = func()
            if brief:
                msg += ": {}".format( brief )
        # add the request dump
        func = getattr( req, "dump", None )
        if func:
            buf = io.StringIO()
            func( out=buf )
            buf = buf.getvalue().strip()
            if buf:
                msg += "\n{}".format( buf )
        # log the message
        _logger.info( "TEST CONTROL: %s", msg )
