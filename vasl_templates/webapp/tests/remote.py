"""Allow a remote server to be controlled during tests.

We sometimes make changes to the webapp server during tests, and while we used to do that using pytest's monkeypatch,
that will not work if we are talking to a remote (i.e. in another process) server. This module defines the things
that can be changed during the course of tests, and a simple RPC mechanism that lets them be executed remotely.
It needs to be enabled in the server via the ENABLE_REMOTE_TEST_CONTROL debug switch.
"""

import os
import urllib.request
import json
import glob
import base64
import tempfile
import logging
import random

import pytest

from vasl_templates.webapp import app, globvars
from vasl_templates.webapp.config.constants import DATA_DIR
from vasl_templates.webapp.vasl_mod import set_vasl_mod
from vasl_templates.webapp import main as webapp_main
from vasl_templates.webapp import snippets as webapp_snippets
from vasl_templates.webapp import scenarios as webapp_scenarios
from vasl_templates.webapp import vasl_mod as vasl_mod_module
from vasl_templates.webapp import vo_utils as vo_utils_module

_logger = logging.getLogger( "control_tests" )

_ORIG_CHAPTER_H_NOTES_DIR = app.config.get( "CHAPTER_H_NOTES_DIR", os.environ.get("CHAPTER_H_NOTES_DIR") )

# ---------------------------------------------------------------------

class ControlTests:
    """Control a remote server during tests."""

    def __init__( self, webapp ):
        self.webapp = webapp
        try:
            self.server_url = pytest.config.option.server_url #pylint: disable=no-member
        except AttributeError:
            self.server_url = None
        # set up a temp directory for our test VASL extensions
        self._vasl_extns_temp_dir = tempfile.TemporaryDirectory()

    def __del__( self ):
        self._vasl_extns_temp_dir.cleanup()

    def __getattr__( self, name ):
        """Generic entry point for handling control requests."""
        if name.startswith( ("get_","set_","reset_") ):
            # check if we are talking to a local or remote server
            if self.server_url:
                # remote: return a function that will invoke the handler function on the remote server
                def call_remote( **kwargs ): #pylint: disable=missing-docstring
                    return self._remote_test_control( name, **kwargs )
                return call_remote
            else:
                # local: return the actual handler function
                return getattr( self, "_"+name )
        raise AttributeError( name )

    def _remote_test_control( self, action, **kwargs ):
        """Invoke a handler function on the remote server."""
        if "bin_data" in kwargs:
            kwargs["bin_data"] = base64.b64encode( kwargs["bin_data"] )
        if "gpids" in kwargs:
            kwargs["gpids"] = json.dumps( kwargs["gpids"] )
        resp = urllib.request.urlopen(
            self.webapp.url_for( "control_tests", action=action, **kwargs )
        ).read()
        if resp == b"ok":
            return self
        else:
            return json.loads( resp.decode( "utf-8" ) )

    def _get_app_config( self ): #pylint: disable=no-self-use
        """Get the webapp config."""
        return {
            k: v for k,v in app.config.items()
            if isinstance( v, (str,int,bool,list,dict) )
        }

    def _set_app_config( self, key=None, val=None ):
        """Set the webapp config."""
        if val is None:
            del app.config[ key ]
        else:
            app.config[ key ] = val
        return self

    def _set_data_dir( self, dtype=None ):
        """Set the webapp's data directory."""
        if dtype == "real":
            dname = DATA_DIR
        elif dtype == "test":
            dname = os.path.join( os.path.split(__file__)[0], "fixtures/data" )
        else:
            raise RuntimeError( "Unknown data dir type: {}".format( dtype ) )
        _logger.info( "Setting data dir: %s", dname )
        self.webapp.config[ "DATA_DIR" ] = dname
        vo_utils_module._vo_comments = None #pylint: disable=protected-access
        from vasl_templates.webapp.vo import load_vo_listings
        load_vo_listings( None )
        return self

    def _set_default_scenario( self, fname=None ):
        """Set the default scenario."""
        if fname:
            dname = os.path.join( os.path.split(__file__)[0], "fixtures" )
            fname = os.path.join( dname, fname )
        _logger.info( "Setting default scenario: %s", fname )
        webapp_main.default_scenario = fname
        return self

    def _set_default_template_pack( self, dname=None ):
        """Set the default template pack."""
        if dname == "real":
            dname = os.path.join( os.path.split(__file__)[0], "../data/default-template-pack" )
        elif dname:
            dname2 = os.path.join( os.path.split(__file__)[0], "fixtures" )
            dname = os.path.join( dname2, dname )
        _logger.info( "Setting default template pack: %s", dname )
        webapp_snippets.default_template_pack = dname
        return self

    def _set_gpid_remappings( self, gpids=None ): #pylint: disable=no-self-use
        """Configure the GPID remappings."""
        if isinstance( gpids, str ):
            gpids = json.loads( gpids.replace( "'", '"' ) )
            for row in gpids:
                row[1] = { str(k): v for k,v in row[1].items() }
        _logger.info( "Setting GPID remappings: %s", gpids )
        prev_gpid_mappings = vasl_mod_module.GPID_REMAPPINGS
        vasl_mod_module.GPID_REMAPPINGS = gpids
        return prev_gpid_mappings

    def _get_vasl_mods( self ):
        """Return the available VASL modules."""
        fnames = self._do_get_vasl_mods()
        _logger.debug( "Returning VASL modules:\n%s",
            "\n".join( "- {}".format( f ) for f in fnames )
        )
        return fnames

    def _do_get_vasl_mods( self ): #pylint: disable=no-self-use
        """Return the available VASL modules."""
        try:
            dname = pytest.config.option.vasl_mods #pylint: disable=no-member
            assert dname, "--vasl-mods was not specified."
        except AttributeError:
            dname = app.config[ "TEST_VASL_MODS" ]
        fspec = os.path.join( dname, "*.vmod" )
        return glob.glob( fspec )

    def _set_vasl_mod( self, vmod=None, extns_dtype=None ):
        """Install a VASL module."""

        # configure the VASL extensions
        if extns_dtype:
            if extns_dtype == "real":
                try:
                    dname = pytest.config.option.vasl_extensions #pylint: disable=no-member
                    assert dname, "--vasl-extensions was not specified."
                except AttributeError:
                    dname = app.config[ "TEST_VASL_EXTNS_DIR" ]
            elif extns_dtype == "test":
                dname = self._vasl_extns_temp_dir.name
            else:
                assert False, "Unknown extensions directory type: "+extns_dtype
            _logger.info( "Enabling VASL extensions: %s", dname )
            app.config[ "VASL_EXTNS_DIR" ] = dname
        else:
            _logger.info( "Disabling VASL extensions." )
            app.config[ "VASL_EXTNS_DIR" ] = None

        # configure the VASL module
        if vmod:
            vmod_fnames = self._do_get_vasl_mods()
            if vmod == "random":
                # NOTE: Some tests require a VASL module to be loaded, and since they should all
                # should behave in the same way, it doesn't matter which one we load.
                vmod = random.choice( vmod_fnames )
            else:
                assert vmod in vmod_fnames
            app.config[ "VASL_MOD" ] = vmod
        else:
            app.config[ "VASL_MOD" ] = None
        _logger.info( "Installing VASL module: %s", vmod )

        # install the new VASL module
        from vasl_templates.webapp.main import startup_msg_store
        startup_msg_store.reset()
        vasl_mod_module.warnings = []
        set_vasl_mod( vmod, startup_msg_store )
        from vasl_templates.webapp.vo import load_vo_listings
        load_vo_listings( None )

        return self

    def _get_vasl_extns( self ): #pylint: disable=no-self-use
        """Return the loaded VASL extensions."""
        extns = globvars.vasl_mod.get_extns()
        _logger.debug( "Returning VASL extensions:\n%s",
            "\n".join( "- {}".format( e ) for e in extns )
        )
        return extns

    def _set_test_vasl_extn( self, fname=None, bin_data=None ):
        """Set the test VASL extension."""
        fname = os.path.join( self._vasl_extns_temp_dir.name, fname )
        with open( fname, "wb" ) as fp:
            fp.write( bin_data )
        return self

    def _set_vasl_extn_info_dir( self, dtype=None ):
        """Set the directory containing the VASL extension info files."""
        if dtype:
            dname = os.path.join( os.path.split(__file__)[0], "fixtures/vasl-extensions" )
            dname = os.path.join( dname, dtype )
            _logger.info( "Setting the default VASL extension info directory: %s", dname )
            app.config[ "_VASL_EXTN_INFO_DIR_" ] = dname
        else:
            _logger.info( "Using the default VASL extension info directory." )
            app.config[ "_VASL_EXTN_INFO_DIR_" ] = None
        return self

    def _get_vassal_engines( self ):
        """Get the available VASSAL engines."""
        vassal_engines = self._do_get_vassal_engines()
        _logger.debug( "Returning VASSAL engines:\n%s",
            "\n".join( "- {}".format( ve ) for ve in vassal_engines )
        )
        return vassal_engines

    def _do_get_vassal_engines( self ): #pylint: disable=no-self-use
        """Get the available VASSAL engines."""
        try:
            dname = pytest.config.option.vassal #pylint: disable=no-member
            assert dname, "--vassal was not specified."
        except AttributeError:
            dname = app.config[ "TEST_VASSAL_ENGINES" ]
        vassal_engines = []
        for root,_,fnames in os.walk( dname ):
            for fname in fnames:
                if fname == "Vengine.jar":
                    if root.endswith( "/lib" ):
                        root = root[:-4]
                    vassal_engines.append( root )
        return vassal_engines

    def _set_vassal_engine( self, vengine=None ):
        """Install a VASSAL engine."""
        if vengine:
            assert vengine in self._do_get_vassal_engines()
        _logger.info( "Installing VASSAL engine: %s", vengine )
        app.config["VASSAL_DIR"] = vengine
        return self

    def _set_vo_notes_dir( self, dtype=None ):
        """Set the vehicle/ordnance notes directory."""
        if dtype == "real":
            try:
                dname = pytest.config.option.vo_notes #pylint: disable=no-member
                assert dname, "--vo-notes was not specified."
            except AttributeError:
                dname = _ORIG_CHAPTER_H_NOTES_DIR
        elif dtype == "test":
            dname = os.path.join( os.path.split(__file__)[0], "fixtures/vo-notes" )
        else:
            assert dtype is None
            dname = None
        _logger.info( "Setting vehicle/ordnance notes: %s", dname )
        app.config["CHAPTER_H_NOTES_DIR"] = dname
        from vasl_templates.webapp.vo_notes import load_vo_notes
        load_vo_notes( None )
        return self

    def _set_user_files_dir( self, dtype=None ):
        """Set the user files directory."""
        if dtype == "test":
            dname = os.path.join( os.path.split(__file__)[0], "fixtures/user-files" )
        elif dtype and dtype.startswith( ("http://","https://") ):
            dname = dtype
        else:
            assert dtype is None
            dname = None
        _logger.info( "Setting user files: %s", dname )
        app.config["USER_FILES_DIR"] = dname
        return self

    def _get_last_snippet_image( self ): #pylint: disable=no-self-use
        """Get the last snippet image generated."""
        from vasl_templates.webapp.snippets import last_snippet_image
        assert last_snippet_image
        _logger.info( "Returning the last snippet image: #bytes=%d", len(last_snippet_image) )
        return base64.b64encode( last_snippet_image ).decode( "utf-8" )

    def _get_vasl_mod_warnings( self ): #pylint: disable=no-self-use
        """Get the vasl_mod startup warnings."""
        _logger.info( "Returning the vasl_mod startup warnings: %s", vasl_mod_module.warnings )
        return vasl_mod_module.warnings

    def _reset_template_pack( self ):
        """Force the default template pack to be reloaded."""
        _logger.info( "Reseting the default template pack." )
        globvars.template_pack = None
        return self

    def _set_roar_scenario_index( self, fname=None ):
        """Set the ROAR scenario index file."""
        if fname:
            dname = os.path.join( os.path.split(__file__)[0], "fixtures" )
            fname = os.path.join( dname, fname )
            _logger.info( "Setting the ROAR scenario index file: %s", fname )
            webapp_scenarios._roar_scenarios._set_data( fname ) #pylint: disable=protected-access
        else:
            assert False
        return self

    def _set_scenario_index( self, fname=None ):
        """Set the scenario index file."""
        if fname:
            dname = os.path.join( os.path.split(__file__)[0], "fixtures" )
            fname = os.path.join( dname, fname )
            _logger.info( "Setting the scenario index file: %s", fname )
            webapp_scenarios._asa_scenarios._set_data( fname ) #pylint: disable=protected-access
        else:
            assert False
        return self

    def _reset_last_asa_upload( self ):
        """Reset the saved last upload to the ASL Scenario Archive."""
        _logger.info( "Reseting the last ASA upload." )
        webapp_scenarios._last_asa_upload = None #pylint: disable=protected-access
        return self

    def _get_last_asa_upload( self ): #pylint: disable=no-self-use
        """Get the last set of files uploaded to the ASL Scenario Archive."""
        last_asa_upload = webapp_scenarios._last_asa_upload #pylint: disable=protected-access
        if not last_asa_upload:
            return {} # FUDGE! This is for the remote testing framework :-/
        last_asa_upload = last_asa_upload.copy()
        # FUDGE! We can't send binary data over the remote testing interface, but since the tests just check
        # for the presence of a VASL save file and screenshot, we just send an indicator of that, and not
        # the data itself. This will be reworked when we switch to using gRPC.
        if "vasl_setup" in last_asa_upload:
            assert last_asa_upload["vasl_setup"][:2] == b"PK"
            last_asa_upload[ "vasl_setup" ] = "PK:{}".format( len(last_asa_upload["vasl_setup"]) )
        if "screenshot" in last_asa_upload:
            assert last_asa_upload["screenshot"][:2] == b"\xff\xd8" \
                    and last_asa_upload["screenshot"][-2:] == b"\xff\xd9" # nb: these are the magic numbers for JPEG's
            last_asa_upload[ "screenshot" ] = "JPEG:{}".format( len(last_asa_upload["screenshot"]) )
        _logger.debug( "Returning the last ASA upload: %s", last_asa_upload )
        return last_asa_upload
