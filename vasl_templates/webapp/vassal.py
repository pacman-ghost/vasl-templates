""" Webapp handlers. """
# Kathmandu, Nepal (NOV/18).

import sys
import os
import subprocess
import traceback
import json
import re
import logging
import base64
import time
import xml.etree.cElementTree as ET

from flask import request

from vasl_templates.webapp import app
from vasl_templates.webapp.config.constants import BASE_DIR, IS_FROZEN
from vasl_templates.webapp.vasl_mod import get_vasl_mod
from vasl_templates.webapp.utils import TempFile, SimpleError
from vasl_templates.webapp.webdriver import WebDriver

_logger = logging.getLogger( "update_vsav" )

SUPPORTED_VASSAL_VERSIONS = [ "3.2.15" ,"3.2.16", "3.2.17" ]
SUPPORTED_VASSAL_VERSIONS_DISPLAY = "3.2.15-.17"

# ---------------------------------------------------------------------

@app.route( "/update-vsav", methods=["POST"] )
def update_vsav(): #pylint: disable=too-many-statements
    """Update labels in a VASL scenario file."""

    # parse the request
    start_time = time.time()
    vsav_data = request.json[ "vsav_data" ]
    vsav_filename = request.json[ "filename" ]
    snippets = request.json[ "snippets" ]

    # update the VASL scenario file
    try:

        # get the VSAV data (we do this inside the try block so that the user gets shown
        # a proper error dialog if there's a problem decoding the base64 data)
        vsav_data = base64.b64decode( vsav_data )
        _logger.info( "Updating VSAV (#bytes=%d): %s", len(vsav_data), vsav_filename )

        with TempFile() as input_file:
            # save the VSAV data in a temp file
            input_file.write( vsav_data )
            input_file.close()
            fname = app.config.get( "UPDATE_VSAV_INPUT" ) # nb: for diagnosing problems
            if fname:
                _logger.debug( "Saving a copy of the VSAV data: %s", fname )
                with open( fname, "wb" ) as fp:
                    fp.write( vsav_data )
            with TempFile() as snippets_file:
                # save the snippets in a temp file
                xml = _save_snippets( snippets, snippets_file )
                snippets_file.close()
                fname = app.config.get( "UPDATE_VSAV_SNIPPETS" ) # nb: for diagnosing problems
                if fname:
                    _logger.debug( "Saving a copy of the snippets: %s", fname )
                    with open( fname, "wb" ) as fp:
                        ET.ElementTree( xml ).write( fp )
                # run the VASSAL shim to update the VSAV file
                with TempFile() as output_file, TempFile() as report_file:
                    output_file.close()
                    report_file.close()
                    vassal_shim = VassalShim()
                    vassal_shim.update_scenario(
                        input_file.name, snippets_file.name, output_file.name, report_file.name
                    )
                    # read the updated VSAV data
                    with open( output_file.name, "rb" ) as fp:
                        vsav_data = fp.read()
                    fname = app.config.get( "UPDATE_VSAV_RESULT" ) # nb: for diagnosing problems
                    if fname:
                        _logger.debug( "Saving a copy of the update VSAV: %s", fname )
                        with open( app.config.get("UPDATE_VSAV_RESULT"), "wb" ) as fp:
                            fp.write( vsav_data )
                    # read the report
                    label_report = _parse_label_report( report_file.name )
    except VassalShimError as ex:
        _logger.error( "VASSAL shim error: rc=%d", ex.retcode )
        if ex.retcode != 0:
            return json.dumps( {
                "error": "Unexpected return code from the VASSAL shim: {}".format( ex.retcode ),
                "stdout": ex.stdout,
                "stderr": ex.stderr,
            } )
        return json.dumps( {
            "error": "Unexpected error output from the VASSAL shim.",
            "stdout": ex.stdout,
            "stderr": ex.stderr,
        } )
    except subprocess.TimeoutExpired:
        return json.dumps( {
            "error": "<p>The updater took too long to run, please try again." \
                     "<p>If this problem persists, try configuring a longer timeout."
        } )
    except SimpleError as ex:
        _logger.error( "VSAV update error: %s", ex )
        return json.dumps( { "error": str(ex) } )
    except Exception as ex: #pylint: disable=broad-except
        _logger.error( "Unexpected VSAV update error: %s", ex )
        return json.dumps( {
            "error": str(ex),
            "stdout": traceback.format_exc(),
        } )

    # return the results
    _logger.debug( "Updated the VSAV file OK: elapsed=%.3fs", time.time()-start_time )
    # NOTE: We adjust the recommended save filename to encourage users to not overwrite the original file :-/
    vsav_filename = os.path.split( vsav_filename )[1]
    fname, extn = os.path.splitext( vsav_filename )
    return json.dumps( {
        "vsav_data": base64.b64encode(vsav_data).decode( "utf-8" ),
        "filename": fname+" (updated)" + extn,
        "report": {
            "was_modified": label_report["was_modified"],
            "labels_created": len(label_report["created"]),
            "labels_updated": len(label_report["updated"]),
            "labels_deleted": len(label_report["deleted"]),
            "labels_unchanged": len(label_report["unchanged"]),
        },
    } )

def _save_snippets( snippets, fp ): #pylint: disable=too-many-locals
    """Save the snippets in a file.

    NOTE: We save the snippets as XML because Java :-/
    """

    # NOTE: We used to create a WebDriver here and re-use it for each snippet screenshot,
    # but when we implemented the shared WebDriver, we changed things to request it for each
    # snippet. If we did things the old way, the WebDriver wouldn't be able to shutdown
    # until it had finished *all* the snippet screenshots (since we would have it locked);
    # the new way, we only have to wait for it to finish the snippet it's on, the WebDriver
    # will be unlocked, and then the other thread will be able to grab the lock and shut
    # it down. The downside is that if the user has to disable the shared WebDriver, things
    # will run ridiculously slowly, since we will be launching a new webdriver for each snippet.
    # We optimize for the case where things work properly... :-/

    root = ET.Element( "snippets" )
    for snippet_id,snippet_info in snippets.items():

        # add the next snippet
        auto_create = "true" if snippet_info["auto_create"] else "false"
        elem = ET.SubElement( root, "snippet", id=snippet_id, autoCreate=auto_create )
        elem.text = snippet_info["content"]
        label_area = snippet_info.get( "label_area" )
        if label_area:
            elem.set( "labelArea", label_area )

        # add the raw content
        elem2 = ET.SubElement( elem, "rawContent" )
        for node in snippet_info.get( "raw_content", [] ):
            ET.SubElement( elem2, "phrase" ).text = node

        # include the size of the snippet
        if not app.config.get( "DISABLE_UPDATE_VSAV_SCREENSHOTS" ):
            with WebDriver.get_instance() as webdriver:
                try:
                    start_time = time.time()
                    img = webdriver.get_snippet_screenshot( snippet_id, snippet_info["content"] )
                    width, height = img.size
                    elapsed_time = time.time() - start_time
                    _logger.debug( "Generated screenshot for %s (%.3fs): %dx%d",
                        snippet_id, elapsed_time, width, height
                    )
                    # FUDGE! There's something weird going on in VASSAL e.g. "<table width=300>" gives us something
                    # very different to "<table style='width:300px;'>" :-/ Changing the font size also causes problems.
                    # The following fudging seems to give us something that's somewhat reasonable... :-/
                    if re.search( r"width:\s*?\d+?px", snippet_info["content"] ):
                        width = int( width * 140 / 100 )
                    elem.set( "width", str(width) )
                    elem.set( "height", str(height) )
                except Exception as ex: #pylint: disable=broad-except
                    # NOTE: Don't let an error here stop the process.
                    logging.error( "Can't get snippet screenshot: %s", ex )
                    logging.error( traceback.format_exc() )

    ET.ElementTree( root ).write( fp )
    return root

def _parse_label_report( fname ):
    """Read the label report generated by the VASSAL shim."""
    doc = ET.parse( fname )
    report = {
        "was_modified": doc.getroot().attrib["wasModified"] == "true"
    }
    for action in doc.getroot():
        nodes = []
        for node in action:
            nodes.append( { "id": node.attrib["id"] } )
            if "x" in node.attrib and "y" in node.attrib:
                nodes[-1]["pos"] = ( node.attrib["x"], node.attrib["y"] )
        report[ action.tag ] = nodes
    return report

# ---------------------------------------------------------------------

class VassalShim:
    """Provide access to VASSAL via the Java shim."""

    def __init__( self ): #pylint: disable=too-many-branches

        # initialize
        self.boards_dir = None

        # locate the VASSAL engine
        vassal_dir = app.config.get( "VASSAL_DIR" )
        if not vassal_dir:
            raise SimpleError( "The VASSAL installation directory has not been configured." )
        self.vengine_jar = None
        for root,_,fnames in os.walk( vassal_dir ):
            for fname in fnames:
                if fname == "Vengine.jar":
                    self.vengine_jar = os.path.join( root, fname )
                    break
        if not self.vengine_jar:
            raise SimpleError( "Can't find Vengine.jar: {}".format( vassal_dir ) )

        # locate the VASSAL shim JAR
        self.shim_jar = app.config.get( "VASSAL_SHIM" )
        if not self.shim_jar:
            if IS_FROZEN:
                meipass = sys._MEIPASS #pylint: disable=no-member,protected-access
                self.shim_jar = os.path.join( meipass, "vasl_templates/webapp/vassal-shim.jar" )
            else:
                self.shim_jar = os.path.join( os.path.split(__file__)[0], "../../vassal-shim/release/vassal-shim.jar" )
        if not os.path.isfile( self.shim_jar ):
            raise SimpleError( "Can't find the VASSAL shim JAR." )

    def get_version( self ):
        """Get the VASSAL version."""
        # FUDGE! We can't capture the output on Windows, get the result in a temp file instead :-/
        with TempFile() as temp_file:
            temp_file.close()
            self._run_vassal_shim( "version", temp_file.name )
            with open( temp_file.name, "r" ) as fp:
                return fp.read()

    def dump_scenario( self, fname ):
        """Dump a scenario file."""
        return self._run_vassal_shim( "dump", fname )

    def update_scenario( self, vsav_fname, snippets_fname, output_fname, report_fname ):
        """Update a scenario file."""

        # locate the boards
        self.boards_dir = app.config.get( "BOARDS_DIR" )
        if not self.boards_dir:
            raise SimpleError( "The VASL boards directory has not been configured." )
        if not os.path.isdir( self.boards_dir ):
            raise SimpleError( "Can't find the VASL boards: {}".format( self.boards_dir ) )

        # locate the VASL module
        if not get_vasl_mod():
            raise SimpleError( "The VASL module has not been configured." )

        return self._run_vassal_shim(
            "update", self.boards_dir, vsav_fname, snippets_fname, output_fname, report_fname
        )

    def _run_vassal_shim( self, *args ): #pylint: disable=too-many-locals
        """Run the VASSAL shim."""

        # prepare the command
        java_path = app.config.get( "JAVA_PATH" )
        if not java_path:
            java_path = "java" # nb: this must be in the PATH
        class_path = app.config.get( "JAVA_CLASS_PATH" )
        if not class_path:
            class_path = [ self.vengine_jar, self.shim_jar ]
            class_path.append( os.path.split( self.shim_jar )[0] ) # nb: to find logback(-test).xml
            if IS_FROZEN:
                class_path.append( BASE_DIR ) # nb: also to find logback(-test).xml
            sep = ";" if os.name == "nt" else ":"
            class_path = sep.join( class_path )
        args2 = [
            java_path, "-classpath", class_path, "vassal_shim.Main",
            args[0]
        ]
        if args[0] in ("dump","update"):
            args2.append( get_vasl_mod().filename )
        args2.extend( args[1:] )

        # figure out how long to the let the VASSAL shim run
        timeout = int( app.config.get( "VASSAL_SHIM_TIMEOUT", 120 ) )
        if timeout <= 0:
            timeout = None

        # run the VASSAL shim
        _logger.debug( "Running VASSAL shim (timeout=%s): %s", str(timeout), " ".join(args2) )
        start_time = time.time()
        # NOTE: We can't use pipes to capture the output here when we're frozen on Windows ("invalid handle" errors),
        # I suspect because we freeze the application using --noconsole, which causes problems when
        # the child process tries to inherit handles. Capturing the output in temp files also fails (!),
        # as does using subprocess.DEVNULL (!!!) Setting close_fds when calling Popen() also made no difference.
        # The only thing that worked was removing "--noconsole" when freezing the application, but that causes
        # a DOS box to appear when we are run :-/
        # However, we can also not specify any stdout/stderr, and since we don't actually check the output,
        # we can get away with this, even if it is a bit icky :-/ However, if the VASSAL shim throws an error,
        # we won't be able to show the stack trace, just a generic "VASSAL shim failed" message :-(
        with TempFile() as buf1, TempFile() as buf2:
            kwargs = {}
            if not ( os.name == "nt" and IS_FROZEN ):
                kwargs = { "stdout": buf1.temp_file, "stderr": buf2.temp_file }
            if os.name == "nt":
                # NOTE: Using CREATE_NO_WINDOW doesn't fix the problem of VASSAL's UI sometimes appearing,
                # but it does hide the DOS box if the user has configured java.exe instead of javaw.exe.
                kwargs["creationflags"] = 0x8000000 # nb: win32process.CREATE_NO_WINDOW
            try:
                proc = subprocess.Popen( args2, **kwargs )
            except FileNotFoundError as ex:
                raise SimpleError( "Can't run the VASSAL shim (have you configured Java?): {}".format( ex ) )
            try:
                proc.wait( timeout )
            except subprocess.TimeoutExpired:
                proc.kill()
                raise
            buf1.close()
            stdout = open( buf1.name, "r", encoding="utf-8" ).read()
            buf2.close()
            stderr = open( buf2.name, "r", encoding="utf-8" ).read()
        elapsed_time = time.time() - start_time
        _logger.debug( "- Completed OK: %.3fs", elapsed_time )

        # check the result
        stderr = stderr.replace( "Warning: Could not get charToByteConverterClass!", "" ).strip()
        # NOTE: VASSAL's internal representation of a scenario seems to be tightly coupled with its UI,
        # which means that when we load a scenario, bits of the UI sometimes start appearing (although not always,
        # presumably because there's a race between how fast we can make our changes and save the scenario
        # vs. how fast the UI can start up :-/). When the UI does start to appear, it fails, presumably because
        # we haven't performed the necessary startup incantations, and dumps a stack trace to stderr.
        # The upshot is that the only thing we look for is an exit code of 0, which means that the VASSAL shim
        # saved the scenario successfully and exited cleanly; any output on stderr means that some part
        # of VASSAL barfed as it was trying to start up and can (hopefully) be safely ignored.
        if stderr:
            _logger.info( "VASSAL shim stderr output:\n%s", stderr )
        if proc.returncode != 0:
            raise VassalShimError( proc.returncode, stdout, stderr )
        return stdout

    @staticmethod
    def check_vassal_version( msg_store ):
        """Check the version of VASSAL."""
        if not app.config.get( "VASSAL_DIR" ) or not msg_store:
            return
        version = VassalShim().get_version()
        if version not in SUPPORTED_VASSAL_VERSIONS:
            msg_store.warning(
                "VASSAL {} is unsupported.<p>Things might work, but they might not...".format( version )
            )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class VassalShimError( Exception ):
    """Represents an error returned by the VASSAL shim."""

    def __init__( self, retcode, stdout, stderr ):
        super().__init__()
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr
