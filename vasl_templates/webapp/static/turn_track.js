DEFAULT_TURN_TRACK_TURNS_MIN = 6 ;
DEFAULT_TURN_TRACK_TURNS_MAX = 10 ;

// NOTE: Reinforcement flags get clipped on turn 100, but this is unlikely to be an issue :-/
_MAX_TURN_TRACK_TURNS = 100 ;

gTurnTrackReinforcements = null ;
gTurnTrackShadings = null ;

gTurnTrackDlgState = null ;

// --------------------------------------------------------------------

function editTurnTrackSettings()
{
    // initialize
    var $dlg, $iframe, iframeSeqNo=0 ;
    // FUDGE! This should work as a local variable, but causes a weird problem where it doesn't get reset properly :-/
    gTurnTrackReinforcements = null ;
    gTurnTrackShadings = null ;

    function loadControls() {
        // load the dialog controls
        $dlg.find( "select[name='nturns']" ).val(
            $panel.find( "select[name='TURN_TRACK_NTURNS'].param" ).val()
        ).trigger("change" ) ;
        var width = $panel.find( "input[name='TURN_TRACK_WIDTH']" ).val() ;
        $dlg.find( "select[name='width']" ).val(
            isNaN( parseInt( width ) ) ? "" : width
        ).trigger( "change" ) ;
        $dlg.find( "input[name='vertical']" ).prop( "checked",
            $panel.find( "input[name='TURN_TRACK_VERTICAL']" ).prop( "checked" )
        ) ;
        $dlg.find( "input[name='swap-players']" ).prop( "checked",
            $panel.find( "input[name='TURN_TRACK_SWAP_PLAYERS']" ).prop( "checked" )
        ) ;
        // load the reinforcements
        var params = updatePreview( false ) ;
        var args = parseTurnTrackParams( params ) ;
        gTurnTrackReinforcements = { 1: args.reinforce1, 2: args.reinforce2 } ;
        gTurnTrackShadings = parseTurnTrackShadings( args.shadings ) ;
        // update the UI
        updateUI() ;
    }

    function onResetControls() {
        // reset all the controls
        ask( "Reset turn track", "Do you want to reset the turn track?", {
            ok: function() {
                setTurnTrackNTurns( DEFAULT_TURN_TRACK_TURNS_MIN ) ;
                $panel.find( "input[name='TURN_TRACK_WIDTH']" ).val( "" ) ;
                $panel.find( "input[name='TURN_TRACK_VERTICAL']" ).prop( "checked", false ) ;
                $panel.find( "input[name='TURN_TRACK_SWAP_PLAYERS']" ).prop( "checked", false ) ;
                $panel.find( "input[name='TURN_TRACK_SHADING']" ).val( "" ) ;
                $panel.find( "input[name='TURN_TRACK_REINFORCEMENTS_1']" ).val( "" ) ;
                $panel.find( "input[name='TURN_TRACK_REINFORCEMENTS_2']" ).val( "" ) ;
                gTurnTrackReinforcements = null ;
                gTurnTrackShadings = null ;
                loadControls() ;
            }
        } ) ;
    }

    function initTurnCountSelect2( $sel ) {
        // initialize the TURN COUNT droplist
        init_select2(
            $sel, "4em", false, formatTurnTrackOption
        ).on( "select2:open", function() {
            restrict_droplist_height( $(this) ) ;
        } ).on( "change", function() {
            setTurnTrackNTurns( $(this).val() ) ;
            if ( $dlg )
                updateUI() ;
        } ) ;
        for ( var nTurns=1 ; nTurns <= _MAX_TURN_TRACK_TURNS ; nTurns += 0.5 )
            $sel.append( $( "<option value='" + nTurns + "'>" + nTurns + "</option>" ) ) ;
    }
    function initWidthSelect2( $sel ) {
        // initialize the WIDTH droplist
        init_select2(
            $sel, "3.5em", false, null
        ).on( "select2:open", function() {
            restrict_droplist_height( $(this) ) ;
        } ).on( "change", function() {
            $panel.find( "input[name='TURN_TRACK_WIDTH']" ).val( $(this).val() ) ;
            if ( $dlg )
                updateUI() ;
        } ) ;
        $sel.append( $( "<option value=''>-</option>" ) ) ;
        for ( var i=1 ; i <= 30 ; ++i )
            $sel.append( $( "<option value='" + i + "'>" + i + "</option>" ) ) ;
    }

    function syncCheckbox( $elem, $target ) {
        // sync the target checkbox in the SCENARIO panel with the one in this dialog
        $target.prop( "checked", $elem.prop("checked") ) ;
        updateUI() ;
    }

    function updatePreview( showAllFlags ) {

        // generate the turn track snippet
        var params = unload_snippet_params( true, "turn_track" ) ;
        if ( showAllFlags )
            params.TURN_TRACK.REINFORCEMENTS_1 = params.TURN_TRACK.REINFORCEMENTS_2 = makeCommaList( _MAX_TURN_TRACK_TURNS ) ;
        params.TURN_TRACK_PREVIEW_MODE = true ;
        var $btn = $( "button.generate[data-id='turn_track']" ) ;
        var snippet = make_snippet( $btn, params, {}, false ).content ;

        // update the preview
        // NOTE: To minimize flickering, we load the snippet into a hidden <iframe>,
        // then replace the preview <iframe> with it.
        // FUDGE! We should be able to wait until the new iframe has finished loading before removing the old one,
        // but for some inexplicable reason, the remove doesn't work on Windows, and the iframe's just build up :-/
        // Instead, we remove the old iframe here, but by fiddling with opacity, we can avoid flicker. Sigh...
        var style = $iframe.attr( "style" ) ;
        style.opacity = 0 ;
        var $newFrame = $( "<iframe></iframe>", { style: style, "data-seqno": ++iframeSeqNo } ) ;
        $iframe.after( $newFrame ) ;
        $iframe.remove() ;
        $iframe = $newFrame ;
        $newFrame.attr( "srcdoc", snippet ).on( "load", function() {
            // update the state of each reinforcement flag
            for ( var turnNo=1 ; turnNo <= _MAX_TURN_TRACK_TURNS ; ++turnNo ) {
                for ( var playerNo=1 ; playerNo <= 2 ; ++playerNo )
                    updateFlag( turnNo, playerNo ) ;
            }
            // install the new <iframe>
            $newFrame.attr( "id", "turn-track-preview" ).css( "opacity", 1 ) ;
            // FUDGE! This works around a weird problem when we load a scenario with a vertical turn track
            // and show it in a turn track dialog that was previously showing a horizontal turn track :-/
            updateLayout() ;
        } ) ;

        return params ;
    }

    function onFlagClick( turnNo, playerNo ) {
        // NOTE: This method gets called by a click handler in the snippet HTML.
        // toggle the player turn reinforcements
        if ( gTurnTrackReinforcements[playerNo][turnNo] )
            delete gTurnTrackReinforcements[playerNo][turnNo] ;
        else
            gTurnTrackReinforcements[playerNo][turnNo] = true ;
        $panel.find( "input[name='TURN_TRACK_REINFORCEMENTS_" + playerNo + "']" ).val(
            Object.keys( gTurnTrackReinforcements[playerNo] ).join( "," )
        ) ;
        updateFlag( turnNo, playerNo ) ;
    }

    function onShadingClick( turnNo ) {
        // NOTE: This method gets called by a click handler in the snippet HTML.
        // toggle the turn track square's shading
        // determine the new shading strength
        var strength = gTurnTrackShadings[turnNo] || 0 ;
        var col ;
        if ( ++strength <= gAppConfig.TURN_TRACK_SHADING_COLORS.length ) {
            gTurnTrackShadings[turnNo] = strength ;
            col = gAppConfig.TURN_TRACK_SHADING_COLORS[ strength-1 ] ;
        } else {
            delete gTurnTrackShadings[turnNo] ;
            col = "inherit" ;
        }
        // update the saved setting
        var shadings = [] ;
        Object.keys( gTurnTrackShadings ).forEach( function( key ) {
            var strength = gTurnTrackShadings[key] ;
            for ( var i=1 ; i < strength ; ++i )
                key += "+" ;
            shadings.push( key ) ;
        } ) ;
        $panel.find( "input[name='TURN_TRACK_SHADING']" ).val( shadings.join( "," ) ) ;
        // update the turn square in the UI
        $iframe.contents().find( "#turn-square-" + turnNo ).css( { "background-color": col } ) ;
    }

    function updateFlag( turnNo, playerNo ) {
        // update the specified reinforcement flag
        $iframe.contents().find( "#flag-" + turnNo + "_" + flipPlayerNo2(playerNo) ).css( {
            opacity: gTurnTrackReinforcements && gTurnTrackReinforcements[playerNo][turnNo] ? 1 : 0.4,
        } ) ;
    }

    function updateUI() {
        // update the UI
        updateLayout() ;
        updatePreview( true ) ;
    }

    function updateLayout() {
        // update the layout based on the direction of the turn track
        if ( $dlg.find( "input[name='vertical']" ).prop( "checked" ) ) {
            // vertical layout
            $iframe.css( { position: "absolute",
                top: "18px", height: "calc(100% - 25px)", left: "170px", width: "calc(100% - 160px)"
            } ) ;
            $dlg.addClass( "vert" ).removeClass( "horz" ) ;
            $dlg.find( ".controls" ).addClass( "vert" ).removeClass( "horz" ) ;
            $dlg.find( ".reset1" ).hide() ;
            $dlg.find( ".reset2" ).show() ;
        } else {
            // horizontal layout
            $iframe.css( { position: "absolute",
                top: "110px", height: "calc(100% - 120px)", left: "18px", width: "calc(100% - 33px)"
            } ) ;
            $dlg.addClass( "horz" ).removeClass( "vert" ) ;
            $dlg.find( ".controls" ).addClass( "horz" ).removeClass( "vert" ) ;
            $dlg.find( ".reset1" ).show() ;
            $dlg.find( ".reset2" ).hide() ;
        }
    }

    // NOTE: Since Player 1 in the UI is Player 2 in the Turn Track template (by default),
    // and vice versa, we often need to flip the player numbers.
    function flipPlayerNo( playerNo ) { return parseInt(playerNo) === 1 ? 2 : 1 ; }
    function flipPlayerNo2( playerNo ) {
        if ( ! $panel.find("input[name='TURN_TRACK_SWAP_PLAYERS']").prop( "checked" ) )
            playerNo = flipPlayerNo( playerNo ) ;
        return playerNo ;
    }

    function makeCommaList( nVals ) {
        // generate a comma-separated list of values
        var vals = [] ;
        for ( var i=1 ; i <= nVals ; ++i )
            vals.push( i ) ;
        return vals.join( "," ) ;
    }

    // show the TURN TRACK dialog
    var $panel = $( "#panel-scenario" ) ;
    $( "#turn-track" ).dialog( {
        "title": "Turn track",
        dialogClass: "turn-track",
        modal: true,
        position: gTurnTrackDlgState ? gTurnTrackDlgState.position : { my: "center", at: "center", of: window },
        width: gTurnTrackDlgState ? gTurnTrackDlgState.width : $(window).width() * 0.8,
        height: gTurnTrackDlgState ? gTurnTrackDlgState.height : $(window).height() * 0.5,
        minWidth: 500, minHeight: 280,
        resizable: true,
        create: function() {
            // initialize the dialog
            init_dialog( $(this), "OK", true ) ;
            initTurnCountSelect2( $(this).find( "select[name='nturns']" ) ) ;
            initWidthSelect2( $(this).find( "select[name='width']" ) ) ;
            $(this).find( "button.reset" ).button().on(
                "click", onResetControls
            ) ;
            // keep the settings in the SCENARIO panel in sync with the dialog
            $(this).find( "input[name='vertical']" ).on( "change", function() {
                syncCheckbox( $(this), $panel.find("input[name='TURN_TRACK_VERTICAL']") ) ;
            } ) ;
            $(this).find( "input[name='swap-players']" ).on( "change", function() {
                syncCheckbox( $(this), $panel.find("input[name='TURN_TRACK_SWAP_PLAYERS']") ) ;
            } ) ;
            // update the UI when the direction of the turn track is changed
            $(this).find( "input[name='vertical']" ).on( "change", function() {
                updateUI() ;
            } ) ;
            // handle clicks on reinforcement flags in the turn track preview
            window.addEventListener( "message", function( evt ) {
                if ( evt.data.type === "FlagClick" )
                    onFlagClick( evt.data.turnNo, flipPlayerNo2(evt.data.uiPlayerNo) ) ;
                else if ( evt.data.type === "ShadingClick" )
                    onShadingClick( evt.data.turnNo ) ;
            } ) ;

        },
        open: function() {
            // initialize the dialog
            var $btnPane = $( ".ui-dialog.turn-track .ui-dialog-buttonpane" ) ;
            var $btn = $btnPane.find( "button.snippet" ) ;
            $btn.prepend(
                $( "<img src='" + gImagesBaseUrl+"/snippet.png" + "' style='height:0.9em;margin:0 0 -2px -2px;'>" )
            ) ;
            $btn.css( { position: "absolute", left: 15 } ) ;
            // load the dialog
            $dlg = $(this) ;
            $iframe = $dlg.find( "iframe#turn-track-preview" ) ;
            loadControls() ;
        },
        beforeClose: function() {
            gTurnTrackDlgState = getDialogState( $(this) ) ;
        },
        buttons: {
            Snippet: { text:" Snippet", class: "snippet", click: function( evt ) {
                var $btn = $( "button.generate[data-id='turn_track']" ) ;
                generate_snippet( $btn, evt.shiftKey, null ) ;
            } },
            Close: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// --------------------------------------------------------------------

function setTurnTrackNTurns( nTurns )
{
    // select the specified number of turns
    updateTurnTrackNTurns( nTurns ) ;
    $( "select[name='TURN_TRACK_NTURNS']" ).val(
        nTurns
    ).trigger( "change" ) ;
}

function updateTurnTrackNTurns( nTurns )
{
    function makeExtraOption( val, caption ) {
        return $( "<option class='extra' value='" + val + "'>" + caption + "</option>" ) ;
    }

    // initialize
    var $sel = $( "select[name='TURN_TRACK_NTURNS']" ) ;
    var $extra = $sel.find( "option.extra" ) ;

    // check if the specified number of turns is already in the droplist
    var $opt = $sel.find( "option[value='" + nTurns + "']" ) ;
    if ( $opt.length > 0 ) {
        // yup - check if it's the special extra entry
        if ( ! $opt.hasClass( "extra" ) ) {
            // nope - we don't need it any more
            $extra.remove() ;
        }
        // check if the turn track has been disabled
        if ( nTurns === "" ) {
            // yup - add a special extra entry to open the turn track dialog
            $sel.append( makeExtraOption( "(show-dialog)", "(more)" ) ) ;
        }
    } else {
        // nope - add it as a special extra entry
        if ( $extra.length > 0 ) {
            // FUDGE! If the special entry is already there, we delete and re-create it to get the select2 to work :-/
            $extra.remove() ;
        }
        var $opt2 = makeExtraOption( nTurns, nTurns ) ;
        if ( nTurns < DEFAULT_TURN_TRACK_TURNS_MIN )
            $sel.find( "option[value='']" ).after( $opt2 ) ;
        else
            $sel.append( $opt2 ) ;
    }
}

function parseTurnTrackShadings( shadings ) {
    // NOTE: A turn track shading setting consists of a number (the turn number),
    // followed by 0 or more plus signs (to indicate a darker shading color).
    var shadingTable = {} ;
    shadings.forEach( function( shading ) {
        var strength = 1 ;
        while ( shading.length > 0 && shading.substr( shading.length-1 ) === "+" ) {
            strength += 1 ;
            shading = shading.substr( 0, shading.length-1 ) ;
        }
        if ( strength > gAppConfig.TURN_TRACK_SHADING_COLORS.length )
            return ;
        var turnNo = parseInt( shading ) ;
        if ( isNaN( turnNo ) )
            return ;
        shadingTable[turnNo] = strength ;
    } ) ;
    return shadingTable ;
}

function formatTurnTrackOption( opt ) {
    // format the turn track <option> element
    if ( opt.id === "(show-dialog)" )
        return $( "<span style='font-size:80%;font-style:italic;color:#666;'>" + opt.text + "</span>" ) ;
    if ( opt.text.substr( opt.text.length-2 ) === ".5" )
        return $( "<span>" + opt.text.substr( 0, opt.text.length-2 ) + "&half;" + "</span>" ) ;
    return opt.text ;
}
