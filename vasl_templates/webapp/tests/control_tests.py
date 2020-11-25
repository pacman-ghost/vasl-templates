""" Allow the test suite to control a remote webapp server. """

import json
import base64

import grpc
from google.protobuf.empty_pb2 import Empty

from vasl_templates.webapp.tests.proto.generated.control_tests_pb2_grpc import ControlTestsStub
from vasl_templates.webapp.tests.proto.utils import enum_from_string

from vasl_templates.webapp.tests.proto.generated.control_tests_pb2 import \
    SetVassalVersionRequest, SetVaslVersionRequest, SetVaslExtnInfoDirRequest, SetGpidRemappingsRequest, \
    SetDataDirRequest, SetDefaultScenarioRequest, SetDefaultTemplatePackRequest, \
    SetVehOrdNotesDirRequest, SetUserFilesDirRequest, \
    SetAsaScenarioIndexRequest, SetRoarScenarioIndexRequest, \
    DumpVsavRequest, GetVaslPiecesRequest, \
    SetAppConfigValRequest, DeleteAppConfigValRequest,  \
    SaveTempFileRequest

# ---------------------------------------------------------------------

# NOTE: The API for this class should be kept in sync with ControlTestsServicer.

class ControlTests: #pylint: disable=too-many-public-methods
    """Control a remote webapp server."""

    def __init__( self, addr ):
        # initialize
        channel = grpc.insecure_channel( addr )
        self._stub = ControlTestsStub( channel )
        self._caps = None

    def has_capability( self, cap ) :
        """Check if the remote webapp has the specified capability."""
        return cap in self._caps

    def start_tests( self ):
        """Start a new test run."""
        resp = self._stub.startTests( Empty() )
        self._caps = set( resp.capabilities )
        return self

    def end_tests( self ):
        """End a test run."""
        self._stub.endTests( Empty() )
        self._caps = None

    def get_vassal_versions( self ):
        """Get the available VASSAL versions."""
        resp = self._stub.getVassalVersions( Empty() )
        return resp.vassalVersions

    def set_vassal_version( self, vassal_version ):
        """Set the VASSAL version."""
        self._stub.setVassalVersion(
            SetVassalVersionRequest( vassalVersion = vassal_version )
        )
        return self

    def get_vasl_versions( self ):
        """Get the available VASL versions."""
        resp = self._stub.getVaslVersions( Empty() )
        return resp.vaslVersions

    def set_vasl_version( self, vasl_mod, vasl_extns_type ):
        """Set the VASL version."""
        vasl_extns_type = enum_from_string(
            SetVaslVersionRequest.VaslExtnsType, #pylint: disable=no-member
            vasl_extns_type or "{NONE}"
        )
        self._stub.setVaslVersion(
            SetVaslVersionRequest( vaslVersion=vasl_mod, vaslExtnsType=vasl_extns_type )
        )
        return self

    def get_vasl_extns( self ):
        """Get the VASL extensions."""
        resp = self._stub.getVaslExtns( Empty() )
        return json.loads( resp.vaslExtnsJson )

    def set_vasl_extn_info_dir( self, dname ):
        """Set the VASL extensions info directory."""
        self._stub.setVaslExtnInfoDir(
            SetVaslExtnInfoDirRequest( dirName = dname )
        )
        return self

    def set_gpid_remappings( self, gpid_remappings ):
        """Set the GPID remappings."""
        self._stub.setGpidRemappings(
            SetGpidRemappingsRequest( gpidRemappingsJson = json.dumps( gpid_remappings ) )
        )
        return self

    def get_vasl_mod_warnings( self ):
        """Get the vasl_mod warnings."""
        resp = self._stub.getVaslModWarnings( Empty() )
        return resp.warnings

    def set_data_dir( self, dtype ):
        """Set the data directory."""
        dtype = enum_from_string( SetDataDirRequest.DirType, dtype ) #pylint: disable=no-member
        self._stub.setDataDir(
            SetDataDirRequest( dirType = dtype )
        )
        return self

    def set_default_scenario( self, fname ):
        """Set the default scenario."""
        self._stub.setDefaultScenario(
            SetDefaultScenarioRequest( fileName = fname )
        )
        return self

    def set_default_template_pack( self, template_pack ):
        """Set the default template pack."""
        if isinstance( template_pack, str ) and template_pack.startswith( "{" ) and template_pack.endswith( "}" ):
            val = enum_from_string(
                SetDefaultTemplatePackRequest.TemplatePackType, #pylint: disable=no-member
                template_pack
            )
            req = SetDefaultTemplatePackRequest( templatePackType = val )
        elif isinstance( template_pack, str ):
            req = SetDefaultTemplatePackRequest( dirName = template_pack )
        elif isinstance( template_pack, bytes ):
            req = SetDefaultTemplatePackRequest( zipData = template_pack )
        else:
            raise ValueError( "Can't identify template pack type: {}".format( type(template_pack).__name__ ) )
        self._stub.setDefaultTemplatePack( req )
        return self

    def set_vo_notes_dir( self, dtype ):
        """Set the vehicle/ordnance notes directory."""
        dtype = enum_from_string( SetVehOrdNotesDirRequest.DirType, dtype or "{NONE}" ) #pylint: disable=no-member
        self._stub.setVehOrdNotesDir(
            SetVehOrdNotesDirRequest( dirType = dtype )
        )
        return self

    def set_user_files_dir( self, dname_or_url ):
        """Set the user files directory."""
        self._stub.setUserFilesDir(
            SetUserFilesDirRequest( dirOrUrl = dname_or_url )
        )
        return self

    def set_asa_scenario_index( self, fname ):
        """Set the ASL Scenario Archive scenario index."""
        self._stub.setAsaScenarioIndex(
            SetAsaScenarioIndexRequest( fileName = fname )
        )
        return self

    def set_roar_scenario_index( self, fname ):
        """Set the ROAR scenario index."""
        self._stub.setRoarScenarioIndex(
            SetRoarScenarioIndexRequest( fileName = fname )
        )
        return self

    def get_last_snippet_image( self ):
        """Get the last snippet image."""
        resp = self._stub.getLastSnippetImage( Empty() )
        return resp.imageData

    def reset_last_asa_upload( self ):
        """Reset the last ASL Scenario Archive upload."""
        self._stub.resetLastAsaUpload( Empty() )
        return self

    def get_last_asa_upload( self ):
        """Get the last ASL Scenario Archive upload."""
        resp = self._stub.getLastAsaUpload( Empty() )
        last_asa_upload = json.loads( resp.lastUploadJson )
        if last_asa_upload:
            for key in ("vasl_setup","screenshot"):
                if last_asa_upload.get( key ):
                    last_asa_upload[key] = base64.b64decode( last_asa_upload[key].encode( "ascii" ) )
        return last_asa_upload

    def dump_vsav( self, vsav ):
        """Dump a VASL save file."""
        if isinstance( vsav, str ):
            with open( vsav, "rb" ) as fp:
                vsav = fp.read()
        resp = self._stub.dumpVsav(
            DumpVsavRequest( vsavData = vsav )
        )
        return resp.vsavDump

    def get_vasl_pieces( self, vasl_version ):
        """Get the pieces for the specified VASL module."""
        resp = self._stub.getVaslPieces( GetVaslPiecesRequest( vaslVersion=vasl_version ) )
        return resp.pieceDump, resp.gpids

    def get_app_config( self ):
        """Get the app config."""
        resp = self._stub.getAppConfig( Empty() )
        return json.loads( resp.appConfigJson )

    def set_app_config_val( self, key, val ):
        """Set an app config value."""
        if isinstance( val, str ):
            req = SetAppConfigValRequest( key=key, strVal=val )
        elif isinstance( val, int ):
            req = SetAppConfigValRequest( key=key, intVal=val )
        elif isinstance( val, bool ):
            req = SetAppConfigValRequest( key=key, boolVal=val )
        else:
            raise ValueError( "Invalid value type: {}".format( type(val).__name__ ) )
        self._stub.setAppConfigVal( req )
        return self

    def delete_app_config_key( self, key ):
        """Delete an app config value."""
        self._stub.deleteAppConfigVal(
            DeleteAppConfigValRequest( key = key )
        )
        return self

    def save_temp_file( self, fname, data ):
        """Save a temp file."""
        self._stub.saveTempFile(
            SaveTempFileRequest( fileName=fname, data=data )
        )
        return self
