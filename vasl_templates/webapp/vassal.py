""" Webapp handlers. """
# Kathmandu, Nepal (NOV/18).

import sys
import os
import shutil
import subprocess
import traceback
import re
import logging
import pprint
import base64
import time
import xml.etree.cElementTree as ET

from flask import request, jsonify

from vasl_templates.webapp import app, globvars
from vasl_templates.webapp.config.constants import BASE_DIR, IS_FROZEN
from vasl_templates.webapp.utils import TempFile, SimpleError, compare_version_strings, is_windows
from vasl_templates.webapp.webdriver import WebDriver
from vasl_templates.webapp.vasl_mod import get_reverse_remapped_gpid

# NOTE: VASSAL dropped support for Java 8 from 3.3.0. The first version of VASL that supported
# the later versions of Java was 6.6.0, but it was compiled against VASSAL 3.4.2, so we don't
# need to support versions of VASSAL prior to this (3.3.0-.2, 3.4.0-.1), since VASL is known
# to not work with them.
# The versions of VASSAL each version of VASL was compiled against, and Java bundled with
# the Windows version of VASSAL are:
#   VASL  | VASSAL  Java
#   ------+------------------
#   6.6.0 | 3.4.2   14.0.2+12
#   6.6.1 | 3.4.6   15+36
#   6.6.2 | 3.5.5   16+36
# NOTE: VASSAL+VASL back-compat has gone out the window :-/ We have to tie versions of VASL
# to specific versions of VASSAL. Sigh...
SUPPORTED_VASSAL_VERSIONS = {
    "3.4.2": [ "6.6.0", "6.6.1" ],
    "3.4.6": [ "6.6.0", "6.6.1" ],
    "3.5.5": [ "6.6.0", "6.6.1", "6.6.2" ],
}
SUPPORTED_VASSAL_VERSIONS_DISPLAY = "3.4.2, 3.4.6, 3.5.5"

# ---------------------------------------------------------------------

@app.route( "/update-vsav", methods=["POST"] )
def update_vsav(): #pylint: disable=too-many-statements,too-many-locals
    """Update labels in a VASL scenario file."""

    # parse the request
    start_time = time.time()
    vsav_data = request.json[ "vsav_data" ]
    vsav_filename = request.json[ "filename" ]
    players = request.json[ "players" ]
    snippets = request.json[ "snippets" ]
    test_mode = request.json.get( "testMode" )

    # initialize
    logger = logging.getLogger( "update_vsav" )

    # update the VASL scenario file
    try:

        # get the VSAV data (we do this inside the try block so that the user gets shown
        # a proper error dialog if there's a problem decoding the base64 data)
        vsav_data = base64.b64decode( vsav_data )
        logger.info( "Updating VSAV (#bytes=%d): %s", len(vsav_data), vsav_filename )

        with TempFile() as input_file:

            # save the VSAV data in a temp file
            input_file.write( vsav_data )
            input_file.close( delete=False )
            fname = app.config.get( "UPDATE_VSAV_INPUT" ) # nb: for diagnosing problems
            if fname:
                logger.debug( "Saving a copy of the VSAV data: %s", fname )
                with open( fname, "wb" ) as fp:
                    fp.write( vsav_data )

            with TempFile() as snippets_file:
                # save the snippets in a temp file
                xml = _save_snippets( snippets, players, snippets_file, test_mode, logger )
                snippets_file.close( delete=False )
                fname = app.config.get( "UPDATE_VSAV_SNIPPETS" ) # nb: for diagnosing problems
                if fname:
                    logger.debug( "Saving a copy of the snippets: %s", fname )
                    with open( fname, "wb" ) as fp:
                        ET.ElementTree( xml ).write( fp )

                # run the VASSAL shim to update the VSAV file
                with TempFile() as output_file, TempFile() as report_file:
                    output_file.close( delete=False )
                    report_file.close( delete=False )
                    vassal_shim = VassalShim()
                    vassal_shim.update_scenario(
                        input_file.name, snippets_file.name, output_file.name, report_file.name
                    )
                    # read the updated VSAV data
                    with open( output_file.name, "rb" ) as fp:
                        vsav_data = fp.read()
                    fname = app.config.get( "UPDATE_VSAV_RESULT" ) # nb: for diagnosing problems
                    if fname:
                        logger.debug( "Saving a copy of the updated VSAV: %s", fname )
                        with open( fname, "wb" ) as fp:
                            fp.write( vsav_data )
                    # read the report
                    report = _parse_label_report( report_file.name )

    except Exception as ex: #pylint: disable=broad-except

        return VassalShim.translate_vassal_shim_exception( ex, logger )

    # return the results
    logger.info( "Updated the VSAV file OK: elapsed=%.3fs", time.time()-start_time )
    vsav_filename = os.path.split( vsav_filename )[1]
    errors = []
    for fail in report["failed"]:
        if fail.get("message"):
            errors.append( "{} <div class='pre'> {} </div>".format( fail["caption"], fail["message"] ) )
        else:
            errors.append( fail["caption"] )
    return jsonify( {
        "vsav_data": base64.b64encode(vsav_data).decode( "utf-8" ),
        "filename": vsav_filename,
        "report": {
            "was_modified": report["was_modified"],
            "labels_created": len(report["created"]),
            "labels_updated": len(report["updated"]),
            "labels_deleted": len(report["deleted"]),
            "labels_unchanged": len(report["unchanged"]),
            "errors": errors,
        },
    } )

def _save_snippets( snippets, players, fp, test_mode, logger ): #pylint: disable=too-many-locals
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

    # add the player details
    root = ET.Element( "snippets" )
    ET.SubElement( root, "player1", nat=players[0] )
    ET.SubElement( root, "player2", nat=players[1] )

    # FUDGE! Some of the VASSAL tests update a scenario and check what labels were updated, but this can fail
    # if we're using the real data files, and make a change to e.g. the common CSS (since it will cause labels
    # to update unexpectedly). To work-around this, if we are running tests, we do tell the VASSAL shim to do
    # "fuzzy" comparisons (and ignore un-important content) when deciding if a label needs to be updated.
    if test_mode:
        root.set( "fuzzyLabelCompares", "true" )

    # add the snippets
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
                    logger.debug( "Generated screenshot for %s (%.3fs): %dx%d",
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
            if "caption" in node.attrib:
                nodes[-1]["caption"] = node.attrib["caption"]
            if node.text:
                nodes[-1]["message"] = node.text
        report[ action.tag ] = nodes
    return report

# ---------------------------------------------------------------------

@app.route( "/analyze-vsav", methods=["POST"] )
def analyze_vsav():
    """Analyze a VASL scenario file."""

    # parse the request
    start_time = time.time()
    vsav_data = request.json[ "vsav_data" ]
    vsav_filename = request.json[ "filename" ]

    # initialize
    logger = logging.getLogger( "analyze_vsav" )

    try:

        # get the VSAV data (we do this inside the try block so that the user gets shown
        # a proper error dialog if there's a problem decoding the base64 data)
        vsav_data = base64.b64decode( vsav_data )
        logger.info( "Analyzing VSAV (#bytes=%d): %s", len(vsav_data), vsav_filename )

        with TempFile() as input_file:

            # save the VSAV data in a temp file
            input_file.write( vsav_data )
            input_file.close( delete=False )
            fname = app.config.get( "ANALYZE_VSAV_INPUT" ) # nb: for diagnosing problems
            if fname:
                logger.debug( "Saving a copy of the VSAV data: %s", fname )
                with open( fname, "wb" ) as fp:
                    fp.write( vsav_data )

            # run the VASSAL shim to analyze the VSAV file
            with TempFile() as report_file:
                report_file.close( delete=False )
                vassal_shim = VassalShim()
                vassal_shim.analyze_scenario( input_file.name, report_file.name )
                report = _parse_analyze_report( report_file.name )

    except Exception as ex: #pylint: disable=broad-except

        return VassalShim.translate_vassal_shim_exception( ex, logger )

    # translate any remapped GPID's back into their original values
    # NOTE: We need to do this e.g. if we're analyzing a scenario that was created using VASL 6.5.0
    # and it contains pieces that had their GPID's changed from 6.4.4. This kind of nonsense
    # is probably unsustainable over the long-term, but we try to maintain some semblance of
    # back-compatibility for as long as we can :-/
    report2 = {}
    for gpid,vals in report.items():
        orig_gpid = get_reverse_remapped_gpid( globvars.vasl_mod, gpid )
        if orig_gpid == gpid:
            report2[ gpid ] = vals
        else:
            report2[ orig_gpid ] = vals

    # return the results
    logger.info( "Analyzed the VSAV file OK: elapsed=%.3fs\n%s",
        time.time() - start_time,
        pprint.pformat( report2, indent=2, width=120 )
    )

    return jsonify( report2 )

def _parse_analyze_report( fname ):
    """Read the analysis report generated by the VASSAL shim."""
    doc = ET.parse( fname )
    report = {}
    for node in doc.getroot():
        report[ node.attrib["gpid"] ] = { "name": node.attrib["name"], "count": node.attrib["count"] }
    return report

# ---------------------------------------------------------------------

class VassalShim:
    """Provide access to VASSAL via the Java shim."""

    _vassal_version = None

    def __init__( self ): #pylint: disable=too-many-branches

        # locate the VASSAL engine
        vassal_dir = self._get_vassal_dir()
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

        # FUDGE! The VASSAL shim looks for a config file in the same directory as itself, but if we are frozen,
        # the user runs the executable that unpacks everything to a temp directory and runs from there, and so
        # they can't set up the config file. Instead, we allow them to place it in the config/ directory and
        # copy it over over to the temp directory, where the VASSAL shim JAR will find it when it runs.
        fname = os.path.join( os.path.join(BASE_DIR,"config"), "vassal-shim.properties" )
        if os.path.isfile( fname ):
            shutil.copy( fname, os.path.split(self.shim_jar)[0] )

    @staticmethod
    def get_version():
        """Get the VASSAL version."""
        if VassalShim._vassal_version:
            return VassalShim._vassal_version
        vassal_dir = VassalShim._get_vassal_dir()
        if not vassal_dir:
            return None
        # FUDGE! We can't capture the output on Windows, get the result in a temp file instead :-/
        with TempFile() as temp_file:
            temp_file.close( delete=False )
            VassalShim()._run_vassal_shim( "version", temp_file.name ) #pylint: disable=protected-access
            with open( temp_file.name, "r", encoding="utf-8" ) as fp:
                VassalShim._vassal_version = fp.read()
                return VassalShim._vassal_version

    @staticmethod
    def is_compatible_version( vassal_version, vasl_version ):
        """Check if the VASSAL+VASL versions are compatible."""
        return vasl_version in SUPPORTED_VASSAL_VERSIONS.get( vassal_version, [] )

    def dump_scenario( self, fname ):
        """Dump a scenario file."""
        return self._run_vassal_shim( "dump", fname )

    def analyze_scenario( self, vsav_fname, report_fname ):
        """Analyze a scenario file."""
        return self._run_vassal_shim(
            "analyze", vsav_fname, report_fname
        )

    def update_scenario( self, vsav_fname, snippets_fname, output_fname, report_fname ):
        """Update a scenario file."""

        # locate the boards
        return self._run_vassal_shim(
            "update", VassalShim.get_boards_dir(), vsav_fname, snippets_fname, output_fname, report_fname
        )

    def analyze_logfiles( self, *fnames ):
        """Analyze a log file."""
        return self._run_vassal_shim(
            "analyzeLogs", *fnames
        )

    def prepare_asa_upload( self, vsave_fname, stripped_vsav_fname, screenshot_fname ):
        """Prepare files for upload to the ASL Scenario Archive."""
        return self._run_vassal_shim(
            "prepareUpload", vsave_fname, stripped_vsav_fname, screenshot_fname
        )

    def _run_vassal_shim( self, *args ): #pylint: disable=too-many-locals
        """Run the VASSAL shim."""

        # initialize
        logger = logging.getLogger( "vassal_shim" )

        # figure out where Java is
        java_path = app.config.get( "JAVA_PATH" )
        java8_path = app.config.get( "JAVA8_PATH" )
        if java8_path:
            # FUDGE! From 3.3, VASSAL no longer works with Java 8. We want to mantain back-compatibility
            # with the older versions of VASL (6.5.1 and older) for some time, and while it's not a big issue
            # from the user's perspective (they just configure the appropriate VASSAL+VASL), it's problematic
            # for the test suite (since it has to be able to run the correct version of Java for the VASSAL
            # being used). We do this here, and since it's just for the purpose of running tests, we can
            # require that the VASSAL version be embedded in the filename.
            # NOTE: I eventually gave up trying to maintain back-compat with older versions of VASL, but
            # the GPID remapping test (test_gpid_remapping() in test_counters.py) is an important one,
            # but is currently only relevant for 6.4.4 and 6.5.0-.1, so for the sole purpose of being able
            # to run those tests, we still support Java 8. Sigh...
            mo = re.search( r"\d+\.\d+\.\d+", self.vengine_jar )
            if compare_version_strings( mo.group(), "3.3.0" ) < 0:
                # we're using a legacy version of VASSAL - use Java 8
                java_path = java8_path
        if not java_path and is_windows():
            # we're on Windows - try to use the Java that is now bundled with VASSAL
            fname = os.path.join( self._get_vassal_dir(), "jre/bin/java.exe" )
            if os.path.isfile( fname ):
                java_path = fname
        if not java_path:
            java_path = "java" # nb: this must be in the PATH

        # prepare the command
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
        if args[0] in ("dump","analyze","analyzeLogs","update","prepareUpload"):
            if not globvars.vasl_mod:
                raise SimpleError( "The VASL module has not been configured." )
            args2.append( globvars.vasl_mod.filename )
        args2.extend( args[1:] )

        # figure out how long to the let the VASSAL shim run
        # NOTE: This used to be 2 minutes, but adding the ability to load images from the internet
        # slows the process down, since VASSAL loads images insanely slowly :-/
        timeout = int( app.config.get( "VASSAL_SHIM_TIMEOUT", 5*60 ) )
        if timeout <= 0:
            timeout = None

        # run the VASSAL shim
        logger.info( "Running VASSAL shim (timeout=%s): %s", str(timeout), " ".join(args2) )
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
                raise SimpleError( "Can't run the VASSAL shim (have you configured Java?): {}".format( ex ) ) from ex
            try:
                proc.wait( timeout )
            except subprocess.TimeoutExpired:
                proc.kill()
                raise
            buf1.close( delete=False )
            stdout = open( buf1.name, "r", encoding="utf-8" ).read()
            buf2.close( delete=False )
            stderr = open( buf2.name, "r", encoding="utf-8" ).read()
        elapsed_time = time.time() - start_time
        logger.info( "- Completed OK: %.3fs", elapsed_time )

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
            logger.warning( "VASSAL shim stderr output:\n%s", stderr )
        if proc.returncode != 0:
            raise VassalShimError( proc.returncode, stdout, stderr )
        return stdout

    @staticmethod
    def get_boards_dir():
        """Get the configured boards directory."""
        boards_dir = app.config.get( "BOARDS_DIR" )
        if not boards_dir:
            raise SimpleError( "The VASL boards directory has not been configured." )
        if not os.path.isdir( boards_dir ):
            raise SimpleError( "Can't find the VASL boards: {}".format( boards_dir ) )
        return boards_dir

    @staticmethod
    def translate_vassal_shim_exception( ex, logger ):
        """Convert an exception thrown by the VassalShim to a JSON response to return to the caller."""

        if isinstance( ex, VassalShimError ):
            logger.error( "VASSAL shim error: rc=%d", ex.retcode )
            if ex.retcode != 0:
                return jsonify( {
                    "error": "Unexpected return code from the VASSAL shim: {}".format( ex.retcode ),
                    "stdout": ex.stdout,
                    "stderr": ex.stderr,
                } )
            return jsonify( {
                "error": "Unexpected error output from the VASSAL shim.",
                "stdout": ex.stdout,
                "stderr": ex.stderr,
            } )
        if isinstance( ex, subprocess.TimeoutExpired ):
            return jsonify( {
                "error": "<p>The VASSAL shim took too long to run, please try again." \
                         "<p>If this problem persists, try configuring a longer timeout."
            } )
        if isinstance( ex, SimpleError ):
            logger.error( "VASSAL shim error: %s", ex )
            return jsonify( { "error": str(ex) } )

        logger.error( "Unexpected VASSAL shim error: %s", ex )
        return jsonify( {
            "error": str(ex),
            "stdout": traceback.format_exc(),
        } )

    @staticmethod
    def check_vassal_version( msg_store ):
        """Check the version of VASSAL."""
        if not VassalShim._get_vassal_dir() or not msg_store:
            return
        try:
            version = VassalShim.get_version()
        except Exception as ex: #pylint: disable=broad-except
            if msg_store:
                msg_store.error( "Can't get the VASSAL version: <p> {}", ex )
            return
        if version not in SUPPORTED_VASSAL_VERSIONS:
            if msg_store:
                msg_store.warning(
                    "This program has not been tested with VASSAL {}.<p>Things might work, but they might not...",
                    version
                )
        elif globvars.vasl_mod:
            if not VassalShim.is_compatible_version( version, globvars.vasl_mod.vasl_version ):
                if msg_store:
                    msg_store.error(
                        "VASSAL {} and VASL {} are not compatible.".format( version, globvars.vasl_mod.vasl_version ),
                        version
                    )

    @staticmethod
    def _get_vassal_dir():
        """Get the VASSAL installation directory."""
        return app.config.get( "VASSAL_DIR" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

class VassalShimError( Exception ):
    """Represents an error returned by the VASSAL shim."""

    def __init__( self, retcode, stdout, stderr ):
        super().__init__()
        self.retcode = retcode
        self.stdout = stdout
        self.stderr = stderr

    def __str__( self ):
        return "VassalShim error: rc={}".format( self.retcode )
