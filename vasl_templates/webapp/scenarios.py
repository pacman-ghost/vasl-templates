"""Provide access to the scenarios."""

# NOTE: Disable "DownloadedFile has no 'index' member" warnings.
#pylint: disable=no-member

import os
import json
import urllib.request
import base64
import re
import time
import math
import logging

from flask import request, render_template, jsonify, abort
from PIL import Image, ImageOps

from vasl_templates.webapp import app
from vasl_templates.webapp.downloads import DownloadedFile
from vasl_templates.webapp.vassal import VassalShim
from vasl_templates.webapp.utils import TempFile, \
    get_month_name, make_formatted_day_of_month, friendly_fractions, parse_int, \
    trim_image, get_image_data, remove_alpha_from_image

# ---------------------------------------------------------------------

def _build_asa_scenario_index( df, new_data, logger ):
    """Build the ASL Scenario Archive index."""
    df.index = {
        scenario["scenario_id"]: scenario
        for scenario in new_data["scenarios"]
    }
    if logger:
        logger.debug( "Loaded the ASL Secenario Archive index: #scenarios=%d", len(df.index) )
        logger.debug( "- Generated at: %s", new_data.get( "_generatedAt_", "n/a" ) )

_asa_scenarios = DownloadedFile( "ASA", 1*24,
    "asl-scenario-archive.json",
    "https://vasl-templates.org/services/asl-scenario-archive/scenario-index.json",
    _build_asa_scenario_index,
    extra_args = { "index": None }
)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _build_roar_scenario_index( df, new_data, logger ):
    """Build the ROAR scenario index."""
    df.index, df.title_matching, df.id_matching = {}, {}, {}
    for roar_id,scenario in new_data.items():
        if roar_id.startswith( "_" ):
            continue
        scenario[ "roar_id" ] = roar_id
        df.index[ roar_id ] = scenario
        _update_roar_matching_index( df.title_matching, scenario.get("name"), roar_id )
        _update_roar_matching_index( df.id_matching, scenario.get("scenario_id"), roar_id )
    if logger:
        logger.debug( "Loaded the ROAR scenario index: #scenarios=%d", len(df.index) )
        logger.debug( "- Generated at: %s", new_data.get( "_generatedAt_", "n/a" ) )
        logger.debug( "- Last updated: %s", new_data.get( "_lastUpdated_", "n/a" ) )
        logger.debug( "- # playings:   %s", str( new_data.get( "_nPlayings_", "n/a" ) ) )

def _update_roar_matching_index( index, val, roar_id ):
    """Update the index that will be used for matching ROAR scenarios."""
    if not val:
        return
    key = _make_roar_matching_key( val )
    if key not in index:
        index[ key ] = set()
    index[ key ].add( roar_id )

def _make_roar_matching_key( val ):
    """Generate a key value that will be used to match ROAR scenarios."""
    if not val:
        return val
    return re.sub( "[^a-z0-9]", "", val.lower() )

_roar_scenarios = DownloadedFile( "ROAR", 1*24,
    "roar-scenario-index.json",
    "https://vasl-templates.org/services/roar/scenario-index.json",
    _build_roar_scenario_index,
    extra_args = { "index": None }
)

# ---------------------------------------------------------------------

@app.route( "/scenario-index" )
def get_scenario_index():
    """Return the scenario index."""

    def add_field( entry, key, val ): #pylint: disable=missing-docstring
        if val:
            entry[ key ] = val
    def make_entry( scenario ):
        """Make an entry for the scenario index."""
        entry = { "scenario_id": scenario["scenario_id"] }
        add_field( entry, "scenario_name", _make_scenario_name( scenario ) )
        add_field( entry, "scenario_display_id", scenario.get( "sc_id" ) )
        add_field( entry, "scenario_location", scenario.get( "scen_location" ) )
        add_field( entry, "scenario_date", _parse_date( scenario.get( "scen_date" ) ) )
        add_field( entry, "publication_name", scenario.get( "pub_name" ) )
        add_field( entry, "publication_id", scenario.get( "pub_id" ) )
        add_field( entry, "publication_date", _parse_date( scenario.get( "published_date" ) ) )
        add_field( entry, "publisher_name", scenario.get( "publisher_name" ) )
        add_field( entry, "publisher_id", scenario.get( "publisher_id" ) )
        return entry

    # generate the scenario index
    with _asa_scenarios:
        if _asa_scenarios.index is None:
            return _make_not_available_response(
                "Please wait, the scenario index is still downloading.", _asa_scenarios.error_msg
            )
        return jsonify( [
            make_entry( scenario )
            for scenario in _asa_scenarios.index.values()
        ] )

@app.route( "/roar/scenario-index" )
def get_roar_scenario_index():
    """Return the ROAR scenario index."""
    with _roar_scenarios:
        if _roar_scenarios.index is None:
            return _make_not_available_response(
                "Please wait, the ROAR scenarios are still downloading.", _roar_scenarios.error_msg
            )
        return jsonify( _roar_scenarios.index )

def _make_not_available_response( msg, msg2 ):
    """Generate a "not available" response."""
    resp = { "warning": msg }
    if msg2:
        resp[ "message" ] = msg2
    return jsonify( resp )

# ---------------------------------------------------------------------

@app.route( "/scenario/<scenario_id>" )
def get_scenario( scenario_id ): #pylint: disable=too-many-locals
    """Return a scenario."""

    # get the parameters
    roar_override = request.args.get( "roar" )

    # get the basic scenario information
    scenario, args = _do_get_scenario( scenario_id )
    args[ "scenario_date_iso" ] = _parse_date_iso( scenario.get( "scen_date" ) )
    args[ "defender_name" ] = scenario.get( "defender" )
    args[ "attacker_name" ] = scenario.get( "attacker" )
    args = { k.lower(): v for k,v in args.items() }

    def get_win_score( key ):
        """Get a player's win percentage."""
        nWins = parse_int( playings.get( key+"_wins" ), -1 )
        if nWins < 0:
            return None
        score = 100 * nWins / nGames
        return int( score + 0.5 )

    # get any files available for download
    downloads = {}
    keys = { "vt_setup": "vaslTemplates", "vasl_setup": "vaslTemplateSetups", "screenshot": "templateImages" }
    for key in keys:
        for entry in scenario.get( keys[key], [] ):
            fname = os.path.basename( entry.get( "url", "" ) )
            pos = fname.find( "|" )
            if pos < 0:
                continue
            fkey = fname[:pos]
            if fkey not in downloads:
                downloads[ fkey ] = {
                    "user": entry.get( "user" ),
                    "timestamp": entry.get( "created" ),
                }
            downloads[ fkey ][ key ] = entry.get( "url" )
    downloads = sorted( downloads.values(), key=lambda u: u["timestamp"], reverse=True )
    if downloads:
        args[ "downloads" ] = [
            d for d in downloads
            if "vt_setup" in d or "vasl_setup" in d
        ]

    # get the map previews
    map_images = []
    for fgroup in downloads:
        if "screenshot" in fgroup:
            map_images.append( fgroup )
    for map_image in scenario.get( "mapImages", [] ):
        map_images.append( {
            "screenshot": map_image.get( "url" ),
            "user": map_image.get( "user" ),
            "timestamp": map_image.get( "created" ),
        } )
    if map_images:
        args[ "map_images" ] = map_images

    # get the ASL Scenario Archive playings
    playings = scenario.get( "playings", [ {} ] )[ 0 ]
    nGames = parse_int( playings.get( "totalGames" ), 0 )
    if playings and nGames > 0:
        # NOTE: The player names are display names, only shown in the balance graphs,
        # so it doesn't matter if we know about them or not.
        args[ "balance" ] = [ {
            "name": scenario.get( "defender" ),
            "wins": playings.get( "defender_wins" ),
            "percentage": get_win_score( "defender" )
        }, {
            "name": scenario.get( "attacker" ),
            "wins": playings.get( "attacker_wins" ),
            "percentage": get_win_score( "attacker" )
        } ]

    # try to match the scenario with one in ROAR
    roar_id = None
    if roar_override == "auto-match":
        matches = _match_roar_scenario( scenario )
        if matches:
            roar_id = matches[0][ "roar_id" ]
    else:
        roar_id = roar_override
    if roar_id:
        args[ "roar" ] = _get_roar_info( roar_id )

    return jsonify( args )

def _do_get_scenario( scenario_id ):
    """Return the basic details for the specified scenario."""
    scenario = _get_scenario( scenario_id )
    url_template = app.config[ "ASA_SCENARIO_URL" ]
    scenario_url = url_template.replace( "{ID}", scenario_id )
    return scenario, {
        "SCENARIO_ID": scenario_id,
        "SCENARIO_URL": scenario_url,
        "SCENARIO_NAME": _make_scenario_name( scenario ),
        "SCENARIO_DISPLAY_ID": scenario.get( "sc_id" ),
        "SCENARIO_LOCATION": scenario.get( "scen_location" ),
        "SCENARIO_DATE": _parse_date( scenario.get( "scen_date" ) ),
        "THEATER": scenario.get( "theatre" ),
        "DEFENDER_DESC": scenario.get( "def_desc" ),
        "ATTACKER_DESC": scenario.get( "att_desc" ),
    }

def _match_roar_scenario( scenario ):
    """Try to match the scenario with a ROAR scenario."""

    def get_result_count( scenario ):
        """Get the number of playings for a ROAR scenario."""
        results = scenario.get( "results", [] )
        return sum( r[1] for r in results )

    with _roar_scenarios:
        # try to match by scenario title
        title = scenario.get( "title" )
        if not title:
            return None
        matches = _roar_scenarios.title_matching.get( _make_roar_matching_key( title ) )
        if not matches:
            return []
        elif len( matches ) == 1:
            # there was exactly one match - return it
            roar_id = next( iter( matches ) )
            return [ _roar_scenarios.index[ roar_id ] ]
        else:
            # we found multiple scenarios with the same title, filter by ID
            matches2 = _roar_scenarios.id_matching.get( _make_roar_matching_key( scenario.get("sc_id") ), set() )
            if matches2:
                matches = matches.intersection( matches2 )
            matches = [ _roar_scenarios.index[m] for m in matches ]
            matches.sort( key=get_result_count, reverse=True )
            return matches

def _get_roar_info( roar_id ):
    """Get the information for the specified ROAR scenario."""

    def get_balance( player_no ):
        """Get a player's balance stats."""
        # NOTE: The player names are display names, only shown in the balance graphs,
        # so it doesn't matter if we know about them or not.
        balance = {
            "name": playings[ player_no ][0],
            "wins": playings[ player_no ][1]
        }
        if nGames > 0:
            balance[ "percentage" ] = int( 100 * playings[player_no][1] / nGames + 0.5 )
        return balance

    with _roar_scenarios:

        # find the ROAR scenario
        index = _roar_scenarios.index or {}
        scenario = index.get( roar_id )
        if not scenario:
            abort( 404 )

        # return the scenario details
        results = {
            "scenario_id": roar_id,
            "scenario_display_id": scenario.get( "scenario_id" ),
            "name": scenario.get( "name" ),
            "url": scenario.get( "url" )
        }
        playings = scenario.get( "results" )
        if playings:
            nGames = playings[0][1] + playings[1][1]
            results[ "balance" ] = [ get_balance(0), get_balance(1) ]

        return results

# ---------------------------------------------------------------------

@app.route( "/scenario-card/<scenario_id>" )
def get_scenario_card( scenario_id ): #pylint: disable=too-many-branches
    """Return a scenario card (HTML)."""

    # get the arguments
    brief_mode = request.args.get( "brief" )

    # find the specified scenario
    scenario, args = _do_get_scenario( scenario_id )

    # prepare the template parameters
    args[ "DESIGNER" ] = scenario.get( "author" )
    args[ "PUBLICATION" ] = scenario.get( "pub_name" )
    args[ "PUBLISHER" ] = scenario.get( "publisher_name" )
    args[ "PUBLICATION_DATE" ] = _parse_date( scenario.get( "published_date" ) )
    args[ "PREV_PUBLICATION" ] = scenario.get( "prior_publication" )
    args[ "REVISED_PUBLICATION" ] = scenario.get( "revision" )
    args[ "OVERVIEW" ] = scenario.get( "overview" )
    if brief_mode:
        args[ "OVERVIEW_BRIEF" ] = _make_brief_overview( scenario.get( "overview" ) )
    args[ "DEFENDER_NAME" ] = scenario.get( "defender" )
    args[ "ATTACKER_NAME" ] = scenario.get( "attacker" )
    args[ "BOARDS" ] = ", ".join( str(m) for m in scenario.get("maps",[]) )
    overlays = ", ".join( str(o) for o in scenario.get("overlays",[]) )
    if overlays.upper() == "NONE":
        overlays = None
    if overlays:
        args[ "OVERLAYS" ] = overlays
    args[ "EXTRA_RULES" ] = scenario.get( "misc" )
    args[ "ERRATA" ] = scenario.get( "errata" )

    # prepare the template parameters
    if scenario.get( "pub_id" ):
        url_template = app.config[ "ASA_PUBLICATION_URL" ]
        args[ "PUBLICATION_URL" ] = url_template.replace( "{ID}", scenario["pub_id"] )
    if scenario.get( "publisher_id" ):
        url_template = app.config[ "ASA_PUBLISHER_URL" ]
        args[ "PUBLISHER_URL" ] = url_template.replace( "{ID}", scenario["publisher_id"] )
    playing_time = scenario.get( "time_to_play", "0" )
    if not str( playing_time ).startswith( "0" ):
        args[ "PLAYING_TIME" ] = friendly_fractions( playing_time, "hour", "hours" )

    # prepare the turn count
    min_turns = scenario.get( "min_turns", "0" )
    max_turns = scenario.get( "max_turns", "0" )
    if min_turns != "0":
        if min_turns == max_turns or max_turns == "0":
            args[ "TURN_COUNT" ] = friendly_fractions( min_turns, "turn", "turns" )
        elif max_turns != "0":
            args[ "TURN_COUNT" ] = "{}-{} turns".format( friendly_fractions(min_turns), friendly_fractions(max_turns) )

    # prepare any info icons
    icons = {}
    if scenario.get( "oba" ) in ("D","B"):
        icons[ "DEFENDER_OBA" ] = True
    if scenario.get( "oba" ) in ("A","B"):
        icons[ "ATTACKER_OBA" ] = True
    if scenario.get( "night" ) == "1":
        icons[ "IS_NIGHT" ] = True
    if scenario.get( "aslsk" ) == "1":
        icons[ "IS_ASLSK" ] = True
    if scenario.get( "deluxe" ) == "1":
        icons[ "IS_DELUXE" ] = True
    if icons:
        args[ "ICONS" ] = icons

    # prepare the lat/long co-ordinates
    is_valid_coord = lambda val: val and val != "-99.99"
    if is_valid_coord( scenario.get("gps_lat") ) and is_valid_coord( scenario.get("gps_long") ):
        url_template = app.config.get( "MAP_URL", "https://maps.google.com/maps?q={LAT},{LONG}&z=4&output=embed" )
        args["MAP_URL"] = url_template.replace( "{LAT}", scenario["gps_lat"] ).replace( "{LONG}", scenario["gps_long"] )

    # process the template and return the generated HTML
    return render_template( "scenario-card.html", **args )

def _make_brief_overview( content ):
    """Truncate the scenario overview."""
    if not content:
        return None
    threshold = parse_int( app.config.get( "BRIEF_CONTENT_THRESHOLD" ), 200 )
    if threshold <= 0 or len(content) < threshold:
        return None
    regex = re.compile( "[.?!]+" )
    mo = regex.search( content, threshold )
    if not mo:
        return content[:threshold] + "..."
    val = content[ : mo.start() + len(mo.group()) ]
    if val == content:
        return None
    return val

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _get_scenario( scenario_id ):
    """Get the specified scenario."""
    with _asa_scenarios:
        index = _asa_scenarios.index or {}
        scenario = index.get( scenario_id )
        if not scenario:
            abort( 404 )
        return scenario

def _make_scenario_name( scenario ):
    """Get the scenario's name."""
    return scenario.get( "title" ) or "Untitled scenario (#{})".format( scenario["scenario_id"] )

# ---------------------------------------------------------------------

@app.route( "/prepare-asa-upload", methods=["POST"] )
def prepare_asa_upload(): #pylint: disable=too-many-locals
    """Prepare files for upload to the ASL Scenario Archive."""

    # parse the request
    vsav_data = request.json[ "vsav_data" ]
    vsav_filename = request.json[ "filename" ]

    # initialize
    start_time = time.time()
    logger = logging.getLogger( "prepare_asa_upload" )

    try:

        # get the VSAV data (we do this inside the try block so that the user gets shown
        # a proper error dialog if there's a problem decoding the base64 data)
        vsav_data = base64.b64decode( vsav_data )
        logger.info( "Preparing VSAV (#bytes=%d): %s", len(vsav_data), vsav_filename )

        with TempFile() as input_file:

            # save the VSAV data in a temp file
            input_file.write( vsav_data )
            input_file.close( delete=False )
            fname = app.config.get( "PREPARE_ASA_UPLOAD_INPUT" ) # nb: for diagnosing problems
            if fname:
                logger.debug( "Saving a copy of the VSAV data: %s", fname )
                with open( fname, "wb" ) as fp:
                    fp.write( vsav_data )

            # prepare the files to be uploaded
            with TempFile() as stripped_vsav_file, TempFile() as screenshot_file:

                # run the VASSAL shim to prepare the VSAV file
                stripped_vsav_file.close( delete=False )
                screenshot_file.close( delete=False )
                vassal_shim = VassalShim()
                vassal_shim.prepare_asa_upload(
                    input_file.name, stripped_vsav_file.name, screenshot_file.name
                )

                # read the stripped VSAV data
                with open( stripped_vsav_file.name, "rb" ) as fp:
                    stripped_vsav = fp.read()
                stripped_vsav_file.save_copy(
                    app.config.get( "PREPARE_ASA_UPLOAD_STRIPPED_VSAV" ),
                    logger, "stripped VSAV"
                )

                # read the screenshot image
                if os.path.getsize( screenshot_file.name ) == 0:
                    # NOTE: The VASSAL shim sometimes crashes while trying to generate a screenshot :-(
                    screenshot_data = None
                else:
                    # NOTE: These screenshots are used as map preview images on the ASL Scenario Archive
                    # web site (and by us, as well), so we want to optimize them for size.
                    # NOTE: I tried changing the PNG from 24-bit RGB to using a palette:
                    #   img.convert( "P", palette=Image.ADAPTIVE/WEB )
                    # but since PNG is a lossless format, the benefits are minimal. Also, weird things happen
                    # if we do this before shrinking the image, which makes calculating the ratio tricky.
                    # clean up the original screenshot
                    img = trim_image( screenshot_file.name )
                    img = remove_alpha_from_image( img )
                    # get the image data
                    def save_image( img ): #pylint: disable=missing-docstring
                        quality = parse_int( app.config.get( "ASA_SCREENSHOT_QUALITY" ), 50 )
                        return get_image_data( img, format="JPEG", quality=quality, optimize=True, subsampling=0 )
                    screenshot_data = save_image( img )
                    # resize it to (roughly) the maximum allowed size
                    max_size = parse_int( app.config.get( "ASA_MAX_SCREENSHOT_SIZE" ), 200 ) * 1024
                    if len(screenshot_data) > max_size:
                        ratio = math.sqrt( float(max_size) / len(screenshot_data) )
                        img = img.resize( ( int(img.width * ratio), int(img.height * ratio) ), Image.ANTIALIAS )
                    # add a border
                    border_size = parse_int( app.config.get( "ASA_SCREENSHOT_BORDER_SIZE" ), 5 )
                    img = ImageOps.expand( img, border_size, (255,255,255,255) )
                    # get the final image data
                    screenshot_data = save_image( img )

                # save a copy of the screenshot image
                fname = app.config.get( "PREPARE_ASA_UPLOAD_SCREENSHOT" )
                if fname:
                    if screenshot_data:
                        logger.debug( "Saving a copy of the generated screenshot: %s", fname )
                        with open( fname, "wb" ) as fp:
                            fp.write( screenshot_data )
                    else:
                        if os.path.isfile( fname ):
                            os.unlink( fname )

    except Exception as ex: #pylint: disable=broad-except

        return VassalShim.translate_vassal_shim_exception( ex, logger )

    # return the results
    logger.info( "Prepared the VSAV file OK: elapsed=%.3fs", time.time()-start_time )
    results = {
        "filename": vsav_filename,
        "stripped_vsav": base64.b64encode( stripped_vsav ).decode( "utf-8" ),
    }
    if screenshot_data:
        results[ "screenshot" ] = base64.b64encode( screenshot_data ).decode( "utf-8" )
    return jsonify( results )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

@app.route( "/on-successful-asa-upload/<scenario_id>" )
def on_successful_asa_upload( scenario_id ):
    """Update the local scenario index after a successful upload."""

    if app.config.get( "DISABLE_LOCAL_ASA_INDEX_UPDATES" ):
        return jsonify( { "status": "ok" } )

    # download the specified scenario
    url = app.config["ASA_GET_SCENARIO_URL"].replace( "{ID}", scenario_id )
    try:
        fp = urllib.request.urlopen( url )
        new_scenario = json.loads( fp.read().decode( "utf-8" ) )
    except Exception as ex: #pylint: disable=broad-except
        msg = str( getattr(ex,"reason",None) or ex )
        return jsonify( { "status": "error", "message": msg } )

    # update the local index
    if os.path.isfile( _asa_scenarios.cache_fname ):
        # NOTE: Since the downloaded index file contains a *list* of scenarios, we append the new scenario info
        # to the end of that list, and then the next time the program starts and reads the list into a dict,
        # the most-recent version is the one that will ultimately be used. This lets us identify these temporary changes
        # that have been made to the cached index file (which will be overwritten when we download a fresh copy).
        # This is not particularly efficient, but it won't happen too often.
        with open( _asa_scenarios.cache_fname, "r" ) as fp:
            data = json.load( fp )
        data["scenarios"].append( new_scenario )
        with open( _asa_scenarios.cache_fname, "w" ) as fp:
            json.dump( data, fp )

    # update the in-memory scenario index
    with _asa_scenarios:
        _asa_scenarios.index[ scenario_id ] = new_scenario

    return jsonify( { "status": "ok" } )

# ---------------------------------------------------------------------

_last_asa_upload = None

@app.route( "/test-asa-upload/<int:scenario_id>", methods=["POST"] )
def test_asa_upload( scenario_id ):
    """A test endpoint that can be used to simulate ASL Scenario Archive uploads."""

    def save_file( key, asa_upload, convert=None ):
        """Save a file that has been uploaded to us."""
        f = request.files.get( key )
        if not f:
            print( "- {}: not present.".format( key ) )
            return
        data = f.read()
        asa_upload[ key ] = convert(data) if convert else data
        print( "- {}: {} ({}) ; #bytes={}".format( key, f.filename, f.content_type, len(data) ) )
        fname = app.config.get( "SAVE_ASA_UPLOAD_" + key.upper() )
        if fname:
            with open( fname, "wb" ) as fp:
                fp.write( data )
            print( "  - Saved to:", fname )

    def make_response( fname ):
        """Generate a response."""
        dname = os.path.join( os.path.dirname(__file__), "tests/fixtures/asa-responses/" )
        fname = os.path.join( dname, "{}.json".format( fname ) )
        resp = json.load( open( fname, "r" ) )
        return jsonify( resp )

    # simulate a slow response
    delay = parse_int( app.config.get( "ASA_UPLOAD_DELAY" ), 0 )
    if delay > 0:
        time.sleep( delay )

    # parse the request
    user_name = request.args.get( "user" )
    if not user_name:
        return make_response( "missing-user-name" )
    api_token = request.args.get( "token" )
    if not api_token:
        return make_response( "missing-token" )
    if api_token == "incorrect-token":
        return make_response( "incorrect-token" )

    # process the request
    print( "ASA upload: id={} ; user=\"{}\" ; token=\"{}\"".format( scenario_id, user_name,api_token ) )
    asa_upload = {}
    save_file( "vasl_setup", asa_upload )
    save_file( "vt_setup", asa_upload, lambda v: json.loads(v) ) #pylint: disable=unnecessary-lambda
    save_file( "screenshot", asa_upload )
    if asa_upload:
        asa_upload.update( { "user": user_name, "token": api_token } )
        global _last_asa_upload
        _last_asa_upload = asa_upload

    return make_response( "ok" )

# ---------------------------------------------------------------------

@app.route( "/scenario/nat-report" )
def scenario_nat_report():
    """Generate the scenario nationalities report (for testing porpoises)."""
    return render_template( "scenario-nat-report.html" )

# ---------------------------------------------------------------------

def _parse_date( val ):
    """Parse a date string."""
    parts = _split_date_parts( val )
    if not parts:
        return None
    return "{} {}, {}".format(
        make_formatted_day_of_month( parts[0] ),
        get_month_name( parts[1] ),
        parts[2]
    )

def _parse_date_iso( val ):
    """Parse a date string."""
    parts = _split_date_parts( val )
    if not parts:
        return None
    return "{:04}-{:02}-{:02}".format( parts[2], parts[1], parts[0] )

def _split_date_parts( val ):
    """Split a date into its component parts."""
    if val is None:
        return None
    mo = re.search( r"^(\d{4})-(\d{2})-(\d{2})", val )
    if not mo:
        return None
    if mo.group(1) == "1901":
        return None # nb: 1901-01-01 seems to be used as a "invalid date" marker
    parts = [ int(mo.group(3)), int(mo.group(2)), int(mo.group(1)) ]
    if parts == [ 0, 0, 0, ]:
        return None # nb: 0000-00-00 also seems to be used as an "invalid date" marker
    return parts
