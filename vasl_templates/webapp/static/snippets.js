// NOTE: These fields aren't mandatory in the sense that snippet generation will fail
// if they're not set, but they're really, really, really expected to be there.
var _MANDATORY_PARAMS = {
    scenario: { "SCENARIO_NAME": "scenario name", "SCENARIO_DATE": "scenario date" },
} ;

// NOTE: Blood & Jungle has a lot of multi-applicable notes that simply refer to other
// multi-applicable notes e.g. "Fr C" = "French Multi-Applicable Note C".
// NOTE: These are also used for Lend-Lease vehicles.
var MA_NOTE_REDIRECTS = {
    "Br": "british",
    "Ch": "chinese",
    "Fr": "french",
    "Ge": "german",
    "Jp": "japanese",
    "Ru": "russian",
    "US": "american",
    "LC": "landing-craft",
    "AllM": "allied-minor",
    "AxM": "axis-minor",
} ;

// NOTE: There are BFP references like "Jp 5" and "AllM 34", but we ignore these since they are
// referring to a vehicle/ordnance *note*, not a multi-applicable note.
MA_NOTE_REDIRECT_REGEX = new RegExp(
    "^((Br|Ch|Fr|Ge|Jp|Ru|US|AllM|AxM) [A-Z]{1,2})(\\u2020(<sup>\\d</sup>)?|<sup>T</sup>)?$"
) ;
NO_WARNING_FOR_MA_NOTE_KEYS_REGEX = new RegExp(
    "^(Jp 5|AllM 34)"
) ;

var gDefaultScenario = null ;
var gLastSavedScenario = null ;
var gLastSavedScenarioFilename = null ;
var gScenarioCreatedTime = null ;

// --------------------------------------------------------------------

function generate_snippet( $btn, as_image, extra_params )
{
    // generate the snippet
    var template_id = $btn.data( "id" ) ;
    var params = unload_snippet_params( true, template_id ) ;
    var snippet = make_snippet( $btn, params, extra_params, true ) ;

    // check if the user is requesting the snippet as an image
    if ( as_image ) {
        // yup - send the snippet to the backend to generate the image
        // NOTE: Generating the first snippet image is slow (because the backend has to spin up a webdriver),
        // but subsequent snippet images are very fast, so we wait for a short while, and if a response
        // hasn't been received, then we show a "please wait" dialog.
        var $pleaseWait = null ;
        var timeout_id = setTimeout( function() {
            $pleaseWait = showPleaseWaitDialog( "Generating the snippet image..." ) ;
        }, 1*1000 ) ;
        $.ajax( {
            url: gMakeSnippetImageUrl,
            type: "POST",
            data: snippet.content,
            contentType: "text/html",
        } ).done( function( resp ) {
            clearTimeout( timeout_id ) ;
            if ( $pleaseWait )
                $pleaseWait.dialog( "close" ) ;
            if ( resp.substr( 0, 6 ) === "ERROR:" ) {
                showErrorMsg( resp.substr(7) ) ;
                return ;
            }
            if ( getUrlParam( "snippet_image_persistence" ) ) {
                // FOR TESTING PORPOISES! We can't control a file download from Selenium (since
                // the browser will use native controls), so we store the result in a <textarea>
                // and the test suite will collect it from there).
                var fname = _make_snippet_image_filename( snippet ) ;
                $("#_snippet-image-persistence_").val( fname + "|" + resp ) ;
                return ;
            }
            if ( gWebChannelHandler ) {
                // if we are running inside the PyQt wrapper, let it copy the image to the clipbaord
                gWebChannelHandler.on_snippet_image( resp, function() {
                    showInfoMsg( "The snippet image was copied to the clipboard." ) ;
                } ) ;
            } else {
                // otherwise let the user download the generated image
                download( atob(resp), _make_snippet_image_filename(snippet), "image/png" ) ;
            }
        } ).fail( function( xhr, status, errorMsg ) {
            clearTimeout( timeout_id ) ;
            if ( $pleaseWait )
                $pleaseWait.dialog( "close" ) ;
            showErrorMsg( "Can't get the snippet image:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        } ) ;
        return ;
    }

    // copy the snippet to the clipboard
    try {
        copyToClipboard( snippet.content ) ;
    }
    catch( ex ) {
        showErrorMsg( "Can't copy to the clipboard:<div class'pre'>" + escapeHTML(ex) + "</div>" ) ;
        return ;
    }
    // NOTE: This notification will be shown even if there was an error generating the snippet,
    // but the error message was copied to the clipboard, so it's still techincally correct... :-/
    // We disabled the ability to generate a snippet if a template file is not present, so it should
    // only be an issue if there was a problem processing the template.
    showInfoMsg( "The HTML snippet has been copied to the clipboard." ) ;
}

function make_snippet( $btn, params, extra_params, show_date_warnings )
{
    // initialize
    var template_id = $btn.data( "id" ) ;
    var snippet_save_name = null ;

    // add server constants
    if ( ! getUrlParam( "no_app_config_snippet_params" ) ) {
        params.APP_NAME = gAppConfig.APP_NAME ;
        params.APP_VERSION = gAppConfig.APP_VERSION ;
        params.VASSAL_VERSION = gAppConfig.VASSAL_VERSION ;
        params.VASL_VERSION = gAppConfig.VASL_VERSION ;
    }

    // add simple parameters
    params.TIMESTAMP = (new Date()).toISOString() ;
    params.IMAGES_BASE_URL = gUserSettings["scenario-images-source"] == SCENARIO_IMAGES_SOURCE_INTERNET ?
        gAppConfig.ONLINE_IMAGES_URL_BASE :
        make_app_url( gImagesBaseUrl, true ) ;
    if ( gUserSettings["snippet-font-family"] ) {
        // NOTE: Layout of snippets ends up being slightly different on Windows and Linux, presumably because
        // VASSAL is using different fonts. Unfortunately, explicitly specifying which font to use doesn't
        // fix this, even web-safe ones :-(
        params.SNIPPET_FONT_FAMILY = gUserSettings["snippet-font-family"] ;
    }
    if ( gUserSettings["snippet-font-size"] )
        params.SNIPPET_FONT_SIZE = gUserSettings["snippet-font-size"] ;
    if ( gUserSettings["custom-list-bullets"] )
        params.CUSTOM_LIST_BULLETS = true ;
    // some versions of Java require <img> tags to have the width and height specified!?!
    params.PLAYER_FLAG_SIZE = "width='11' height='11'" ;
    // FUDGE! A lot of labels use a larger font for their heading (e.g. V/O notes, PF, ATMM, etc.) and so
    // we would like to show a larger flag to match, or at least vertically center the flag. This would be
    // trivial to do with CSS, but VASSAL's HTML engine can't handle it, so we have to manually force
    // the flag to render at a larger size >:-/
    params.PLAYER_FLAG_SIZE_LARGE = "width='13' height='13'" ;

    // set player-specific parameters
    var player_no ;
    if ( template_id.substring( 0, 9 ) === "nat_caps_" )
        player_no = template_id.substring( 9 ) ;
    else
        player_no = get_player_no_for_element( $btn ) ;
    var player_nat = get_player_nat( player_no ) ;
    if ( player_no ) {
        params.PLAYER_NAT = player_nat ;
        params.PLAYER_NAME = get_nationality_display_name( params["PLAYER_"+player_no] ) ;
        var colors = get_player_colors( player_no ) ;
        params.OB_COLOR = colors[0] ;
        params.OB_COLOR_2 = colors[2] ;
        if ( gUserSettings["include-flags-in-snippets"] && gHasPlayerFlag[player_nat] )
            params.PLAYER_FLAG = make_player_flag_url( player_nat, true ) ;
    }

    // set the snippet ID
    var data ;
    if ( ["ob_setup","ob_note","ob_vehicle_note","ob_ordnance_note"].indexOf( template_id ) !== -1 ) {
        data = $btn.parent().parent().data( "sortable2-data" ) ;
        params.SNIPPET_ID = template_id + "_" + player_no + "." + data.id ;
    } else if ( template_id === "scenario_note" ) {
        data = $btn.parent().parent().data( "sortable2-data" ) ;
        params.SNIPPET_ID = template_id + "." + data.id ;
    } else
        params.SNIPPET_ID = template_id ;
    if ( player_nat )
        params.SNIPPET_ID = player_nat + "/" + params.SNIPPET_ID ;

    // set the vehicle/ordnance labels
    if ( template_id.indexOf( "_vehicle_" ) !== -1 || template_id.indexOf( "_vehicles_" ) !== -1 ) {
        params.VO_TYPE = "Vehicle" ;
        params.VO_TYPES = "Vehicles" ;
    } else if ( template_id.indexOf( "_ordnance_" ) !== -1 ) {
        params.VO_TYPE = "Ordnance" ;
        params.VO_TYPES = "Ordnance" ;
    }
    if ( params.PLAYER_NAME && params.VO_TYPE ) {
        // NOTE: How long the vehicle/ordnance name can be before we force it to be full-width
        // depends on how wide the snippet is, which depends on the nationality + vehicle/ordnance type.
        var max_cap_width = 5 ; // FIXME! We should really calculate this :-/
        params.MAX_VO_NAME_LEN = ( params.PLAYER_NAME.length + 1 + params.VO_TYPE.length ) - max_cap_width ;
    }

    // set player-specific parameters
    if ( template_id === "ob_vehicles_1" ) {
        template_id = "ob_vehicles" ;
        params.OB_VO = params.OB_VEHICLES_1 ;
        params.OB_VO_WIDTH = params.OB_VEHICLES_WIDTH_1 ;
        snippet_save_name = params.PLAYER_1 + " vehicles" ;
    } else if ( template_id === "ob_vehicles_2" ) {
        template_id = "ob_vehicles" ;
        params.OB_VO = params.OB_VEHICLES_2 ;
        params.OB_VO_WIDTH = params.OB_VEHICLES_WIDTH_2 ;
        snippet_save_name = params.PLAYER_2 + " vehicles" ;
    }
    if ( template_id === "ob_ordnance_1" ) {
        template_id = "ob_ordnance" ;
        params.OB_VO = params.OB_ORDNANCE_1 ;
        params.OB_VO_WIDTH = params.OB_ORDNANCE_WIDTH_1 ;
        snippet_save_name = params.PLAYER_1 + " ordnance" ;
    } else if ( template_id === "ob_ordnance_2" ) {
        template_id = "ob_ordnance" ;
        params.OB_VO = params.OB_ORDNANCE_2 ;
        params.OB_VO_WIDTH = params.OB_ORDNANCE_WIDTH_2 ;
        snippet_save_name = params.PLAYER_2 + " ordnance" ;
    }
    if ( template_id === "nat_caps_1" || template_id === "nat_caps_2" )
        template_id = "nat_caps" ;

    // adjust comments
    adjust_vo_comments( params ) ;

    // set vehicle/ordnance note parameters
    function set_vo_note( vo_type ) {
        var data = $btn.parent().parent().data( "sortable2-data" ) ;
        params.VO_NAME = data.vo_entry.name ;
        if ( data.vo_note.substr( 0, 7 ) === "http://" ) {
            // the vehicle/ordnance note is an image - just include it directly
            params.VO_NOTE_HTML = '<img src="' + data.vo_note + '">' ;
            // FUDGE! People are asking to be able to load Chapter H images from an online server.
            // The code that figures out how to generate Chapter H content is horrendously complicated :-/,
            // and letting the user point to the source content via a base URL or file system directory
            // would make it even worse :-/
            // We could add a debug setting that specifies a base URL, and use it when we generate the image URL
            // at the end of get_vo_note(), but that means that the location of the Chapter H content would be
            // configurable in the UI, but ignored :-/
            // Parsing the generated image URL like this, and then getting the user to change their template
            // to use this new parameter, is a bit hacky, but (1) it's more likely to get the path right,
            // (2) is less likely to break existing functionality,  and (3) we don't really want to be encouraging
            // people to put their Chapter H content up online, anyway :-/
            var match = data.vo_note.match( /^https?:\/\/.*?\/(.*?)\/(.*?)\/note\/(.*)/ ) ;
            if ( match ) {
                params.VO_NOTE_IMAGE_URL_PATH = match[2] === "landing-craft" ?
                    match[2] + "/" + match[3] :
                    match[2] + "/" + match[1] + "/" + match[3] ;
            }
        } else {
            // the vehicle/ordnance is HTML - check if we should show it as HTML or as an image
            if ( gUserSettings["vo-notes-as-images"] ) {
                // show the vehicle/ordnance note as an image
                params.VO_NOTE_HTML = '<img src="' + data.vo_note_image_url + '">' ;
            } else {
                // insert the raw HTML into the snippet
                params.VO_NOTE_HTML = data.vo_note ;
            }
        }
        snippet_save_name = data.vo_entry.name ;
    }
    if ( template_id === "ob_vehicle_note" )
        set_vo_note( "vehicles" ) ;
    else if ( template_id === "ob_ordnance_note" )
        set_vo_note( "ordnance" ) ;

    // generate snippets for multi-applicable vehicle/ordnance notes
    var pos, i ;
    function add_ma_notes( ma_notes, keys, param_name, nat, vo_type ) {
        if ( ! keys )
            return ;
        params[ param_name ] = [] ;
        for ( i=0 ; i < keys.length ; ++i ) {
            var ma_note = get_ma_note( nat, vo_type, keys[i] ) ;
            var key = keys[i] ;
            var extn_marker = "" ;
            if ( nat === "italian" && vo_type === "ordnance" && keys[i] === "R" )
                key = "<s>R</s>" ;
            else {
                pos = key.indexOf( ":" ) ;
                if ( pos !== -1 ) {
                    extn_marker = "&#x2756; " ;
                    key = key.substring( pos+1 ) ;
                }
            }
            if ( !ma_note && gUserSettings["hide-unavailable-ma-notes"] )
                continue ;
            // NOTE: We don't exclude disabled multi-applicable notes, since it can be confusing for
            // the user (e.g. a vehicle references note X, but note X is not there), so instead,
            // we allow them to be styled to have less visual impact.
            var ma_note_enabled = ma_note && ma_note.indexOf( "<!-- disabled -->" ) === -1 ;
            params[ param_name ].push( [ ma_note_enabled,
                extn_marker +
                "<span class='key'>" + key + ":" + "</span> " +
                (ma_note || "Unavailable.")
            ] ) ;
        }
    }
    function get_ma_notes( vo_type, player_no, param_name ) {
        var nat = params[ "PLAYER_" + player_no ] ;
        var vo_entries = params[ "OB_" + vo_type.toUpperCase() + "_" + player_no ] ;
        var result = get_ma_notes_keys( nat, vo_entries, vo_type, null ) ;
        if ( ! result )
            return ;
        // NOTE: If the V/O entries contain landing craft, we get:
        //   [ m/a note keys, m/a note keys for the extras, nat ID for the extras, display caption for the extras, unrecognized keys ]
        // where "extras" = landing craft. Otherwise, we get:
        //   [ m/a note keys, null, null, null, unrecognized keys ]
        add_ma_notes( get_ma_notes_for_nat(nat,vo_type), result[0], param_name, nat, vo_type ) ;
        if ( result[1] ) {
            // there are extras, show their multi-applicable notes separately
            add_ma_notes( get_ma_notes_for_nat(result[2],vo_type), result[1], param_name.replace("_MA_NOTES_","_EXTRA_MA_NOTES_"), result[2], vo_type ) ;
            if ( result[0] ) {
                var param_name2 = "OB_" + vo_type.toUpperCase() + "_EXTRA_MA_NOTES_CAPTION_" + player_no ;
                params[param_name2] = result[3] ;
            }
        }
    }
    get_ma_notes( "vehicles", 1, "OB_VEHICLES_MA_NOTES_1" ) ;
    get_ma_notes( "ordnance", 1, "OB_ORDNANCE_MA_NOTES_1" ) ;
    get_ma_notes( "vehicles", 2, "OB_VEHICLES_MA_NOTES_2" ) ;
    get_ma_notes( "ordnance", 2, "OB_ORDNANCE_MA_NOTES_2" ) ;
    function set_ma_notes_params( vo_type, player_no ) {
        template_id = "ob_" + vo_type + "_ma_notes" ;
        var vo_type_uc = vo_type.toUpperCase() ;
        var postfixes = [ "MA_NOTES", "MA_NOTES_WIDTH", "EXTRA_MA_NOTES", "EXTRA_MA_NOTES_CAPTION" ] ;
        for ( i=0 ; i < postfixes.length ; ++i ) {
            params[ "OB_" + postfixes[i] ] = params[ "OB_" + vo_type_uc + "_" + postfixes[i] + "_" + player_no ] ;
        }
        snippet_save_name = params["PLAYER_"+player_no] + (vo_type === "vehicles" ? " vehicle notes" : " ordnance notes") ;
    }
    if ( template_id === "ob_vehicles_ma_notes_1" )
        set_ma_notes_params( "vehicles", 1 ) ;
    else if ( template_id === "ob_ordnance_ma_notes_1" )
        set_ma_notes_params( "ordnance", 1 ) ;
    else if ( template_id === "ob_vehicles_ma_notes_2" )
        set_ma_notes_params( "vehicles", 2 ) ;
    else if ( template_id === "ob_ordnance_ma_notes_2" )
        set_ma_notes_params( "ordnance", 2 ) ;

    // include the player display names and flags
    params.PLAYER_1_NAME = get_nationality_display_name( params.PLAYER_1 ) ;
    params.PLAYER_2_NAME = get_nationality_display_name( params.PLAYER_2 ) ;
    if ( gUserSettings["include-flags-in-snippets"] ) {
        if ( gHasPlayerFlag[ get_player_nat( 1 ) ] )
            params.PLAYER_FLAG_1 = make_player_flag_url( get_player_nat(1), true ) ;
        if ( gHasPlayerFlag[ get_player_nat( 2 ) ] )
            params.PLAYER_FLAG_2 = make_player_flag_url( get_player_nat(2), true ) ;
    }

    // pass through all the player colors and names
    params.PLAYER_NAMES = {} ;
    params.PLAYER_COLORS = {} ;
    params.PLAYER_FLAGS = {} ;
    $.each( gTemplatePack.nationalities, function( nat ) {
        params.PLAYER_NAMES[nat] = gTemplatePack.nationalities[nat].display_name ;
        params.PLAYER_COLORS[nat] = gTemplatePack.nationalities[nat].ob_colors ;
        if ( gUserSettings["include-flags-in-snippets"] )
            params.PLAYER_FLAGS[nat] = make_player_flag_url( nat, true ) ;
    } ) ;

    // generate PF parameters
    if ( params.SCENARIO_YEAR < 1944 || (params.SCENARIO_YEAR === 1944 && params.SCENARIO_MONTH < 6) )
        params.PF_RANGE = 1 ;
    else if ( params.SCENARIO_YEAR === 1944 )
        params.PF_RANGE = 2 ;
    else
        params.PF_RANGE = 3 ;
    if ( params.SCENARIO_YEAR >= 1945 )
        params.PF_CHECK_DR = 4 ;
    else
        params.PF_CHECK_DR = 3 ;

    // generate BAZ parameters
    if ( params.SCENARIO_YEAR >= 1945 ) {
        params.BAZ_TYPE = 45 ;
        params.BAZ_BREAKDOWN = 11 ;
        params.BAZ_TK = 16 ;
        params.BAZ_WP = 6 ;
        params.BAZ_RANGE = 5 ;
    } else if ( params.SCENARIO_YEAR >= 1944 ) {
        params.BAZ_TYPE = 44 ;
        params.BAZ_BREAKDOWN = 11 ;
        params.BAZ_TK = 16 ;
        params.BAZ_RANGE = 4 ;
    } else if ( params.SCENARIO_YEAR === 1943 || (params.SCENARIO_YEAR === 1942 && params.SCENARIO_MONTH >= 11) ) {
        params.BAZ_TYPE = 43 ;
        params.BAZ_BREAKDOWN = 10 ;
        params.BAZ_TK = 13 ;
        params.BAZ_RANGE = 4 ;
    }

    // set the national capabilities parameters
    set_nat_caps_params( player_nat, params ) ;

    // check for mandatory parameters
    if ( template_id in _MANDATORY_PARAMS ) {
        var missing_params = [] ;
        for ( var param_id in _MANDATORY_PARAMS[template_id] ) {
            if ( ! (param_id in params && params[param_id].length > 0) )
                missing_params.push( _MANDATORY_PARAMS[template_id][param_id] ) ;
        }
        if ( missing_params.length > 0 )
            showWarningMsg( makeBulletListMsg( "Missing parameters:", missing_params, li_class="pre" ) ) ;
    }

    // check for date-specific parameters
    if ( show_date_warnings ) {
        if ( template_id === "pf" && ! is_pf_available() )
            showWarningMsg( "PF are only available after September 1943." ) ;
        if ( template_id === "pf-finnish" && ! is_pf_finnish_available() )
            showWarningMsg( "PF are only available from July 1944." ) ;
        if ( template_id === "pf-hungarian" && ! is_pf_hungarian_available() )
            showWarningMsg( "PF are only available from June 1944." ) ;
        if ( template_id === "pf-romanian" && ! is_pf_romanian_available() )
            showWarningMsg( "PF are only available from March 1944." ) ;
        if ( template_id === "psk" && ! is_psk_available() )
            showWarningMsg( "PSK are only available after September 1943." ) ;
        if ( template_id === "baz" && ! is_baz_available() )
            showWarningMsg( "BAZ are only available from November 1942." ) ;
        if ( template_id === "atmm" && ! is_atmm_available() )
            showWarningMsg( "ATMM are only available from 1944." ) ;
        if ( template_id === "atmm-romanian" && ! is_atmm_romanian_available() )
            showWarningMsg( "ATMM are only available from July 1943." ) ;
        if ( template_id == "thh" && ! params.SCENARIO_YEAR )
            showWarningMsg( "Can't determine the THH ATMM check dr without the scenario year." ) ;
    }

    // add in any extra parameters
    if ( extra_params )
        $.extend( true, params, extra_params ) ;

    // allow EXC blocks to be styled
    params.VICTORY_CONDITIONS = wrapExcWithSpan( params.VICTORY_CONDITIONS ) ;
    params.SCENARIO_NOTE = wrapExcWithSpan( params.SCENARIO_NOTE ) ;
    if ( params.SSR ) {
        for ( i=0 ; i < params.SSR.length ; ++i )
            params.SSR[i] = wrapExcWithSpan( params.SSR[i] ) ;
    }
    params.OB_NOTE = wrapExcWithSpan( params.OB_NOTE ) ;
    params.VO_NOTE_HTML = wrapExcWithSpan( params.VO_NOTE_HTML ) ;
    [ "VEHICLES", "ORDNANCE" ].forEach( function( voType ) {
        for ( var playerId=1 ; playerId <= 2 ; ++playerId ) {
            var notes = params[ "OB_" + voType + "_MA_NOTES_" + playerId ] ;
            if ( ! notes )
                continue ;
            for ( var i=0 ; i < notes.length ; ++i )
                notes[i][1] = wrapExcWithSpan( notes[i][1] ) ;
        }
    } ) ;

    // check that the players have different nationalities
    if ( params.PLAYER_1 === params.PLAYER_2 )
        showWarningMsg( "Both players have the same nationality!" ) ;

    // get the template to generate the snippet from
    var templ = get_template( template_id, true ) ;
    if ( templ === null )
        return { content: "[error: can't find template]" } ;
    for ( var key in gTemplatePack.css )
        templ = strReplaceAll( templ, "{{CSS:"+key+"}}", gTemplatePack.css[key] ) ;
    for ( key in gTemplatePack.includes )
        templ = strReplaceAll( templ, "{{INCLUDE:"+key+"}}", gTemplatePack.includes[key].trim() ) ;
    var func ;
    try {
        func = jinja.compile( templ ).render ;
    }
    catch( ex ) {
        showErrorMsg( "Can't compile template:<div class='pre'>" + escapeHTML(ex) + "</div>" ) ;
        return { content: "[error: can't compile template]" } ;
    }

    // generate the turn track parameters
    make_turn_track_params( params ) ;

    // process the template
    var snippet ;
    try {
        // NOTE: While it's generally not a good idea to disable auto-escaping, the whole purpose
        // of this application is to generate HTML snippets, and so virtually every single
        // template parameter would have to be piped through the "safe" filter :-/ We never render
        // any of the generated HTML, so any risk exists only when the user pastes the HTML snippet
        // into a VASL scenario, which uses an ancient HTML engine (with probably no Javascript)...
        snippet = func( params, {
            autoEscape: false,
            filters: {
                join: function( vals, sep ) { return vals ? vals.join(sep) : "" ; },
                nbsp: function( val ) { return strReplaceAll( val, " ", "&nbsp;" ) ; },
                upper: function( val ) { return val ? val.toUpperCase() : "" ; },
            } ,
        } ) ;
        snippet = snippet.trim() ;
    }
    catch( ex ) {
        showErrorMsg( "Can't process template: <span class='pre'>" + template_id + "</span><div class='pre'>" + escapeHTML(ex) + "</div>" ) ;
        return { content: "[error: can't process template'" } ;
    }

    // fixup any user file URL's
    var url = make_app_url( "/user", true ) ;
    snippet = strReplaceAll( snippet, "{{USER_FILES}}", url ) ;
    snippet = strReplaceAll( snippet, "{{USER-FILES}}", url ) ;
    url = make_app_url( "/chapter-h", true ) ;
    snippet = strReplaceAll( snippet, "{{CHAPTER_H}}", url ) ;
    snippet = strReplaceAll( snippet, "{{CHAPTER-H}}", url ) ;

    // tidy up the final snippet
    snippet = snippet.replace( /[^\S\r\n]+$/gm, "" ) ; // nb: trim trailing whitespace

    return {
        content: snippet,
        template_id: template_id,
        snippet_id: params.SNIPPET_ID,
        save_name: snippet_save_name,
    } ;
}

function make_turn_track_params( params )
{
    // initialize
    if ( ! params.TURN_TRACK || ! params.TURN_TRACK.NTURNS )
        return ;
    var args = parseTurnTrackParams( params ) ;

    // generate the data for each turn track square
    var turnTrackSquares=[], nTurnTrackSquares=0 ;
    var nRows = Math.ceil( args.nTurns / args.width ) ;
    for ( var row=0 ; row < nRows ; ++row ) {
        turnTrackSquares.push( [] ) ;
        for ( var col=0 ; col < args.width ; ++col ) {
            var turnNo ;
            if ( args.vertical )
                turnNo = 1 + col * nRows + row ;
            else
                turnNo = 1 + row * args.width + col ;
            if ( turnNo > args.nTurns )
                break ;
            var val = [ turnNo, args.reinforce2[turnNo]?true:false, args.reinforce1[turnNo]?true:false ] ;
            if ( params.TURN_TRACK.SWAP_PLAYERS )
                val = [ val[0], val[2], val[1] ] ;
            turnTrackSquares[ turnTrackSquares.length-1 ].push( val ) ;
            nTurnTrackSquares += 1 ;
        }
    }

    // update the snippet params
    params.TURN_TRACK_SQUARES = turnTrackSquares ;
    if ( args.halfTurn )
        params.TURN_TRACK_HALF_TURN = nTurnTrackSquares ;
    // NOTE: The convention is that player 1 sets up first, player 2 moves first,
    // so swapping players actually maps turn track player 1 to the real player 1.
    // NOTE: We generate the player flag URL's instead of using params.PLAYER_FLAG_1/2
    // so that flags will work even if the user has disabled player flags in snippets.
    var forceLocalImages = params.TURN_TRACK_PREVIEW_MODE ;
    params.TURN_TRACK_FLAG_1 = make_player_flag_url(
        get_player_nat( params.TURN_TRACK.SWAP_PLAYERS ? 1 : 2 ),
        true, forceLocalImages
    ) ;
    params.TURN_TRACK_FLAG_2 = make_player_flag_url(
        get_player_nat( params.TURN_TRACK.SWAP_PLAYERS ? 2 : 1 ),
        true, forceLocalImages
    ) ;
}

function parseTurnTrackParams( params )
{
    function parseReinforcements( reinf ) {
        var turnFlags = {} ;
        reinf.split( "," ).forEach( function( turnNo ) {
            turnNo = parseInt( turnNo.trim() ) ;
            if ( ! isNaN( turnNo ) )
                turnFlags[ turnNo ] = true ;
        } ) ;
        return turnFlags ;
    }

    // parse the turn track parameters
    var nTurns = params.TURN_TRACK.NTURNS ;
    var halfTurn = false ;
    if ( nTurns.substr( nTurns.length-2 ) === ".5" ) {
        nTurns = parseInt( nTurns.substr( 0, nTurns.length-2 ) ) + 1 ;
        halfTurn = true ;
    }
    var vertical = params.TURN_TRACK.VERTICAL ;
    var width = params.TURN_TRACK.WIDTH ;
    if ( width === "" )
        width = vertical ? 1 : nTurns ;
    var reinforce1 = parseReinforcements( params.TURN_TRACK.REINFORCEMENTS_1 ) ;
    var reinforce2 = parseReinforcements( params.TURN_TRACK.REINFORCEMENTS_2 ) ;

    return {
        nTurns: nTurns, halfTurn: halfTurn,
        vertical: vertical, width: width,
        reinforce1: reinforce1, reinforce2: reinforce2
    } ;
}

function adjust_vo_comments( params )
{
    // NOTE: I tried replacing things like "(11)" and "(12)" here (for breakdown numbers),
    // with Unicode 246A and 246B, but they're illegible in VASSAL :-/

    // NOTE: We would like to use "(\|\d\*?)+" to match multiple values after the MA,
    // but we can't then capture them :-/
    var splitMGRegex = new RegExp( /\{\{(\d)\|MA(\|\d\*?)(\|\d\*?)?\}\}/ ) ;
    function adjustSplitMG( val ) {
        var match = val.match( splitMGRegex ) ;
        if ( ! match )
            return val ;
        var buf = [ match[1], "MA" ] ;
        for ( var j=2 ; j < match.length ; ++j ) {
            if ( ! match[j] )
                continue ;
            buf.push( "&thinsp;" ) ; // nb: because CSS padding for <span>'s doesn't work in VASSAL :-/
            if ( match[j].substring( match[j].length-1 ) === "*" )
                buf.push( "<span class='split-mg-red'>", "&amp;", match[j].substring(1,match[j].length-1), "</span>" ) ;
            else
                buf.push( "&amp;", match[j].substring(1) ) ;
        }
        return val.substring(0,match.index) + buf.join("") + val.substring(match.index+match[0].length ) ;
    }

    // adjust comments
    if ( params.OB_VO ) {
        for ( i=0 ; i < params.OB_VO.length ; ++i ) {
            if ( ! params.OB_VO[i].comments )
                continue ;
            for ( var j=0 ; j < params.OB_VO[i].comments.length ; ++j ) {
                params.OB_VO[i].comments[j] = adjustSplitMG( wrapExcWithSpan(
                    params.OB_VO[i].comments[j]
                ) ) ;
            }
        }
    }
}

function get_vo_note_key( vo_entry )
{
    // get the note number for the specified vehicle/ordnance
    if ( ! vo_entry.note_number )
        return null ;
    // NOTE: There are some note numbers of the form "1.2" :-/ We also need to handle redirects.
    var match = vo_entry.note_number.match( new RegExp( "^((Br|US|Fr|LC) )?([0-9]+(.\\d)?)" ) ) ;
    if ( ! match )
        return null ;
    var key = match[0] ;
    // NOTE: The K:FW counters appear in the main VASL module, but we handle them as if they were an extension.
    if ( vo_entry.extn_id === "08d" ) {
        // NOTE: All the FfS V/O and M/A notes actually reference K:FW (nb: there are only 2 American counters
        // in this extension, so we can always map them to K:FW UN).
        key = "kfw-un:" + key ;
    } else if ( vo_entry.extn_id )
        key = vo_entry.extn_id + ":" + key ;
    else if ( vo_entry.id.match( /^kfw-(uro|bcfk|rok|ounc|un-common)\// ) )
        key = "kfw-un:" + key ;
    else if ( vo_entry.id.match( /^kfw-(kpa|cpva)\// ) )
        key = "kfw-comm:" + key ;
    return key ;
}

function get_vo_note( vo_type, nat, key )
{
    if ( ! key )
        return null ;

    // check for redirects
    var match = key.match( /^(Br|US|Fr|LC) (.+)$/ ) ;
    if ( match ) {
        nat = MA_NOTE_REDIRECTS[ match[1] ] ;
        key = match[2] ;
    }

    // check if the vehicle/ordnance note key is known to us
    if ( !( vo_type in gVehicleOrdnanceNotes ) )
        return null ;
    if ( !( nat in gVehicleOrdnanceNotes[ vo_type ] ) )
        return null ;
    if ( !( key in gVehicleOrdnanceNotes[ vo_type ][ nat ] ) )
        return null ;

    // check if we have an image or HTML note
    var vo_note = gVehicleOrdnanceNotes[ vo_type ][ nat ][ key ] ;
    if ( vo_note.content !== undefined )
        return vo_note.content ;
    else
        return make_app_url( "/" + vo_type + "/" + nat + "/note/" + key, true ) ;
}

function get_ma_notes_keys( nat, vo_entries, vo_type )
{
    function translate_kfw_key( vo_entry, notes_index, regex, extn_id ) {
        if ( ! vo_entry.id.match( regex ) )
            return null ;
        var key = extn_id + ":" + vo_entry.notes[notes_index] ;
        var pos = key.indexOf( "\u2020" ) ;
        if ( pos >= 0 )
            key = key.substr( 0, pos ) ;
        return key ;
    }

    // figure out which multi-applicable notes are being referenced
    if ( ! vo_entries )
        return null ;
    // NOTE: We need to return 2 sets of referenced keys, one for the normal vehicle/ordnance notes
    // and one for any landing craft, since they share common keys.
    var keys = [ {}, {} ] ;
    var unrecognized = [] ;
    var regexes = [
        new RegExp( "^([A-Z]{1,2})$" ),
        new RegExp( "^([A-Z]{1,2})\\u2020" ),
        new RegExp( "^([a-z])$" ),
        new RegExp( "^([a-z])\\u2020" ),
        new RegExp( "^([A-Z][a-z])$" ),
        new RegExp( "^([A-Za-z])<sup>" ),
        new RegExp( "^<s>([A-Za-z])</s>$" ),
        MA_NOTE_REDIRECT_REGEX,
    ] ;
    var EXTRA_NOTES_INFO = {
        "sh/v":  [ "landing-craft", "Landing Craft" ],
    } ;
    var extra_notes_info = [ null, null ] ;
    var i, j, k ;
    for ( i=0 ; i < vo_entries.length ; ++i ) {
        var vo_entry = vo_entries[i] ;
        if ( ! vo_entry.notes )
            continue ;
        for ( j=0 ; j < vo_entry.notes.length ; ++j ) {

            // NOTE: The K:FW counters appear in the main VASL module, but we handle them as if they were an extension.
            // NOTE: All the FfS V/O and M/A notes actually reference K:FW (nb: there are only 2 American counters
            // in this extension, so we can always map them to K:FW UN).
            var key = translate_kfw_key( vo_entry, j, /^(kfw-(uro|bcfk|rok|ounc|un-common)|ffs)\//, "kfw-un" ) ;
            if ( key ) {
                keys[0][ key ] = true ;
                continue ;
            }
            key = translate_kfw_key( vo_entry, j, /^kfw-(kpa|cpva)\//, "kfw-comm" ) ;
            if ( key ) {
                keys[0][ key ] = true ;
                continue ;
            }

            // handle a special case we can't do with a regex
            if ( vo_entry.notes[j] === "US <s>P</s>" ) {
                keys[0][ vo_entry.extn_id + ":US P" ] = true ;
                continue ;
            }

            // check all the regex's
            var rc = false ;
            for ( k=0 ; k < regexes.length ; ++k ) {
                var match = vo_entry.notes[j].match( regexes[k] ) ;
                if ( match ) {
                    var vo_id = vo_entry.id.split( ":", 1 )[0] ;
                    var is_extra = ( nat !== "landing-craft" && vo_id === "sh/v" ) ;
                    key = match[1] ;
                    if ( vo_entry.extn_id && !( vo_entry.extn_id === "adf-bj" && nat === "american" && key.length === 1 ) ) {
                        // NOTE: We include the extension ID as part of the key, except for BFP American vehicles,
                        // whose multi-applicable notes refer to the main American multi-applicable notes,
                        // not the BFP ones (there aren't any).
                        key = vo_entry.extn_id + ":" + key ;
                    }
                    keys[ is_extra?1:0 ][ key ] = true ;
                    if ( is_extra ) {
                        // NOTE: Only the Americans/British and Japanese have landing craft, while Axis Minor Powers
                        // will never have Allied Minor common vehicles/ordnance (and vice versa), so if we have
                        // extra notes, they should be all of the same type.
                        extra_notes_info = EXTRA_NOTES_INFO[ vo_id ] ;
                    }
                    rc = true ;
                    break ;
                }
            }
            if ( ! rc ) {
                unrecognized.push( [ vo_entry, vo_entry.notes[j] ] ) ;
                if ( ! vo_entry.notes[j].match( NO_WARNING_FOR_MA_NOTE_KEYS_REGEX ) )
                    console.log( "Couldn't recognize multi-applicable note keys for '" + vo_entry.name + "':", vo_entry.notes[j] ) ;
            }
        }
    }

    // delete duplicate keys e.g. if we have notes "X" and "Fr X", we want to include "X" but not "Fr X"
    // *if* the player is French, otherwise we want to include both.
    var keys0 = sort_ma_notes_keys( nat, Object.keys(keys[0]) ) ;
    var keys0a = null ;
    if ( keys0 ) {
        var std_keys = {} ;
        for ( i=0 ; i < keys0.length ; ++i ) {
            if ( keys0[i].match( /^[A-Za-z]{1,2}$/ ) )
                std_keys[ keys0[i] ] = true ;
        }
        keys0a = [] ;
        for ( i=0 ; i < keys0.length ; ++i ) {
            var pos = keys0[i].indexOf( ":" ) ;
            if ( pos > 0 ) {
                var val = keys0[i].substr( pos+1 ) ;
                pos = val.indexOf( " " ) ;
                if ( MA_NOTE_REDIRECTS[ val.substr(0,pos) ] == nat && val.substr(pos+1) in std_keys )
                    continue ;
            }
            keys0a.push( keys0[i] ) ;
        }
    }

    return [
        keys0a,
        sort_ma_notes_keys( nat, Object.keys(keys[1]) ),
        extra_notes_info[0], extra_notes_info[1],
        unrecognized
    ] ;
}

function sort_ma_notes_keys( nat, keys )
{
    // NOTE: I tried sorting the multi-applicable notes on the server side, but it got very messy very quickly
    // e.g. we get an ordered list of notes, so we can no longer access them via the key; we have references
    // to notes that may not be defined e.g. because the user hasn't set them up.

    if ( ! keys || keys.length === 0 )
        return null ;

    function isUpperCase( ch ) { return ch === ch.toUpperCase() ; }
    function isLowerCase( ch ) { return ch === ch.toLowerCase() ; }

    // FUDGE! The sort rules don't apply for the special mixed-case keys in the Allied Minor ordnance.
    // NOTE: There are a few other cases that have two-character mixed-case keys :-/
    function isSpecialKey( key ) { return key.length === 2 && isUpperCase(key[0]) && isLowerCase(key[1]) ; }

    // sort the multi-applicable note keys
    keys.sort( function( lhs, rhs ) {
        if ( ! isSpecialKey(lhs) && ! isSpecialKey(rhs) ) {
            // upper-case sorts lower than lower-case (so that "AA" appears before "a")
            if ( isUpperCase(lhs[0]) && isLowerCase(rhs[0]) )
                return -1 ;
            if ( isLowerCase(lhs[0]) && isUpperCase(rhs[0]) )
                return +1 ;
            // shorter strings sort lower (e.g. so that "A" appears before "AA")
            if ( lhs.length < rhs.length )
                return -1 ;
            else if ( lhs.length > rhs.length )
                return +1 ;
        }
        // return the natural sort order (only for strings with the same case and length)
        if ( lhs < rhs )
            return -1 ;
        else if ( lhs > rhs )
            return +1 ;
        else
            return 0 ;
    } ) ;

    return keys ;
}

function get_ma_note( nat, vo_type, key )
{
    var ma_notes ;
    function redirect_ma_note( target, vo_type ) {
        // extract the multi-applicable note ID
        var match = target.match( MA_NOTE_REDIRECT_REGEX ) ;
        if ( match ) {
            // check if it's a valid redirect
            pos = match[0].indexOf( " " ) ;
            var nat_redirect = MA_NOTE_REDIRECTS[ match[0].substring( 0, pos ) ] ;
            if ( nat_redirect ) {
                // yup - get the referenced multi-applicable note
                ma_notes = get_ma_notes_for_nat( nat_redirect, vo_type ) ;
                return ma_notes[ match[0].substring( pos+1 ) ] ;
            }
        }
        return null ;
    }

    // check for redirected notes
    var ma_note = null ;
    var pos = key.indexOf( ":" ) ;
    if ( pos !== -1 )
        ma_note = redirect_ma_note( key.substring(pos+1), vo_type ) ;
    else
        ma_note = redirect_ma_note( key, vo_type ) ;

    if ( ! ma_note ) {
        // look for a normal note
        ma_notes = get_ma_notes_for_nat( nat, vo_type ) ;
        ma_note = ma_notes[ key ] ;
    }

    if ( ! ma_note ) {
        // still couldn't find anything - if we're Allied/Axis Minor, try the common notes
        if ( gTemplatePack.nationalities[ nat ].type === "allied-minor" )
            ma_note = get_ma_notes_for_nat( "allied-minor", vo_type )[ key ] ;
        else if ( gTemplatePack.nationalities[ nat ].type === "axis-minor" )
            ma_note = get_ma_notes_for_nat( "axis-minor", vo_type )[ key ] ;
    }

    return ma_note ;
}

function get_ma_notes_for_nat( nat, vo_type )
{
    // get the multi-applicable vehicle/ordnance notes for the specified nationality
    var ma_notes ;
    if ( nat === "landing-craft" && nat in gVehicleOrdnanceNotes.vehicles )
        ma_notes = gVehicleOrdnanceNotes.vehicles[ "landing-craft" ][ "multi-applicable" ] ;
    if ( vo_type in gVehicleOrdnanceNotes && nat in gVehicleOrdnanceNotes[vo_type] )
        ma_notes = gVehicleOrdnanceNotes[ vo_type ][ nat ][ "multi-applicable" ] ;
    return ma_notes || {} ;
}

function _make_snippet_image_filename( snippet )
{
    // generate the save filename for a generated snippet image
    var fname = snippet.save_name ;
    if ( ! snippet.save_name ) {
        // no save filename was specified, generate one automatically
        fname = snippet.snippet_id ;
        // strip off "extras/" and owning player nationalities
        var pos = fname.indexOf( "/" ) ;
        if ( pos >= 0 )
            fname = fname.substr( pos+1 ) ;
        fname = fname.replace( /_|-/g, " " ) ;
        // handle characters that are not allowed in filenames
        fname = fname.replace( /:|\||\//g, "-" ) ;
    }
    return fname + ".png" ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function unload_snippet_params( unpack_scenario_date, template_id )
{
    var params = {} ;

    // extract the scenario date components
    if ( unpack_scenario_date ) {
        var scenario_date = get_scenario_date() ;
        if ( scenario_date ) {
            params.SCENARIO_DAY_OF_MONTH = scenario_date[0] ;
            params.SCENARIO_DAY_OF_MONTH_POSTFIX = make_formatted_day_of_month( params.SCENARIO_DAY_OF_MONTH ) ;
            params.SCENARIO_MONTH = scenario_date[1] ;
            params.SCENARIO_MONTH_NAME = get_month_name( params.SCENARIO_MONTH ) ;
            params.SCENARIO_YEAR = scenario_date[2] ;
        }
    }

    // collect all the template parameters
    add_param = function( $elem ) {
        // NOTE: We only unload parameters on the EXTRAS tab if we're processing an extras template.
        if ( $.contains( $("#tabs-extras")[0], $elem[0] ) ) {
            if ( template_id === null || template_id.substr(0,7) !== "extras/" )
                return ;
        }
        params[ $elem.attr("name") ] = $elem.val() ;
    } ;
    $("input[type='text'].param").each( function() { add_param( $(this) ) ; } ) ;
    $("textarea.param").each( function() { add_param( $(this) ) ; } ) ;
    $("select.param").each( function() { add_param( $(this) ) ; } ) ;

    // fix up the turn track parameters
    var nTurns = params.TURN_TRACK_NTURNS ;
    if ( nTurns !== "" ) {
        var width = $( "input[name='TURN_TRACK_WIDTH']" ).val() ;
        params.TURN_TRACK = {
            "NTURNS": nTurns,
            "WIDTH": isNaN( parseInt( width ) ) ? "" : width,
            "VERTICAL": $( "input[name='TURN_TRACK_VERTICAL']" ).prop( "checked" ),
            "REINFORCEMENTS_1": $( "input[name='TURN_TRACK_REINFORCEMENTS_1']" ).val().trim(),
            "REINFORCEMENTS_2": $( "input[name='TURN_TRACK_REINFORCEMENTS_2']" ).val().trim(),
            "SWAP_PLAYERS": $( "input[name='TURN_TRACK_SWAP_PLAYERS']" ).prop( "checked" ),
        } ;
    }
    Object.keys( params ).forEach( function( key ) {
        if ( key.substr(0,11) === "TURN_TRACK_" )
            delete params[key] ;
    } ) ;

    // collect the SSR's
    params.SSR = [] ;
    var data = $("#ssr-sortable").sortable2( "get-entry-data" ) ;
    for ( var i=0 ; i < data.length ; ++i )
        params.SSR.push( data[i].caption ) ;

    // collect the vehicles/ordnance
    function get_vo( vo_type, player_no, key, show_warnings ) {
        var $sortable2 = $( "#ob_" + vo_type + "-sortable_" + player_no ) ;
        var objs = [] ;
        $sortable2.children( "li" ).each( function( index ) {
            var data = $(this).data( "sortable2-data" ) ;
            var vo_entry = data.vo_entry ;
            var vo_image_id = data.vo_image_id ;
            var elite = data.elite ;
            var obj = {
                index: index,
                id: vo_entry.id,
                seq_id: data.id,
                image_id: (vo_image_id !== null) ? vo_image_id[0]+"/"+vo_image_id[1] : null,
                name: vo_entry.name,
                name_len: vo_entry.name.length,
                note_number: vo_entry.note_number,
                notes: vo_entry.notes
            } ;
            if ( vo_entry.extn_id )
                obj.extn_id = vo_entry.extn_id ;
            if ( gUserSettings["include-vasl-images-in-snippets"] ) {
                var url = get_vo_image_url( vo_entry, vo_image_id, false, true ) ;
                if ( url )
                    obj.image = url ;
                if ( $(this).find( ".vo-entry" ).hasClass( "small-piece" ) )
                    obj.small_piece = true ;
            }
            // NOTE: It would be nice to have a Jinja2 filter that inserted the raw capabilities or selected
            // the correct one for the scenario date e.g.
            //   {% for c in veh.capabilities %} {{c|selcap}} {%endif%}}
            // but the problem is that if a capability is not available, we want nothing to appear,
            // but by the time the filter gets called, it's too late :-( Instead, we provide a "raw_capabilities"
            // parameter that people can use in their templates - ugly, but probably not something that will
            // get a lot of use :-/
            var nat = params[ "PLAYER_"+player_no ] ;
            var capabilities = $(this).data( "sortable2-data" ).custom_capabilities ;
            if ( capabilities ) {
                obj.capabilities = capabilities ;
                obj.capabilities_len = capabilities.length ;
                obj.custom_capabilities = capabilities.slice() ;
            } else {
                // NOTE: We don't show warnings here; if there's something wrong,
                // we will show the warnings when we make the raw capabilities.
                capabilities = make_capabilities(
                    false,
                    vo_entry, vo_type, nat, elite,
                    params.SCENARIO_THEATER, params.SCENARIO_YEAR, params.SCENARIO_MONTH,
                    false
                ) ;
                if ( capabilities ) {
                    obj.capabilities = capabilities ;
                    obj.capabilities_len = capabilities.length ;
                }
            }
            capabilities = make_capabilities(
                true,
                vo_entry, vo_type, nat, elite,
                params.SCENARIO_THEATER, params.SCENARIO_YEAR, params.SCENARIO_MONTH,
                show_warnings
            ) ;
            if ( capabilities ) {
                obj.raw_capabilities = capabilities ;
                if ( elite )
                    obj.elite = true ;
            }
            var custom_comments = $(this).data( "sortable2-data" ).custom_comments ;
            if ( custom_comments ) {
                obj.comments = custom_comments ;
                obj.custom_comments = custom_comments.slice() ;
            } else {
                // NOTE: Loading up the vehicle/ordnance comments verbatim here might cause problems with time-based comments,
                // since the user will see them in the UI and not know what they mean. However, the alternative is to perhaps
                // load the appropriate comment for the current scenario date, but that means they will become different
                // to the default set of comments, and thus treated as if the user had changed them. If the scenario date
                // is then changed, the time-based comments won't update accordingly, which will be more confusing than
                // the original problem we're trying to fix :-/
                // We could work around this by checking if a saved comment is the same as the calculated time-based comment
                // for the scenario date, but this is far, far more trouble than it's worth :-/
                obj.comments = get_vo_comments( vo_entry, params.SCENARIO_MONTH, params.SCENARIO_YEAR ) ;
            }
            objs.push( obj ) ;
        } ) ;
        if ( objs.length > 0 )
            params[key] = objs ;
    }
    get_vo( "vehicles", 1, "OB_VEHICLES_1", template_id === "ob_vehicles_1" ) ;
    get_vo( "vehicles", 2, "OB_VEHICLES_2", template_id === "ob_vehicles_2" ) ;
    get_vo( "ordnance", 1, "OB_ORDNANCE_1", template_id === "ob_ordnance_1" ) ;
    get_vo( "ordnance", 2, "OB_ORDNANCE_2", template_id === "ob_ordnance_2" ) ;

    return params ;
}

function get_vo_comments( vo_entry, month, year )
{
    if ( ! vo_entry.comments )
        return vo_entry.comments ;

    // generate the vehicle/ordnance's comments
    var voComments=[], cmt, i ;
    for ( i=0 ; i < vo_entry.comments.length ; ++i ) {
        cmt = make_time_based_comment( vo_entry.comments[i], month, year ) ;
        if ( cmt )
            voComments.push( cmt ) ;
    }

    // remove any disabled comments
    // NOTE: We do this in the backend, but we need to do it here as well,
    // to remove any time-based comments.
    if ( vo_entry.disabled_comments ) {
        var disabled = {} ;
        for ( i=0 ; i < vo_entry.disabled_comments.length ; ++i ) {
            cmt = vo_entry.disabled_comments[ i ] ;
            if ( cmt.substring( 0, 2 ) === "?:" )
                disabled[ cmt.substring(2).trim() ] = true ;
            else
                disabled[ cmt ] = true ;
        }
        var voComments2 = [] ;
        for ( i=0 ; i < voComments.length ; ++i ) {
            if ( ! disabled[ voComments[i] ] )
                voComments2.push( voComments[i] ) ;
        }
        voComments = voComments2 ;
    }

    return voComments ;
}

function make_time_based_comment( val, month, year )
{
    function parseDateControl( val ) {
        // parse a date control string
        var dates = val.split( "-" ) ;
        if ( dates.length != 2 )
            return null ;
        for ( var i=0 ; i < 2 ; ++i ) {
            var date = dates[i].trim() ;
            if ( date !== "" ) {
                var match = date.match( /^(\d\d)\/(19\d\d)$/ ) ;
                if ( ! match )
                    return null ;
                dates[i] = [ match[1], match[2] ] ;
            } else {
                dates[i] = null ;
            }
        }
        return dates ;
    }
    function checkDateControl( dateControl ) {
        // check if the date passed in falls within the date control
        if ( dateControl[0] && ( year < dateControl[0][1] || ( year == dateControl[0][1] && month < dateControl[0][0] ) ) )
            return false ;
        if ( dateControl[1] && ( year > dateControl[1][1] || ( year == dateControl[1][1] && month > dateControl[1][0] ) ) )
            return false ;
        return true ;
    }

    // process any time-based values
    var words, dateControl ;
    for ( ; ; ) {

        // check for a time-based substitution
        var parts = findDelimitedSubstring( val, "{?", "?}" ) ;
        if ( $.isArray( parts ) ) {
            // found one - this form has the following syntax:
            //   {? DATE CONTROL | within the date control | outside the date control | fallback text ?}
            // parse the date control
            words = parts[1].split( "|" ) ;
            dateControl = parseDateControl( words[0] ) ;
            if ( words.length != 4 || dateControl === null ) {
                showErrorMsg( "Invalid time-based comment: " + val ) ;
                return null ;
            }
            // figure out which value to use
            if ( month && year )
                val = parts[0] + words[ checkDateControl(dateControl) ? 1 : 2 ].trim() + parts[2] ;
            else
                val = parts[0] + words[3].trim() + parts[2] ;
            continue ;
        }

        // check for a time-based substitution
        parts = findDelimitedSubstring( val, "{!", "!}" ) ;
        if ( $.isArray( parts ) ) {
            // found one - this form has the following syntax:
            //   {! DATE CONTROL = text | DATE CONTROL = text | etc... | fallback text !}
            var fallbackText = "" ;
            choices = parts[1].split( "|" ) ;
            for ( var i=0 ; i < choices.length ; ++i ) {
                // parse the next choice
                var pos = choices[i].indexOf( "=" ) ;
                if ( pos !== -1 ) {
                    dateControl = parseDateControl( choices[i].substring( 0, pos ) ) ;
                    if ( dateControl !== null ) {
                        // the choice is valid - save it, and its substitution text
                        choices[i] = [ dateControl, choices[i].substring(pos+1).trim() ] ;
                        continue ;
                    }
                }
                // the choice is invalid
                if ( i === choices.length-1 ) {
                    // this is the last choice - use it as the fallback text
                    fallbackText = choices.pop().trim() ;
                    break ;
                } else {
                    showErrorMsg( "Invalid time-based comment: " + choices[i] ) ;
                    return null ;
                }
            }
            // check each choice to try find a match
            var replaceText = fallbackText ;
            if ( month && year ) {
                for ( i=0 ; i < choices.length ; ++i ) {
                    if ( checkDateControl( choices[i][0] ) ) {
                        // found a match - replace the content with the substitution text
                        replaceText = choices[i][1] ;
                        break ;
                    }
                }
            }
            val = parts[0] + replaceText + parts[2] ;
        }

        // NOTE: If we get here, there are no more time-based substitutions to be made.
        break ;
    }

    return val ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function make_capabilities( raw, vo_entry, vo_type, nat, elite, scenario_theater, scenario_year, scenario_month, show_warnings )
{
    var capabilities = [] ;

    // check if the vehicle has no radio
    if ( vo_entry.no_radio )
        capabilities.push( vo_entry.no_radio ) ;

    // extract the static capabilities
    var i ;
    if ( "capabilities" in vo_entry ) {
        for ( i=0 ; i < vo_entry.capabilities.length ; ++i )
            capabilities.push( vo_entry.capabilities[i] ) ;
    }

    // extract the variable capabilities
    if ( "capabilities2" in vo_entry ) {
        var indeterminate_caps=[], unexpected_caps=[], invalid_caps=[] ;
        for ( var key in vo_entry.capabilities2 ) {
            // check if the capability is dependent on the scenario date
            if ( !( vo_entry.capabilities2[key] instanceof Array ) ) {
                capabilities.push( key + vo_entry.capabilities2[key] ) ;
                continue ;
            }
            // check for LF
            if ( key === "LF" ) {
                var caps = $.extend( true, [], vo_entry.capabilities2[key] ) ;
                if ( caps[caps.length-1] === "\u2020" ) {
                    caps.pop() ;
                    capabilities.push( "LF\u2020" ) ;
                } else
                    capabilities.push( "LF" ) ;
                capabilities[ capabilities.length-1 ] += " [" + caps.join(", ") + "]" ;
                continue ;
            }
            if ( $.inArray( key, ["HE","AP","A","D","C","H","B","S","s","sM","sD","sN","WP","IR","Towed"] ) === -1 ) {
                unexpected_caps.push( key ) ;
                continue ;
            }
            // check if we should return the raw capability, or select the one for the scenario date
            if ( ! scenario_year ) {
                // NOTE: We should really check for theater/nationality flags here (e.g. perhaps by calling
                // _check_capability_timestamp()), but at this stage (just before the v1.0 release),
                // it's not worth the risk. The superscripts will still appear in the UI/snippets,
                // so we're not completely doing the wrong thing, and in practice, the scenario date
                // will always be set.
                indeterminate_caps.push( key ) ;
                raw = true ;
            }
            if ( raw ) {
                capabilities.push( make_raw_capability( key, vo_entry.capabilities2[key] ) ) ;
            }
            else {
                var cap = _select_capability_by_date( vo_entry.capabilities2[key], nat, scenario_theater, scenario_year, scenario_month ) ;
                if ( cap === null )
                    continue ;
                if ( cap === "<invalid>" ) {
                    invalid_caps.push( vo_entry.name + ": " + key + ": " + vo_entry.capabilities2[key] ) ;
                    continue ;
                }
                capabilities.push( key + cap ) ;
            }
        }
        // check if there were any capabilities not set
        if ( show_warnings && indeterminate_caps.length > 0 ) {
            showWarningMsg( makeBulletListMsg(
                "Can't determine capabilities for " + vo_entry.name + " without a scenario year:",
                indeterminate_caps
            ) ) ;
        }
        // check if there were any unexpected capabilities
        if ( unexpected_caps.length > 0 ) {
            showErrorMsg( makeBulletListMsg(
                "Internal error (" + vo_entry.name + "): unexpected date-based capabilities:",
                unexpected_caps
            ) ) ;
        }
        // check if there were any invalid capabilities
        if ( invalid_caps.length > 0 ) {
            showErrorMsg( makeBulletListMsg(
                "Internal error (" + vo_entry.name + "): invalid date-based capabilities:",
                invalid_caps
            ) ) ;
        }
    }

    // include damage points (for Landing Craft)
    if ( "damage_points" in vo_entry )
        capabilities.push( "DP " + vo_entry.damage_points ) ;

    // include crew survival
    var crew_survival = make_crew_survival( vo_entry ) ;
    if ( crew_survival )
        capabilities.push( crew_survival ) ;

    // do any special adjustments
    if ( vo_entry.id.substr(0,3) === "am/"  && vo_type === "ordnance" && scenario_theater === "PTO" ) {
        // NOTE: We used to do this if nat == "american" here, but the addition of K:FW broke that,
        // since it contains counters (e.g. M3A1 37mm AT Gun) that has a Note C which is similar
        // to the standard Note C, but doesn't have this special case.
        adjust_capabilities_for_us_ordnance_note_c( capabilities, vo_entry ) ;
    }
    if ( elite )
        adjust_capabilities_for_elite( capabilities, +1 ) ;

    return capabilities ;
}

function make_raw_capability( name, capability )
{
    // NOTE: The capability can sometimes not have a # e.g. Tetrarch CS has a s# of "ref1".
    if ( capability[0] === null ) {
        var cap = capability[1] ;
        if ( cap.match( /^\d\+?$/ ) )
            cap = "<sup>" + cap + "</sup>" ;
        return name + cap ;
    }

    // generate the raw capability string
    var buf = [ name ] ;
    for ( var i=0 ; i < capability.length ; ++i ) {
        if ( typeof(capability[i]) === "string" )
            buf.push( capability[i] ) ;
        else {
            if ( capability[i][0] )
                buf.push( escapeHTML( capability[i][0] ) ) ;
            if ( capability[i][1] )
                buf.push( "<sup>", escapeHTML( capability[i][1] ), "</sup>" ) ;
        }
    }
    return buf.join( "" ) ;
}

function _select_capability_by_date( capabilities, nat, scenario_theater, scenario_year, scenario_month )
{
    // NOTE: The capability can sometimes not have a number e.g. Tetrarch CS s# = "ref1", Stuart III(a) = "HE(4+)"
    var timestamp, val ;
    if ( capabilities[0] === null ) {
        timestamp = capabilities[1] ;
        if ( timestamp.match( /^\d\+?$/ ) ) {
            val = _check_capability_timestamp( capabilities, timestamp, nat, scenario_theater, scenario_year, scenario_month ) ;
            if ( val === "<ignore>" )
                return null ;
            return "";
        }
        return timestamp ;
    }

    // initialize
    capabilities = capabilities.slice() ;
    var ref = has_ref( capabilities ) ;
    if ( ref && capabilities.length === 0 )
        return ref ;

    // check all the capability timestamps
    var retval = "???" ;
    for ( var i=0 ; i < capabilities.length ; ++i ) {
        timestamp = capabilities[i][1].toString() ;
        val = _check_capability_timestamp( capabilities[i], timestamp, nat, scenario_theater, scenario_year, scenario_month ) ;
        if ( val === "<invalid>" )
            return val ;
        if ( val === "<ignore>" )
            continue ;
        retval = val ;
    }
    if ( retval === "???" )
        return null ;
    if ( retval === null )
        retval = "" ; // nb: this can happen for IR
    return ref ? retval+ref : retval ;
}

function _check_capability_timestamp( capabilities, timestamp, nat, scenario_theater, scenario_year, scenario_month )
{
    var MONTH_NAMES = { F:2, M:3, J:6, A:8, S:9, N:11 } ;

    // check for a theater flag
    THEATER_FLAGS = { E: "ETO", P: "PTO", B: "BURMA" } ;
    var required_theater = THEATER_FLAGS[ timestamp.substring( timestamp.length-1 ) ] ;
    if ( required_theater ) {
        timestamp = timestamp.substring( 0, timestamp.length-1 ) ;
        if ( scenario_theater !== required_theater )
            return "<ignore>" ;
    }

    // check for a nationality flag
    NAT_FLAGS = { R: ["romanian"], S: ["slovakian"], CS: ["croatian","slovakian"] } ;
    for ( var i=2 ; i >= 1 ; --i ) {
        var required_nats = NAT_FLAGS[ timestamp.substring( timestamp.length-i ) ];
        if ( required_nats ) {
            timestamp = timestamp.substring( 0, timestamp.length-i ) ;
            if ( required_nats.indexOf( nat ) === -1 )
                return "<ignore>" ;
            break ;
        }
    }

    // check for a trailing "+"
    var hasTrailingPlus = false ;
    if ( timestamp.substring( timestamp.length-1 ) === "+" ) {
        hasTrailingPlus = true ;
        timestamp = timestamp.substring( 0, timestamp.length-1 ) ;
    }

    // check if there is anything left
    if ( ! timestamp ) {
        // nope - the capability is always available
        return capabilities[0] ;
    }

    // parse the month/year the capability becomes available
    var match = timestamp.match( /^(\d+)-$/ ) ;
    if ( match ) {
        if ( scenario_year < 1900 + parseInt(match[1]) )
            return capabilities[0] ;
        else
            return "" ;
    }
    var month = MONTH_NAMES[ timestamp.substring(0,1) ] ;
    if ( month )
        timestamp = timestamp.substring( 1 ) ;
    if ( /^\d+$/.test( timestamp ) ) {
        // this is a single year
        timestamp = parseInt( timestamp ) ;
        // check if the capabilitity is available
        if ( timestamp >= 50 )
            timestamp -= 40 ;
        if ( hasTrailingPlus && scenario_year > 1940 + timestamp )
            return capabilities[0] ;
        else if ( scenario_year === 1940 + timestamp ) {
            if( !month || scenario_month >= month )
                return capabilities[0] ;
        }
    } else if ( /^\d-\d$/.test( timestamp ) ) {
        // this is a range of years
        var timestamp1 = parseInt( timestamp[0] ) ;
        var timestamp2 = parseInt( timestamp[timestamp.length-1] ) ;
        // check if the capabilitity is available
        if ( 1940+timestamp1 <= scenario_year && scenario_year <= 1940+timestamp2 )
            return capabilities[0] ;
    }
    else
        return "<invalid>" ;

    return "<ignore>" ;
}

function has_ref( val )
{
    var last = val[ val.length-1 ] ;
    if ( typeof(last) === "string" && last.match( /^\u2020(<sup>\d<\/sup>)?$/ ) ) {
        val.pop() ;
        return last ;
    }
    return null ;
}

function make_crew_survival( vo_entry )
{
    function make_cs_string( prefix, val ) {
        if ( val.length === 2 && val[0] === null && val[1] === "\u2020" )
            return "\u2020" ;
        else
            return prefix + " " + val ;
    }

    // check if the vehicle has a crew survival field
    var crew_survival = null ;
    if ( "CS#" in vo_entry )
        crew_survival = make_cs_string( "CS", vo_entry["CS#"] ) ;
    else if ( "cs#" in vo_entry )
        crew_survival = make_cs_string( "cs", vo_entry["cs#"] ) ;
    if ( crew_survival === null )
        return null ;

    // check if the vehicle is subject to brew up
    var pos = crew_survival.indexOf( ":brewup" ) ;
    if ( pos !== -1 ) {
        crew_survival = "<span class='brewup'>" +
            crew_survival.substring(0,pos) + crew_survival.substring(pos+7) +
            "</span>" ;
    }

    return crew_survival ;
}

function adjust_capabilities_for_us_ordnance_note_c( capabilities, vo_entry )
{
    // NOTE: American Ordnance Note C: Canister depletion number is increased by 3 in the PTO,
    // unless it has a "P" superscript. This seems to affect the following ordnance:
    // - M3A1 37mm AT Gun
    // - T32 37mm Manpack Gun
    // - M1A1 75mm Pack Howitzer
    // - M2A1 105mm Howitzer (*)
    // - M3 105mm Howitzer (*)
    // (*) = has "P" superscript.

    // check if the ordnance has Note C
    if ( ! vo_entry.notes )
        return ;
    var hasNoteC=false, i ;
    for ( i=0 ; i < vo_entry.notes.length ; ++i ) {
        if ( vo_entry.notes[i].match( /^C\u2020?/ ) )
            hasNoteC = true ;
    }
    if ( ! hasNoteC )
        return ;

    // FUDGE! Figuring out if a capability has a "P" subscript would be incredibly messy, since it gets removed
    // in _check_capability_timestamp() :-/ We just hard-code the relevant counters instead :-/
    if ( ["am/o:013","am/o:014"].indexOf( vo_entry.id ) !== -1 )
        return ;

    // update the Canister depletion number
    for ( i=0 ; i < capabilities.length ; ++i ) {
        var match = capabilities[i].match( /^C(\d+)/ ) ;
        if ( match )
            capabilities[i] = "C" + (parseInt(match[1]) + 3) + capabilities[i].substr(match[0].length) ;
    }
}

function adjust_capabilities_for_elite( capabilities, delta )
{
    // adjust the list of capabilities for elite status
    // Pondicherry, India (FEB/19)
    if ( ! capabilities )
        return ;
    for ( var i=0 ; i < capabilities.length ; ++i ) {
        if ( capabilities[i].indexOf( "<sup>" ) !== -1 )
            continue ; // nb: ignore raw capabilities (e.g. if the scenario date hasn't been set)
        // NOTE: Elite status doesn't apply to vehicular smoke dispensers (C8.9).
        var match = capabilities[i].match( /^(A|M|H|C|D|HE|AP|WP|s)([1-9][0-9]?)/ ) ;
        if ( match )
            capabilities[i] = match[1] + (parseInt(match[2]) + delta) + capabilities[i].substr(match[1].length+match[2].length) ;
    }
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function get_template( template_id, fixup )
{
    // get the specified template
    if ( template_id in gTemplatePack.templates ) {
        var template = gTemplatePack.templates[ template_id ] ;
        if ( fixup ) {
            if ( template_id.substr(0,7) === "extras/" ) {
                for ( var key in gTemplatePack.css )
                    template = strReplaceAll( template, "{{CSS:"+key+"}}", gTemplatePack.css[key] ) ;
                template = fixup_template_parameters( template ) ;
            }
        }
        return template ;
    }
    showErrorMsg( "Unknown template: <span class='pre'>" + escapeHTML(template_id) + "</span>" ) ;
    return null ;
}

// --------------------------------------------------------------------

function edit_template( template_id )
{
    // get the specified template
    var template = get_template( template_id, false ) ;
    if ( template === null )
        return ;

    function on_template_change() {
        // install the new template
        gTemplatePack.templates[template_id] = $("#edit-template textarea").val() ;
    }

    // let the user edit the template
    $("#edit-template textarea").val( template ) ;
    $("#edit-template").dialog( {
        dialogClass: "edit-template",
        title: "Editing template: " + escapeHTML(template_id),
        modal: false,
        minWidth: 600, minHeight: 300,
        create: function() {
            init_dialog( $(this), "Close", true ) ;
        },
        open: function() {
            on_dialog_open( $(this) ) ;
            $(this).height( $(this).height() ) ; // fudge: force the textarea to resize
            $("#edit-template textarea").change( on_template_change ) ;
        },
        close: function() {
            $("#edit-template textarea").off( "change", on_template_change ) ;
        },
        buttons: {
            Close: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// --------------------------------------------------------------------

function on_load_scenario()
{
    // check if the scenario is dirty
    if ( ! is_scenario_dirty() )
        do_on_load_scenario() ;
    else {
        // yup - confirm the operation
        ask( "Load scenario",
            "<p> This scenario has been changed. <p> Do you want to load another scenario, and lose your changes?", {
            width: 470,
            ok: do_on_load_scenario,
        } ) ;
    }

    function do_on_load_scenario() {
        // FOR TESTING PORPOISES! We can't control a file upload from Selenium (since
        // the browser will use native controls), so we get the data from a <textarea>).
        if ( getUrlParam( "scenario_persistence" ) ) {
            var $elem = $( "#_scenario-persistence_" ) ;
            do_load_scenario( $elem.val(), null ) ;
            showInfoMsg( "The scenario was loaded." ) ; // nb: the tests are looking for this
            return ;
        }

        // if we are running inside the PyQt wrapper, let it handle everything
        if ( gWebChannelHandler ) {
            gWebChannelHandler.load_scenario( function( resp ) {
                if ( ! resp )
                    return ;
                do_load_scenario( resp.data, resp.filename ) ;
            } ) ;
            return ;
        }

        // ask the user to upload the scenario file
        $("#load-scenario").trigger( "click" ) ;
    }
}

function on_load_scenario_file_selected()
{
    // read the selected file
    var fileReader = new FileReader() ;
    var file = $("#load-scenario").prop( "files" )[0] ;
    fileReader.onload = function() {
        do_load_scenario( fileReader.result, file.name ) ;
    } ;
    fileReader.readAsText( file ) ;
}

function do_load_scenario( data, fname )
{
    // NOTE: We reset the scenario first, in case the loaded scenario is missing fields,
    // so that those fields will be reset to their default values (instead of just staying unchanged).
    do_on_new_scenario( false ) ;

    // load the scenario
    try {
        data = JSON.parse( data ) ;
    } catch( ex ) {
        showErrorMsg( "Can't load the scenario file:<div class='pre'>" + escapeHTML(ex) + "</div>" ) ;
        return false ;
    }
    do_load_scenario_data( data ) ;
    gLastSavedScenarioFilename = fname ;
    showInfoMsg( "The scenario was loaded." ) ;

    return true ;
}

function do_load_scenario_data( params )
{
    // reset the scenario
    reset_scenario() ;
    gScenarioCreatedTime = params._creation_time ;

    // auto-assign ID's to the OB setup notes and notes
    // NOTE: We do this here to handle scenarios that were created before these ID's were implemented.
    auto_assign_ids( params.SCENARIO_NOTES, "id" ) ;
    auto_assign_ids( params.OB_SETUPS_1, "id" ) ;
    auto_assign_ids( params.OB_NOTES_1, "id" ) ;
    auto_assign_ids( params.OB_VEHICLES_1, "seq_id" ) ;
    auto_assign_ids( params.OB_ORDNANCE_1, "seq_id" ) ;
    auto_assign_ids( params.OB_SETUPS_2, "id" ) ;
    auto_assign_ids( params.OB_NOTES_2, "id" ) ;
    auto_assign_ids( params.OB_VEHICLES_2, "seq_id" ) ;
    auto_assign_ids( params.OB_ORDNANCE_2, "seq_id" ) ;

    // set default values
    function set_default_val( key, val ) {
        if ( ! (key in params) )
            params[key] = val ;
    }
    set_default_val( "OB_VEHICLES_MA_NOTES_WIDTH_1", "300px" ) ;
    set_default_val( "OB_ORDNANCE_MA_NOTES_WIDTH_1", "300px" ) ;
    set_default_val( "OB_VEHICLES_MA_NOTES_WIDTH_2", "300px" ) ;
    set_default_val( "OB_ORDNANCE_MA_NOTES_WIDTH_2", "300px" ) ;

    // load the scenario parameters
    var params_loaded = {} ;
    var warnings = [] ;
    var unknown_vo = [] ;
    var set_param = function( $elem, key ) {
        if ( key === "SCENARIO_DATE" ) {
            try {
                var scenario_date = $.datepicker.parseDate( "yy-mm-dd", params[key] ) ;
                $elem.datepicker( "setDate", scenario_date ) ; // nb: don't need to adjust for timezone here
            } catch( ex ) {
                warnings.push( "Invalid scenario date: " + escapeHTML( params[key] ) ) ;
            }
        }
        else {
            $elem.val( params[key] ) ;
            if ( key === "ASA_ID" )
                updateForConnectedScenario( params[key], params.ROAR_ID ) ;
        }
        if ( $elem[0].nodeName.toLowerCase() === "select" )
            $elem.trigger( "change" ) ;
        params_loaded[key] = true ;
        return $elem ;
    } ;
    // FUDGE! We must set the players first, since changing these will reset the OB tabs.
    function is_valid_player_id( player_nat ) {
        return gTemplatePack.nationalities[ player_nat ] !== undefined ;
    }
    if ( "PLAYER_1" in params ) {
        if ( is_valid_player_id( params.PLAYER_1 ) ) {
            set_param( $("select[name='PLAYER_1']"), "PLAYER_1" ) ;
            on_player_change( 1 ) ;
        } else {
            showErrorMsg( "Invalid player nationality: " + params.PLAYER_1 ) ;
            params_loaded.PLAYER_1 = true ;
        }
    }
    if ( "PLAYER_2" in params ) {
        if ( is_valid_player_id( params.PLAYER_2 ) ) {
            set_param( $("select[name='PLAYER_2']"), "PLAYER_2" ) ;
            on_player_change( 2 ) ;
        } else {
            showErrorMsg( "Invalid player nationality: " + params.PLAYER_2 ) ;
            params_loaded.PLAYER_2 = true ;
        }
    }
    var i ;
    for ( var key in params ) {
        var player_no, $sortable2 ;
        if ( key === "TURN_TRACK" ) {
            setTurnTrackNTurns( params[key].NTURNS ) ;
            $( "input[name='TURN_TRACK_VERTICAL']" ).prop( "checked", params[key].VERTICAL ) ;
            $( "input[name='TURN_TRACK_WIDTH']" ).val( params[key].WIDTH ) ;
            $( "input[name='TURN_TRACK_REINFORCEMENTS_1']" ).val( params[key].REINFORCEMENTS_1 ) ;
            $( "input[name='TURN_TRACK_REINFORCEMENTS_2']" ).val( params[key].REINFORCEMENTS_2 ) ;
            $( "input[name='TURN_TRACK_SWAP_PLAYERS']" ).prop( "checked", params[key].SWAP_PLAYERS ) ;
            params_loaded[key] = true ;
            continue ;
        }
        if ( key === "SSR" ) {
            $sortable2 = $( "#ssr-sortable" ) ;
            for ( i=0 ; i < params[key].length ; ++i )
                do_add_scenario_note( $sortable2, { caption: params[key][i] } ) ;
            params_loaded[key] = true ;
            continue ;
        }
        if ( key === "SCENARIO_NOTES" ) {
            $sortable2 = $( "#scenario_notes-sortable" ) ;
            for ( i=0 ; i < params[key].length ; ++i )
                do_add_scenario_note( $sortable2, params[key][i] ) ;
            params_loaded[key] = true ;
            continue ;
        }
        if ( key === "OB_SETUPS_1" || key === "OB_SETUPS_2" ) {
            player_no = key.substring( key.length-1 ) ;
            $sortable2 = $( "#ob_setups-sortable_" + player_no ) ;
            for ( i=0 ; i < params[key].length ; ++i )
                do_add_ob_setup( $sortable2, params[key][i] ) ;
            params_loaded[key] = true ;
            continue ;
        }
        if ( key === "OB_NOTES_1" || key === "OB_NOTES_2" ) {
            player_no = key.substring( key.length-1 ) ;
            $sortable2 = $( "#ob_notes-sortable_" + player_no ) ;
            for ( i=0 ; i < params[key].length ; ++i )
                do_add_ob_note( $sortable2, params[key][i] ) ;
            params_loaded[key] = true ;
            continue ;
        }
        if ( key === "OB_VEHICLES_1" || key === "OB_ORDNANCE_1" || key === "OB_VEHICLES_2" || key === "OB_ORDNANCE_2" ) {
            player_no = key.substring( key.length-1 ) ;
            var nat = params[ "PLAYER_" + player_no ] ;
            var vo_type = (key.substring(0,12) === "OB_VEHICLES_") ? "vehicles" : "ordnance" ;
            for ( i=0 ; i < params[key].length ; ++i ) {
                var vo_id = params[key][i].id ;
                var vo_entry ;
                if ( vo_id )
                    vo_entry = find_vo( vo_type, nat, vo_id ) ;
                else {
                    // FUDGE! Early versions stored vehicles/ordnance by name, but these are not unique (even within
                    // a single nationality :-/), so we switched to manually-assigned unique ID's. For legacy save files,
                    // if there is no ID field, we load vehicles/ordnance by name.
                    vo_id = params[key][i].name ; // nb: we store the name in the ID variable, in case we have to log an error below
                    vo_entry = find_vo_by_name( vo_type, nat, vo_id ) ;
                }
                var vo_image_id = null ;
                if ( "image_id" in params[key][i] ) {
                    var matches = params[key][i].image_id.match( /^([a-z0-9:]{3,10})\/(\d)$/ ) ;
                    if ( matches )
                        vo_image_id = [ matches[1], parseInt(matches[2]) ] ;
                    else
                        warnings.push( "Invalid V/O image ID for '" + params[key][i].name + "': " + params[key][i].image_id ) ;
                }
                if ( vo_entry )
                    do_add_vo( vo_type, player_no, vo_entry, vo_image_id, params[key][i].elite, params[key][i].custom_capabilities, params[key][i].custom_comments, params[key][i].seq_id ) ;
                else
                    unknown_vo.push( vo_id || "(not set)" ) ;
            }
            params_loaded[key] = true ;
            continue ;
        }
        //jshint loopfunc: true
        var $elem = $("input[type='text'][name='"+key+"'].param").each( function() {
            set_param( $(this), key ) ;
        } ) ;
        $elem = $("textarea[type='text'][name='"+key+"'].param").each( function() {
            set_param( $(this), key ) ;
        } ) ;
        $elem = $("select[name='"+key+"'].param").each( function() {
            if ( key !== "PLAYER_1" && key !== "PLAYER_2" )
                set_param( $(this), key ).trigger( "change" ) ;
        } ) ;
    }
    if ( ! params.ASA_ID )
        updateForConnectedScenario( null, null ) ;

    // look for unrecognized keys
    var buf = [] ;
    for ( key in params ) {
        if ( !(key in params_loaded) && key.substring(0,1) !== "_" )
            buf.push( key + " = " + params[key] ) ;
    }
    if ( buf.length > 0 ) {
        showWarningMsg( makeBulletListMsg(
            "Unknown keys in the scenario file:",
            buf, li_class="pre"
        ) ) ;
    }

    // report any unknown vehicles/ordnance
    if ( unknown_vo.length > 0 ) {
        showWarningMsg( makeBulletListMsg(
            "Unknown vehicles/ordnance:", unknown_vo
        ) ) ;
    }

    // show any other warnings
    if ( warnings.length === 1 )
        showWarningMsg( warnings[0] ) ;
    else if ( warnings.length > 1 ) {
        showWarningMsg( makeBulletListMsg(
            "", warnings
        ) ) ;
    }

    // remember the state of this scenario
    gLastSavedScenario = unload_params_for_save( false ) ;

    // update the UI
    $("#tabs").tabs( "option", "active", 0 ) ;
    on_scenario_date_change() ;
    update_scenario_status() ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function auto_assign_ids( vals, key )
{
    if ( ! vals )
        return ;

    // NOTE: These ID's are used to uniquely identify OB setup notes and OB notes, since they are generated
    // from the same template ("ob_setup" and "ob_note") and so the template_id alone won't be enough. We need
    // to be able to uniquely identify each snippet so that we can match them with labels in the VASL scenario.
    // However, we need to be able to handle the following situation:
    // - the scenario has, say, 5 OB notes, with ID's 1-5
    // - the user deletes #3, and creates a new one
    // If we track the highest ID ever used across the life of the scenario, the new snippet will be assigned ID #6,
    // but when we inject the snippets into the VASL scenario, the label corresponding to snippet #3 will be left
    // as it is, and a new label created for snippet #6, which is not what the user will want. Instead, we re-use
    // ID 3 and give it to the new snippet, so that when we inject snippets, the old label corresponding to snippet #3
    // will simply be updated with the contents of the new snippet #6.

    // identify which ID's are currently in use
    var usedIds = {} ;
    for ( var i=0 ; i < vals.length ; ++i ) {
        if ( vals[i][key] )
            usedIds[ vals[i][key] ] = true ;
    }

    // assign ID's to entries that don't have one
    for ( i=0 ; i < vals.length ; ++i ) {
        if ( ! vals[i][key] )
            vals[i][key] = auto_assign_id( usedIds ) ;
    }
}

function auto_assign_id( usedIds )
{
    // assign the next available ID
    for ( var i=1 ; ; ++i ) {
        if ( ! usedIds[i] ) {
            usedIds[i] = true ;
            return i ;
        }
    }
}

// --------------------------------------------------------------------

function on_save_scenario()
{
    // unload the template parameters
    var params = unload_params_for_save( true ) ;
    var data = JSON.stringify( params, null, 4 ) ;

    // FOR TESTING PORPOISES! We can't control a file download from Selenium (since
    // the browser will use native controls), so we store the result in a <textarea>
    // and the test suite will collect it from there).
    if ( getUrlParam( "scenario_persistence" ) ) {
        $("#_scenario-persistence_").val( data ) ;
        gLastSavedScenario = params ;
        return ;
    }

    // generate the save filename
    var save_fname = gLastSavedScenarioFilename ;
    if ( ! save_fname ) {
        var scenario_name = params.SCENARIO_NAME.trim() ;
        var scenario_id = params.SCENARIO_ID.trim() ;
        if ( scenario_name && scenario_id )
            save_fname = scenario_name + " (" + scenario_id + ").json" ;
        else if ( scenario_name )
            save_fname = scenario_name + ".json" ;
        else if ( scenario_id )
            save_fname = scenario_id + ".json" ;
        else
            save_fname = "scenario.json" ;
    }

    // if we are running inside the PyQt wrapper, let it handle everything
    if ( gWebChannelHandler ) {
        gWebChannelHandler.save_scenario( save_fname, data, function( save_fname ) {
            if ( ! save_fname )
                return ;
            gLastSavedScenario = params ;
            gLastSavedScenarioFilename = save_fname ;
            showInfoMsg( "The scenario was saved." ) ;
        } ) ;
        return ;
    }

    // return the parameters to the user as a downloadable file
    download( toUTF8(data), save_fname, "application/json" ) ;

    // NOTE: We get no indication if the download was successful, so we can't show feedback :-/
    // Also, if the download didn't actually happen (e.g. because it was cancelled), then setting
    // the last saved scenario here is not quite the right thing to do, since subsequent checks
    // for a dirty scenario will return the wrong result, since they assume that the scenario
    // was saved properly here :-/
    gLastSavedScenario = params ;
    // NOTE: It would be nice to set gLastSavedScenarioFilename here, but this will give the wrong behaviour
    // if the user loads a scenario from a file that is named using a non-standard convention.
}

function unload_params_for_save( includeMetadata )
{
    function extract_vo_entries( key ) {
        if ( !( key in params ) )
            return ;
        var entries = [] ;
        for ( var i=0 ; i < params[key].length ; ++i ) {
            var entry = {
                id: params[key][i].id,
                seq_id: params[key][i].seq_id,
                name: params[key][i].name, // nb: not necessary, but convenient
            } ;
            if ( params[key][i].image_id !== null )
                entry.image_id = params[key][i].image_id ;
            if ( params[key][i].custom_capabilities )
                entry.custom_capabilities = params[key][i].custom_capabilities ;
            if ( params[key][i].elite )
                entry.elite = true ;
            if ( params[key][i].custom_comments )
                entry.custom_comments = params[key][i].custom_comments ;
            entries.push( entry ) ;
        }
        params[key] = entries ;
    }

    // unload the template parameters
    var params = unload_snippet_params( false, null ) ;
    function get_sortable2_data( $elem ) {
        // IMPORTANT: "get-entry-data" returns a *reference* to the data associated with each sortable2 entry,
        // but we need to return a completely independent data structure that contains the unloaded parameters,
        // otherwise we run into problems when checking if a scenario has been modified (because the copy of
        // the last-saved scenario has references to the same underlying data structures as the sortable2 entries).
        return $.extend( true, [], $elem.sortable2( "get-entry-data" ) ) ;
    }
    params.SCENARIO_NOTES = get_sortable2_data( $("#scenario_notes-sortable") ) ;
    params.OB_SETUPS_1 = get_sortable2_data( $("#ob_setups-sortable_1") ) ;
    params.OB_SETUPS_2 = get_sortable2_data( $("#ob_setups-sortable_2") ) ;
    params.OB_NOTES_1 = get_sortable2_data( $("#ob_notes-sortable_1") ) ;
    params.OB_NOTES_2 = get_sortable2_data( $("#ob_notes-sortable_2") ) ;
    extract_vo_entries( "OB_VEHICLES_1" ) ;
    extract_vo_entries( "OB_ORDNANCE_1" ) ;
    extract_vo_entries( "OB_VEHICLES_2" ) ;
    extract_vo_entries( "OB_ORDNANCE_2" ) ;

    // save the scenario date in ISO-8601 format
    var scenario_date = get_scenario_date() ;
    if ( scenario_date )
        params.SCENARIO_DATE = scenario_date[3] ;

    // save some admin metadata
    if ( includeMetadata ) {
        params._app_version = gAppVersion ;
        var now = (new Date()).toISOString() ;
        params._last_update_time = now ;
        if ( gScenarioCreatedTime )
            params._creation_time = gScenarioCreatedTime ;
        else {
            params._creation_time = now ;
            gScenarioCreatedTime = now ;
        }
    }

    return params ;
}

// --------------------------------------------------------------------

function on_new_scenario()
{
    // check if the scenario is dirty
    if ( ! is_scenario_dirty() )
        do_on_new_scenario( true ) ;
    else {
        // yup - confirm the operation
        ask( "New scenario",
            "<p> This scenario has been changed. <p> Do you want to reset it, and lose your changes?", {
            ok: function() { do_on_new_scenario( true ) ; },
        } ) ;
    }
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function do_on_new_scenario( user_requested ) {
    // load the default scenario
    if ( gDefaultScenario )
        do_load_scenario_data( gDefaultScenario ) ;
    else {
        $.getJSON( gGetDefaultScenarioUrl, function(data) {
            gDefaultScenario = data ;
            do_load_scenario_data( data ) ;
            update_page_load_status( "default-scenario" ) ;
        } ).fail( function( xhr, status, errorMsg ) {
            showErrorMsg( "Can't get the default scenario:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
            update_page_load_status( "default-scenario" ) ;
            return ;
        } ) ;
    }

    // flag that we have a new scenario
    gLastSavedScenarioFilename = null ;
    if ( gWebChannelHandler && user_requested )
        gWebChannelHandler.on_new_scenario() ;

    // provide some feedback to the user
    if ( user_requested )
        showInfoMsg( "The scenario was reset." ) ;
}

function reset_scenario()
{
    // reset all the template parameters
    $("input[type='text'].param").each( function() {
        if ( ! $.contains( $("#tabs-extras")[0], $(this)[0] ) )
            $(this).val( "" ) ;
    } ) ;
    $("textarea.param").each( function() { $(this).val("") ; } ) ;
    $("input[type='checkbox']").prop( "checked", false ) ;
    $( "select[name='TURN_TRACK_NTURNS'].param" ).val( "" ).trigger( "change" ) ;

    // reset the player droplist's
    var player_no ;
    for ( player_no=1 ; player_no <= 2 ; ++player_no ) {
        on_player_change( player_no ) ;
        $("select[name='PLAYER_" + player_no + "_ELR']").val( "" ).trigger( "change" ) ;
        $("select[name='PLAYER_" + player_no + "_SAN']").val( "" ).trigger( "change" ) ;
    }

    // reset all the template parameters
    $("#scenario_notes-sortable").sortable2( "delete-all" ) ;
    $("#ssr-sortable").sortable2( "delete-all" ) ;
}

// --------------------------------------------------------------------

function is_scenario_dirty( force )
{
    // nb: confirming operations is insanely annoying during development :-/
    if ( !force && getUrlParam( "disable-dirty-scenario-check" ) )
        return false ;

    // check if the scenario has been changed since it was loaded, or last saved
    if ( gLastSavedScenario === null )
        return false ;
    var last_saved_scenario = {} ;
    for ( var key in gLastSavedScenario ) {
        if ( key.substr(0,1) !== "_" )
            last_saved_scenario[key] = gLastSavedScenario[key] ;
    }
    var params = unload_params_for_save( false ) ;
    return JSON.stringify( params ) != JSON.stringify( last_saved_scenario ) ;
}

// --------------------------------------------------------------------

function on_template_pack()
{
    // FOR TESTING PORPOISES! We can't control a file upload from Selenium (since
    // the browser will use native controls), so we store the result in a <div>).
    if ( getUrlParam( "template_pack_persistence" ) ) {
        var data = $( "#_template-pack-persistence_" ).val() ;
        var pos = data.indexOf( "|" ) ;
        var fname = data.substring( 0, pos ).trim() ;
        data = data.substring( pos+1 ).trim() ;
        if ( getFilenameExtn( fname ) === ".zip" )
            data = atob( data ) ;
        do_load_template_pack( fname, data ) ;
        return ;
    }

    // ask the user to upload the template pack
    $("#load-template-pack").trigger( "click" ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function on_template_pack_file_selected()
{
    // read the selected file
    var MAX_FILE_SIZE = 2 ; // nb: MB
    var file = $("#load-template-pack").prop( "files" )[0] ;
    if ( file.size > 1024*1024*MAX_FILE_SIZE ) {
        showErrorMsg( "Template pack is too large (must be no larger than " + MAX_FILE_SIZE + "MB)." ) ;
        return ;
    }
    var fileReader = new FileReader() ;
    fileReader.onload = function() {
        var data = fileReader.result ;
        do_load_template_pack( file.name, data ) ;
    } ;
    fileReader.readAsArrayBuffer( file ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function do_load_template_pack( fname, data )
{
    // initialize
    var invalid_filename_extns = [] ;
    var unknown_template_ids = [] ;
    var template_pack = {
        nationalities: $.extend( true, {}, gDefaultTemplatePack.nationalities ),
        "national-capabilities": $.extend( true, {}, gDefaultTemplatePack["national-capabilities"] ),
        templates: {},
        css: {},
        includes: {},
    } ;

    // NOTE: We always start with the default extras templates; user-defined template packs
    // can add to them, or modify existing ones, but not remove them.
    for ( var template_id in gDefaultTemplatePack.templates ) {
        if ( template_id.substr( 0, 7 ) === "extras/" )
            template_pack.templates[template_id] = gDefaultTemplatePack.templates[template_id].slice() ;
    }

    // initialize
    function on_template_pack_file( fname, data ) {
        // make sure the filename is valid
        if ( fname.toLowerCase() === "nationalities.json" ) {
            var nationalities = null ;
            try {
                nationalities = JSON.parse( data ) ;
            } catch( ex ) {
                showWarningMsg( "Can't parse the nationalities JSON data:<div class='pre'>" + escapeHTML(ex) + "</div>" ) ;
                return ;
            }
            $.extend( true, template_pack.nationalities, nationalities ) ;
            return ;
        }
        if ( fname.toLowerCase() === "national-capabilities.json" ) {
            var nat_caps = null ;
            try {
                nat_caps = JSON.parse( data ) ;
            } catch( ex ) {
                showWarningMsg( "Can't parse the nationalities JSON data:<div class='pre'>" + escapeHTML(ex) + "</div>" ) ;
                return ;
            }
            $.extend( true, template_pack["national-capabilities"], nat_caps ) ;
            return ;
        }
        var extn = getFilenameExtn( fname ) ;
        if ( [".j2",".css",".include"].indexOf( extn ) === -1 ) {
            invalid_filename_extns.push( fname ) ;
            return ;
        }
        // save the template pack file
        var template_id = fname.substring( 0, fname.length-extn.length ).toLowerCase() ;
        if ( extn === ".css" )
            template_pack.css[template_id] = data ;
        else if ( extn === ".include" )
            template_pack.includes[template_id] = data ;
        else if ( template_id === "ob_vo" )
            template_pack.templates.ob_vehicles = template_pack.templates.ob_ordnance = data ;
        else if ( template_id === "ob_vo_note" )
            template_pack.templates.ob_vehicle_note = template_pack.templates.ob_ordnance_note = data ;
        else if ( template_id === "ob_ma_notes" )
            template_pack.templates.ob_vehicles_ma_notes = template_pack.templates.ob_ordnance_ma_notes = data ;
        else {
            if ( gValidTemplateIds.indexOf( template_id ) === -1 && template_id.substr(0,7) !== "extras/" ) {
                unknown_template_ids.push( fname ) ;
                return ;
            }
            template_pack.templates[template_id] = data ;
        }
    }

    // initialize
    function install_new_template_pack( success_msg ) {
        // check if there were any errors
        var ok = true ;
        var buf, tid, i ;
        if ( invalid_filename_extns.length > 0 ) {
            buf = [] ;
            buf.push(
                "Invalid template ",
                pluralString( invalid_filename_extns.length, "extension:", "extensions:" ),
                "<div class='pre'>"
            ) ;
            for ( i=0 ; i < invalid_filename_extns.length ; ++i )
                buf.push( escapeHTML(invalid_filename_extns[i]) + "<br>" ) ;
            buf.push( "</div>" ) ;
            buf.push( 'Must be <span class="pre">".zip"</span> or <span class="pre">".j2"</span>.' ) ;
            showErrorMsg( buf.join("") ) ;
            ok = false ;
        }
        if ( unknown_template_ids.length > 0 ) {
            buf = [] ;
            buf.push(
                "Invalid template ",
                pluralString( unknown_template_ids.length, "filename:", "filenames:" ),
                "<div class='pre'>"
            ) ;
            for ( i=0 ; i < unknown_template_ids.length ; ++i )
                buf.push( escapeHTML(unknown_template_ids[i]) + "<br>" ) ;
            buf.push( "</div>" ) ;
            var buf2 = [] ;
            for ( i=0 ; i < gValidTemplateIds.length ; ++i )
                buf2.push( gValidTemplateIds[i] + ".j2" ) ;
            buf.push( makeBulletListMsg( "Must be one of:<div class='pre'>", buf2 ) ) ;
            buf.push( "</div>" ) ;
            showErrorMsg( buf.join("") ) ;
            ok = false ;
        }
        if ( ! ok )
            return ;
        // all good - install the new template pack
        install_template_pack( template_pack ) ;
        showInfoMsg( success_msg ) ;
    }

    // check if we have a ZIP file
    fname = fname.toLowerCase() ;
    if ( getFilenameExtn( fname ) === ".zip" ) {
        // yup - process each file in the ZIP
        var nFiles = 0 ;
        JSZip.loadAsync( data ).then( function( zip ) {
            zip.forEach( function( relPath, zipEntry ) {
                ++ nFiles ;
                zipEntry.async( "string" ).then( function( data ) {
                    // extract the filename (i.e. we ignore sub-directories)
                    fname = zipEntry.name ;
                    var pos = Math.max( fname.lastIndexOf("/"), fname.lastIndexOf("\\") ) ;
                    if ( pos === fname.length-1 )
                        return ; // nb: ignore directory entries
                    if ( pos !== -1 && fname.substr(0,7) !== "extras/" )
                        fname = fname.substring( pos+1 ) ;
                    on_template_pack_file( fname, data ) ;
                } ).then( function() {
                    if ( --nFiles === 0 ) {
                        install_new_template_pack( "The template pack was loaded." ) ;
                    }
                } ) ;
            } ) ;
        } ).catch( function(ex) {
            showErrorMsg( "Can't unpack the ZIP:<div class='pre'>" + escapeHTML(ex) + "</div>" ) ;
        } ) ;
    }
    else {
        // nope - assume an individual template file
        if ( data instanceof ArrayBuffer )
            data = String.fromCharCode.apply( null, new Uint8Array(data) ) ;
        on_template_pack_file( fname, data ) ;
        install_new_template_pack( "The template file was loaded." ) ;
    }

}

// --------------------------------------------------------------------

function _is_scenario_in_or_after( month, year ) {
    // check if the scenario is after the specified month/year
    var scenario_date = get_scenario_date() ;
    if ( ! scenario_date )
        return false ;
    if ( scenario_date[2] > year )
        return true ;
    if ( scenario_date[2] < year )
        return false ;
    return scenario_date[1] >= month  ;
}

function is_pf_available() { return _is_scenario_in_or_after( 10, 1943 ) ; }
function is_pf_finnish_available() { return _is_scenario_in_or_after( 7, 1944 ) ; }
function is_pf_hungarian_available() { return _is_scenario_in_or_after( 6, 1944 ) ; }
function is_pf_romanian_available() { return _is_scenario_in_or_after( 3, 1944 ) ; }
function is_psk_available() { return _is_scenario_in_or_after( 9, 1943 ) ; }
function is_baz_available() { return _is_scenario_in_or_after( 11, 1942 ) ; }
function is_atmm_available() { return _is_scenario_in_or_after( 1, 1944 ) ; }
function is_atmm_romanian_available() { return _is_scenario_in_or_after( 7, 1943 ) ; }

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function on_scenario_date_change()
{
    // NOTE: We update the visual appearance of the buttons to indicate whether
    // the support weapons are available, but leave the buttons active since
    // the date restrictions are not strict, and the SW are sometimes available
    // (by SSR) even outside the normal time.
    function update_ui( id, is_available ) {
        var $btn = $( "button.generate[data-id='" + id + "']" ) ;
        if ( is_available )
            $btn.removeClass( "inactive" ) ;
        else
            $btn.addClass( "inactive" ) ;
        $btn.children( "img" ).each( function() {
            $(this).attr( "src", gImagesBaseUrl + (is_available?"/snippet.png":"/snippet-disabled.png") ) ;
        } ) ;
    }
    update_ui( "pf", is_pf_available() ) ;
    update_ui( "pf-finnish", is_pf_finnish_available() ) ;
    update_ui( "pf-hungarian", is_pf_hungarian_available() ) ;
    update_ui( "pf-romanian", is_pf_romanian_available() ) ;
    update_ui( "psk", is_psk_available() ) ;
    update_ui( "baz", is_baz_available() ) ;
    update_ui( "atmm", is_atmm_available() ) ;
    update_ui( "atmm-romanian", is_atmm_romanian_available() ) ;

    // update the vehicle/ordnance entries
    _update_vo_sortable2_entries() ;
}

function _update_vo_sortable2_entries()
{
    // update all the vehicle/ordnance entries
    var snippet_params = unload_snippet_params( true, null ) ;
    function update_vo( vo_type, player_no ) {
        var $sortable2 = $( "#ob_" + vo_type + "-sortable_" + player_no ) ;
        $sortable2.children( "li" ).each( function() {
            update_vo_sortable2_entry( $(this), vo_type, snippet_params ) ;
        } ) ;
    }
    for ( var player_no=1 ; player_no <= 2 ; ++player_no ) {
        update_vo( "vehicles", player_no ) ;
        update_vo( "ordnance", player_no ) ;
    }
}

// --------------------------------------------------------------------

function update_scenario_status()
{
    // get the scenario details
    var scenario_name = $("input[name='SCENARIO_NAME']").val().trim() ;
    var scenario_id = $("input[name='SCENARIO_ID']").val().trim() ;
    var caption = "" ;
    if ( scenario_name && scenario_id )
        caption = scenario_name + " (" + scenario_id + ")" ;
    else if ( scenario_name )
        caption = scenario_name ;
    else if ( scenario_id )
        caption = scenario_id ;

    // update the window title
    var title = gAppName ;
    if ( caption )
        title += " - " + caption ;
    var is_dirty = is_scenario_dirty( true ) ;
    if ( is_dirty )
        title += " (*)" ;
    document.title = title ;

    // notify the PyQt wrapper application
    if ( gWebChannelHandler )
        gWebChannelHandler.on_update_scenario_status( caption, is_dirty ) ;
}

function on_scenario_theater_change()
{
    // update the vehicle/ordnance entries
    _update_vo_sortable2_entries() ;

    // show/hide the nationality-specific buttons
    update_nationality_specific_buttons( 1 ) ;
    update_nationality_specific_buttons( 2 ) ;
}
