gAppConfig = {} ;
gProgramInfo = {} ;
gDefaultTemplatePack = null ;
gTemplatePack = {} ;
gHasPlayerFlag = {} ;
gValidTemplateIds = [] ;
gVehicleOrdnanceListings = {} ;
gVehicleOrdnanceNotes = {} ;
gVaslPieceInfo = {} ;
gOnlineCounterImages = {} ;
gAslRulebook2VoNoteTargets = {} ;

gWebChannelHandler = null ;
gPlayerOBSplitters = {} ;
gEmSize = null ;

var NATIONALITY_SPECIFIC_BUTTONS = {
    "pf": [ "german" ],
    "pf-finnish": [ "finnish" ],
    "pf-hungarian": [ "hungarian" ],
    "pf-romanian": [ "romanian" ],
    "atmm": [ "german" ],
    "atmm-romanian": [ "romanian" ],
    "psk": [ "german" ],
    "mol": [ "russian" ],
    "mol-p": [ "russian" ],
    "baz": [ "american!korea" ],
    "baz45": [ "american@korea", "kfw-rok", "kfw-ounc" ],
    "baz50": [ "american@korea", "kfw-rok", "kfw-ounc" ],
    "baz-cpva16": [ "kfw-cpva" ],
    "baz-cpva17": [ "kfw-cpva" ],
    "piat": [ "british" ],
    "thh": [ "japanese" ],
} ;

GENERATE_SNIPPET_HINT = "Generate an HTML snippet" ;
EDIT_TEMPLATE_HINT = "Edit the template" ;

// --------------------------------------------------------------------

$(document).ready( function () {

    // initialize the PyQt web channel
    if ( getUrlParam( "pyqt" ) ) {
        $.getScript( "qrc:///qtwebchannel/qwebchannel.js", function() {
            // connect to the web channel
            new QWebChannel( qt.webChannelTransport, function(channel) {
                gWebChannelHandler = channel.objects.handler ;
                // FUDGE! If the page finishes loading before the web channel is ready,
                // the desktop won't get this notification. To be sure, we issue it again...
                gWebChannelHandler.on_app_loaded() ;
                fixup_external_links( $("body") ) ; // ditto for this :-/
            } ) ;
        } ) ;
    }

    // initialize the menu
    var $menu = $("#menu input") ;
    var imagesDir = gImagesBaseUrl + "/menu" ;
    var menuItems = {
        new_scenario: { label: "New scenario", icon: imagesDir+"/new.png", action: on_new_scenario },
        load_scenario: { label: "Load scenario", icon: imagesDir+"/open.png", action: on_load_scenario },
        save_scenario: { label: "Save scenario", icon: imagesDir+"/save.png", action: on_save_scenario },
        separator: { type: "separator" },
        analyze_vsav: { label: "Analyze VASL scenario", icon: imagesDir+"/analyze-vsav.png", action: on_analyze_vsav },
        update_vsav: { label: "Update VASL scenario", icon: imagesDir+"/update-vsav.png", action: on_update_vsav },
        analyze_vlog: { label: "Analyze log files", icon: imagesDir+"/lfa.png", action: on_analyze_vlog },
        separator2: { type: "separator" },
        template_pack: { label: "Load template pack", icon: imagesDir+"/template-pack.png", action: on_template_pack },
        user_settings: { label: "Settings", icon: imagesDir+"/settings.png", action: function() {
            user_settings( null, null ) ;
        } },
        separator3: { type: "separator" },
        program_info: { label: "Program info", icon: imagesDir+"/info.png", action: show_program_info },
        show_help: { label: "Help", icon: imagesDir+"/help.png", action: show_help },
    } ;
    if ( getUrlParam( "pyqt" ) )
        delete menuItems.program_info ;
    $menu.popmenu( menuItems ) ;
    // nb: we only show the popmenu on left click (not the normal right-click)
    $menu.off( "contextmenu" ) ;
    $menu.click( function() {
        $(this).blur() ;
        var pos = $(this).offset() ;
        $(this).data( "PopMenu.contextmenu" ).data( "PopMenu.instance" ).show(
            pos.left+$(this).width(), pos.top+$(this).height()+2, "fade", 200
        ) ;
    } ) ;
    // add handlers
    $("#load-scenario").change( on_load_scenario_file_selected ) ;
    $("#load-template-pack").change( on_template_pack_file_selected ) ;
    $("#load-vsav").change( on_load_vsav_file_selected ) ;
    $("#load-vlog").change( on_load_vlog_file_selected ) ;
    // preload the menu item images
    for ( var item in menuItems ) {
        var url = menuItems[ item ].icon ;
        if ( url )
            $.get( make_app_url( url )  ) ;
    }
    // all done - we can show the menu now
    $("#menu").show() ;

    // dynamically create the OB2 tab from OB1
    var $ob2 = $("#tabs-ob1").clone() ;
    var adjustAttr = function( $elem, attrName ) {
        var val = $elem.attr( attrName ) ;
        if ( val && val.substring(val.length-1) === "1" )
            $elem.attr( attrName, val.substring(0,val.length-1)+"2" ) ;
    } ;
    function fixupOB2( $elem ) {
        adjustAttr( $elem, "id" ) ;
        adjustAttr( $elem, "name" ) ;
        adjustAttr( $elem, "data-id" ) ;
        adjustAttr( $elem, "for" ) ;
        $elem.children().each( function() {
            fixupOB2( $(this) ) ;
        } ) ;
    }
    fixupOB2( $ob2 ) ;
    $("#tabs-ob2").html( $ob2.html() ).addClass( "tabs-ob" ) ;

    // initialize the tabs
    $("#tabs").tabs( {
        heightStyle: "fill",
        disabled: [1, 2, 3], // nb: we enable these when the page has finished loading
        activate: on_tab_activate,
    } ).show() ;
    var navHeight = $("#tabs .ui-tabs-nav").height() ;
    $("#tabs .ui-tabs-nav a").click( function() { $(this).blur() ; } ) ;

    // initialize scenario search
    function scenarioSearchOrInfo( evt ) {
        if ( ! $( "input[name='ASA_ID']" ).val() || evt.shiftKey )
            searchForScenario() ;
        else
            showScenarioInfo() ;
    }
    $(".scenario-search").button( {} )
        .html( "<img src='" + gImagesBaseUrl + "/search.png'>" )
        .click( scenarioSearchOrInfo ) ;

    // initialize the scenario theater
    init_select2(
        $("select[name='SCENARIO_THEATER']"), "5em", false, null
    ).on( "change", function() {
        on_scenario_theater_change() ;
    } ) ;

    // initialize the scenario date picker
    $("input[name='SCENARIO_DATE']").datepicker( {
        showAnim: "slideDown",
        changeMonth: true, changeYear: true,
        onClose: on_scenario_date_change,
    } ) ;

    // initialize the turn track controls
    var $turnCountSel = $( "select[name='TURN_TRACK_NTURNS']" ) ;
    init_select2(
        $turnCountSel, "4em", false, formatTurnTrackOption
    ).on( "select2:open", function() {
        restrict_droplist_height( $(this) ) ;
    } ).on( "change", function() {
        if ( $(this).val() === "(show-dialog)" ) {
            $(this).val( DEFAULT_TURN_TRACK_TURNS_MIN ).trigger( "change" ) ;
            editTurnTrackSettings() ;
        } else {
            updateTurnTrackNTurns( $(this).val() ) ;
            $( "#panel-scenario .turn-track-controls" ).css( {
                display: $(this).val() !== "" ? "flex" : "none"
            } ) ;
        }
    } ) ;
    $turnCountSel.append( $( "<option value=''>-</option>" ) ) ;
    for ( var nTurns=DEFAULT_TURN_TRACK_TURNS_MIN ; nTurns <= DEFAULT_TURN_TRACK_TURNS_MAX ; nTurns += 0.5 )
        $turnCountSel.append( $( "<option value='" + nTurns + "'>" + nTurns + "</option>" ) ) ;
    $( "button#turn-track-settings" ).button().click( editTurnTrackSettings ) ;

    // initialize the SSR's
    $("#ssr-sortable").sortable2( "init", {
        add: add_ssr, edit: edit_ssr
    } ) ;
    $("fieldset[name='vc']").fadeIn( 2*1000 ) ;
    $("fieldset[name='ssr']").fadeIn( 2*1000 ) ;

    // initialize the scenario notes
    $("#scenario_notes-sortable").sortable2( "init", {
        add: add_scenario_note, edit: edit_scenario_note,
    } ) ;
    $("fieldset[name='scenario_notes']").fadeIn( 2*1000 ) ;

    // initialize the OB setups
    $("#ob_setups-sortable_1").sortable2( "init", {
        add: function() { add_ob_setup(1) ; },
        edit: edit_ob_setup
    } ) ;
    $("#ob_setups-sortable_2").sortable2( "init", {
        add: function() { add_ob_setup(2) ; },
        edit: edit_ob_setup
    } ) ;

    // initialize the OB notes
    $("#ob_notes-sortable_1").sortable2( "init", {
        add: function() { add_ob_note(1) ; },
        edit: edit_ob_note
    } ) ;
    $("#ob_notes-sortable_2").sortable2( "init", {
        add: function() { add_ob_note(2) ; },
        edit: edit_ob_note
    } ) ;

    // initialize the OB vehicles
    $("#ob_vehicles-sortable_1").sortable2( "init", {
        add: function() { add_vo( "vehicles", 1 ) ; },
        edit: function( $sortable2, $entry ) { edit_ob_vehicle( $entry, 1 ) ; },
    } ) ;
    $("#ob_vehicles-sortable_2").sortable2( "init", {
        add: function() { add_vo( "vehicles", 2 ) ; },
        edit: function( $sortable2, $entry ) { edit_ob_vehicle( $entry, 2 ) ; },
    } ) ;

    // initialize the OB ordnance
    $("#ob_ordnance-sortable_1").sortable2( "init", {
        add: function() { add_vo( "ordnance", 1 ) ; },
        edit: function( $sortable2, $entry ) { edit_ob_ordnance( $entry, 1 ) ; },
    } ) ;
    $("#ob_ordnance-sortable_2").sortable2( "init", {
        add: function() { add_vo( "ordnance", 2 ) ; },
        edit: function( $sortable2, $entry ) { edit_ob_ordnance( $entry, 2 ) ; },
    } ) ;

    // load the ELR's and SAN's
    buf = [ "<option value=''>-</option>" ] ; // nb: to help the user to remember to set this
    for ( var i=0 ; i <= 5 ; ++i ) // nb: A19.1: ELR is 0-5
        buf.push( "<option value='" + i + "'>" + i + "</option>" ) ;
    buf = buf.join( "" ) ;
    var player_no, $sel ;
    for ( player_no=1 ; player_no <= 2 ; ++player_no ) {
        $sel = init_select2( $( "select[name='PLAYER_" + player_no + "_ELR']" ),
            "3em", false, null
        ).html( buf ) ;
        $sel.data( "select2" ).$results.css( "max-height", "15em" ) ;
    }
    buf = [ "<option value=''>-</option>" ] ; // nb: allow scenarios that have no SAN
    for ( i=2 ; i <= 7 ; ++i ) // nb: A14.1: SAN is 2-7
        buf.push( "<option value='" + i + "'>" + i + "</option>" ) ;
    buf = buf.join( "" ) ;
    for ( player_no=1 ; player_no <= 2 ; ++player_no ) {
        $sel = init_select2( $( "select[name='PLAYER_" + player_no + "_SAN']" ),
            "3em", false, null
        ).html( buf ) ;
        $sel.data( "select2" ).$results.css( "max-height", "15em" ) ;
    }

    // initialize the splitters
    initSplitters() ;

    // initialize the HTML textbox's
    [ "SCENARIO_NAME", "SCENARIO_ID", "SCENARIO_LOCATION", "PLAYER_1_DESCRIPTION", "PLAYER_2_DESCRIPTION" ].forEach( function( key ) {
        var $elem = $( "div.html-textbox[name='" + key + "']" ) ;
        var caption = $elem.attr( "title" ) ;
        initHtmlTextbox( $elem,
            caption[0].toLowerCase() + caption.substring(1),
            key.substr( 0, 7 ) === "PLAYER_"
        ) ;
    } ) ;
    // FUDGE! We also need to stop the HTML textboxes that are in a flexbox from expanding out
    // if they contain long words with no spaces. The layout still isn't quite right, but this
    // isn't something that will happen often, so we just live with it :-/
    // NOTE: Things work when the SCENARIO panel gets wider, but not when it narrows (because
    // the HTML textbox has expanded out, and doesn't want to narrow when the parent element
    // narrows, and so the panel doesn't narrow). We work-around this by checking the width
    // of the SCENARIO NOTES panel, which will always be the same width as the SCENARIO panel.
    var $panel2 = $("fieldset[name='scenario_notes']" ) ;
    ( new ResizeObserver( function() {
        // limit the horizontal width of the rows in the SCENARIO panel
        var $panel = $( "fieldset[name='scenario']" ) ;
        $panel.find( ".row" ).css( "max-width", $panel2.width() ) ;
        // limit the width of the individual HTML textbox's
        $( "div.html-textbox[name='SCENARIO_NAME']" ).css( {
            "max-width": "calc(100% - 210px)"
        } ) ;
        $( "div.html-textbox[name='SCENARIO_LOCATION']" ).css( {
            "max-width": "calc(100% - 237px)"
        } ) ;
        for ( var playerNo=1 ; playerNo <= 2 ; ++playerNo ) {
            $( "div.html-textbox[name='PLAYER_" + playerNo + "_DESCRIPTION']" ).css( {
                "max-width": "calc(100% - 7em - 8px)"
            } ) ;
        }
        // update the overflow icons
        $panel.find( "div.html-textbox" ).each( function() {
            $(this).data( "updateOverflowIcon" )() ;
        } ) ;
    } ) ).observe( $panel2[0] ) ;

    // get the application config
    $.getJSON( gAppConfigUrl, function(data) {
        gAppConfig = data ;
        update_page_load_status( "app-config" ) ;
        // load the available theaters
        var $sel = $( "select[name='SCENARIO_THEATER']" ) ;
        gAppConfig.THEATERS.forEach( function( theater ) {
            $sel.append( $( "<option value='" + theater + "'>" + theater + "</option>" ) ) ;
        } ) ;
        // set the alternate webapp base URL
        var alt_base_url = gAppConfig.ALTERNATE_WEBAPP_BASE_URL ;
        if ( alt_base_url ) {
            var $elem = $( "#alt-webapp-base-url" ) ;
            $elem.text( $elem.text() + " " + alt_base_url ).show() ;
        }
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the application config:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        update_page_load_status( "app-config" ) ;
    } ) ;

    // get the vehicle/ordnance listings
    $.getJSON( gVehicleListingsUrl, function(data) {
        gVehicleOrdnanceListings.vehicles = data ;
        update_page_load_status( "vehicle-listings" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the vehicle listings:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        update_page_load_status( "vehicle-listings" ) ;
    } ) ;
    $.getJSON( gOrdnanceListingsUrl, function(data) {
        gVehicleOrdnanceListings.ordnance = data ;
        update_page_load_status( "ordnance-listings" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the ordnance listings:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        update_page_load_status( "ordnance-listings" ) ;
    } ) ;
    $.getJSON( gVehicleNotesUrl, function(data) {
        gVehicleOrdnanceNotes.vehicles = data ;
        update_page_load_status( "vehicle-notes" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the vehicle notes:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        update_page_load_status( "vehicle-notes" ) ;
    } ) ;
    $.getJSON( gOrdnanceNotesUrl, function(data) {
        gVehicleOrdnanceNotes.ordnance = data ;
        update_page_load_status( "ordnance-notes" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the ordnance notes:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        update_page_load_status( "ordnance-notes" ) ;
    } ) ;

    // get the VASL piece info
    $.getJSON( gGetVaslPieceInfoUrl, function(data) {
        gVaslPieceInfo = data ;
        update_page_load_status( "vasl-piece-info" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the VASL piece info:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        update_page_load_status( "vasl-piece-info" ) ;
    } ) ;

    // get the online counter images data
    $.getJSON( gGetOnlineCounterImagesUrl, function(data) {
        gOnlineCounterImages = data ;
        update_page_load_status( "online-counter-images" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the online counter images:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        update_page_load_status( "online-counter-images" ) ;
    } ) ;

    // get the template pack
    $.getJSON( gGetTemplatePackUrl, function(data) {
        if ( "error" in data )
            showErrorMsg( "Can't get the template pack:<div class='pre'>" + escapeHTML(data.error) + "</div>" ) ;
        else {
            if ( "_path_" in data ) {
                showInfoMsg( "Auto-loaded template pack:<div class='pre'>" + escapeHTML(data._path_) + "</div>" ) ;
                delete data._path_ ;
            }
        }
        gDefaultTemplatePack = $.extend( true, {}, data ) ;
        install_template_pack( data ) ;
        // NOTE: If we are loading a user-defined template pack, then what we think
        // is the set of valid template ID's will depend on what's in it :-/
        gValidTemplateIds = Object.keys( data.templates ) ;
        update_page_load_status( "template-pack" ) ;
        // figure out which player flags are available (because some nationalities don't have one)
        var nats = Object.keys( gTemplatePack.nationalities ) ;
        var nFlagsChecked = 0 ;
        function onFlagChecked() {
            if ( ++nFlagsChecked === nats.length ) {
                // we've checked all the flags - now we can build the player droplists
                init_player_droplists() ;
                update_ob_tab_header( 1 ) ;
                update_ob_tab_header( 2 ) ;
                update_page_load_status( "flag-urls" ) ;
            }
        }
        nats.forEach( function( nat ) {
            var url = make_player_flag_url( nat, false ) + "?no-spacer=1" ;
            $.ajax( url, {
                success: function() { gHasPlayerFlag[nat] = true ; onFlagChecked() ; },
                error: function() { onFlagChecked() ; },
            } ) ;
        } ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the template pack:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        update_page_load_status( "template-pack" ) ;
    } ) ;

    // get the ASL Rulebook2 vehicle/ordnance note targets
    $.getJSON( gGetAslRulebook2VoNoteTargetsUrl, function(data) {
        gAslRulebook2VoNoteTargets = data ;
        update_page_load_status( "asl-rulebook2-vo-note-targets" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the ASL Rulebook2 vehicle/ordnance note targets:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        update_page_load_status( "asl-rulebook2-vo-note-targets" ) ;
    } ) ;

    // fixup the layout
    var prevHeight = [] ;
    $(window).resize( function() {
        // FUDGE! CSS grids don't seem to update their layout vertically when
        // inside a jQuery tab control - we do it manually :-/
        $(".ui-tabs-panel").each( function() {
            $(this).css( "padding", "5px" ) ; // FUDGE! doesn't work when set in the CSS :-/
            var id = $(this).attr( "id" ) ;
            var h = $(this).parent().innerHeight() - navHeight - 20 ;
            if ( h !== prevHeight[id] )
            {
                $(this).css( "height", h+"px" ) ;
                prevHeight[id] = h ;
            }
        } ) ;
    } ) ;
    $(window).trigger( "resize" ) ;

    // replace the "generate" buttons with menu droplists
    $("button.generate").each( function() { init_snippet_button( $(this) ) ; } ) ;

    // replace the "add sortable" buttons with menu droplists
    $("button.sortable-add").each( function() { init_sortable_add_button( $(this) ) ; } ) ;

    // add a tooltip to the snippet width textbox's
    $( "input.param.snippet-width" ).each( function() {
        // NOTE: I tried putting a little icon in the textbox background, and placeholder text, but it didn't
        // look good (and the whole point of removing the "Width:" labels was to remove visual clutter),
        // so we just leave the textbox's blank. Hopefully, the default values in some of them, plus the tooltip,
        // will be enough for the user to figure out what's going on.
        $(this).attr( "title", "Snippet width" ) ;
    } ) ;

    // add special options to the COMPASS snippet button menu
    var $compassMenu = $( "select[data-id='compass']" ) ;
    var compassDirns = [ "", "right", "left", "down", "up" ] ;
    compassDirns.forEach( function( dirn ) {
        var caption = (dirn === "") ? "-" : dirn[0].toUpperCase() + dirn.substring(1) ;
        $compassMenu.prepend(
            "<option value='" + dirn + "'>" + caption + "</option>"
        ) ;
    } ) ;
    $( ".snippet-control[data-id='compass'] select" ).on( "selectmenuselect", function( evt, ui ) {
        var dirn = ui.item.value ;
        if ( ! compassDirns.includes( dirn ) )
            return ;
        $( "input.param[name='COMPASS']" ).val( dirn ) ;
        updateCompassImage() ;
    } ) ;

    // watch for changes to the scenario details
    // NOTE: The following is to add/remove the "scenario modified" indicator. It's pretty inefficent
    // to do this using a timer, but we would otherwise have to attach a "on change" event handler
    // to every single input field, simple note, etc., which would be far more complicated and error-prone.
    if ( ! getUrlParam( "disable-dirty-scenario-check" ) )
        setInterval( update_scenario_status, 1*1000 ) ;

    // adjust the layout on resize
    $(window).resize( function() {
        // update the max height of sortable2 entries
        var tab_id = $("#tabs .ui-tabs-tab.ui-state-active").attr( "aria-controls" ) ;
        $( "#"+tab_id ).find( ".sortable" ).each( function() {
            $(this).sortable2( "adjust-entry-heights" ) ;
        } ) ;
    } ) ;

    // initialize keyboard handlers
    init_hotkeys() ;
    $(document).on( "keydown", function( evt ) {
        if ( evt.keyCode == $.ui.keyCode.ESCAPE )
            handle_escape( evt ) ;
    } ) ;

    // check for a dirty scenario before leaving the page
    if ( ! getUrlParam( "disable_close_window_check" ) ) {
        window.addEventListener( "beforeunload", function(evt) {
            // NOTE: We don't check for this if we're running inside the desktop app, since it will intercept the click
            // and open the page in a new external browser window (see AppWebPage.acceptNavigationRequest()).
            if ( !gWebChannelHandler && is_scenario_dirty() ) {
                evt.returnValue = "This scenario has been changed. Do you want to leave the page, and lose your changes?" ;
                return evt.returnValue ;
            }
        } ) ;
    }

    // prevent files from being dragged in
    // NOTE: It would be nice to stop the cursor from changing, but there doesn't seem to be any way of doing that :-/
    // In particualar, the dragstart events doesn't fire if something is being dragged into the browser from outside.
    $(document).on( { dragenter: stopEvent, dragleave: stopEvent, dragover: stopEvent, drop: stopEvent } ) ;

    // FUDGE! We need this to get the input box in the LFA colorpicker to work :-/
    //   https://github.com/bgrins/spectrum/issues/161#issuecomment-108089372
    $.widget( "custom.dialog", $.ui.dialog, {
        _allowInteraction: function( evt ) {
            return !! $(evt.target).is( ".sp-input" ) || this._super( evt );
        }
    } ) ;

    // figure out how many pixels an em is
    var $em = $( "<span>M</span>" ) ;
    $("body").append( $em ) ;
    gEmSize = $em.width() ;
    $em.remove() ;

    // add some dummy links for the test suite to edit templates
    function add_edit_template_link( $btn ) {
        var template_id = $btn.attr( "data-id" ) ;
        if ( ! template_id )
            return ;
        if ( template_id.substring(0,9) === "ob_setup_" )
            template_id = "ob_setup" ;
        else if ( template_id.substring(0,21) === "ob_vehicles_ma_notes_" )
            template_id = "ob_vehicles_ma_notes" ;
        else if ( template_id.substring(0,21) === "ob_ordnance_ma_notes_" )
            template_id = "ob_ordnance_ma_notes" ;
        else if ( template_id.substring(0,12) === "ob_vehicles_" )
            template_id = "ob_vehicles" ;
        else if ( template_id.substring(0,12) === "ob_ordnance_" )
            template_id = "ob_ordnance" ;
        else if ( template_id.substring(0,9) === "nat_caps_" )
            template_id = "nat_caps" ;
        $( "<a href='#' class='_edit-template-link_' data-id='" + template_id + "'" +
           " onclick='edit_template(\"" + template_id + "\")'" +
           "></a>"
        ).appendTo( "body" ) ;
    }
    if ( getUrlParam( "edit_template_links" ) ) {
        $( "button.generate" ).each( function() { add_edit_template_link( $(this) ) ; } ) ;
        $( "button.sortable-add" ).each( function() { add_edit_template_link( $(this) ) ; } ) ;
    }

    // flag that we've finished initialization
    update_page_load_status( "main" ) ;
} ) ;

function init_player_droplists()
{
    // initialize the player droplists
    function on_player_droplist_open( $sel ) {
        // remember the current selection
        $sel.data( "prev-val", $sel.val() ) ;
        // limit the droplist's height to the available space
        restrict_droplist_height( $sel ) ;
    }
    function format_player_droplist_item( opt ) {
        if ( ! opt.id )
            return opt.text ;
        var url = gHasPlayerFlag[opt.id] ? make_player_flag_url( opt.id, false ) : "" ;
        return $( "<div style='display:flex;align-items:center;height:23px;'>" +
            "<div style='width:12px;margin-right:5px;text-align:center;'>" +
            "<img src='" + url + "' style='height:12px;'>" +
            "</div>" +
            " " + opt.text +
        "</div>" ) ;
    }
    init_select2( $( "select[name='PLAYER_1']" ),
        "auto", false, format_player_droplist_item
    ).on( "select2:open", function() {
        on_player_droplist_open( $(this) ) ;
    } ).on( "change", function() {
        on_player_change_with_confirm( 1 ) ;
    } ) ;
    init_select2( $( "select[name='PLAYER_2']" ),
        "auto", false, format_player_droplist_item
    ).on( "select2:open", function() {
        on_player_droplist_open( $(this) ) ;
    } ).on( "change", function() {
        on_player_change_with_confirm( 2 ) ;
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function initSplitters()
{
    // add splitters to the SCENARIO tab
    Split( [ "#tabs-scenario .left", "#tabs-scenario .right" ], {
        direction: "horizontal",
        sizes: [ 1, 99 ],
        gutterSize: 8,
    } ) ;
    addSplitterGripper( $( "#tabs-scenario .left + .gutter" ), true, 8, {
        margin: "5px -2px", "background-color": "inherit"
    } ) ;
    Split( [ "#tabs-scenario .left .tl", "#tabs-scenario .left .bl" ], {
        direction: "vertical",
        sizes: [ 99, 1 ],
        gutterSize: 8,
    } ) ;
    addSplitterGripper( $( "#tabs-scenario .left .gutter" ), false, 8, {
        margin: "-2px 5px -6px 5px", "background-color": "inherit",
    } ) ;
    Split( [ "#tabs-scenario .right .tr", "#tabs-scenario .right .br" ], {
        direction: "vertical",
        sizes: [ 50, 50 ],
        gutterSize: 8,
    } ) ;
    addSplitterGripper( $( "#tabs-scenario .right .gutter" ), false, 8, {
        margin: "-2px 5px -6px 5px", "background-color": "inherit",
    } ) ;

    // add splitters to the OB tabs
    // NOTE: The split sizes will be set later by on_player_change().
    function initOBSplitter( col ) {
        var $col = $( "#tabs-ob" + playerNo + " ." + col ) ;
        gPlayerOBSplitters[ playerNo ].push(
            Split( [ $col.find( ".t"+col[0] )[0], $col.find( ".b"+col[0] )[0] ], {
                direction: "vertical",
                gutterSize: 8,
            } )
        ) ;
        addSplitterGripper( $col.find(".gutter"), false, 8, {
            margin: "-2px 5px -6px 5px", "background-color": "inherit",
        } ) ;
    }
    for ( var playerNo=1 ; playerNo <= 2 ; ++playerNo ) {
        gPlayerOBSplitters[ playerNo ] = [] ;
        gPlayerOBSplitters[ playerNo ].push(
            Split( [ "#tabs-ob"+playerNo+" .left", "#tabs-ob"+playerNo+" .right" ], {
                direction: "horizontal",
                gutterSize: 8,
            } )
        ) ;
        addSplitterGripper( $( "#tabs-ob"+playerNo+" .left + .gutter" ), true, 8, {
            margin: "5px -2px", "background-color": "inherit",
        } ) ;
        [ "left", "right" ].forEach( initOBSplitter ) ;
    }
}

function updatePlayerOBSplitters( playerNo )
{
    // FUDGE! We want to set the minimum width of the left column in the OB tab based on how many
    // extra template buttons the nationality has in the NOTES panel, but their widths will be 0
    // if another tab is active.
    // Instead, we count how many buttons there are, and estimate what the min-width should be,
    // based on the number of buttons and their captions.
    var nButtons=0, nChars=0 ;
    $( "#panel-ob_notes_" + playerNo + " .footer .snippet-control" ).each( function() {
        if ( $(this).css( "display" ) === "none" )
            return ;
        nButtons += 1 ;
        nChars += $(this).find( "button.generate" ).text().length ;
    } ) ;
    var minWidth = Math.max( 160 + 60*nButtons + gEmSize*nChars*0.5, 320 ) ;
    $( "#tabs-ob" + playerNo + " .left" ).css( "min-width", minWidth ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function init_snippet_button( $btn )
{
    // figure out what template we're dealing with
    var template_id = $btn.attr( "data-id" ) ;
    var template_id2 ;
    if ( template_id.substring(0,9) === "ob_setup_" )
        template_id2 = "ob_setup" ;
    else if ( template_id.substring(0,21) === "ob_vehicles_ma_notes_" )
        template_id2 = "ob_vehicles_ma_notes" ;
    else if ( template_id.substring(0,21) === "ob_ordnance_ma_notes_" )
        template_id2 = "ob_ordnance_ma_notes" ;
    else if ( template_id.substring(0,12) === "ob_vehicles_" )
        template_id2 = "ob_vehicles" ;
    else if ( template_id.substring(0,12) === "ob_ordnance_" )
        template_id2 = "ob_ordnance" ;
    else if ( template_id.substring(0,9) === "nat_caps_" )
        template_id2 = "nat_caps" ;
    else
        template_id2 = template_id ;

    // create the new button
    var buf = [ "<div class='snippet-control' data-id='" + template_id + "'>",
        $btn.prop( "outerHTML" ),
        "<select data-id='" + template_id2 + "'>",
        // NOTE: We use really short captions so they don't get truncated if the popup menu
        // is opened near the right-hand edge of the window :-/
        "<option value='edit' class='edit-template' title='" + EDIT_TEMPLATE_HINT + "'>Edit</option>",
        "<option value='as-image' class='as-image' title='Generate the snippet as an image'>Image</option>",
        "</select>",
        "</div>"
    ] ;
    var $newBtn = $( buf.join("") ) ;
    var fname="snippet.png", style="" ;
    if ( template_id.substring( 0, 9 ) === "nat_caps_" ) {
        fname = "nat-caps.png" ;
        style = "height:15px;" ;
    } else if ( template_id == "compass" ) {
        fname = "compass/none.png" ;
    }
    $newBtn.find( "button" )
        .prepend( $( "<img src='" + gImagesBaseUrl + "/" + fname + "' style='" + style + "'>" ) )
        .click( function( evt ) {
            generate_snippet( $(this), evt.shiftKey, null ) ;
            return false ;
        } )
        .attr( "title", GENERATE_SNIPPET_HINT )
        .css( { "padding-right": $btn.text() !== "" ? "10px" : "0" } ) ;

    // add in the droplist
    $newBtn.controlgroup() ;
    $newBtn.children( "select" ).each( function() {
        $(this).selectmenu( {
            classes: {
                "ui-selectmenu-button": "ui-button-icon-only",
                "ui-selectmenu-menu": "snippet-control-menu-item",
            },
        } ) ;
    } ) ;
    $newBtn.children( ".ui-button-icon-only" ).css( "width", "1em" ) ;

    // handle requests to edit the template
    $newBtn.children( "select" ).on( "selectmenuselect", function( evt, ui ) {
        if ( ui.item.value === "edit" )
            edit_template( $(this).attr("data-id") ) ;
        else if ( ui.item.value === "as-image" )
            generate_snippet( $newBtn, true, null ) ;
    } ) ;

    // replace the existing button with the new replacement button
    $btn.replaceWith( $newBtn ) ;
}

function init_sortable_add_button( $btn )
{
    // NOTE: We used to have buttons in the UI for editing templates for SCENARIO NOTE's and OB SETUP/NOTE's,
    // which took up a lot of real estate for something that almost certainly nobody is using :-/, so we instead
    // tuck them away in a droplist, attached to the ADD button. We could put a button for this functionality
    // in the "edit simple note" dialog, but here is OK, as well.
    // They are currenly only used by simple notes, and are identified by having an "id" data attribute
    // that specifies the associated template ID. Note that we don't do this for SSR's since it already has
    // a snippet control, which works a little differenly (all the simple notes are munged together into
    // a single label).

    // check if this sortable-add button should be able to edit the underlying template
    var template_id = $btn.data( "id" ) ;
    if ( ! template_id )
        return ;

    // create the new button
    // NOTE: It's important we retain the original button element, since it's already been initialized
    // as a sortable helper. Since we want to replace the original button with the new one, we have to
    // do a bit of stuffing around to figure out where to place it
    var $btnPlaceholder = $( "<span class='orig-button'></span>" ) ;
    $btn.before( $btnPlaceholder ) ;
    $btn.detach() ;
    var $newBtn = $( "<div class='snippet-control' data-id='" + template_id + "'></div>" ) ;
    $newBtn.append( $btn ) ;
    $newBtn.append( [
        "<select data-id='" + template_id + "'>",
        // NOTE: We can't have too many options, since these appear near the bottom of the window :-/
        "<option value='edit' class='edit-template' title='" + EDIT_TEMPLATE_HINT + "'>Edit</option>",
        "</select>"
    ].join( "" ) ) ;

    // add in the droplist
    $newBtn.controlgroup() ;
    $newBtn.children( "select" ).each( function() {
        $(this).selectmenu( {
            classes: {
                "ui-selectmenu-button": "ui-button-icon-only",
                "ui-selectmenu-menu": "snippet-control-menu-item",
            },
        } ) ;
    } ) ;
    $newBtn.children( ".ui-button-icon-only" ).css( {
        width: "1em", height: 28, "border-left": "none"
    } ) ;

    // give the combined button rounded corners
    $btn.css( "border-radius", "3px 0 0 3px" ) ;
    $btn.parent().children( ".ui-selectmenu-button" ).css( "border-radius", "0 3px 3px 0" ) ;

    // handle menu items
    $newBtn.children( "select" ).on( "selectmenuselect", function( evt, ui ) {
        if ( ui.item.value === "edit" )
            edit_template( $(this).data( "id" ) ) ;
    } ) ;

    // replace the existing button with the new replacement button
    $btnPlaceholder.replaceWith( $newBtn ) ;
}

function updateCompassImage() {
    // update the image in the COMPASS snippet button
    var dirn = $( "input.param[name='COMPASS']" ).val() || "none" ;
    var $btn = $( "button.generate[data-id='compass']" ) ;
    var imagePadding = {
        up: "2px 0 0 0", down: "0 0 2px 0", left: "0", right: "0",
        none: "0"
    } ;
    $btn.find( "img" ).attr( "src",
        make_app_url( "/static/images/compass/" + dirn + ".png" )
    ).css( {
        opacity: (dirn === "none") ? 1 : 0.85,
        padding: imagePadding[dirn]
    } ) ;
    $btn.button( dirn === "none" ? "disable" : "enable" ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

gPageLoadStatus = [
    "main", "app-config",
    "vehicle-listings", "ordnance-listings", "reset-scenario",
    "vehicle-notes", "ordnance-notes", "asl-rulebook2-vo-note-targets",
    "vasl-piece-info", "online-counter-images", "template-pack", "flag-urls", "default-scenario"
] ;

function update_page_load_status( id )
{
    // track the page load progress
    var pos = gPageLoadStatus.indexOf( id ) ;
    if ( pos === -1 ) {
        if ( id !== "default-scenario" )
            console.log( "Multiple page-load status:", id ) ;
        return ;
    }
    gPageLoadStatus.splice( pos, 1 ) ;
    if ( id === "template-pack" )
        $("fieldset[name='scenario']").fadeIn( 2*1000 ) ;

    // check if we can reset the scenario
    if ( gPageLoadStatus.indexOf( "reset-scenario" ) !== -1 ) {
        // NOTE: If the default scenario contains any vehicles or ordnance, it will look up the V/O listings,
        // so we need to wait until those have arrived. Note that while the default scenario will normally
        // be empty, having stuff in it is very useful during development.
        // NOTE: We also have to wait for the vehicle/ordnance notes to arrive, so that we can show/hide
        // the UI controls in the OB tabs.
        if ( gPageLoadStatus.indexOf( "vehicle-listings" ) === -1 && gPageLoadStatus.indexOf( "ordnance-listings" ) === -1 &&
             gPageLoadStatus.indexOf( "vehicle-notes" ) === -1 && gPageLoadStatus.indexOf( "ordnance-notes" ) === -1 ) {
            // NOTE: We also need to wait for the app config to arrive (for the scenario theaters).
            if ( gPageLoadStatus.indexOf( "app-config" ) === -1 ) {
                do_on_new_scenario( false ) ;
                update_page_load_status( "reset-scenario" ) ;
            }
        }
    }

    function show_startup_msgs( msgs, msg_type ) {
        if ( msg_type in msgs ) {
            for ( var i=0 ; i < msgs[msg_type].length ; ++i )
                doShowNotificationMsg( msg_type, msgs[msg_type][i] ) ;
        }
    }

    // check if the page has finished loading
    if ( gPageLoadStatus.length === 0 ) {
        // yup - update the UI
        if ( gWebChannelHandler ) {
            // inject CSS to work-around layout problems in the desktop app
            $( "head" ).append(
                "<link href='" + make_app_url("/static/css/desktop.css") + "' type='text/css' rel='stylesheet'>"
            ) ;
        }
        apply_user_settings() ;
        $( "a[href='#tabs-extras']" ).html(
            "<img src='" + gImagesBaseUrl + "/extras.png'>Extras"
        ) ;
        $("#tabs").tabs({ disabled: [] }) ;
        $("#loader").fadeOut( 500 ) ;
        // initialize the HTML WYSIWYG editors (nb: we do it here, since we need the app config
        // and template pack (for the player flags))
        initVictoryConditionsTrumbowyg() ;
        // FUDGE! There are problems with the layout jumping around during startup in the desktop app,
        // so we hide the footers on the scenario tab (which is the one visible during startup),
        // and only show them them when we're ready.
        $( "#tabs-scenario .footer" ).fadeIn( 2*1000 ) ;
        adjust_footer_vspacers() ;
        // FUDGE! This works around a timing problem during startup, where we unload the current parameters
        // before the Victory Conditions Trumbowyg control has initialized (and so doesn't get included).
        gLastSavedScenario = unload_params_for_save( false ) ;
        $("#watermark").fadeIn( 5*1000 ) ;
        // notify the test suite
        $("body").append( $("<div id='_page-loaded_'></div>") ) ;
        // notify the PyQT desktop application
        if ( gWebChannelHandler )
            gWebChannelHandler.on_app_loaded() ;
        // show any startup messages
        $.get( gGetStartupMsgsUrl, function( resp ) {
            $("body").append( $("<div id='_startup-msgs-ready_'></div>") ) ;
            show_startup_msgs( resp, "error" ) ;
            show_startup_msgs( resp, "warning" ) ;
            show_startup_msgs( resp, "info" ) ;
        } ).fail( function( xhr, status, errorMsg ) {
            showErrorMsg( "Can't get the startup messages:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        } ) ;
        // get the program info (nb: we need this, but it's not required during startup)
        getProgramInfo( function( resp ) {
            gProgramInfo = resp ;
        }, function( errorMsg ) {
            showErrorMsg( "Can't get the program info:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        } ) ;
    }
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function init_hotkeys()
{
    // initialize hotkeys
    jQuery.hotkeys.options.filterInputAcceptingElements = false ;
    jQuery.hotkeys.options.filterContentEditable = false ;
    jQuery.hotkeys.options.filterTextInputs = false ;

    function set_focus_to( tab, $ctrl ) {
        if ( $(".ui-widget-overlay").length > 0 )
            return ; // nb: a dialog is up
        if ( $( ".select2-dropdown" ).length > 0 ) {
            // FUDGE! A select2 dropdown is showing, but which one? We just close them all :-/
            $( ".app-select2" ).each( function() {
                $(this).select2( "close" ) ;
            } ) ;
        }
        var curr_tab = $("#tabs .ui-tabs-active a").attr( "href" ) ;
        if ( curr_tab !== tab )
            $("#tabs .ui-tabs-nav a[href='"+tab+"']").trigger( "click" ) ;
        if ( $ctrl )
            $ctrl.focus() ;
    }
    $(document).bind( "keydown", "alt+c", function() {
        set_focus_to( "#tabs-scenario", $("div.html-textbox[name='SCENARIO_NAME']") ) ;
    } ) ;
    $(document).bind( "keydown", "alt+p", function() {
        set_focus_to( "#tabs-scenario", $("select[name='PLAYER_1']") ) ;
    } ) ;
    $(document).bind( "keydown", "alt+y", function() {
        var $elem = $(".trumbowyg-editor[name='VICTORY_CONDITIONS']") ;
        if ( $elem.parent().hasClass( "trumbowyg-editor-visible" ) )
            set_focus_to( "#tabs-scenario", $elem ) ;
        else
            set_focus_to( "#tabs-scenario", $elem.parent().find( ".trumbowyg-textarea" ) ) ;
    } ) ;
    $(document).bind( "keydown", "alt+0", function() {
        set_focus_to( "#tabs-scenario", $("div.html-textbox[name='SCENARIO_NAME']") ) ; // nb: for consistency with Alt-1 and Alt-2
    } ) ;
    $(document).bind( "keydown", "alt+1", function() {
        set_focus_to( "#tabs-ob1" ) ;
    } ) ;
    $(document).bind( "keydown", "alt+2", function() {
        set_focus_to( "#tabs-ob2" ) ;
    } ) ;
    $(document).bind( "keydown", "alt+x", function() {
        set_focus_to( "#tabs-extras" ) ;
    } ) ;
}

// --------------------------------------------------------------------

function install_template_pack( data )
{
    // install the template pack
    gTemplatePack = data ;
    init_extras() ;

    // update the player droplists
    var nats = get_sorted_nats() ;
    var curSel = {
        1: $("select[name='PLAYER_1']").val(),
        2: $("select[name='PLAYER_2']").val()
    } ;
    var buf = [] ;
    for ( var i=0 ; i < nats.length ; ++i )
        buf.push( "<option value='" + nats[i] + "'>" + get_nationality_display_name(nats[i]) + "</option>" ) ;
    buf = buf.join( "" ) ;
    for ( var player_no=1 ; player_no <= 2 ; ++player_no ) {
        var $sel = $( "select[name='PLAYER_" + player_no + "']" ) ;
        $sel.html( buf ) ;
        if ( curSel[player_no] )
            $sel.val( curSel[player_no] ) ; // nb: we don't trigger a "change" event
    }

    // update the OB tab headers
    // NOTE: We don't do this while the page is initially loading, since we need the player flags.
    if ( gPageLoadStatus.indexOf( "flag-urls" ) === -1 ) {
        update_ob_tab_header( 1 ) ;
        update_ob_tab_header( 2 ) ;
    }

    // update the snippet buttons
    function update_generate_button( $btn ) {
        var template_id = $btn.attr( "data-id" ) ;
        if ( template_id.substr( 0, 7 ) === "extras/" )
            return ;
        if ( template_id.match( /^ob_(vehicles|ordnance).*_[12]$/ ) )
            template_id = template_id.substring( 0, template_id.length-2 ) ;
        var enable = is_template_available( template_id ) ;
        if ( $btn.parent().hasClass( "snippet-control" ) ) {
            $btn.parent().controlgroup( enable ? "enable" : "disable" ) ;
            // check if there's a corresponding "snippet-width" textbox
            var sel = $btn.attr( "data-id" ) ;
            if ( sel.match( /_[12]$/ ) )
                sel = sel.substr( 0, sel.length-2 ) + "_width" + sel.substr( sel.length-2 ) ;
            else
                sel += "_width" ;
            var $width = $( "input.snippet-width[name='" + sel.toUpperCase() + "']" ) ;
            if ( $width.length > 0 ) {
                // yup - update it as well
                $width.val( "" ).prop( "disabled", !enable ) ;
            }
        } else
            $btn.button( enable ? "enable": "disable" ) ;
    }
    function update_sortable_add_button( $btn ) {
        var template_id = $btn.attr( "data-id" ) ;
        if ( ! template_id )
            return ;
        var $dropdown = $btn.parent().find( "select[data-id='" + template_id + "']" ) ;
        var enable = is_template_available( template_id ) ;
        $dropdown.find( "option.edit-template" ).attr( "disabled", !enable ) ;
        $dropdown.selectmenu( "refresh" ) ;
    }
    $( "button.generate" ).each( function() { update_generate_button( $(this) ) ; } ) ;
    $( "button.sortable-add" ).each( function() { update_sortable_add_button( $(this) ) ; } ) ;

    // update the turn track controls
    enable = is_template_available( "turn_track" ) ;
    $( "select[name='TURN_TRACK_NTURNS']" ).css("color","red").prop( "disabled", !enable ) ;
    $( "button#turn-track-settings" ).button( enable ? "enable" : "disable" ) ;
}

// --------------------------------------------------------------------

function on_player_change_with_confirm( player_no )
{
    // check if we need to do anything
    var $select = $( "select[name='PLAYER_" + player_no + "']" ) ;
    if ( $select.val() == $select.data("prev-val") )
        return ;

    // check if we should confirm this operation
    if ( is_player_ob_empty( player_no ) ) {
        // nope - just do it
        on_player_change( player_no ) ;
    } else {
        // yup - make it so
        ask( "Change player nationality",
            "<p> Do you want to change this player's nationality? <p> You will lose changes made to their OB.", {
            ok: function() { on_player_change( player_no ) ; },
            cancel: function() { $select.val( $select.data("prev-val") ).trigger( "change" ) ; },
        } ) ;
    }
}

function is_player_ob_empty( player_no )
{
    // check if the specified player's OB is empty
    var is_empty = true ;
    $( "#tabs-ob" + player_no + " .sortable" ).each( function() {
        if ( $(this).children( "li" ).length > 0 )
            is_empty = false ;
    } ) ;
    return is_empty ;
}

function on_player_change( player_no )
{
    // update the UI
    var player_nat = update_ob_tab_header( player_no ) ;
    update_nationality_specific_buttons( player_no ) ;
    $( "div.html-textbox[name='PLAYER_" + player_no + "_DESCRIPTION']" ).html( "" ) ;
    updateTrumbowygFlagsDropdown( $( ".param[name='VICTORY_CONDITIONS']" ) ) ;

    // show/hide the vehicle/ordnance multi-applicable notes controls
    function update_ma_notes_controls( vo_type ) {
        if ( ! gTemplatePack.nationalities )
            return ;
        var show = ( gVehicleOrdnanceNotes[vo_type] && gVehicleOrdnanceNotes[vo_type][player_nat] ) ||
                   ["allied-minor","axis-minor"].indexOf( gTemplatePack.nationalities[ player_nat ].type ) !== -1 ||
                   player_nat === "free-french" ;
        var $fieldset = $( "#tabs-ob" + player_no + " fieldset[name='ob_" + vo_type + "_" + player_no ) ;
        $fieldset.find( ".snippets-notes" ).css( "display", show?"block":"none" ) ;
        $fieldset.find( "label[for='ob']" ).css( "display", show?"inline-block":"none" ) ;
        return show ;
    }
    var hasVehicles = update_ma_notes_controls( "vehicles" ) ;
    var hasOrdnance = update_ma_notes_controls( "ordnance" ) ;
    // TO DO: We should also show a button that lets the ob_vehicle/ordnance_note template to be edited.

    // reset the OB params
    $( "#ob_setups-sortable_" + player_no ).sortable2( "delete-all" ) ;
    $("input[name='OB_SETUP_WIDTH_"+player_no+"']").val( "" ) ;
    $( "#ob_notes-sortable_" + player_no ).sortable2( "delete-all" ) ;
    $( "#ob_vehicles-sortable_" + player_no ).sortable2( "delete-all" ) ;
    $("input[name='OB_VEHICLES_WIDTH_"+player_no+"']").val( "" ) ;
    $( "#ob_ordnance-sortable_" + player_no ).sortable2( "delete-all" ) ;
    $("input[name='OB_ORDNANCE_WIDTH_"+player_no+"']").val( "" ) ;

    // disable the vehicles/ordnance panels if none are available
    function update_add_vo_button( vo_type ) {
        var $panel = $( "#panel-ob_" + vo_type + "_" + player_no ) ;
        if ( gVehicleOrdnanceListings[ vo_type ] !== undefined && gVehicleOrdnanceListings[vo_type][ player_nat ] !== undefined ) {
            var hasMaNotes = (vo_type === "vehicles" && hasVehicles) || (vo_type === "ordnance" && hasOrdnance) ;
            $panel.parent().css( "min-height", hasMaNotes ? "10.7em" : "9em" ) ;
            $panel.find( ".footer" ).show() ;
        } else {
            $panel.parent().css( "min-height", "2.5em" ) ;
            $panel.find( ".footer" ).hide() ;
            $panel.find( ".sortable-hint" ).html( "There are no " + vo_type + " available." ) ;
        }
    }
    update_add_vo_button( "vehicles" ) ;
    update_add_vo_button( "ordnance" ) ;

    // reset the player's splitters
    updatePlayerOBSplitters( player_no ) ;
    gPlayerOBSplitters[ player_no ].forEach( function( splitter ) {
        splitter.setSizes( [ 50, 50 ] ) ;
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function update_ob_tab_header( player_no )
{
    // update the OB tab header for the specified player
    var player_nat = $( "select[name='PLAYER_" + player_no + "']" ).val() ;
    var display_name = get_nationality_display_name( player_nat ) ;
    var image_url = make_player_flag_url( player_nat, false ) ;
    var $elem = $( "#tabs .ui-tabs-nav a[href='#tabs-ob" + player_no + "']" ) ;
    var buf = [] ;
    if ( gHasPlayerFlag[ player_nat ] )
        buf.push( "<img src='" + image_url + "'>" ) ;
    buf.push( "<span>" + escapeHTML(display_name) + " OB</span>" ) ;
    $elem.html( buf.join("") ) ;

    return player_nat ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function update_nationality_specific_buttons( player_no )
{
    // initialize
    var player_nat = $( "select[name='PLAYER_" + player_no + "']" ).val() ;
    var theater = $( "select.param[name='SCENARIO_THEATER']" ).val() ;
    if ( theater )
        theater = theater.toLowerCase() ;

    // hide/show each nationality-specific button
    var $elem ;
    for ( var button_id in NATIONALITY_SPECIFIC_BUTTONS ) {
        var show = false ;
        for ( var i=0 ; i < NATIONALITY_SPECIFIC_BUTTONS[button_id].length ; ++i ) {
            var nat = NATIONALITY_SPECIFIC_BUTTONS[button_id][i] ;
            if ( nat == player_nat )
                show = true ;
            else if ( nat == player_nat+"@"+theater )
                show = true ;
            else {
                var pos = nat.indexOf( "!" ) ;
                if ( pos !== -1 )
                    show = nat.substr(0,pos) == player_nat && nat.substr(pos+1) !== theater ;
            }
        }
        $elem = $( "#panel-ob_notes_" + player_no + " div.snippet-control[data-id='" + button_id + "']" ) ;
        $elem.css( "display", show ? "inline-block" : "none" ) ;
    }

    // update the CAPABILITIES button
    var $btn = $( "button.generate[data-id='nat_caps_" + player_no + "']" ) ;
    if ( get_national_capabilities( player_nat ) )
        $btn.removeClass( "inactive" ) ;
    else
        $btn.addClass( "inactive" ) ;
}

// --------------------------------------------------------------------

function on_tab_activate( evt, ui )
{
    function set_colors( tab_id, bgd, border ) {
        var $elem = $("#tabs .ui-tabs-tab[aria-controls='" + tab_id + "']" ) ;
        $elem.css( {
            background: bgd,
            border: "1px solid "+border,
            "border-bottom": "none",
        } ) ;
        $( "#"+tab_id ).css( "border", "1px solid "+border ) ;
    }

    // style the tab being de-activated
    var tab_id = ui.oldPanel.prop( "id" ) ;
    set_colors( tab_id, "#f6f6f6", "#c5c5c5" ) ;

    // set the tab being activated
    function set_colors_for_player( tab_id, player_no ) {
        var colors = get_player_colors( player_no ) ;
        set_colors( tab_id, colors[0], colors[2] ) ;
    }
    tab_id = ui.newPanel.prop( "id" ) ;
    var $tab = $( "#"+tab_id ) ;
    if ( tab_id === "tabs-ob1" )
        set_colors_for_player( tab_id, 1 ) ;
    else if ( tab_id === "tabs-ob2" )
        set_colors_for_player( tab_id, 2 ) ;
    else
        set_colors( tab_id, "#ddd", "#ccc" ) ;

    // adjust the layout
    $tab.find( ".sortable" ).each( function() {
        $(this).sortable2( "adjust-entry-heights" ) ;
    } ) ;
    adjust_footer_vspacers() ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function adjust_footer_vspacers()
{
    // FUDGE! Different browsers have different ideas about how big 100% of a fieldset is :-/
    // To work-around this, we compare where the bottom of each footer is, relative to
    // its parent fieldset, and adjust a vertical spacer element to compensate. Sigh...
    $("fieldset").each( function() {
        // check if the next fieldset has a footer
        $footer = $(this).find( ".footer" ) ;
        if ( $footer.length === 0 )
            return ;
        // check if we've already adjusted this fieldset
        if ( $(this).find( ".vspacer" ).length !== 0 )
            return ;
        // locate the bottom of the fieldset
        var $fieldset = $(this) ;
        var fieldset_bottom = $fieldset.position().top + $fieldset.height() ;
        if ( fieldset_bottom < 0 )
            return ;
        // locate the bottom of the footer
        var footer_bottom = $footer.position().top + $footer.height() ;
        var delta = footer_bottom - fieldset_bottom ;
        delta -= 4 ;
        if ( gWebChannelHandler && $(this).attr("name").indexOf( "ob_" ) === 0 )
            delta += 28 ;
        // add a vertical spacer after the footer (to push it up a bit)
        $footer.after( "<div class='vspacer' style='height:" + Math.ceil(Math.max(0,delta)) + "px'></div>" ) ;
    } ) ;

}

// --------------------------------------------------------------------

function handle_escape( evt )
{
    // NOTE: Handling Escape is messy, since we could have a modal dialog that opened another modal dialog
    // that opened an image gallery, etc. We add a global keydown handler for Escape and try to figure out
    // what we should do here. The only requirement is that dialogs set "closeOnEscape".

    // NOTE: We ignore ESCAPE if an image gallery is on-screen (we let it handle it).
    if ( $( ".lg-outer" ).length > 0 )
        return ;

    // always close the menu and any notifications
    $("#menu input").popmenu( "hide" ) ;
    $(".growl-close").each( function() {
        $(this).trigger( "click" ) ;
    } ) ;

    // check if there is a Trumbowyg control full-screen
    var $elem = $( ".trumbowyg-fullscreen" ) ;
    if ( $elem.length > 0 ) {
        // yup - restore it back to normal size
        $elem.children( ".trumbowyg-editor" ).trumbowyg( "execCmd", { cmd: "fullscreen" } ) ;
        return ;
    }

    // find the top-most dialog (if any) and close it
    var $topmost = findTopmostDialog() ;
    if ( $topmost ) {
        var $dlg = $topmost.children( ".ui-dialog-content" ) ;
        if ( [ "please-wait", "ask", "lfa" ].indexOf( $dlg.attr("id") ) === -1 ) {
            // NOTE: We prefer clicking on a Cancel button, so that the dialog has a chance
            // to confirm (and perhaps cancel) the operation.
            var $btn = $topmost.find( ".ui-dialog-buttonpane button.cancel" ) ;
            if ( $btn.length > 0 )
                $btn.trigger( "click" ) ;
            else
                $topmost.children( ".ui-dialog-content" ).dialog( "close" ) ;
        }
    }
}

function findTopmostDialog()
{
    // find the top-most dialog
    var $topmost = null ;
    $( ".ui-dialog" ).each( function() {
        if ( $(this).css( "display" ) != "block" )
            return ;
        if ( $topmost === null || $(this).css("z-index") > $topmost.css("z-index") )
            $topmost = $(this) ;
    } ) ;
    return $topmost ;
}

// --------------------------------------------------------------------

var gProgramInfoDlgState = null ;

function show_program_info()
{
    // show the PROGRAM INFO dialog
    var caption = "Program info" ;
    if ( gAppConfig.APP_NAME ) {
        caption = gAppConfig.APP_NAME ;
        if ( gAppConfig.APP_VERSION )
            caption += " (" + gAppConfig.APP_VERSION + ")" ;
    }
    $( "#program-info" ).dialog( {
        title: caption,
        dialogClass: "program-info",
        modal: true,
        position: gProgramInfoDlgState ? gProgramInfoDlgState.position : { my: "center", at: "center", of: window },
        width: gProgramInfoDlgState ? gProgramInfoDlgState.width : $(window).width() * 0.8,
        height: gProgramInfoDlgState ? gProgramInfoDlgState.height : $(window).height() * 0.8,
        minWidth: 750,
        minHeight: 400,
        open: function() {
            var $dlg = $(this) ;
            $dlg.find( ".content" ).hide() ;
            $dlg.find( ".loader" ).show() ;
            getProgramInfo( function( resp ) {
                $dlg.find( ".loader" ).hide() ;
                $dlg.find( ".content" ).html( resp ).fadeIn( 250 ) ;
            }, function( errorMsg ) {
                showErrorMsg( "Can't get the program info:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
                $dlg.dialog( "close" ) ;
            }, "html" ) ;
        },
        beforeClose: function() {
            gProgramInfoDlgState = getDialogState( $(this) ) ;
        },
        buttons: {
            OK: function() {
                $(this).dialog( "close" ) ;
            }
        },
    } ) ;
}

function getProgramInfo( onSuccess, onError, format )
{
    // get the program info
    var url = gGetProgramInfoUrl + "?tz_offset=" + -new Date().getTimezoneOffset() ;
    if ( format )
        url += "&f=" + format ;
    $.get( url, function( resp ) {
        onSuccess( resp ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        onError( errorMsg ) ;
    } ) ;
}
// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function show_help()
{
    // check if we need to load the HELP tab
    var $iframe = $("#tabs-help iframe") ;
    if ( ! $iframe.attr( "src" ) ) {
        // yup - make it so
        // NOTE: We show the help in an iframe so that we can use the same files elsewhere e.g. on the web site or Github.
        var url = gHelpUrl + "?version=" + gAppVersion + "&embedded=1&tab=userguide" ;
        if ( getUrlParam( "pyqt" ) )
            url += "&pyqt=1" ;
        $iframe.attr( "src", url ) ;
        $("#tabs .ui-tabs-tab[aria-controls='tabs-help']").show() ;
    }

    // show the HELP tab
    $("#tabs a[href='#tabs-help']").click() ;
}
