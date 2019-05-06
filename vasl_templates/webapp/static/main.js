APP_URL_BASE = window.location.origin ;

gAppConfig = {} ;
gDefaultTemplatePack = null ;
gTemplatePack = {} ;
gValidTemplateIds = [] ;
gVehicleOrdnanceListings = {} ;
gVehicleOrdnanceNotes = {} ;
gVaslPieceInfo = {} ;

gWebChannelHandler = null ;
gEmSize = null ;

var NATIONALITY_SPECIFIC_BUTTONS = {
    "russian": [ "mol", "mol-p" ],
    "german": [ "pf", "psk", "atmm" ],
    "american": [ "baz" ],
    "british": [ "piat" ],
    "japanese": [ "thh" ],
} ;

GENERATE_SNIPPET_HINT = "Generate an HTML snippet (shift-click to get an image)." ;

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
    $menu.popmenu( {
        new_scenario: { label: "New scenario", action: function() { on_new_scenario() ; } },
        load_scenario: { label: "Load scenario", action: on_load_scenario },
        save_scenario: { label: "Save scenario", action: on_save_scenario },
        update_vsav: { label: "Update VASL scenario", action: on_update_vsav },
        separator: { type: "separator" },
        template_pack: { label: "Load template pack", action: on_template_pack },
        separator2: { type: "separator" },
        user_settings: { label: "Settings", action: user_settings },
        show_help: { label: "Help", action: show_help },
    } ) ;
    // nb: we only show the popmenu on left click (not the normal right-click)
    $menu.off( "contextmenu" ) ;
    $menu.click( function() {
        $(this).blur() ;
        var pos = $(this).offset() ;
        $(this).data( "PopMenu.contextmenu" ).data( "PopMenu.instance" ).show(
            pos.left+$(this).width(), pos.top+$(this).height()+2, "fade", 200
        ) ;
    } ) ;
    // nb: we dismiss the popmenu and any notifications on ESCAPE
    $(document).keydown( function(evt) {
        if ( evt.keyCode == 27 ) {
            $menu.popmenu( "hide" ) ;
            $(".growl-close").each( function() {
                $(this).trigger( "click" ) ;
            } ) ;
        }
    } ) ;
    // add handlers
    $("#load-scenario").change( on_load_scenario_file_selected ) ;
    $("#load-template-pack").change( on_template_pack_file_selected ) ;
    $("#load-vsav").change( on_load_vsav_file_selected ) ;
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

    // initialize ROAR integration
    $("#search-roar").button( {} )
        .html( "<img src='" + gImagesBaseUrl + "/search.png'>" )
        .click( search_roar ) ;
    $("#go-to-roar").button( {} ).click( go_to_roar_scenario ) ;
    $("#disconnect-roar").button( {} )
        .html( "<img src='" + gImagesBaseUrl + "/cross.png'>" )
        .click( disconnect_roar ) ;

    // initialize the scenario theater
    init_select2( $("select[name='SCENARIO_THEATER']"), "5em", false, null ) ;

    // initialize the scenario date picker
    $("input[name='SCENARIO_DATE']").datepicker( {
        showAnim: "slideDown",
        changeMonth: true, changeYear: true,
        onClose: on_scenario_date_change,
    } ) ;

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
        var url = make_player_flag_url( opt.id, false ) ;
        return $( "<div style='display:flex;align-items:center;'>" +
            "<img src='" + url + "' style='height:0.9em;margin-right:0.25em;'>" +
            " " + opt.text +
        "</div>" ) ;
    }
    init_select2( $( "select[name='PLAYER_1']" ),
        "9.5em", false, format_player_droplist_item
    ).on( "select2:open", function() {
        on_player_droplist_open( $(this) ) ;
    } ).on( "change", function() {
        on_player_change_with_confirm( 1 ) ;
    } ) ;
    init_select2( $( "select[name='PLAYER_2']" ),
        "9.5em", false, format_player_droplist_item
    ).on( "select2:open", function() {
        on_player_droplist_open( $(this) ) ;
    } ).on( "change", function() {
        on_player_change_with_confirm( 2 ) ;
    } ) ;

    // load the ELR's and SAN's
    var buf = [] ;
    for ( var i=0 ; i <= 5 ; ++i ) // nb: A19.1: ELR is 0-5
        buf.push( "<option value='" + i + "'>" + i + "</option>" ) ;
    buf = buf.join( "" ) ;
    var player_no, $sel ;
    for ( player_no=1 ; player_no <= 2 ; ++player_no ) {
        init_select2( $( "select[name='PLAYER_" + player_no + "_ELR']" ),
            "3em", false, null
        ).html( buf ) ;
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

    // get the application config
    $.getJSON( gAppConfigUrl, function(data) {
        gAppConfig = data ;
        update_page_load_status( "app-config" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the application config:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
    } ) ;

    // get the vehicle/ordnance listings
    $.getJSON( gVehicleListingsUrl, function(data) {
        gVehicleOrdnanceListings.vehicles = data ;
        update_page_load_status( "vehicle-listings" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the vehicle listings:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
    } ) ;
    $.getJSON( gOrdnanceListingsUrl, function(data) {
        gVehicleOrdnanceListings.ordnance = data ;
        update_page_load_status( "ordnance-listings" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the ordnance listings:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
    } ) ;
    $.getJSON( gVehicleNotesUrl, function(data) {
        gVehicleOrdnanceNotes.vehicles = data ;
        update_page_load_status( "vehicle-notes" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the vehicle notes:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
    } ) ;
    $.getJSON( gOrdnanceNotesUrl, function(data) {
        gVehicleOrdnanceNotes.ordnance = data ;
        update_page_load_status( "ordnance-notes" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the ordnance notes:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
    } ) ;

    // get the VASL piece info
    $.getJSON( gGetVaslPieceInfoUrl, function(data) {
        gVaslPieceInfo = data ;
        update_page_load_status( "vasl-piece-info" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the VASL piece info:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
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
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the template pack:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
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
        // FUDGE! Some panels are rendering with the wrong width in IE :-/
        if ( isIE() ) {
            var set_width = function($elem) { $elem.width( $elem.parent().width() ) ; } ;
            set_width( $("#panel-vc textarea") ) ;
            set_width( $("#panel-ssr .content") ) ;
        }
    } ) ;
    $(window).trigger( "resize" ) ;

    // replace all the "generate" buttons with "generate/edit" button/droplist's
    $("button.generate").each( function() { init_snippet_button( $(this) ) ; } ) ;

    // handle requests to edit the templates
    $("button.edit-template").click( function() {
        edit_template( $(this).data( "id" ) ) ;
    } ).html( "<div><img src='" + gImagesBaseUrl + "/edit-template.png'>Edit</div>" )
        .attr( "title", "Edit the template." )
        .button( {} ) ;

    // watch for changes to the scenario details
    $("input[name='SCENARIO_NAME']").on( "input propertychange paste", function() {
        on_scenario_details_change() ;
    } ) ;
    $("input[name='SCENARIO_ID']").on( "input propertychange paste", function() {
        on_scenario_details_change() ;
    } ) ;

    // adjust the layout on resize
    $(window).resize( function() {
        // update the max height of sortable2 entries
        var tab_id = $("#tabs .ui-tabs-tab.ui-state-active").attr( "aria-controls" ) ;
        $( "#"+tab_id ).find( ".sortable" ).each( function() {
            $(this).sortable2( "adjust-entry-heights" ) ;
        } ) ;
    } ) ;

    // initialize hotkeys
    init_hotkeys() ;

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

    // figure out how many pixels an em is
    var $em = $( "<span>M</span>" ) ;
    $("body").append( $em ) ;
    gEmSize = $em.width() ;
    $em.remove() ;

    // add some dummy links for the test suite to edit templates
    if ( getUrlParam( "edit_template_links" ) ) {
        $("button.generate").each( function() {
            var template_id = $(this).attr( "data-id" ) ;
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
            $( "<a href='#' class='_edit-template-link_' data-id='" + template_id + "'" +
               " onclick='edit_template(\"" + template_id + "\")'" +
               "></a>"
            ).appendTo( "body" ) ;
        } ) ;
    }

    // flag that we've finished initialization
    update_page_load_status( "main" ) ;
    $("input[name='SCENARIO_NAME']").focus().focus() ;
} ) ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function init_snippet_button( $btn )
{
    // figure out what template we're dealing with
    var template_id = $btn.attr( "data-id" ) ;
    var template_id2 ;
    if ( template_id.substring(0,9) === "ob_setup_" )
        template_id2 = "ob_setup" ;
    else if ( template_id.substring(0,21) == "ob_vehicles_ma_notes_" )
        template_id2 = "ob_vehicles_ma_notes" ;
    else if ( template_id.substring(0,21) == "ob_ordnance_ma_notes_" )
        template_id2 = "ob_ordnance_ma_notes" ;
    else if ( template_id.substring(0,12) == "ob_vehicles_" )
        template_id2 = "ob_vehicles" ;
    else if ( template_id.substring(0,12) == "ob_ordnance_" )
        template_id2 = "ob_ordnance" ;
    else
        template_id2 = template_id ;

    // create the new button
    var buf = [ "<div class='snippet-control' data-id='" + template_id + "'>",
        $btn.prop( "outerHTML" ),
        "<select data-id='" + template_id2 + "'>",
        "<option value='edit' class='edit-template' title='Edit the template that will generate this snippet.'>Edit</option>",
        "</select>",
        "</div>"
    ] ;
    var $newBtn = $( buf.join("") ) ;
    $newBtn.find( "button" ).prepend(
        $( "<img src='" + gImagesBaseUrl + "/snippet.png'>" )
    ).click( function( evt ) {
        generate_snippet( $(this), evt, null ) ;
        return false ;
    } ).attr( "title", GENERATE_SNIPPET_HINT ) ;

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
    $newBtn.children( ".ui-selectmenu-button" ).click( function() { $btn.blur() ; } ) ;

    // handle requests to edit the template
    $newBtn.children( "select" ).on( "selectmenuselect", function() {
        edit_template( $(this).attr("data-id") ) ;
    } ) ;

    // replace the existing button with the new replacement button
    $btn.replaceWith( $newBtn ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

gPageLoadStatus = [
    "main", "app-config",
    "vehicle-listings", "ordnance-listings", "reset-scenario",
    "vehicle-notes", "ordnance-notes",
    "vasl-piece-info", "template-pack", "default-scenario"
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

    // check if the vehicle/ordnance listings have finished loading
    if ( gPageLoadStatus.indexOf( "vehicle-listings" ) === -1 && gPageLoadStatus.indexOf( "ordnance-listings" ) === -1 ) {
        // NOTE: If the default scenario contains any vehicles or ordnance, it will look up the V/O listings,
        // so we need to wait until those have arrived. Note that while the default scenario will normally
        // be empty, having stuff in it is very useful during development.
        if ( gPageLoadStatus.indexOf( "reset-scenario" ) !== -1 ) {
            do_on_new_scenario( false ) ;
            update_page_load_status( "reset-scenario" ) ;
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
        apply_user_settings() ;
        $( "a[href='#tabs-extras'] div" ).html(
            "<img src='" + gImagesBaseUrl + "/extras.png'>&nbsp;Extras"
        ) ;
        $("#tabs").tabs({ disabled: [] }) ;
        $("#loader").fadeOut( 500 ) ;
        adjust_footer_vspacers() ;
        // NOTE: The watermark image appears briefly in IE when reloading the page, but not even
        // creating the watermark dynamically and removing it when the page unloads fixes it :-(
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
        // preload the flag images (so that the player droplist renders immediately)
        for ( var nat in gTemplatePack.nationalities ) {
            $("body").append( $(
                "<img src='" + make_player_flag_url(nat,false) + "' style='display:none;'>"
            ) ) ;
        }
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
        set_focus_to( "#tabs-scenario", $("input[name='SCENARIO_NAME']") ) ;
    } ) ;
    $(document).bind( "keydown", "alt+p", function() {
        set_focus_to( "#tabs-scenario", $("select[name='PLAYER_1']") ) ;
    } ) ;
    $(document).bind( "keydown", "alt+y", function() {
        set_focus_to( "#tabs-scenario", $("textarea[name='VICTORY_CONDITIONS']") ) ;
    } ) ;
    $(document).bind( "keydown", "alt+0", function() {
        set_focus_to( "#tabs-scenario", $("input[name='SCENARIO_NAME']") ) ; // nb: for consistency with Alt-1 and Alt-2
    } ) ;
    $(document).bind( "keydown", "alt+1", function() {
        set_focus_to( "#tabs-ob1", $("textarea[name='OB_SETUP_1']") ) ;
    } ) ;
    $(document).bind( "keydown", "alt+2", function() {
        set_focus_to( "#tabs-ob2", $("textarea[name='OB_SETUP_2']") ) ;
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

    // sort the nationalities
    var nats = Object.keys( gTemplatePack.nationalities ) ;
    nats.sort( function( lhs, rhs ) {
        lhs = gTemplatePack.nationalities[lhs].display_name.toUpperCase() ;
        rhs = gTemplatePack.nationalities[rhs].display_name.toUpperCase() ;
        if ( lhs < rhs )
            return -1 ;
        else if ( lhs > rhs )
            return +1 ;
        else
            return 0 ;
    } ) ;

    // update the player droplists
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
    // NOTE: We don't do this while the page is initially loading, it will be done when the default scenario loaded.
    if ( gPageLoadStatus.indexOf( "template-pack" ) === -1 ) {
        update_ob_tab_header( 1 ) ;
        update_ob_tab_header( 2 ) ;
    }

    // update the snippet buttons
    function update_button( $btn ) {
        var template_id = $btn.attr( "data-id" ) ;
        if ( template_id.substr( 0, 7 ) === "extras/" )
            return ;
        if ( template_id.match( /^ob_(vehicles|ordnance).*_[12]$/ ) )
            template_id = template_id.substring( 0, template_id.length-2 ) ;
        var enable = is_template_available( template_id ) ;
        if ( $btn.parent().hasClass( "snippet-control" ) )
            $btn.parent().controlgroup( enable ? "enable" : "disable" ) ;
        else
            $btn.button( enable ? "enable": "disable" ) ;
    }
    $( "button.generate" ).each( function() { update_button( $(this) ) ; } ) ;
    $( "button.edit-template" ).each( function() { update_button( $(this) ) ; } ) ;
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
            "<p>Do you want to change this player's nationality?<p>You will lose changes made to their OB.", {
            ok: function() { on_player_change( player_no ) ; },
            cancel: function() {
                $select.val( $select.data("prev-val") ).trigger( "change" ) ;
            },
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
    // update the tab label
    var player_nat = update_ob_tab_header( player_no ) ;

    // show/hide the nationality-specific buttons
    for ( var nat in NATIONALITY_SPECIFIC_BUTTONS ) {
        for ( var i=0 ; i < NATIONALITY_SPECIFIC_BUTTONS[nat].length ; ++i ) {
            var button_id = NATIONALITY_SPECIFIC_BUTTONS[nat][i] ;
            var $elem = $( "#panel-ob_notes_" + player_no + " div.snippet-control[data-id='" + button_id + "']" ) ;
            $elem.css( "display", nat == player_nat ? "inline-block" : "none" ) ;
        }
    }

    // show/hide the vehicle/ordnance multi-applicable notes controls
    function update_ma_notes_controls( vo_type ) {
        var show = ( gVehicleOrdnanceNotes[vo_type] && gVehicleOrdnanceNotes[vo_type][player_nat] ) ||
                   ["allied-minor","axis-minor"].indexOf( gTemplatePack.nationalities[ player_nat ].type ) !== -1 ||
                   player_nat === "free-french" ;
        var $fieldset = $( "#tabs-ob" + player_no + " fieldset[name='ob_" + vo_type + "_" + player_no ) ;
        $fieldset.find( ".snippets-notes" ).css( "display", show?"block":"none" ) ;
        $fieldset.find( "label[for='ob']" ).css( "display", show?"inline-block":"none" ) ;
    }
    update_ma_notes_controls( "vehicles" ) ;
    update_ma_notes_controls( "ordnance" ) ;
    // TO DO: We should also show a button that lets the ob_vehicle/ordnance_note template to be edited.

    // reset the OB params
    $( "#ob_setups-sortable_" + player_no ).sortable2( "delete-all" ) ;
    $("input[name='OB_SETUP_WIDTH_"+player_no+"']").val( "" ) ;
    $( "#ob_notes-sortable_" + player_no ).sortable2( "delete-all" ) ;
    $( "#ob_vehicles-sortable_" + player_no ).sortable2( "delete-all" ) ;
    $("input[name='OB_VEHICLES_WIDTH_"+player_no+"']").val( "" ) ;
    $( "#ob_ordnance-sortable_" + player_no ).sortable2( "delete-all" ) ;
    $("input[name='OB_ORDNANCE_WIDTH_"+player_no+"']").val( "" ) ;

    // update the ROAR info panel
    set_roar_scenario( $("input[name='ROAR_ID']").val() ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function update_ob_tab_header( player_no )
{
    // update the OB tab header for the specified player
    var player_nat = $( "select[name='PLAYER_" + player_no + "']" ).val() ;
    var display_name = get_nationality_display_name( player_nat ) ;
    var image_url = make_player_flag_url( player_nat, false ) ;
    var $elem = $( "#tabs .ui-tabs-nav a[href='#tabs-ob" + player_no + "']" ) ;
    $elem.html(
        "<img src='" + image_url + "'>&nbsp;" +
        "<span>" + escapeHTML(display_name) + " OB</span>"
    ) ;

    return player_nat ;
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
        // add a vertical spacer after the footer (to push it up a bit)
        $footer.after( "<div class='vspacer' style='height:" + Math.ceil(Math.max(0,delta)) + "px'></div>" ) ;
    } ) ;

}

// --------------------------------------------------------------------

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
