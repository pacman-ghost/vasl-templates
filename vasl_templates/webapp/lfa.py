""" Webapp handlers. """

import os
import time
import base64
import logging
import xml.etree.cElementTree as ET

from flask import request, jsonify

from vasl_templates.webapp import app
from vasl_templates.webapp.vassal import VassalShim
from vasl_templates.webapp.utils import SimpleError, TempFile

# weights for each possible roll value
DEFAULT_LFA_DICE_HOTNESS_WEIGHTS = {
    "DR": { 2: 20, 3: 16, 4: 12, 5: 8, 6: 4, 7: 0, 8: -4, 9: -8, 10: -12, 11: -16, 12: -20 },
    "dr": { 1: 3, 2: 2, 3: 1, 4: -1, 5: -2, 6: -3 }
}

# minimum number of rolls for dice hotness to be considered reasonable
DEFAULT_LFA_DICE_HOTNESS_THRESHOLDS = {
    "DR": 100, "dr": 50
}

# ---------------------------------------------------------------------

@app.route( "/analyze-vlogs", methods=["POST"] )
def analyze_vlogs(): #pylint: disable=too-many-locals
    """Analyze VASL log file(s)."""

    # parse the request
    start_time = time.time()
    vlog_data = request.json

    # initialize
    logger = logging.getLogger( "analyze_vlogs" )
    temp_files = []

    try:

        # save each VLOG file in a temp file
        if not vlog_data:
            raise SimpleError( "No log files were submitted." )
        for vlog_no, vlog in enumerate( vlog_data ):
            fname, data = vlog
            data = base64.b64decode( data )
            logger.info( "Analyzing VLOG (#bytes=%d): %s", len(data), fname )
            temp_file = TempFile()
            temp_file.open()
            temp_file.write( data )
            temp_file.close( delete=False )
            save_fname = app.config.get( "ANALYZE_VLOG_INPUT" )
            if save_fname:
                if len(vlog_data) == 1:
                    temp_file.save_copy( save_fname, logger, "VLOG data" )
                else:
                    parts = os.path.splitext( save_fname )
                    temp_file.save_copy( "{}-{}".format(parts[0],1+vlog_no) + parts[1], logger, "VLOG data" )
            temp_files.append( temp_file )

        # run the VASSAL shim to analyze the VLOG file(s)
        with TempFile() as report_file:
            report_file.close( delete=False )
            vassal_shim = VassalShim()
            fnames = [ tf.name for tf in temp_files ]
            fnames.append( report_file.name )
            vassal_shim.analyze_logfiles( *fnames )
            report_file.save_copy( app.config.get("ANALYZE_VLOG_REPORT"), logger, "analysis report" )
            report = parse_analysis_report( report_file.name, logger )

    except Exception as ex: #pylint: disable=broad-except

        return VassalShim.translate_vassal_shim_exception( ex, logger )

    finally:

        # clean up
        for tf in temp_files:
            tf.close( delete=True )

    # insert the filenames for each log file, as they were passed in to us
    for vlog_no,vlog in enumerate( vlog_data ):
        report["logFiles"][ vlog_no ]["filename"] = vlog[0]

    # return the results
    logger.info( "Analyzed the VLOG file(s) OK: elapsed=%.3fs", time.time()-start_time )
    return jsonify( report )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def parse_analysis_report( fname, logger=None ):
    """Parse the analysis report generated by the VASSAL shim."""

    # initialize
    doc = ET.parse( fname )

    # get the complete list of players across all the log files
    players = {}
    for elem in doc.findall( ".//diceEvent" ):
        player_name = elem.attrib[ "player" ]
        if player_name not in players:
            # NOTE: ChartJS (in the frontend Javascript) identifies datasets using a 0-based index,
            # so to avoid accidentally mixing these up with player ID's, we generate non-numeric player ID's.
            player_id = "p:{}".format( len(players) + 1 )
            players[ player_name ] = player_id

    # generate the results for each log file
    log_files = []
    for logFileElem in doc.findall( ".//logFile" ):

        # process the events for the next log file
        events, scenario = [], {}
        for elem in logFileElem.find( ".//events" ):

            if elem.tag == "diceEvent":
                # found a DICE ROLL event
                player_id = players[ elem.attrib["player"] ]
                values = [ int(v) for v in elem.text.split(",") ]
                events.append( {
                    "eventType": "roll",
                    "playerId": player_id,
                    "rollType": elem.attrib[ "rollType" ],
                    "rollValue": values[0] if len(values) == 1 else values
                } )
            elif elem.tag == "turnTrackEvent":
                # found a TURN TRACK event
                events.append( {
                    "eventType": "turnTrack",
                    "side": elem.attrib[ "side" ],
                    "turnNo": elem.attrib[ "turnNo" ],
                    "phase": elem.attrib[ "phase" ]
                } )
            elif elem.tag == "customLabelEvent":
                # found a CUSTOM label
                events.append( {
                    "eventType": "customLabel",
                    "caption": elem.text
                } )
            else:
                if logger:
                    logger.warn( "Found an unknown analysis event: %s", elem.tag )

        # extract the scenario details
        elem = logFileElem.find( ".//scenario" )
        if elem is not None:
            scenario[ "scenarioName" ] = elem.text
            if "id" in elem.attrib:
                scenario[ "scenarioId" ] = elem.attrib["id"]

        log_files.append( {
            "filename": logFileElem.attrib[ "filename" ],
            "scenario": scenario,
            "events": events,
        } )

    return {
        "players": { v: k for k,v in players.items() },
        "logFiles": log_files
    }
