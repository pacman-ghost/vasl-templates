gTemplatePack = {} ;
gDefaultNationalities = {} ;
gValidTemplateIds = [] ;
gVehicleOrdnanceListings = {} ;

gWebChannelHandler = null ;
gEmSize = null ;

var _NATIONALITY_SPECIFIC_BUTTONS = {
    "russian": [ "mol", "mol-p" ],
    "german": [ "pf", "psk", "atmm" ],
    "american": [ "baz" ],
    "british": [ "piat" ],
} ;

// --------------------------------------------------------------------

$(document).ready( function () {

    // initialize the PyQt web channel
    if ( getUrlParam( "pyqt" ) ) {
        $.getScript( "qrc:///qtwebchannel/qwebchannel.js", function() {
            // connect to the web channel
            new QWebChannel( qt.webChannelTransport, function(channel) {
                gWebChannelHandler = channel.objects.handler ;
            } ) ;
        } ) ;
    }

    // initialize the menu
    var $menu = $("#menu input") ;
    $menu.popmenu( {
        new_scenario: { label: "New scenario", action: function() { on_new_scenario(true) ; } },
        load_scenario: { label: "Load scenario", action: on_load_scenario },
        save_scenario: { label: "Save scenario", action: on_save_scenario },
        separator: { type: "separator" },
        template_pack: { label: "Load template pack", action: on_template_pack },
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
    // add a handler for when the "load scenario" file has been selected
    $("#load-scenario").change( on_load_scenario_file_selected ) ;
    // add a handler for when the "load template pack" file has been selected
    $("#load-template-pack").change( on_template_pack_file_selected ) ;
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
        disabled: [1, 2], // nb: we enable these when the page has finished loading
        activate: on_tab_activate,
    } ).show() ;
    var navHeight = $("#tabs .ui-tabs-nav").height() ;
    $("#tabs .ui-tabs-nav a").click( function() { $(this).blur() ; } ) ;

    // initialize the scenario date picker
    $("input[name='SCENARIO_DATE']").datepicker( {
        showAnim: "slideDown",
        changeMonth: true, changeYear: true,
        defaultDate: "01/01/1940",
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
    } ) ;
    $("#ob_vehicles-sortable_2").sortable2( "init", {
        add: function() { add_vo( "vehicles", 2 ) ; },
    } ) ;

    // initialize the OB ordnance
    $("#ob_ordnance-sortable_1").sortable2( "init", {
        add: function() { add_vo( "ordnance", 1 ) ; },
    } ) ;
    $("#ob_ordnance-sortable_2").sortable2( "init", {
        add: function() { add_vo( "ordnance", 2 ) ; },
    } ) ;

    // handle ENTER and double-clicks in the "select vehicle/ordnance" dialog
    function auto_select_vo( evt ) {
        if ( $("#select-vo select").val() ) {
            $(".ui-dialog.select-vo button:contains('OK')").click() ;
            evt.preventDefault() ;
        }
    }
    $("#select-vo").keydown( function(evt) {
        if ( evt.keyCode == 13 )
            auto_select_vo( evt ) ;
    } ) ;
    $("#select-vo").dblclick( function(evt) { auto_select_vo(evt) ; } ) ;

    // add player change handlers
    $("select[name='PLAYER_1']").selectmenu( {
        width: "7em",
        open: function() { $(this).data("prev-val",$(this).val()) ; },
        select: function() { on_player_change_with_confirm( 1 ) ; },
    } ) ;
    $("select[name='PLAYER_2']").selectmenu( {
        width: "7em",
        open: function() { $(this).data("prev-val",$(this).val()) ; },
        select: function() { on_player_change_with_confirm( 2 ) ; },
    } ) ;

    // load the ELR's and SAN's
    var buf = [] ;
    for ( var i=0 ; i <= 5 ; ++i ) // nb: A19.1: ELR is 0-5
        buf.push( "<option value='" + i + "'>" + i + "</option>" ) ;
    buf = buf.join( "" ) ;
    for ( var player_no=1 ; player_no <= 2 ; ++player_no ) {
        $( "select[name='PLAYER_" + player_no + "_ELR']" ).html( buf ).selectmenu( {
            classes: { "ui-selectmenu-button": "player" + player_no + "_elr" },
            width: "3em"
        } ) ;
    }
    buf = [ "<option value=''></option>" ] ; // nb: allow scenarios that have no SAN
    for ( i=2 ; i <= 7 ; ++i ) // nb: A14.1: SAN is 2-7
        buf.push( "<option value='" + i + "'>" + i + "</option>" ) ;
    buf = buf.join( "" ) ;
    for ( player_no=1 ; player_no <= 2 ; ++player_no ) {
        $( "select[name='PLAYER_" + player_no + "_SAN']" ).html( buf ).selectmenu( {
            classes: { "ui-selectmenu-button": "player" + player_no + "_san" },
            width: "3em"
        } ) ;
    }

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
        install_template_pack( data ) ;
        on_new_scenario( false ) ;
        gDefaultNationalities = $.extend( true, {}, data.nationalities ) ;
        // NOTE: If we are loading a user-defined template pack, then what we think
        // is the set of valid template ID's will depend on what's in it :-/
        gValidTemplateIds = Object.keys( data.templates ) ;
        update_page_load_status( "template-pack" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the template pack:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
    } ) ;

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
    $("button.generate").each( function() {
        var template_id = $(this).attr( "data-id" ) ;
        var template_id2 ;
        if ( template_id.substring(0,9) === "ob_setup_" )
            template_id2 = "ob_setup" ;
        else if ( template_id.substring(0,12) == "ob_vehicles_" )
            template_id2 = "ob_vehicles" ;
        else if ( template_id.substring(0,12) == "ob_ordnance_" )
            template_id2 = "ob_ordnance" ;
        else
            template_id2 = template_id ;
        var buf = [ "<div class='snippet-control' data-id='" + template_id + "'>",
            $(this).prop( "outerHTML" ),
            "<select data-id='" + template_id2 + "'>",
            "<option value='edit' class='edit-template' title='Edit the template that will generate this snippet.'>Edit</option>",
            "</select>",
            "</div>"
        ] ;
        var $newElem = $( buf.join("") ) ;
        $newElem.find( "button" ).prepend(
            $( "<img src='" + gImagesBaseUrl + "/snippet.png'>" )
        ) ;
        $newElem.controlgroup() ;
        $newElem.children("select").each( function() {
            $(this).selectmenu( {
                classes: {
                    "ui-selectmenu-button": "ui-button-icon-only",
                    "ui-selectmenu-menu": "snippet-control-menu-item",
                },
            } ) ;
        } ) ;
        $newElem.children(".ui-button-icon-only").css( "width", "1em" ) ;
        $newElem.children(".ui-selectmenu-button").click( function() {  $(this).blur() ; } ) ;
        $(this).replaceWith( $newElem ) ;
    } ) ;

    // handle requests to generate/edit HTML snippets
    $("button.generate").click( function() {
        generate_snippet( $(this), null ) ;
    } ).attr( "title", "Generate a snippet." ) ;
    $("div.snippet-control select").on( "selectmenuselect", function() {
        edit_template( $(this).attr("data-id") ) ;
    } ) ;

    // handle requests to edit the templates
    $("button.edit-template").click( function() {
        edit_template( $(this).data( "id" ) ) ;
    } ).html( "<div><img src='" + gImagesBaseUrl + "/edit-template.png'>Edit</div>" )
        .attr( "title", "Edit the template." )
        .addClass( "ui-button" ) ;

    // watch for changes to the scenario name
    $("input[name='SCENARIO_NAME']").on( "input propertychange paste", function() {
        on_scenario_name_change() ;
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
            if ( is_scenario_dirty() ) {
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

gPageLoadStatus = [ "main", "vehicle-listings", "ordnance-listings", "template-pack", "default-scenario" ] ;

function update_page_load_status( id )
{
    // track the page load progress
    gPageLoadStatus.splice( gPageLoadStatus.indexOf(id), 1 ) ;
    if ( id === "template-pack" )
        $("fieldset[name='scenario']").fadeIn( 2*1000 ) ;

    // check if the page has finished loading
    if ( gPageLoadStatus.length === 0 ) {
        // yup - update the UI
        $("#tabs").tabs({ disabled: [] }) ;
        adjust_footer_vspacers() ;
        // NOTE: The wtermark image appears briefly in IE when reloading the page, but not even
        // creating the watermark dynamically and removing it when the page unloads fixes it :-(
        $("#watermark").fadeIn( 5*1000 ) ;
        // notify the test suite
        $("body").append( $("<div id='_page-loaded_'></div>") ) ;
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
        var curr_tab = $("#tabs .ui-tabs-active a").attr( "href" ) ;
        if ( curr_tab !== tab )
            $("#tabs .ui-tabs-nav a[href='"+tab+"']").trigger( "click" ) ;
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
}

// --------------------------------------------------------------------

function install_template_pack( data )
{
    // install the template pack
    gTemplatePack = data ;

    // update the player droplists
    var curSel = {
        1: $("select[name='PLAYER_1']").val(),
        2: $("select[name='PLAYER_2']").val()
    } ;
    var buf = [] ;
    var nationalities = gTemplatePack.nationalities ;
    for ( var id in nationalities )
        buf.push( "<option value='" + id + "'>" + nationalities[id].display_name + "</option>" ) ;
    buf = buf.join( "" ) ;
    for ( var player_no=1 ; player_no <= 2 ; ++player_no ) {
        var $sel = $( "select[name='PLAYER_" + player_no + "']" ) ;
        $sel.html( buf ).selectmenu( {
            classes: { "ui-selectmenu-button": "player" + player_no },
        } ) ;
        if ( curSel[player_no] )
            $sel.val( curSel[player_no] ).selectmenu( "refresh" ) ;
    }

    // update the OB tab headers
    // NOTE: We don't do this while the page is initially loading, it will be done when the default scenario loaded.
    if ( gPageLoadStatus.indexOf( "template-pack" ) === -1 ) {
        update_ob_tab_header( 1 ) ;
        update_ob_tab_header( 2 ) ;
    }
}

// --------------------------------------------------------------------

function on_player_change_with_confirm( player_no )
{
    // check if we need to do anything
    var $select = $( "select[name='PLAYER_" + player_no + "']" ) ;
    if ( $select.val() == $select.data("prev-val") )
        return ;

    // check if we should confirm this operation
    var is_empty = true ;
    $( "#tabs-ob" + player_no + " .sortable" ).each( function() {
        if ( $(this).children( "li" ).length > 0 )
            is_empty = false ;
    } ) ;
    if ( is_empty ) {
        // nope - just do it
        on_player_change( player_no ) ;
    } else {
        // yup - make it so
        ask( "Change player nationality",
            "<p>Do you want to change this player's nationality?<p>You will lose changes made to their OB.", {
            ok: function() { on_player_change( player_no ) ; },
            cancel: function() {
                $select.val( $select.data("prev-val") ).selectmenu( "refresh" ) ;
            },
        } ) ;
    }
}

function on_player_change( player_no )
{
    // update the tab label
    var player_nat = update_ob_tab_header( player_no ) ;

    // show/hide the nationality-specific buttons
    for ( var nat in _NATIONALITY_SPECIFIC_BUTTONS ) {
        for ( var i=0 ; i < _NATIONALITY_SPECIFIC_BUTTONS[nat].length ; ++i ) {
            var button_id = _NATIONALITY_SPECIFIC_BUTTONS[nat][i] ;
            var $elem = $( "#panel-ob_notes_" + player_no + " div.snippet-control[data-id='" + button_id + "']" ) ;
            $elem.css( "display", nat == player_nat ? "inline-block" : "none" ) ;
        }
    }

    // reset the OB params
    $( "#ob_setups-sortable_" + player_no ).sortable2( "delete-all" ) ;
    $("input[name='OB_SETUP_WIDTH_"+player_no+"']").val( "" ) ;
    $( "#ob_notes-sortable_" + player_no ).sortable2( "delete-all" ) ;
    $( "#ob_vehicles-sortable_" + player_no ).sortable2( "delete-all" ) ;
    $("input[name='OB_VEHICLES_WIDTH_"+player_no+"']").val( "" ) ;
    $( "#ob_ordnance-sortable_" + player_no ).sortable2( "delete-all" ) ;
    $("input[name='OB_ORDNANCE_WIDTH_"+player_no+"']").val( "" ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function update_ob_tab_header( player_no )
{
    // update the OB tab header for the specified player
    var player_nat = $( "select[name='PLAYER_" + player_no + "']" ).val() ;
    var display_name = gTemplatePack.nationalities[ player_nat ].display_name ;
    var image_url = gImagesBaseUrl + "/flags/" + player_nat + ".png" ;
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
        set_colors( tab_id, colors[0], colors[1] ) ;
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
