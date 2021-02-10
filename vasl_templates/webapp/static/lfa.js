/* jshint esnext: true */

( function() { // nb: put the entire file into its own local namespace, global stuff gets added to window.

// --------------------------------------------------------------------

var DEFAULT_PLAYER_COLORS = [
    "#00ff00", // nb: this is for the "expected results" line graph
    "#479dd6", "#c48718", "#cf75c9", "#5fd760"
] ;

var DR_VALS = {
    "DR": [ 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12 ],
    "dr": [ 1, 2, 3, 4, 5, 6 ],
} ;

var DR_CLASS_IDS = { DR: ".d6x2", dr: ".d6x1" } ;

var ROLL_TYPES = {
    "IFT": "IFT",
    "MC": "Morale Check",
    "Rally": "Rally",
    "TH": "To Hit",
    "TK": "To Kill",
    "CC": "Close Combat",
    "SA": "Sniper Activation",
    "TC": "Task Check",
    "RS": "Random Selection",
    "Other": "Other",
} ;

var MOVING_AVERAGE_WINDOW_SIZES = [ 5, 10, 20, 50, 100 ] ;
var PREFERRED_WINDOW_SIZE = 20 ;
var MAX_TIME_PLOT_SPACING = 40 ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

// NOTE: We store this information in globals so that ChartJS callbacks use the latest data (even if
// it has been re-generated after the user has changed the roll type filter), not what was active
// when the charts were first created (because it was captured by an enclosure).

// data extracted from a log file
var gRawResponseData, gLogFileAnalysis, gLfaStats, gTimePlotEvents ;
var gPlayerColorIndex={} ;

// these map ChartJS dataset index's to player ID's
var gDistribDatasetPlayerIndex={}, gPieDatasetPlayerIndex={}, gTimePlotDatasetPlayerIndex, gHotnessPlayerIndex ;

// ChartJS chart objects
var gDistribCharts={}, gPieCharts={}, gTimePlotChart, gHotnessChart ;

var $gDialog ;
var $gBanner, $gHotness, $gHotnessPopup, $gSelectFilePopup, $gOptions, $gRollTypeDropList, $gDistribLineGraphsCheckBox, $gStackBarGraphsCheckBox ;
var $gPlayerColorsButton, $gPlayerColorsPopup ;
var $gTimePlot, $gTimePlotChartWrapper ;
var $gTimePlotOptions, $gMovingAverageDropList, $gTimePlotZoomInButton, $gTimePlotZoomOutButton ;

var gEventHandlers, gIsInitialLoad ;
var gHotnessBorderColor, gTimePlotValOffset, gTimePlotZoom ;

var gShowTabularData ; // nb: for testing porpoises

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

// NOTE: Adding keyboard shortcuts was ridiculously complicated >:-/ The problem was that selectmenu's
// were processing key-presses, even if the Alt key was down, and selecting any option that started
// with that letter e.g. pressing Alr-R to activate the Roll Types droplist would also select "Rally".
// Adding a keydown handler to the selectmenu to ignore these events worked, unless the droplist
// already had focus. The only way I could get things to work properly was to change the selectmenu's
// prototype (!) and ignore events there :wtf:

SHORTCUT_HANDLERS = {
    82: function () { // "R"
        $gOptions.css( "opacity", 1.0 ) ;
        $gRollTypeDropList.selectmenu("instance").button.focus() ;
    },
    71: function () { // "G"
        $gMovingAverageDropList.selectmenu("instance").button.focus() ;
    },
    88: function () { // "X"
        var $elem = $gBanner.find( ".select-file" ) ;
        if ( $elem.css( "display" ) != "none" )
            $gBanner.find( ".select-file" ).click() ;
    },
    50: function() { // "2"
        $( "#lfa .hotness img.dice" ).click() ;
    },
} ;

gPrevSelectMenuKeyDownHandler = $.ui.selectmenu.prototype._buttonEvents.keydown ;
$.ui.selectmenu.prototype._buttonEvents.keydown = function( evt ) {
    if ( evt.altKey && SHORTCUT_HANDLERS[evt.keyCode] )
        return ;
    gPrevSelectMenuKeyDownHandler.call( this, evt ) ;
} ;

const gOptionsNormalOpacity = 0.5 ;
function restoreOptionsOpacity() { $gOptions.css( "opacity", gOptionsNormalOpacity ) ; }

// --------------------------------------------------------------------

window.show_lfa_dialog = function( resp )
{
    // save a copy of the raw response data
    gRawResponseData = resp ;

    function closeDialog() { $gDialog.dialog( "close" ) ; }

    function onKeyDown( evt ) {
        if ( evt.keyCode == $.ui.keyCode.ESCAPE ) {
            if ( evt.shiftKey ) {
                // NOTE: Since analyzing a log file is a lengthy process, we make it harder
                // to accidentally close the dialog (need to Shift-Escape).
                closeDialog() ;
            } else {
                // NOTE: However, we allow ESCAPE to close popups.
                closeAllPopupsAndDropLists() ;
                restoreOptionsOpacity() ;
            }
        }
    }
    function fixupDropListOptions( $dropList ) {
        // fixup styling for droplist items
        var id = $dropList.attr( "id" ) ;
        $( "#" + id + "-menu" ).find( ".ui-menu-item" ).each( function() {
            $(this).css( { "font-size": "80%" } ) ;
        } ) ;
    }

    // initialize user settings
    if ( ! gUserSettings.lfa )
        gUserSettings.lfa = {} ;
    if ( ! gUserSettings.lfa[ "player-colors" ] )
        gUserSettings.lfa[ "player-colors" ] = DEFAULT_PLAYER_COLORS.slice() ;

    // show the main window (implemented as a dialog)
    gEventHandlers = new jQueryHandlers() ;
    $( "#lfa" ).dialog( {
        dialogClass: "lfa",
        modal: true,
        resizable: false,
        // NOTE: We handle ESCAPE ourself, handle_escape() has an exception for this dialog.
        closeOnEscape: false,
        create: function() {
            // initialize the splitter
            Split( [ "#lfa .top-pane", "#lfa .bottom-pane" ], {
                direction: "vertical",
                sizes: [ 60, 40 ],
                minSize: [ 350, 200 ], /* nb: this needs to be set in the CSS as well */
                gutterSize: 3,
                onDrag: updateLayout,
            } ) ;
            var $gripper = $( "<img src='" + gImagesBaseUrl + "/gripper-horz.png'>" ) ;
            $( "#lfa .gutter.gutter-vertical" ).append( $gripper ) ;
            // initialize other controls
            $(this).find( "select[name='roll-type']" ).selectmenu( {
                width: 70,
                open: function() { fixupDropListOptions( $(this) ) ; },
            } ) ;
            $(this).find( "select[name='moving-average']" ).selectmenu( {
                width: 55,
                open: function() { fixupDropListOptions( $(this) ) ; },
            } ) ;
            $(this).find( "button.download" ).button() ;
            $(this).find( "button.player-colors" ).button() ;
            $(this).find( "button.zoom-in" ).button() ;
            $(this).find( "button.zoom-out" ).button() ;
        },
        open: function() {
            $gDialog = $(this) ;
            gEventHandlers.addHandler( $("#lfa .ui-dialog-titlebar-close"), "click", closeDialog ) ;
            gEventHandlers.addHandler( $(document), "keydown", onKeyDown ) ;
            loadDialog() ;
        },
        close: function() {
            // NOTE: We explicitly close everything so that they aren't visible next time we open.
            closeAllPopupsAndDropLists() ;
            // clean up handlers
            gEventHandlers.cleanUp() ;
            // clean up charts
            for ( var key in gDistribCharts )
                gDistribCharts[key].destroy() ;
            for ( key in gPieCharts )
                gPieCharts[key].destroy() ;
            gTimePlotChart.destroy() ;
            gHotnessChart.destroy() ;
        },
    } ) ;
} ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function loadDialog()
{
    // initialize
    gShowTabularData = getUrlParam( "lfa_tables" ) ;
    gIsInitialLoad = true ;
    var i ;

    // initialize
    $gBanner = $( "#lfa .banner" ) ;
    $gHotness = $( "#lfa .hotness" ).hide() ;
    $gHotnessPopup = $( "#lfa .hotness-popup" ) ;
    $gSelectFilePopup = $( "#lfa .select-file-popup" ) ;
    $gOptions = $( "#lfa .options" ) ;
    $gRollTypeDropList = $( "#lfa select[name='roll-type']" ) ;
    $gDistribLineGraphsCheckBox = $( "#lfa input[name='distrib-line-graphs']" ).prop(
        "checked", gUserSettings.lfa["distrib-line-graphs"]
    ) ;
    $gStackBarGraphsCheckBox = $( "#lfa input[name='stack-bar-graphs']" ).prop(
        "checked", gUserSettings.lfa["stack-bar-graphs"]
    ) ;
    $gPlayerColorsButton = $( "#lfa .options .player-colors" ) ;
    $gPlayerColorsPopup = $( "#lfa .player-colors-popup" ) ;
    $gDisableAnimationsCheckBox = $( "#lfa input[name='disable-animations']" ).prop(
        "checked", gUserSettings["disable-animations"]
    ) ;
    $gTimePlot =  $( "#lfa .time-plot" ) ;
    $gTimePlotChartWrapper = $( "#lfa .time-plot .wrapper" ) ;
    $gTimePlotOptions = $( "#lfa .time-plot-options" ) ;
    $gMovingAverageDropList = $( "#lfa select[name='moving-average']" ) ;
    $gTimePlotZoomInButton = $( "#lfa .time-plot-options .zoom-in" ) ;
    $gTimePlotZoomOutButton = $( "#lfa .time-plot-options .zoom-out" ) ;

    // analyze the log files
    gLogFileAnalysis = new LogFileAnalysis( gRawResponseData, -1 ) ;
    var rollTypes = gLogFileAnalysis.getRollTypes() ;

    // initialize the hotness popup
    initHotnessPopup() ;

    // initialize the player colors
    var prevColorsLen = gUserSettings.lfa[ "player-colors" ].length ; // nb: this includes the "expected results" color
    gLogFileAnalysis.forEachPlayer( function( playerId, playerNo ) {
        if ( playerNo >= prevColorsLen-1 ) {
            // NOTE: We have more players than colors - create a new player color based on what we have
            gUserSettings.lfa["player-colors"].push(
                gUserSettings.lfa["player-colors"][ 1 + (playerNo % (prevColorsLen-1)) ]
            ) ;
        }
        gPlayerColorIndex[ playerId ] = 1 + playerNo ;
    } ) ;
    if ( gUserSettings.lfa["player-colors"].length > prevColorsLen )
        save_user_settings() ;

    // initialize the file selection popup
    initSelectFilePopup() ;
    if ( gLogFileAnalysis.logFiles.length > 1 )
        $gBanner.find( ".select-file" ).show() ;
    else
        $gBanner.find( ".select-file" ).hide() ;

    // create the charts
    for ( var key in DR_CLASS_IDS ) {
        gDistribCharts[ key ] = createDistribChart( key, DR_CLASS_IDS[key] ) ;
        gPieCharts[ key ] = createPieChart( key, DR_CLASS_IDS[key] ) ;
    }
    gTimePlotChart = createTimePlotChart() ;
    gHotnessChart = createHotnessChart() ;
    gHotnessBorderColor = $gHotness.css( "border-top-color" ) ;

    // load the roll types
    var buf = [ "<option value=''>", "All", "</option>" ] ;
    function addRollType( rollType ) {
        buf.push( "<option value='"+rollType+"'>", rollType, "</option>" ) ;
    }
    for ( key in ROLL_TYPES )
        addRollType( key ) ;
    rollTypes.forEach( function( rollType ) {
        if ( ! ROLL_TYPES[ rollType ] )
            addRollType( rollType ) ;
    } ) ;
    $gRollTypeDropList.html( buf.join("") ).selectmenu( "refresh" ) ;
    gEventHandlers.addHandler( $gRollTypeDropList, "selectmenuchange", reloadAll ) ;

    // add a click handler for distrib line graphs
    gEventHandlers.addHandler( $gDistribLineGraphsCheckBox, "click", function() {
        // update the UI
        var isChecked = $(this).is( ":checked" ) ;
        for ( var key in DR_VALS ) {
            for ( var i=0 ; i < gDistribCharts[key].data.datasets.length-1 ; ++i )
                gDistribCharts[key].data.datasets[i].type = isChecked ? "line" : "bar" ;
            gDistribCharts[key].options.animation.duration = $gDisableAnimationsCheckBox.is( ":checked" ) ? 0 : 1000 ;
            gDistribCharts[key].update() ;
        }
        // save the new setting
        gUserSettings.lfa["distrib-line-graphs"] = isChecked ;
        save_user_settings() ;
    } ) ;

    // add a click handler for stacked bar graphs
    gEventHandlers.addHandler( $gStackBarGraphsCheckBox, "click", function() {
        // update the UI
        var isChecked = $(this).is( ":checked" ) ;
        for ( var key in DR_VALS ) {
            gDistribCharts[key].options.scales.xAxes[0].stacked = isChecked ;
            gDistribCharts[key].options.animation.duration = $gDisableAnimationsCheckBox.is( ":checked" ) ? 0 : 1000 ;
            gDistribCharts[key].update() ;
        }
        // save the new setting
        gUserSettings.lfa["stack-bar-graphs"] = isChecked ;
        save_user_settings() ;
    } ) ;

    // add a click handler for enabling/disabling animations
    gEventHandlers.addHandler( $gDisableAnimationsCheckBox, "click", function() {
        // save the new setting
        gUserSettings["disable-animations"] = $(this).is( ":checked" ) ;
        save_user_settings() ;
    } );

    // add a handler for the moving average window size
    gEventHandlers.addHandler( $gMovingAverageDropList, "selectmenuchange", function() {
        updateTimePlotChart( null ) ;
    } ) ;

    // add handlers to zoom the time-plot chart in and out
    gEventHandlers.addHandler( $gTimePlotZoomInButton, "click", function( evt ) {
        zoomTimePlotChart( evt.ctrlKey ? null : +1 ) ;
    } ) ;
    gEventHandlers.addHandler( $gTimePlotZoomOutButton, "click", function( evt ) {
        zoomTimePlotChart( evt.ctrlKey ? null : -1 ) ;
    } ) ;

    // add a click handler to download the data
    gEventHandlers.addHandler( $("#lfa .options button.download"), "click", onDownloadData ) ;

    // initialize the color pickers
    initPlayerColorsConfig() ;

    // preload the die images
    [ "yellow", "white" ].forEach( function( color ) {
        for ( i=1 ; i <= 6 ; ++i )
            $.get( makeDieImageUrl( i, color ) ) ;
    } ) ;

    // handle window resizing
    gEventHandlers.addHandler( $(window), "resize", function() {
        closeAllPopupsAndDropLists() ;
        updateLayout() ;
    } ) ;

    // add keyboard shortcut handlers
    gEventHandlers.addHandler( $(document), "keydown", function( evt ) {
        var handler = SHORTCUT_HANDLERS[ evt.keyCode ] ;
        if ( evt.altKey && handler ) {
            closeAllPopupsAndDropLists() ;
            handler( evt ) ;
        }
    } ) ;

    // NOTE: We used to get the options panel to fade in and out as the mouse moves over it via opacity CSS.
    // However, when we added keyboard shortcuts, we temporarily set the opacity to 1.0 if the Roll Type droplist
    // is requested, but we can't set it back since we can't set CSS pseudo-selectors (:hover) in Javascript :-/
    // So, we dropped the :hover CSS and always do it via mouse enter/leave events.
    gEventHandlers.addHandler( $gOptions, "mouseenter", function() { $(this).css("opacity",1.0) ; } ) ;
    gEventHandlers.addHandler( $gOptions, "mouseleave", restoreOptionsOpacity ) ;
    // NOTE: We also need to restore opacity after the Roll Types droplist has been used/dismissed.
    gEventHandlers.addHandler( $gRollTypeDropList, "selectmenuclose", restoreOptionsOpacity ) ;
    gEventHandlers.addHandler( $gRollTypeDropList.selectmenu("instance").button, "focusout", restoreOptionsOpacity ) ;
    restoreOptionsOpacity() ;

    // load the charts with data
    Chart.defaults.global.defaultFontColor = "#444" ;
    reloadAll() ;

    // set initial focus
    $gRollTypeDropList.focus() ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function initHotnessPopup()
{
    function makeReport() {

        // initialize
        var rolls={}, snipers={} ;
        gLogFileAnalysis.forEachPlayer( function( playerId, playerNo ) {
            rolls[ playerId ] = {} ;
            for ( var rollType in ROLL_TYPES )
                rolls[ playerId ][ rollType ] = { 2: 0, 12: 0 } ;
            snipers[ playerId ] = { 1: 0, 2: 0 } ;
        } ) ;

        // count how many 2's and 12's were rolled, and Sniper Activations
        gLogFileAnalysis.extractEvents( 1, {
            onRollEvent: function( evt ) {
                var rollTotal = LogFileAnalysis.rollTotal( evt.rollValue ) ;
                if ( evt.rollType == "SA" && ( rollTotal == 1 || rollTotal == 2 ) )
                    ++ snipers[ evt.playerId ][ rollTotal ] ;
                else if ( ! LogFileAnalysis.isSingleDie( evt.rollValue ) && ( rollTotal == 2 || rollTotal == 12 ) )
                    ++ rolls[ evt.playerId ][ evt.rollType ][ rollTotal ] ;
            }
        } ) ;

        // figure out which roll types had at least one 2 or 12
        var rollTypesToShow = {} ;
        gLogFileAnalysis.forEachPlayer( function( playerId, playerNo ) {
            for ( var rollType in ROLL_TYPES ) {
                if ( rolls[playerId][rollType][2] > 0 || rolls[playerId][rollType][12] > 0 )
                    rollTypesToShow[ rollType ] = true ;
            }
        } ) ;

        // add the 2's and 12's to the report
        var buf = [] ;
        function addRollReport( tableClass, die1, die2 ) {
            // add the header
            buf.push( "<table class='" + tableClass + "'>" ) ;
            buf.push( "<tr>", "<td class='icon'>",
                "<img src='" + makeDieImageUrl( die1, "yellow" ) + "' class='die'>",
                "<img src='" + makeDieImageUrl( die2, "white" ) + "' class='die'>"
            ) ;
            for ( var rollType in ROLL_TYPES ) {
                if ( rollTypesToShow[ rollType ] )
                    buf.push( "<th>", rollType ) ;
            }
            gLogFileAnalysis.forEachPlayer( function( playerId, playerNo ) {
                buf.push( "<tr>", "<td class='player'>", makePlayerNameHTML(playerId) ) ;
                for ( var rollType in ROLL_TYPES ) {
                    if ( ! rollTypesToShow[ rollType ] )
                        continue ;
                    var nRollTypes = rolls[ playerId ][ rollType ][ die1+die2 ] ;
                    buf.push( "<td class='val'>", nRollTypes === 0 ? "-" : nRollTypes ) ;
                }
            } ) ;
            buf.push( "</table>" ) ;
        }
        addRollReport( "2s", 1, 1 ) ;
        addRollReport( "12s", 6, 6 ) ;

        // add a divider
        buf.push(
            "<div style='height:0.25em;border-bottom:1px dotted #aaa;'>&nbsp;</div>",
            "<div style='height:0.75em;'>&nbsp;</div>"
        ) ;

        // add the Sniper Activations to the report
        buf.push( "<table class='snipers'>" ) ;
        buf.push( "<tr>", "<td class='icon'>",
            "<img src='" + gImagesBaseUrl+"/sniper.png" + "' class='sniper'>",
            "<th>", "dr 1", "<th>", "dr 2"
        ) ;
        gLogFileAnalysis.forEachPlayer( function( playerId, playerNo ) {
            buf.push( "<tr>", "<td class='player'>", makePlayerNameHTML(playerId) ) ;
            [ 1, 2 ].forEach( function( val ) {
                var nActivations = snipers[ playerId ][ val ] ;
                buf.push( "<td class='val'>", nActivations === 0 ? "-" : nActivations ) ;
            } ) ;
        } ) ;
        buf.push( "</table>" ) ;

        // generate the report
        return buf.join( "" ) ;
    }

    function makePlayerNameHTML( playerId ) {
        return escapeHTML( gLogFileAnalysis.playerName( playerId )  ) ;
    }

    // add a click handler for the hotness popup
    var $elem = $( "#lfa .hotness img.dice" ) ;
    gEventHandlers.addHandler( $elem, "click", function( evt ) {
        closeAllPopupsAndDropLists() ;
        // NOTE: We have to re-generate the report each time it's shown, since the user
        // may have chosen a different set of log files.
        $gHotnessPopup.html( makeReport() ).show() ;
        var maxWidth = 0 ;
        $gHotnessPopup.find( "table" ).each( function() {
            maxWidth = Math.max( $(this).outerWidth() , maxWidth ) ;
        } ) ;
        $gHotnessPopup.css( { width: maxWidth } ) ;
        $gHotnessPopup.position( {
            my: "right top", at: "left-5 top+2", of: $elem, collision: "fit"
        } ) ;
        stopEvent( evt ) ;
    } ) ;

    // handle clicks outside the popup (to dismiss it)
    // NOTE: We do this by adding a click handler to the main dialog window, and a click handler
    // to the popup that prevents the event from bubbling up i.e. if the main dialog window receives
    // a click event, it must've been outside the popup window.
    gEventHandlers.addHandler( $gHotnessPopup, "click", function() {
        return false ;
    } ) ;
    gEventHandlers.addHandler( $("#lfa"), "click", function() {
        $gHotnessPopup.hide() ;
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function initSelectFilePopup()
{
    // initialize the file selection popup
    var buf = [] ;
    function addRadioButton( val, caption ) {
        buf.push( "<div class='row'>",
            "<input type='radio' value='" + val + "' name='select-file-radio-group'>",
            "<label>", caption, "</label>",
            "</div>"
        ) ;
    }
    addRadioButton( -1, "All files" )  ;
    for ( i=0 ; i < gLogFileAnalysis.logFiles.length ; ++i )
        addRadioButton( i, gLogFileAnalysis.logFiles[i] ) ;
    $gSelectFilePopup.html( buf.join("") ).hide() ;
    var $currSel = $gSelectFilePopup.find( "input[type='radio']" ).first() ;

    // handle a new log file being selected
    // FUDGE! Normally we would call this handler when the "change" event fires on a radio button,
    // but we have to hack around some problems with the "click outside the popup to dismiss it" feature,
    // and so we call it manually ourself elsewhere.
    function selectNewLogFile( $radio ) {
        $currSel = $radio ;
        gLogFileAnalysis = new LogFileAnalysis( gRawResponseData, $radio.val() ) ;
        $gSelectFilePopup.hide() ;
        reloadAll() ;
    }
    function onFileSelected( $radio, evt ) {
        if ( evt.clientX === 0 && evt.clientY === 0 )
            return ; // nb: this selection was done via the keyboard
        selectNewLogFile( $radio ) ;
    }
    function selectFocusRadioButton() {
        // FUDGE! We can't rely on the timing of event processing, so we give the UI a bit of time
        // to catch up before checking which radio button has focus.
        setTimeout( function() {
            var $radio = $gSelectFilePopup.find( "input[type='radio']:focus" ) ;
            $radio.prop( "checked", true ) ;
        }, 10 ) ;
    }
    gEventHandlers.addHandler( $gSelectFilePopup, "keydown", function( evt ) {
        if ( evt.keyCode == 13 )
            selectNewLogFile( $gSelectFilePopup.find( "input[type='radio']:focus" ) ) ;
        else if ( evt.keyCode == $.ui.keyCode.HOME ) {
            $gSelectFilePopup.find( "input[type='radio']" ).first().focus() ;
            selectFocusRadioButton() ;
        }
        else if ( evt.keyCode == $.ui.keyCode.END ) {
            $gSelectFilePopup.find( "input[type='radio']" ).last().focus() ;
            selectFocusRadioButton() ;
        }
        else if ( evt.keyCode == $.ui.keyCode.UP || evt.keyCode == $.ui.keyCode.DOWN || evt.keyCode == $.ui.keyCode.LEFT || evt.keyCode == $.ui.keyCode.RIGHT ) {
            // FUDGE! The browser will move the focus rectangle, but we want
            // the radio button to become actually selected.
            selectFocusRadioButton() ;
        }
    } ) ;

    // FUDGE! Make the labels clickable as well.
    $gSelectFilePopup.find( ".row" ).each( function( evt ) {
        gEventHandlers.addHandler( $(this).children( "label" ), "click", function( evt ) {
            onFileSelected( $(this).parent().children( "input[type='radio']" ), evt ) ;
        } ) ;
    } ) ;

    // add a click handler to open the file selection popup
    gEventHandlers.addHandler( $gBanner.find( ".select-file" ), "click", function( evt ) {
        // show the popup
        closeAllPopupsAndDropLists() ;
        $gSelectFilePopup.show().position( {
            my: "right top", at: "right+3 bottom+5", of: $(this), collision: "fit"
        } ) ;
        $currSel.prop( "checked", true ).focus() ;
        stopEvent( evt ) ;
    } ) ;

    // handle clicks outside the popup (to dismiss it)
    // NOTE: We do this by adding a click handler to the main dialog window, and a click handler
    // to the popup that prevents the event from bubbling up i.e. if the main dialog window receives
    // a click event, it must've been outside the popup window.
    // Unfortunately, this messes up the operation of radio buttons, so we have to manage them ourself :-/
    gEventHandlers.addHandler( $gSelectFilePopup, "click", function() {
        return false ;
    } ) ;
    gEventHandlers.addHandler( $("#lfa"), "click", function() {
        $gSelectFilePopup.hide() ;
    } ) ;
    gEventHandlers.addHandler( $gSelectFilePopup.find( "input[type='radio']" ), "click", function( evt ) {
        // FUDGE! We have to handle clicks on the radio button ourself :-/
        onFileSelected( $(this), evt ) ;
        return false ;
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function initPlayerColorsConfig()
{
    // NOTE: This works around a gnarly problem with how we interact with the Spectrum color pickers.
    // We want to auto-close the popup dialog when a color picker is closed (whether the changes
    // were accepted or cancelled), *unless* the user is opening another color picker. In this case,
    // Spectrum automatically closes the color picker and opens the new one, but we don't want to close
    // our popup.
    // In the normal case (user opens a color picker, does stuff, then closes it), we get these events:
    //   BEFORE SHOW ; SHOW ; ... ; HIDE
    // If the user opens a color picker while another one is already on-screen, we get:
    //   BEFORE SHOW ; HIDE ; SHOW ; ...
    var isBeforeShowActive = false ;

    // initialize the color pickers
    function initColorPicker( colorPickerNo, playerId, caption, style ) {
        var buf = [ "<div class='row'>",
            "<input class='color-picker player" + colorPickerNo + "'></input>",
            "<span class='caption'>", caption, "</span>",
            "</div>"
        ] ;
        var $elem = $( buf.join("") ).attr( "data-playerId", playerId ) ;
        if ( style )
            $elem.css( style ) ;
        $gPlayerColorsPopup.append( $elem ) ;
        $elem = $gPlayerColorsPopup.find( ".color-picker.player" + colorPickerNo ) ;
        $elem.spectrum( {
            color: playerId === ":expected:" ? gUserSettings.lfa["player-colors"][0] : gUserSettings.lfa["player-colors"][gPlayerColorIndex[playerId]],
            chooseText: "OK",
            cancelText: "Cancel",
            clickoutFiresChange: false,
            move: function( color ) { updateChartColors( playerId, color.toHexString() ) ; },
            beforeShow: function() { isBeforeShowActive=true ; },
            show: function() {
                $(this).attr( "data-prev-color", $(this).spectrum("get").toHexString() ) ;
                isBeforeShowActive = false ;
            },
            hide: function( color ) {
                // NOTE: We get this event when the color-picker is closed, regardless of whether a new color
                // was picked or not. If it was accepted, we get the new color, if it was cancelled, we get the old one,
                // so either way, we want to update the chart colors and save the color.
                color = color.toHexString() ;
                updateChartColors( playerId, color ) ;
                var colorIndex = playerId === ":expected:" ? 0 : gPlayerColorIndex[playerId] ;
                gUserSettings.lfa["player-colors"][ colorIndex ] = color ;
                save_user_settings() ;
                if ( ! isBeforeShowActive )
                    $gPlayerColorsPopup.hide() ;
                $(this).attr( "data-prev-color", null ) ;
            },
        } ) ;
    }
    $gPlayerColorsPopup.hide().empty() ;
    gLogFileAnalysis.forEachPlayer( function( playerId, playerNo ) {
        initColorPicker( 1+playerNo, playerId, gLogFileAnalysis.playerName(playerId)) ;
    } ) ;
    initColorPicker( 0, ":expected:", "expected results", {"border-top":"1px dotted #aaa","padding-top":"0.75em"} ) ;

    // add a click handler to open the player colors popup
    gEventHandlers.addHandler( $gPlayerColorsButton, "click", function( evt ) {
        // show the popup
        closeAllPopupsAndDropLists() ;
        $gPlayerColorsPopup.find( ".row" ).each( function() {
            // NOTE: Because the set of players can change over time (e.g. if multiple log files are analyzed
            // that have different players in them, and the user switches between them), we want to only show
            // color pickers for the players currently on-screen. If we re-create the color pickers each time
            // the popup opens, this could result in the color assigned to each player changing, so instead,
            // we create color pickers for *all* players once at startup, then show/hide them as necessary.
            var playerId = $(this).attr( "data-playerId" ) ;
            if ( gLogFileAnalysis.playerIds().indexOf( playerId ) !== -1 || playerId === ":expected:" )
                $(this).show() ;
            else
                $(this).hide() ;
        } ) ;
        var leftPos = $gPlayerColorsButton.offset().left - 6 ;
        $gPlayerColorsPopup.css( {
            position: "absolute",
            left: Math.min( leftPos, $gDialog.innerWidth() - $gPlayerColorsPopup.outerWidth() ),
            top: $gPlayerColorsButton.offset().top + $gPlayerColorsButton.height() + 5,
        } ).show() ;
        stopEvent( evt ) ;
    } ) ;

    // handle clicks outside the popup (to dismiss it)
    // NOTE: We do this by adding a click handler to the main dialog window, and a click handler
    // to the popup that prevents the event from bubbling up i.e. if the main dialog window receives
    // a click event, it must've been outside the popup window.
    gEventHandlers.addHandler( $gPlayerColorsPopup, "click", function() {
        return false ;
    } ) ;
    gEventHandlers.addHandler( $("#lfa"), "click", function() {
        $gPlayerColorsPopup.hide() ;
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function onInitialLoadCompleted()
{
    // show the hotness chart
    if ( gAppConfig.DISABLE_LFA_HOTNESS_FADEIN )
        $gHotness.show() ;
    else
        setTimeout( function() { $gHotness.fadeIn(1000) ; }, 1000 ) ;

    // update the UI after the initial load has completed
    $gOptions.show() ;
    $gTimePlotOptions.show() ;
    gIsInitialLoad = false ;
}

// --------------------------------------------------------------------

function reloadAll()
{
    // initialize
    var rollType = $gRollTypeDropList.val() ;

    // update the banner
    $gBanner.find( ".title" ).text( gLogFileAnalysis.title ) ;
    $gBanner.find( ".title2" ).text( gLogFileAnalysis.title2 ? "("+gLogFileAnalysis.title2+")" : "" ) ;
    var buf = [] ;
    if ( gLogFileAnalysis.logFileNo >= 0 && gRawResponseData.logFiles.length > 1 ) {
        buf.push( "<span class='caption'>",
            (1+parseInt(gLogFileAnalysis.logFileNo)) + "/" + gRawResponseData.logFiles.length,
            "</span>"
        ) ;
    }
    buf.push( "<span class='ui-selectmenu-icon ui-icon ui-icon-triangle-1-s'>", "</span>" ) ; // nb: jQuery down arrow
    $gBanner.find( ".select-file" ).html( buf.join("") ) ;
    var val ;
    if ( ROLL_TYPES[ rollType ] )
        val = ROLL_TYPES[ rollType ] ;
    else if ( rollType === "" )
        val = "all" ;
    else
        val = "\"" + rollType + "\"" ;
    $gBanner.find( ".roll-type" ).text( "Showing " + val + " rolls." ) ;

    // update the distribution charts
    gLfaStats = gLogFileAnalysis.extractStats( function( evt ) {
        return rollType === "" || checkRollType( evt, rollType ) ;
    } ) ;
    var key, data ;
    for ( key in DR_VALS ) {
        data = getDistribData( key) ;
        var $parentElem = $( "#lfa .distrib" + DR_CLASS_IDS[key] ) ;
        if ( gShowTabularData ) {
            // show the data in tables (for testing porpoises)
            $parentElem.html(
                makeTabularDataHtml( DR_VALS[key], data.datasets )
            ) ;
        } else {
            // load the charts
            gDistribCharts[key].data.datasets = data.datasets ;
            setChartAnimation( gDistribCharts[key].options ) ;
            updateChartForNoData( data.datasets.length === 0, gDistribCharts[key], $parentElem ) ;
            gDistribCharts[key].update() ;
        }
    }

    // update the pie charts
    for ( key in DR_VALS ) {
        data = getPieData( key ) ;
        if ( gShowTabularData ) {
            // show the data in tables (for testing porpoises)
            $( "#lfa .pie" + DR_CLASS_IDS[key] ).html(
                makeTabularDataHtml( data.labels, data.datasets )
            ) ;
        } else {
            // load the charts
            gPieCharts[key].data.datasets = data.datasets ;
            gPieCharts[key].data.labels = data.labels ;
            setChartAnimation( gPieCharts[key].options ) ;
            updatePieChartForNoData( data.datasets.length === 0, gPieCharts[key] ) ;
            gPieCharts[key].update() ;
        }
    }

    // FUDGE! We try to show moving averages in the time-plot chart, since raw rolls are usually too spiky
    // to derive any insights. However, if the user switches to a roll type that has no (or very few) points,
    // the droplist of available window sizes only shows "1" (i.e. for the raw rolls), which persists if
    // the user then switches to a roll type that has lots of points (e.g. "All"), and so they have to
    // manually change the window size. This is annoying, so we attempt to remedy that with this.
    var windowSize = $gMovingAverageDropList.val()  == 1 ? PREFERRED_WINDOW_SIZE : null ;

    // update the time-plot chart
    gTimePlotZoom = null ; // nb: force the chart to auto-fit
    updateTimePlotChart( windowSize ) ;

    // update the dice hotness chart
    data = getHotnessData() ;
    if ( gShowTabularData ) {
        // show the data in tables (for testing porpoises)
        $( "#lfa .hotness" ).html(
            makeTabularDataHtml( data.labels, data.datasets, 3 )
        ).css( { border: "none" } ).show() ;
    } else {
        // load the chart
        var dataVals = data.datasets[0].data ;
        var maxVal=0, hasVal=false ;
        for ( var i=0 ; i < dataVals.length ; ++i ) {
            if ( dataVals[i] === null )
                continue ;
            if ( Math.abs( dataVals[i] ) > maxVal )
                maxVal = Math.abs( dataVals[i] ) ;
            hasVal = true ;
        }
        maxVal = Math.ceil( maxVal ) ;
        gHotnessChart.data.datasets = data.datasets ;
        gHotnessChart.data.labels = data.labels ;
        gHotnessChart.options.scales.xAxes[0].ticks.suggestedMin = - maxVal ;
        gHotnessChart.options.scales.xAxes[0].ticks.suggestedMax = maxVal ;
        setChartAnimation( gHotnessChart.options ) ;
        updateChartForNoData( !hasVal, gHotnessChart, $gHotness ) ;
        $gHotness.css( "border-color", hasVal ? gHotnessBorderColor : "#ccc" ) ;
        $gHotness.find( "img.dice" ).css( "display", hasVal ? "block" : "none" ) ;
        $gHotness.find( "canvas" ).css( "display", hasVal ? "block" : "none" ) ;
        gHotnessChart.update() ;
    }

    // update the layout
    updateLayout() ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function updateTimePlotChart( currWindowSize )
{
    // initialize
    var rollType = $gRollTypeDropList.val() ;
    if ( currWindowSize === null )
        currWindowSize = $gMovingAverageDropList.val() || PREFERRED_WINDOW_SIZE ;

    // extract events from the log file analysis
    var isSingleDie, labels, nextLabel, logFileIndexes ;
    function extractEvents( windowSize ) {
        labels = [] ;
        isSingleDie = nextLabel = null ;
        logFileIndexes = [] ;
        return gLogFileAnalysis.extractEvents( windowSize, {
            onTurnTrackEvent: function( evt ) {
                // we have a Turn Track event - use the phase description as the next label
                nextLabel = evt.side + " " + evt.turnNo + " " + evt.phase ;
            },
            onCustomLabelEvent: function( evt ) {
                // we have a custom label event - use the caption as the next label
                nextLabel = evt.caption ;
            },
            onRollEvent: function( evt ) {
                // we have a DR/dr roll - check if we want to include it
                if ( rollType === "" ) {
                    // NOTE: If we are showing "all" rolls, we only show DR's.
                    if ( LogFileAnalysis.isSingleDie( evt.rollValue ) )
                        return false ;
                } else if ( rollType === "Other" ) {
                    if ( ! checkRollType( evt, rollType ) )
                        return false ;
                    // NOTE: If we are showing "other" rolls, we only show DR's.
                    if ( LogFileAnalysis.isSingleDie( evt.rollValue ) )
                        return false ;
                } else if ( ! checkRollType( evt, rollType ) ) {
                    // nope - we're not interested in this one
                    return false ;
                }
                return true ;
            },
            onLogFileEvent: function( evt ) {
                // we're starting a new log file
                logFileIndexes.push( labels.length ) ;
            },
            _onAddEvent: function( evt ) {
                // remember if we are extracting DR's or dr's
                if ( isSingleDie === null )
                    isSingleDie = LogFileAnalysis.isSingleDie( evt.rollValue ) ;
                // add a label for the event
                if ( nextLabel ) {
                    labels.push( nextLabel ) ;
                    nextLabel = null ;
                } else
                    labels.push( "" ) ;
            },
        } ) ;
    }

    // figure out what moving average window sizes we should show
    var windowSizes = [ 1 ] ;
    var events = extractEvents( 1 ) ; // FIXME! We should really cache this.
    var maxNRolls = 0 ;
    for ( var playerId in events.nRolls ) {
        if ( events.nRolls[playerId] > maxNRolls )
            maxNRolls = events.nRolls[ playerId ] ;
    }
    function isUseableWindowSize( windowSize ) {
        return maxNRolls >= windowSize+20 || maxNRolls >= 2*windowSize ;
    }
    MOVING_AVERAGE_WINDOW_SIZES.forEach( function( windowSize ) {
        if ( isUseableWindowSize( windowSize ) )
            windowSizes.push( windowSize ) ;
    } ) ;

    // check if the current window size is too big
    if ( currWindowSize > windowSizes[ windowSizes.length-1 ] ) {
        // yup - set it to the largest value available
        currWindowSize = windowSizes[ windowSizes.length-1 ] ;
    }

    // update the droplist with the available window sizes
    var buf = [ "<option value='1'> - </option>" ] ;
    MOVING_AVERAGE_WINDOW_SIZES.forEach( function( windowSize ) {
        if ( isUseableWindowSize( windowSize ) ) {
            buf.push( "<option value='" + windowSize + "'" ) ;
            if ( windowSize == currWindowSize )
                buf.push( " selected='selected'" ) ;
            buf.push( ">" + windowSize + "</option>" ) ;
        }
    } ) ;
    $gMovingAverageDropList.html( buf.join("") ).selectmenu( "refresh" ) ;

    // generate the chart data
    gTimePlotEvents = extractEvents( currWindowSize ) ;
    // NOTE: It would be nice to offset the single die values so that the X-axis appears
    // half-way up the Y-axis, but since it would appear at y=3.5, this causes the tick labels
    // to be non-integral :-/
    var data = getTimePlotData( isSingleDie ? 0 : 7 ) ;

    // check if we want to show the data in a table (for testing porpoises)
    if ( gShowTabularData ) {
        // yup - make it so
        $gTimePlotChartWrapper.html( makeTabularDataHtml( labels, data.datasets ) ) ;
        return ;
    }

    // configure extra vertical lines to delineate each log file
    logFileIndexes.shift() ; // nb: ignore the first log file
    gTimePlotChart.data.verticalLines = logFileIndexes ;

    // update the controls
    // NOTE: We do this before updating the chart, since we may disable zoom buttons depending on the data.
    var hasData = data.datasets.length > 0 ;
    $gMovingAverageDropList.selectmenu( hasData ? "enable" : "disable" ) ;
    $gTimePlotOptions.find( "label" ).attr( "disabled", !hasData ) ;
    $gTimePlotZoomInButton.button( hasData ? "enable" : "disable" ) ;
    $gTimePlotZoomOutButton.button( hasData ? "enable" : "disable" ) ;

    // update the chart
    gTimePlotChart.data.datasets = data.datasets ;
    gTimePlotChart.data.labels = labels ;
    updateChartForNoData( data.datasets.length === 0, gTimePlotChart, $gTimePlotChartWrapper ) ;
    if ( currWindowSize == 1 ) {
        // we're showing raw rolls - show all possible values in the Y axis
        gTimePlotChart.options.scales.yAxes[0].ticks.suggestedMin = isSingleDie ? 1 : 2-7 ;
        gTimePlotChart.options.scales.yAxes[0].ticks.suggestedMax = isSingleDie ? 6 : 12-7 ;
    } else {
        // we're showing moving averages - let ChartJS zoom in as appropriate
        gTimePlotChart.options.scales.yAxes[0].ticks.suggestedMin = null ;
        gTimePlotChart.options.scales.yAxes[0].ticks.suggestedMax = null ;
    }
    setChartAnimation( gTimePlotChart.options ) ;
    gTimePlotChart.update() ;
    zoomTimePlotChart( 0 ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function zoomTimePlotChart( zoom ) {

    // initialize
    var datasets = gTimePlotChart.data.datasets ;
    var labels = gTimePlotChart.data.labels ;
    var availableWidth = $gTimePlot.width() ;

    var chartWidth ;
    if ( gTimePlotZoom === null || zoom === null ) {
        // set the initial zoom
        gTimePlotZoom = 1.0 ;
        $gTimePlotZoomInButton.button( "enable" ) ;
        $gTimePlotZoomOutButton.button( "enable" ) ;
    } else {
        const zoomDelta = 0.25 ;
        if ( zoom < 0 ) {
            // the user is zooming out
            if ( gTimePlotZoom <= zoomDelta )
                return ;
            gTimePlotZoom -= zoomDelta ;
            $gTimePlotZoomInButton.button( "enable" ) ;
        } else if ( zoom > 0 ) {
            // the user is zooming in
            gTimePlotZoom += zoomDelta ;
            $gTimePlotZoomOutButton.button( "enable" ) ;
            // remove any blank points we may have added earlier
            removeTrailingBlankVals( labels, datasets ) ;
            gTimePlotChart.update() ;
        }
    }

    // figure out how much horizontal space there should be between points
    var nXVals = labels.length ;
    var spacing = availableWidth / nXVals ; // nb: things still work if we have 0 values :-)
    spacing *= gTimePlotZoom ;
    if ( spacing <= 2 ) {
        spacing = 2 ;
    } else if ( spacing >= MAX_TIME_PLOT_SPACING ) {
        spacing = MAX_TIME_PLOT_SPACING ;
        // we've hit the max spacing - zooming in any further won't have any effect
        $gTimePlotZoomInButton.button( "disable" ) ;
    }
    chartWidth = spacing * nXVals ;
    if ( chartWidth < availableWidth ) {
        // NOTE: We have an upper limit on how much space there can be between points, so if there aren't
        // many points, the graph will be narrower than the available width, and we will have unused space
        // on the right. This is ugly, so we add enough dummy points to make the grid lines go all the way
        // to the right edge.
        var nBlankVals = ( availableWidth - chartWidth - 1 ) / spacing ;
        for ( var i=0 ; i < nBlankVals ; ++i ) {
            labels.push( "" ) ;
            for ( var j=0 ; j < datasets.length ; ++j )
                datasets[j].data.push( null ) ;
        }
        gTimePlotChart.update() ;
        chartWidth = availableWidth ;
    }
    if ( chartWidth <= availableWidth ) {
        // the user can see all the values - there's no point zooming out any further
        $gTimePlotZoomOutButton.button( "disable" ) ;
    }

    // NOTE: ChartJS charts don't really like being resized, so we place it inside a wrapper
    // and resize that, with the chart configured to be responsive.
    $gTimePlotChartWrapper.css( { width: chartWidth } ) ;
    gTimePlotChart.resize() ;
}

function removeTrailingBlankVals( labels, datasets ) {
    // count the number of trailing blank values in each dataset
    var minTrailingBlankVals=null, i, j ;
    for ( i=0 ; i < datasets.length ; ++i ) {
        var nTrailingBlankVals = 0 ;
        for ( j=datasets[i].data.length-1 ; j >= 0 ; --j ) {
            if ( datasets[i].data[j] === null )
                ++ nTrailingBlankVals ;
            else
                break ;
        }
        if ( minTrailingBlankVals === null || nTrailingBlankVals < minTrailingBlankVals )
            minTrailingBlankVals = nTrailingBlankVals ;
    }
    // remove trailing blank values from each dataset
    if ( minTrailingBlankVals > 0 ) {
        for ( i=0 ; i < minTrailingBlankVals ; ++i ) {
            labels.pop() ;
            for ( j=0 ; j < datasets.length ; ++j )
                datasets[j].data.pop() ;
        }
    }
}

// --------------------------------------------------------------------

function createDistribChart( key, classId )
{
    // initialize
    var playerId ;

    // chart callbacks
    function legend_label_filter( label ) { return label.text != "(expected)" ; }
    function yAxis_tick( val, index, vals ) { return val+"%" ; }
    function tooltip_title( tooltipItem, data ) { return key + " " + tooltipItem[0].label ; }
    function tooltip_label( tooltipItem, data ) {
        playerId = gDistribDatasetPlayerIndex[key][ tooltipItem.datasetIndex ] ;
        if ( ! playerId )
            return " Expected: " + tooltipItem.value + "%" ;
        return " " + gLogFileAnalysis.playerName( playerId ) ;
    }
    function tooltip_footer( tooltipItem, data ) {
        playerId = gDistribDatasetPlayerIndex[key][ tooltipItem[0].datasetIndex ] ;
        if ( playerId ) {
            playerId = gDistribDatasetPlayerIndex[key][ tooltipItem[0].datasetIndex ] ;
            var nRolls = gLfaStats[playerId][key].nRolls ;
            var nInstances = gLfaStats[playerId][key].distrib[ tooltipItem[0].label ] || 0 ;
            var msg = nInstances + " of " + nRolls ;
            msg += " " + pluralString( nRolls, key, key+"'s" ) ;
            msg += " (" + tooltipItem[0].value + "%)" ;
            return "     " + msg ;
        }
    }

    // create the chart
    var $canvas = $( "#lfa .distrib" + classId + " canvas" ) ;
    var chart = new Chart( $canvas, {
        data: {
            labels: DR_VALS[key],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            legend: {
                labels: { filter: legend_label_filter },
            },
            tooltips: {
                footerFontStyle: "normal",
                callbacks: { title: tooltip_title, label: tooltip_label, footer: tooltip_footer },
            },
            scales: {
                xAxes: [ {
                    stacked: $gStackBarGraphsCheckBox.is( ":checked" ),
                    scaleLabel: {
                        display: true,
                        labelString: key === "dr" ? " ".repeat(8)+"dr distribution" : "DR distribution"+" ".repeat(70),
                        fontSize: 16,
                    },
                } ],
                yAxes: [ {
                    ticks: {
                        display: false,
                        beginAtZero: true,
                        callback: yAxis_tick,
                        // NOTE: Label auto-skip doesn't really work in the Y-axis,
                        // so we ensure label spread by setting the padding.
                        autoSkipPadding: 10,
                    },
                    gridLines: { drawOnChartArea: false },
                } ],
            },
            plugins: { labels: false },
        }
    } ) ;

    return chart ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function getDistribData( key )
{
    // initialize
    gDistribDatasetPlayerIndex[ key ] = {} ;
    var datasets = [] ;

    // generate the data for each player
    // NOTE: We don't need to generate labels since they will always be the same (1-6 or 2-12).
    gLogFileAnalysis.forEachPlayer( function( playerId ) {

        // check if the next player has any rolls
        if ( gLfaStats[playerId][key].nRolls === 0 )
            return ;

        // get the player's rolls
        var dataVals = [] ;
        DR_VALS[key].forEach( function( drVal ) {
            if ( gLfaStats[playerId][key].distrib[ drVal ] === undefined ) {
                dataVals.push( 0 ) ;
                return ;
            }
            var val = 100 * gLfaStats[playerId][key].distrib[ drVal ] / gLfaStats[playerId][key].nRolls ;
            dataVals.push( Math.round( 10 * val ) / 10 ) ;
        } ) ;
        gDistribDatasetPlayerIndex[key][ datasets.length ] = playerId ;
        var label = gLogFileAnalysis.playerName( playerId ) ;
        if ( gLfaStats[playerId][key].rollAverage )
            label += " (" + fpFmt( gLfaStats[playerId][key].rollAverage, 1 ) + ")" ;

        // add a dataset for the player's rolls
        datasets.push( {
            label: label,
            data: dataVals,
            type: $gDistribLineGraphsCheckBox.is(":checked") ? "line" : "bar",
            // nb: the following are used for both bar and line graphs
            borderWidth: 1,
            borderColor: getPlayerColor( playerId ),
            backgroundColor: getPlayerColor2( playerId ),
            // nb: the following are needed for line graphs
            fill: false,
            lineTension: 0,
            pointBackgroundColor: getPlayerColor( playerId ),
            spanGaps: true,
        } ) ;

    } ) ;

    // add a dataset to show the expected distribution
    if ( datasets.length > 0 ) {
        datasets.push( {
            type: "line",
            label: "(expected)",
            data: Object.values( LogFileAnalysis.EXPECTED_DISTRIB[ key ] ),
            borderColor: gUserSettings.lfa["player-colors"][0],
            backgroundColor: gUserSettings.lfa["player-colors"][0],
            borderDash: [5,5],
            borderWidth: 1,
            lineTension: 0,
            fill: false,
            order: 1,
        } ) ;
    }

    return { datasets: datasets } ;
}

// --------------------------------------------------------------------

function createPieChart( key, classId )
{
    // chart callbacks
    function tooltip_label( tooltipItem, data ) { return " " + data.labels[ tooltipItem.index ] ; }
    function tooltip_footer( tooltipItem, data ) {
        var playerId = gPieDatasetPlayerIndex[ key ][ tooltipItem[0].index ] ;
        if ( ! playerId )
            return null ;
        var nRolls = gLfaStats[playerId][key].nRolls ;
        var totalRolls = gLfaStats.totalRolls[ key ] ;
        if ( totalRolls === 0 )
            return null ;
        var msg = gLfaStats[playerId][key].nRolls  + " of " + totalRolls ;
        msg += " " + pluralString( totalRolls, key, key+"'s" ) ;
        return "     " + msg ;
    }

    // create the chart
    var $canvas = $( "#lfa .pie" + classId + " canvas" ) ;
    var chart = new Chart( $canvas, {
        type: "pie",
        options: {
            responsive: true,
            maintainAspectRatio: false,
            legend: { display: false },
            tooltips: {
                bodyFontSize: 12,
                footerFontStyle: "normal",
                footerFontSize: 12,
                callbacks: { label: tooltip_label, footer: tooltip_footer },
            },
            plugins: {
                labels: { fontSize: 12 },
            },
        }
    } ) ;

    return chart ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function getPieData( key )
{
    // initialize
    var datasets = [] ;
    gPieDatasetPlayerIndex[ key ] = {} ;
    var dataVals=[], labels=[], borderColors=[], bgdColors=[] ;

    // generate the data for each player
    // NOTE: We load the players in reverse order to get them to render
    // in the same left-right order as the bar graph labels.
    var playerIds = gLogFileAnalysis.playerIds() ;
    for ( var i=playerIds.length-1 ; i >= 0 ; --i ) {

        // check if the next player has any rolls
        var playerId = playerIds[ i ] ;
        var nRolls = gLfaStats[ playerId ][ key ].nRolls  ;
        if ( nRolls === 0 )
            continue ;

        // add an entry for the player's rolls
        gPieDatasetPlayerIndex[ key ][ dataVals.length ] = playerId ;
        dataVals.push( nRolls ) ;
        labels.push( gLogFileAnalysis.playerName( playerId ) ) ;
        borderColors.push( getPlayerColor(playerId) ) ;
        bgdColors.push( getPlayerColor2(playerId) ) ;

    }

    if ( dataVals.length > 0 ) {
        datasets.push( {
            data: dataVals,
            borderColor: borderColors,
            borderWidth: 1,
            backgroundColor: bgdColors,
        } ) ;
    }
    return { datasets: datasets, labels: labels } ;
}

// --------------------------------------------------------------------

function createHotnessChart()
{
    // chart callbacks
    function tooltip_title( tooltipItem, data ) {
        // NOTE: We disable full tooltips because we don't have a lot of on-screen space
        // and if we're shorter than 90px, tooltips sometimes get cropped :-/
        return null ;
    }
    function tooltip_label( tooltipItem, data ) {
        var playerId = gHotnessPlayerIndex[ tooltipItem.index ] ;
        var playerName = gLogFileAnalysis.playerName( playerId ) ;
        return " " + playerName + ": " + signedVal(tooltipItem.value) ;
    }

    function signedVal( val ) {
        // return the value as a signed value
        val = parseFloat( val ) ;
        if ( val === 0 )
            return "0" ;
        var val2 = gHotnessChart && gHotnessChart.options.scales.xAxes[0].ticks.suggestedMax < 10 || Math.abs(val) < 10 ? fpFmt(val,1) : fpFmt(val,0) ;
        return val < 0 ? val2 : "+"+val2 ;
    }

    // create the chart
    var $canvas = $gHotness.find( "canvas" ) ;
    var chart = new Chart( $canvas, {
        type: "horizontalBar",
        options: {
            responsive: true,
            maintainAspectRatio: false,
            legend: { display: false },
            tooltips: {
                callbacks: { title: tooltip_title, label: tooltip_label },
            },
            scales: {
                xAxes: [ {
                    position: "top",
                    ticks: {
                        display: true,
                        callback: function( val ) { return signedVal( val ) ; },
                        fontSize: 10, fontStyle: "italic",
                    },
                    gridLines: { drawTicks: false },
                } ],
                yAxes: [ {
                    gridLines: { drawTicks: false },
                } ],
            },
        }
    } ) ;

    return chart ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function getHotnessData()
{
    // initialize
    gHotnessPlayerIndex = {} ;
    var dataVals=[], bgdColors=[], borderColors=[], labels=[] ;

    // generate the data
    var hotness = gLogFileAnalysis.calcHotness( gLfaStats ) ;
    gLogFileAnalysis.forEachPlayer( function( playerId ) {

        // add the next player
        gHotnessPlayerIndex[ dataVals.length ] = playerId ;
        var playerName = gLogFileAnalysis.playerName( playerId ) ;
        if ( playerName.length > 20 )
            playerName = playerName.substring(0,20).trim() + "..." ;
        labels.push( playerName + "  " ) ;

        // add the hotness score
        dataVals.push( hotness[ playerId ][0] ) ;
        var rollRatio = hotness[playerId][1] ;
        var alpha = fpFmt( Math.max( rollRatio, 0.5 ), 1 ) ;
        bgdColors.push( rollRatio >= 1 ? getPlayerColor2(playerId) : "rgba(224,224,224,"+alpha+")" ) ;
        borderColors.push( rollRatio >= 1 ? getPlayerColor(playerId) : "rgba(176,176,176,"+alpha+")" ) ;

    } ) ;

    return {
        datasets: [ {
            data: dataVals,
            borderColor: borderColors,
            backgroundColor: bgdColors,
            borderWidth: 1
        } ],
        labels: labels,
    } ;
}

// --------------------------------------------------------------------

function createTimePlotChart()
{
    // chart callbacks
    function tooltip_title( tooltipItem, data ) {
        var evt = gTimePlotEvents.events[ tooltipItem[0].index ] ;
        var rollNo ;
        if ( gTimePlotEvents.windowSize == 1 )
            rollNo = evt.rollNo ;
        else
            rollNo = (evt.rollNo - gTimePlotEvents.windowSize + 1) + "-" + evt.rollNo ;
        var msg = LogFileAnalysis.isSingleDie( evt.rollValue ) ? "dr": "DR" ;
        msg += " " + rollNo + " of " + gTimePlotEvents.nRolls[evt.playerId] ;
        return "<nobr>" + msg + "<nobr>" ;
    }
    function tooltip_label( tooltipItem, data ) {
        var playerId = gTimePlotDatasetPlayerIndex[ tooltipItem.datasetIndex ] ;
        return gLogFileAnalysis.playerName( playerId ) ;
    }
    function tooltip_footer( tooltipItem, data ) {
        var evt = gTimePlotEvents.events[ tooltipItem[0].index ] ;
        var msg ;
        if ( gTimePlotEvents.windowSize != 1 ) {
            var nFpDigits = $gMovingAverageDropList.val() < 50 ? 1 : 2 ;
            msg = fpFmt( evt.movingAverage, nFpDigits ) ;
        } else {
            // NOTE: We should return a string here, but since we implemented a custom tooltip function,
            // we return the actual values, so that we can select the appropriate die image.
            msg = [ evt.rollValue, evt.rollType ] ;
        }
        return msg ;
    }

    // create the chart
    var $canvas = $( "#lfa .time-plot canvas" ) ;
    var chart = new Chart( $canvas, {
        type: "line",
        options: {
            responsive: true,
            maintainAspectRatio: false,
            legend: {
                position: "top", align: "start",
            },
            tooltips: {
                footerFontStyle: "normal",
                callbacks: { title: tooltip_title, label: tooltip_label, footer: tooltip_footer },
                enabled: false, custom: customTimePlotTooltip,
            },
            scales: {
                xAxes: [ {
                    ticks: {
                        minRotation: 0, maxRotation: 30,
                    },
                    gridLines: { drawOnChartArea: false },
                } ],
                yAxes: [ {
                    ticks: {
                        display: false,
                        suggestedMin: 2, suggestedMax: 12, stepSize: 1,
                        callback: function( val, index, vals ) { return gTimePlotValOffset+val ; },
                    },
                } ],
            },
            animation: {
                onComplete: function() {
                    if ( gIsInitialLoad )
                        onInitialLoadCompleted() ;
                },
            },
        }
    } ) ;

    return chart ;
}

function customTimePlotTooltip( tooltipModel )
{
    // NOTE: This creates a tooltip completely from scratch (so we can include the die images).
    // Adapted from:
    //   https://www.chartjs.org/docs/latest/configuration/tooltip.html?h=html#external-custom-tooltips

    // locate the tooltip element
    var tooltipElem = $( "#lfa .timePlot-tooltip" )[ 0 ] ;
    if ( tooltipModel.opacity === 0 ) {
        tooltipElem.style.opacity = 0 ;
        return ;
    }

    // set the caret position
    tooltipElem.classList.remove( "above", "below", "no-transform" ) ;
    if ( tooltipModel.yAlign )
        tooltipElem.classList.add( tooltipModel.yAlign ) ;
    else
        tooltipElem.classList.add( "no-transform" ) ;

    function addDieImage( buf, dieVal, color ) {
        buf.push(
            "<img src='" + makeDieImageUrl(dieVal,color) + "' style='height:1.5em;float:left;margin:0.25em 0.25em 0 0;'>"
        ) ;
    }

    // generate the tooltip HTML
    if ( tooltipModel.body ) {
        // insert the title
        var buf = [ "<thead>" ] ;
        var titleLines = tooltipModel.title || [] ;
        titleLines.forEach( function( title ) {
            buf.push( "<tr> <th style='text-align:left;'>", title ) ;
        } ) ;
        buf.push( "</thead>" ) ;
        // insert the body
        buf.push( "<tbody>", "<tr>", "<td>" ) ;
        tooltipModel.body.forEach( function( bodyItem ) {
            bodyItem.lines.forEach( function( bodyItemLine ) {
                buf.push( bodyItemLine, "<br>" ) ;
            } ) ;
        } ) ;
        // insert the footer
        if ( gTimePlotEvents.windowSize != 1 ) {
            // we are showing moving averages
            buf.push( "<span style='font-style:italic;font-size:120%;'>", tooltipModel.footer[0], "</span>" ) ;
        } else {
            // we are showing the raw DR/dr's
            var dieVals = tooltipModel.footer[ 0 ] ;
            if ( LogFileAnalysis.isSingleDie( dieVals ) )
                addDieImage( buf, dieVals, "yellow" ) ;
            else {
                addDieImage( buf, dieVals[0], "yellow" ) ;
                for ( var i=1 ; i < dieVals.length ; ++i )
                    addDieImage( buf, dieVals[i], "white" ) ;
            }
            buf.push(
                "<div style='display:inline-block;height:1.8em;line-height:1.8em;margin-left:0.25em;font-style:italic;'>",
                tooltipModel.footer[1],
                "</div>"
            ) ;
        }
        buf.push( "</tbody>" ) ;
        // update the tooltip
        var tableRoot = tooltipElem.querySelector( "table" ) ;
        tableRoot.innerHTML = buf.join( "" ) ;
        tableRoot.style.color = tooltipModel.bodyFontColor ;
    }

    // configure the tooltip
    var marginX=8, marginY=4 ;
    var position = this._chart.canvas.getBoundingClientRect() ;
    tooltipElem.style.opacity = 1 ;
    tooltipElem.style.position = "absolute" ;
    var newLeft = position.left + window.pageXOffset + tooltipModel.caretX + marginX ;
    if ( newLeft >= position.width - tooltipElem.offsetWidth - 20 )
        newLeft = tooltipModel.caretX - tooltipElem.offsetWidth ;
    tooltipElem.style["z-index"] = 150 ; // nb: put this on top of the hotness popup
    tooltipElem.style.left = newLeft + "px" ;
    tooltipElem.style.top = position.top + window.pageYOffset + tooltipModel.caretY - tooltipElem.offsetHeight - marginY + "px" ;
    tooltipElem.style.background = tooltipModel.backgroundColor ;
    tooltipElem.style.fontFamily = tooltipModel._bodyFontFamily ;
    tooltipElem.style.fontSize = tooltipModel.bodyFontSize + "px" ;
    tooltipElem.style.fontStyle = tooltipModel._bodyFontStyle ;
    tooltipElem.style.padding = tooltipModel.yPadding + "px " + tooltipModel.xPadding + "px" ;
    tooltipElem.style.pointerEvents = "none" ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function getTimePlotData( valOffset )
{
    // initialize
    gTimePlotDatasetPlayerIndex = {} ;
    gTimePlotValOffset = gShowTabularData ? 0 : valOffset ;
    var datasets = [] ;

    // generate the data for each player
    gLogFileAnalysis.forEachPlayer( function( playerId ) {

        // get the rolls for the next player
        var dataVals=[], nRealVals=0 ;
        gTimePlotEvents.events.forEach( function( evt ) {
            if ( evt === null ) {
                dataVals.push( null ) ;
                return ;
            }
            if ( evt.playerId == playerId ) {
                dataVals.push( evt.movingAverage - gTimePlotValOffset ) ;
                ++ nRealVals ;
            } else {
                dataVals.push( null ) ;
            }
        } ) ;
        if ( nRealVals === 0 )
            return ;
        nRealVals += gTimePlotEvents.windowSize - 1 ;

        // add a dataset for the player's rolls
        gTimePlotDatasetPlayerIndex[ datasets.length ] = playerId ;
        datasets.push( {
            type: "line",
            label: gLogFileAnalysis.playerName( playerId ) + " (" + nRealVals + ")",
            data: dataVals,
            borderColor: getPlayerColor(playerId),
            borderWidth: 1,
            backgroundColor: getPlayerColor2(playerId),
            pointBackgroundColor: getPlayerColor(playerId),
            fill: false,
            lineTension: gTimePlotEvents.windowSize == 1 ? 0 : 0.4,
            spanGaps: true,
        } ) ;

    } ) ;

    return { datasets: datasets } ;
}

// --------------------------------------------------------------------

function updateLayout()
{
    // FUDGE! Charts really don't like being resized, and even the technique of making them responsive
    // and putting them inside a wrapper div, and resizing that, isn't completely reliable :-(
    // I eventually gave up and lay things out using Javascript :-/

    // initialize
    const availableWidth = $( ".ui-dialog.lfa" ).width() - 25 ;
    const optionsWidth = $gOptions.outerWidth() ;
    const pieChartHeight = 90 ;

    function setDistribWidth() {
        // set the width of the DR distribution chart
        var newWidth = availableWidth * 0.7 ;
        var maxWidth = availableWidth - $distrib2.position().left ;
        newWidth = Math.min( newWidth, maxWidth ) ;
        newWidth = Math.max( newWidth, 1.5*optionsWidth ) ;
        $distrib2.width( newWidth ) ;
    }

    // resize the DR distribution chart
    var $distrib2 = $( "#lfa .distrib.d6x2" ) ;
    var availableHeight ;
    if ( ! gShowTabularData ) {
        setDistribWidth() ;
        availableHeight = $("#lfa .top-pane").height() - pieChartHeight ;
        $distrib2.height( availableHeight ) ;
        gDistribCharts.DR.resize() ;
    }

    // resize the dr distribution chart
    $distrib1 = $( "#lfa .distrib.d6x1" ) ;
    if ( ! gShowTabularData ) {
        newWidth = availableWidth * 0.3 ;
        $distrib1.width( Math.max( newWidth, optionsWidth ) ) ;
        var newBottom = $distrib2.position().top + $distrib2.height() + 6 ;
        $distrib1.height( newBottom - $distrib1.position().top ) ;
        gDistribCharts.dr.resize() ;
    }

    // FUDGE! If we restore a maximized window, the DR distribution chart is resized too narrow.
    // It seems to have something to do with adjusting the width of the dr distribution chart,
    // so we do it again here :-/
    setDistribWidth() ;

    // resize the time-plot chart
    // NOTE: Resizing horizontally is more complicated (since it depends on whether or not we're showing
    //  a scrollbar, which depends on how many points there are), which is done in zoomTimePlotChart().
    if ( ! gShowTabularData ) {
        var $timePlot = $( "#lfa .time-plot .wrapper" ) ;
        availableHeight = $("#lfa .bottom-pane").height() - 20 ; // nb: leave some room for the h-scrollbar.
        $timePlot.height( availableHeight ) ;
        gTimePlotChart.resize() ;
    }

    // position the hotness chart
    var nPlayers = gLogFileAnalysis.playerIds().length ;
    var barHeight = Math.max( 12 - 2*nPlayers, 6 ) ;
    var newHeight = 50 + barHeight * nPlayers ;
    $gHotness.css( { height: newHeight } ) ;
    var newImageHeight = 48 - 3 * nPlayers ;
    $gHotness.find( "img.dice" ).css( { height: newImageHeight } ) ;

    // re-position any "no data" signs
    $gDialog.find( ".no-data" ).each( function() {
        positionNoData( $(this) ) ;
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

var gPrevChartColors = {} ;

function updateChartForNoData( hasNoData, chart, $parentElem )
{
    // initialize
    var $noDataElem = $parentElem.children( ".no-data" ) ;

    if ( hasNoData ) {

        // flag that the chart has no data
        if ( $noDataElem.length === 0 ) {
            var $sign = $( "<div class='no-data'> No data </div>" ) ;
            $parentElem.append( $sign ) ;
            positionNoData( $sign ) ;
        }
        // grey out chart elements
        var color = "#ccc" ;
        chart.options.scales.xAxes[0].scaleLabel.fontColor = color ;
        chart.options.scales.xAxes[0].ticks.fontColor = color ;
        chart.options.scales.xAxes[0].gridLines.zeroLineColor = color ;
        chart.options.scales.yAxes[0].gridLines.zeroLineColor = color ;

    } else {

        // remove the "no data" marker
        $noDataElem.remove() ;
        // restore color to chart elements
        if ( ! gPrevChartColors[ chart ] ) {
            gPrevChartColors[ chart ] = {
                scaleLabel: chart.options.scales.xAxes[0].scaleLabel.fontColor,
                ticks: chart.options.scales.xAxes[0].ticks.fontColor,
                xZeroLineColor: chart.options.scales.xAxes[0].gridLines.zeroLineColor,
                yZeroLineColor: chart.options.scales.yAxes[0].gridLines.zeroLineColor,
            } ;
        } else {
            chart.options.scales.xAxes[0].scaleLabel.fontColor = gPrevChartColors[ chart ].scaleLabel ;
            chart.options.scales.xAxes[0].ticks.fontColor = gPrevChartColors[ chart ].ticks ;
            chart.options.scales.xAxes[0].gridLines.zeroLineColor = gPrevChartColors[ chart ].xZeroLineColor ;
            chart.options.scales.yAxes[0].gridLines.zeroLineColor = gPrevChartColors[ chart ].yZeroLineColor ;
        }

    }

    // hide axis ticks if the chart has no data
    chart.options.scales.yAxes[0].ticks.display = ! hasNoData ;
}

function positionNoData( $noData )
{
    // position the "no data" sign
    var $parent = $noData.parent() ;
    $noData.css( {
        position: "absolute",
        left: ($parent.width() - $noData.width()) / 2,
        bottom: ($parent.height() - $noData.height()) / 2,
    } ) ;
}

function updatePieChartForNoData( noData, chart )
{
    // FUDGE! Loading a pie chart with no data makes it disappear :-/ We show a disabled pie chart
    // by loading it with a single dummy data point and changing the color to grey.
    if ( noData ) {
        // flag that the chart has no data
        chart.data.datasets = [ { data: [-1], backgroundColor: "#f0f0f0" } ] ;
        chart.options.tooltips.enabled = false ;
        chart.options.hover.mode = null ;
        chart.options.plugins.labels = false ;
    } else {
        // flag that the chart has data
        chart.options.tooltips.enabled = true ;
        chart.options.hover.mode = "single" ;
        chart.options.plugins.labels = true ;
    }
}

// --------------------------------------------------------------------

function updateChartColors( playerId, newColor )
{
    if ( ! playerId )
        return ;

    // initialize
    var key, i ;

    // update the DR/dr distribution charts
    function isDatasetMatch( datasetNo ) {
        if ( playerId === ":expected:" )
            return datasetNo == gDistribCharts[key].data.datasets.length - 1 ; // nb: "expected results" is the last dataset
        else
            return  gDistribDatasetPlayerIndex[key][ datasetNo ] == playerId ;
    }
    for ( key in DR_CLASS_IDS ) {
        for ( i=0 ; i < gDistribCharts[key].data.datasets.length ; ++i ) {
            if ( isDatasetMatch( i ) ) {
                gDistribCharts[key].data.datasets[ i ].borderColor = newColor ;
                gDistribCharts[key].data.datasets[ i ].backgroundColor = playerId === ":expected:" ? newColor : makePlayerColor2( newColor ) ;
                gDistribCharts[key].data.datasets[ i ].pointBackgroundColor = newColor ;
                gDistribCharts[key].update() ;
                break ;
            }
        }
    }

    // update the DR/dr pie charts
    for ( key in DR_CLASS_IDS ) {
        if ( gPieCharts[key].data.datasets.length === 0 )
            continue ;
        for ( i=0 ; i < gPieCharts[key].data.datasets[0].data.length ; ++i ) {
            if ( gPieDatasetPlayerIndex[ key ][i] == playerId ) {
                gPieCharts[key].data.datasets[0].borderColor[ i ] = newColor ;
                gPieCharts[key].data.datasets[0].backgroundColor[ i ] = makePlayerColor2( newColor ) ;
                gPieCharts[key].update() ;
                break ;
            }
        }
    }

    // update the time-plot chart
    for ( i=0 ; i < gTimePlotChart.data.datasets.length ; ++i ) {
        if ( gTimePlotDatasetPlayerIndex[ i ] == playerId ) {
            gTimePlotChart.data.datasets[ i ].borderColor = newColor ;
            gTimePlotChart.data.datasets[ i ].backgroundColor = makePlayerColor2( newColor ) ;
            gTimePlotChart.data.datasets[ i ].pointBackgroundColor = newColor ;
            gTimePlotChart.update() ;
            break ;
        }
    }

    // update the hotness chart
    var dataset = gHotnessChart.data.datasets[ 0 ] ;
    for ( i=0 ; i < dataset.data.length ; ++i ) {
        if ( gHotnessPlayerIndex[i] == playerId ) {
            dataset.borderColor[i] = newColor ;
            dataset.backgroundColor[i] = makePlayerColor2( newColor ) ;
            gHotnessChart.update() ;
            break ;
        }
    }
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function getPlayerColor( playerId ) { return gUserSettings.lfa["player-colors"][ gPlayerColorIndex[playerId] ] ; }
function getPlayerColor2( playerId ) { return makePlayerColor2( gUserSettings.lfa["player-colors"][ gPlayerColorIndex[playerId] ] ) ; }

function makePlayerColor2( color ) {
    color = tinycolor( color ) ;
    color.setAlpha( 0.2 ) ;
    return color.toRgbString() ;
}

// --------------------------------------------------------------------

function onDownloadData()
{
    // NOTE: Everything is handled as UTF-8, but as usual, dealing with Excel is problematic :-/
    // We could insert a BOM, but there are known issues with Excel barfing on these. Without one,
    // the user may have to import the file via the Data menu (configuring the encoding and delimiter),
    // but at least it will work (and only needs to be done if there is non-ASCII content).
    // We could also set the charset in the Content-Type header, but that doesn't help
    // when the user saves the download in a file, then tries to open it in another application.

    // initialize
    var buf = [ '"Log file","Phase","Player","Type","Die 1","Die 2"\n' ] ;
    function safeVal( val ) {
        return '"' + strReplaceAll(val,'"','""') + '"' ;
    }

    // process each event
    var nextLogFilename=null, nextLabel=null ;
    gLogFileAnalysis.extractEvents( 1, {
        onLogFileEvent: function( evt ) {
            // save the log filename (it will be included in the next row of data)
            nextLogFilename = evt.filename ;
        },
        onTurnTrackEvent: function( evt ) {
            // save the phase (it will be included in the next row of data)
            nextLabel = evt.side + " " + evt.turnNo + " " + evt.phase ;
        },
        onCustomLabelEvent: function( evt ) {
            // save the custom label (it will be included in the next row of data)
            nextLabel = evt.caption ;
        },
        onRollEvent: function( evt ) {
            // generate the next row of data
            if ( nextLogFilename ) {
                buf.push( safeVal( nextLogFilename ) ) ;
                nextLogFilename = null ;
            }
            buf.push( "," ) ;
            if ( nextLabel ) {
                buf.push( safeVal( nextLabel ) ) ;
                nextLabel = null ;
            }
            buf.push( "," ) ;
            buf.push( safeVal( gLogFileAnalysis.playerName( evt.playerId ) ) ) ;
            buf.push( "," ) ;
            buf.push( safeVal( evt.rollType ) ) ;
            buf.push( "," ) ;
            if ( LogFileAnalysis.isSingleDie( evt.rollValue ) )
                buf.push( evt.rollValue, "," ) ;
            else
                buf.push( evt.rollValue[0], ",", evt.rollValue[1] ) ;
            buf.push( "\n" ) ;
        },
    } ) ;

    // return the data to the user
    var data = buf.join( "" ).trim() ;
    if ( getUrlParam( "lfa_persistence" ) )
        $( "#_lfa-download_"). val( data ) ;
    else {
        closeAllPopupsAndDropLists() ;
        if ( gWebChannelHandler )
            gWebChannelHandler.save_log_file_analysis( data ) ;
        else
            download( data, "analysis.csv", "application/text" ) ;
    }
}

// --------------------------------------------------------------------

gTabularDataSeqNo = 0 ;

function makeTabularDataHtml( labels, datasets, nFpDigits )
{
    // NOTE: This is for testing porpoises only. It shows the chart data
    // in tables, so that the test suite can easily extract it.

    // figure out how many rows we have
    var nRows = labels.length ;
    var i, j ;
    datasets.forEach( function( dataset ) {
        if ( dataset.data.length > nRows )
            nRows = dataset.data.length ;
    } ) ;

    var buf = [] ;
    function pushVal( vals, valNo ) {
        if ( valNo < vals.length ) {
            if ( typeof vals[valNo] === "number" && nFpDigits !== undefined )
                buf.push( fpFmt( vals[valNo], nFpDigits ) ) ;
            else
                buf.push( vals[valNo] ) ;
        } else {
            buf.push( "???" ) ; // nb: should never get here!
        }
    }

    // generate the table HTML
    buf.push( "<table class='chart-data' data-seqno='" + (++gTabularDataSeqNo) + "'>" ) ;
    if ( datasets.length > 0 ) {
        buf.push( "<tr>", "<th>" ) ;
        datasets.forEach( function( dataset ) {
            buf.push( "<th>", dataset.label ) ;
        } ) ;
        for ( i=0 ; i < nRows ; ++i ) {
            buf.push( "<tr>", "<td class='label'>" ) ;
            pushVal( labels, i ) ;
            for ( j=0 ; j < datasets.length ; ++j ) {
                buf.push( "<td>" ) ;
                pushVal( datasets[j].data, i ) ;
            }
        }
    }
    buf.push( "</table>" ) ;

    return buf.join( "" ) ;
}

// --------------------------------------------------------------------

var gOriginalLineDraw = Chart.controllers.line.prototype.draw ;

Chart.helpers.extend( Chart.controllers.line.prototype, { draw: function() {

    // NOTE: We install this function into the chart prototype, to draw extra vertical lines
    // in the time-plot chart that indicate the start of each new log file.

    // initialize
    gOriginalLineDraw.apply( this, arguments ) ;
    var chart = this.chart ;

    // figure out where we need to draw vertical lines
    var verticalLines = chart.config.data.verticalLines ;
    if ( ! verticalLines )
        return ;

    // draw each vertical line
    var ctx = chart.chart.ctx ;
    verticalLines.forEach( function( index ) {
        var xAxis = chart.scales[ "x-axis-0" ] ;
        var yAxis = chart.scales[ "y-axis-0" ] ;
        ctx.save() ;
        ctx.beginPath() ;
        var xPos = xAxis.getPixelForValue( undefined, index ) ;
        ctx.moveTo( xPos, yAxis.top ) ;
        ctx.lineWidth = 1 ;
        ctx.setLineDash( [ 5, 3 ] ) ;
        ctx.strokeStyle = "#d0d0d0" ;
        ctx.lineTo( xPos, yAxis.bottom ) ;
        ctx.stroke() ;
        ctx.restore() ;
    } ) ;

} } ) ;

// --------------------------------------------------------------------

function closeAllPopupsAndDropLists()
{
    // close all popups
    $gPlayerColorsPopup.hide() ;
    $gPlayerColorsPopup.find( ".color-picker" ).each( function() {
        var prevColor = $(this).attr( "data-prev-color" ) ;
        if ( prevColor )
            $(this).spectrum( "set", prevColor ) ;
        $(this).spectrum( "hide") ;
    } ) ;
    $gSelectFilePopup.hide() ;
    $gHotnessPopup.hide() ;

    // close all droplists
    $( "#lfa select" ).each( function() {
        $(this).selectmenu( "close" ) ;
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function setChartAnimation( options ) {
    // The ChartJS docs claim that you can disable animations globally via Chart.defaults.global.animation,
    // but it doesn't seem to work :-/ We set it on each individual chart.
    if ( ! options.animation )
        options.animation = {} ;
    options.animation.duration = $gDisableAnimationsCheckBox.is( ":checked" ) ? 0 : 1000 ;
}

function makeArray( val, count ) {
    // create an array consisting of a repeated value
    var arr = [] ;
    for ( var i=0 ; i < count ; ++i )
        arr.push( val ) ;
    return arr ;
}

function checkRollType( evt, rollType ) { return evt.rollType === rollType ; }
function makeDieImageUrl( dieVal, color ) { return gImagesBaseUrl + "/lfa/die/" + color + "/" + dieVal + ".png" ; }

// --------------------------------------------------------------------

} )() ; // end local namespace
