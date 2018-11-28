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
from vasl_templates.webapp.files import vasl_mod
from vasl_templates.webapp.file_server.vasl_mod import SUPPORTED_VASL_MOD_VERSIONS
from vasl_templates.webapp.utils import TempFile, HtmlScreenshots, SimpleError

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

def _save_snippets( snippets, fp ):
    """Save the snippets in a file.

    NOTE: We save the snippets as XML because Java :-/
    """

    def get_html_size( snippet_id, html, window_size ):
        """Get the size of the specified HTML."""
        start_time = time.time()
        img = html_screenshots.get_screenshot( html, window_size )
        elapsed_time = time.time() - start_time
        width, height = img.size
        _logger.debug( "Generated screenshot for %s (%.3fs): %dx%d", snippet_id, elapsed_time, width, height )
        return width, height

    def do_save_snippets( html_screenshots ):
        """Save the snippets."""

        root = ET.Element( "snippets" )
        for key,val in snippets.items():

            # add the next snippet
            auto_create = "true" if val["auto_create"] else "false"
            elem = ET.SubElement( root, "snippet", id=key, autoCreate=auto_create )
            elem.text = val["content"]
            label_area = val.get( "label_area" )
            if label_area:
                elem.set( "labelArea", label_area )

            # add the raw content
            elem2 = ET.SubElement( elem, "rawContent" )
            for node in val["raw_content"]:
                ET.SubElement( elem2, "phrase" ).text = node

            # include the size of the snippet
            if html_screenshots:
                try:
                    # NOTE: Screenshots take significantly longer for larger window sizes. Since most of our snippets
                    # will be small, we first try with a smaller window, and switch to a larger one if necessary.
                    width, height = get_html_size( key, val["content"], (500,500) )
                    if width >= 450 or height >= 450:
                        # NOTE: While it's tempting to set the browser window really large here, if the label ends up
                        # filling/overflowing the available space (e.g. because its width/height has been set to 100%),
                        # then the auto-created label will push any subsequent labels far down the map, possibly to
                        # somewhere unreachable. So, we set it somewhat more conservatively, so that if this happens,
                        # the user still has a chance to recover from it. Note that this doesn't mean that they can't
                        # have really large labels, it just affects the positioning of auto-created labels.
                        width, height = get_html_size( key, val["content"], (1500,1500) )
                    # FUDGE! There's something weird going on in VASSAL e.g. "<table width=300>" gives us something
                    # very different to "<table style='width:300px;'>" :-/ Changing the font size also causes problems.
                    # The following fudging seems to give us something that's somewhat reasonable... :-/
                    if re.search( r"width:\s*?\d+?px", val["content"] ):
                        width = int( width * 140 / 100 )
                    elem.set( "width", str(width) )
                    elem.set( "height", str(height) )
                except Exception as ex: #pylint: disable=broad-except
                    # NOTE: Don't let an error here stop the process.
                    logging.error( "Can't get snippet screenshot: %s", ex )
                    logging.error( traceback.format_exc() )

        ET.ElementTree( root ).write( fp )
        return root

    # save the snippets
    if app.config.get( "DISABLE_UPDATE_VSAV_SCREENSHOTS" ):
        return do_save_snippets( None )
    else:
        with HtmlScreenshots() as html_screenshots:
            return do_save_snippets( html_screenshots )

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

    def __init__( self ):

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

        # locate the boards
        self.boards_dir = app.config.get( "BOARDS_DIR" )
        if not self.boards_dir:
            raise SimpleError( "The VASL boards directory has not been configured." )
        if not os.path.isdir( self.boards_dir ):
            raise SimpleError( "Can't find the VASL boards: {}".format( self.boards_dir ) )

        # locate the VASL module
        self.vasl_mod = app.config.get( "VASL_MOD" )
        if not self.vasl_mod:
            raise SimpleError( "The VASL module has not been configured." )
        if not os.path.isfile( self.vasl_mod ):
            raise SimpleError( "Can't find VASL module: {}".format( self.vasl_mod ) )

        # locate the VASSAL shim JAR
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
            args2.append( self.vasl_mod )
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
            if not IS_FROZEN:
                kwargs = { "stdout": buf1.temp_file, "stderr": buf2.temp_file }
            if os.name == "nt":
                # NOTE: Using CREATE_NO_WINDOW doesn't fix the problem of VASSAL's UI sometimes appearing,
                # but it does hide the DOS box if the user has configured java.exe instead of javaw.exe.
                kwargs["creationflags"] = 0x8000000 # nb: win32process.CREATE_NO_WINDOW
            proc = subprocess.Popen( args2, **kwargs )
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

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class VassalShimError( Exception ):
    """Represents an error returned by the VASSAL shim."""

    def __init__( self, retcode, stdout, stderr ):
        super().__init__()
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr

# ---------------------------------------------------------------------

@app.route( "/check-vassal-version" )
def check_vassal_version():
    """Check if we're running a supported version of VASSAL."""
    vassal_dir = app.config.get( "VASSAL_DIR" )
    if vassal_dir:
        vassal_shim = VassalShim()
        version = vassal_shim.get_version()
        if version not in SUPPORTED_VASSAL_VERSIONS:
            return "VASSAL {} is unsupported.<p>Things might work, but they might not...".format( version )
    return ""

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@app.route( "/check-vasl-version" )
def check_vasl_version():
    """Check if we're running a supported version of VASL."""
    if vasl_mod and vasl_mod.vasl_version not in SUPPORTED_VASL_MOD_VERSIONS:
        return "VASL {} is unsupported.<p>Things might work, but they might not...".format( vasl_mod.vasl_version )
    return ""
