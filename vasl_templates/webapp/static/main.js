var gTemplatePack = {} ;
var gDefaultNationalities = {} ;
var gValidTemplateIds = [] ;

var _NATIONALITY_SPECIFIC_BUTTONS = {
    "russian": [ "mol", "mol-p" ],
    "german": [ "pf", "psk", "atmm" ],
    "american": [ "baz" ],
    "british": [ "piat" ],
} ;

// --------------------------------------------------------------------

$(document).ready( function () {

    // initialize
    var $menu = $("#menu input") ;
    $menu.popmenu( {
        new_scenario: { label: "New scenario", action: on_new_scenario },
        load_scenario: { label: "Load scenario", action: on_load_scenario },
        save_scenario: { label: "Save scenario", action: on_save_scenario },
        separator: { type: "separator" },
        template_pack: { label: "Load template pack", action: on_template_pack },
    } ) ;
    // nb: we only show the popmenu on left click (not the normal right-click)
    $menu.off( "contextmenu" ) ;
    $menu.click( function() {
        var pos = $(this).offset() ;
        $(this).data( "PopMenu.contextmenu" ).data( "PopMenu.instance" ).show(
            pos.left+$(this).width()+4, pos.top+$(this).height()+4, "fade", 200
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
    var fixupOB2 = function( $elem ) {
        adjustAttr( $elem, "id" ) ;
        adjustAttr( $elem, "name" ) ;
        adjustAttr( $elem, "data-id" ) ;
        adjustAttr( $elem, "for" ) ;
        $elem.children().each( function() {
            fixupOB2( $(this) ) ;
        } ) ;
    } ;
    fixupOB2( $ob2 ) ;
    $("#tabs-ob2").html( $ob2.html() ) ;

    // initialize
    $("#tabs").tabs( {
        heightStyle: "fill",
    } ).show() ;
    var navHeight = $("#tabs .ui-tabs-nav").height() ;
    $("input[name='SCENARIO_NAME']").focus().focus() ;

    // initialize
    $("input[name='SCENARIO_DATE']").datepicker( {
        showAnim: "slideDown",
        changeMonth: true, changeYear: true,
        defaultDate: "01/01/1940",
    } ) ;

    // initialize
    $("#ssr-sortable").sortable( { connectWith: "#ssr-trash", cursor: "move" } ) ;
    init_ssr( $("#ssr-sortable li") ) ;
    $("#add-ssr").click( add_ssr ) ;
    $("#ssr-trash").sortable( {
        receive: function( evt, ui ) { ui.item.remove() ; update_ssr_hint() ; }
    } ) ;
    $("#edit-ssr textarea").keydown( function(evt) {
        if ( evt.keyCode == 13 && evt.ctrlKey ) {
            $(".ui-dialog.edit-ssr button:contains('OK')").click() ;
            evt.preventDefault() ;
        }
    } ) ;

    // load the ELR's and SAN's
    var buf = [] ;
    for ( var i=0 ; i <= 5 ; ++i ) // nb: A19.1: ELR is 0-5
        buf.push( "<option value='" + i + "'>" + i + "</option>" ) ;
    buf = buf.join( "" ) ;
    $("select[name='PLAYER_1_ELR']").html( buf ) ;
    $("select[name='PLAYER_2_ELR']").html( buf ) ;
    buf = [ "<option></option>" ] ; // nb: allow scenarios that have no SAN
    for ( i=2 ; i <= 7 ; ++i ) // nb: A14.1: SAN is 2-7
        buf.push( "<option value='" + i + "'>" + i + "</option>" ) ;
    buf = buf.join( "" ) ;
    $("select[name='PLAYER_1_SAN']").html( buf ) ;
    $("select[name='PLAYER_2_SAN']").html( buf ) ;

    // add handlers for player changes
    $("select[name='PLAYER_1']").change( function() { on_player_change($(this)) ; } ) ;
    $("select[name='PLAYER_2']").change( function() { on_player_change($(this)) ; } ) ;

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
    $("input[type='button'].generate").each( function() {
        var template_id = $(this).attr( "data-id" ) ;
        var template_id2 = (template_id.substring(0,9) === "ob_setup_") ? "ob_setup" : template_id ;
        var buf = [ "<div class='snippet-control' data-id='" + template_id + "'>",
            $(this).prop( "outerHTML" ),
            "<select data-id='" + template_id2 + "'>",
            "<option value='edit' class='edit-template'>Edit</option>",
            "</select>",
            "</div>"
        ] ;
        var $newElem = $( buf.join("") ) ;
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
    $("input[type='button'].generate").click( function() {
        generate_snippet( $(this) ) ;
    } ) ;
    $("div.snippet-control select").on( "selectmenuselect", function() {
        edit_template( $(this).attr("data-id") ) ;
    } ) ;

    // initialize hotkeys
    init_hotkeys() ;

    // add some dummy links for the test suite to edit templates
    if ( getUrlParam( "edit_template_links" ) ) {
        $("input[type='button'].generate").each( function() {
           var template_id = $(this).attr( "data-id" ) ;
            if ( template_id.substring(0,9) === "ob_setup_" )
                template_id = "ob_setup" ;
            $( "<a href='#' class='edit-template-link' data-id='" + template_id + "'" +
               " onclick='edit_template(\"" + template_id + "\")'" +
               "></a>"
            ).appendTo( "body" ) ;
        } ) ;
    }
} ) ;

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
    var curSel1 = $("select[name='PLAYER_1']").val() ;
    var curSel2 = $("select[name='PLAYER_2']").val() ;
    var buf = [] ;
    var nationalities = gTemplatePack.nationalities ;
    for ( var id in nationalities )
        buf.push( "<option value='" + id + "'>" + nationalities[id].display_name + "</option>" ) ;
    buf = buf.join( "" ) ;
    $("select[name='PLAYER_1']").html( buf ).val( curSel1 ) ;
    $("select[name='PLAYER_2']").html( buf ).val( curSel2 ) ;

    // update the OB tabs
    if ( curSel1 )
        on_player_change( $("select[name='PLAYER_1']") ) ;
    if ( curSel2 )
        on_player_change( $("select[name='PLAYER_2']") ) ;
}

// --------------------------------------------------------------------

function on_player_change( $select )
{
    // figure out which player was changed
    var name = $select.attr( "name" ) ;
    var player_id = name.substring( name.length-1 ) ;

    // update the tab label
    var player_nat = $select.find( "option:selected" ).val() ;
    var $elem = $("#tabs .ui-tabs-nav a[href='#tabs-ob" + player_id + "']") ;
    var image_url = gImagesBaseUrl + "/flags/" + player_nat + ".png" ;
    var nationalities = gTemplatePack.nationalities ;
    $elem.html(
        "<img src='" + image_url + "'>&nbsp;" +
        "<span>" + escapeHTML(nationalities[player_nat].display_name) + " OB</span>"
    ) ;

    // show/hide the nationality-specific buttons
    for ( var nat in _NATIONALITY_SPECIFIC_BUTTONS ) {
        for ( var i=0 ; i < _NATIONALITY_SPECIFIC_BUTTONS[nat].length ; ++i ) {
            var button_id = _NATIONALITY_SPECIFIC_BUTTONS[nat][i] ;
            $elem = $( "#panel-obsetup" + player_id + " div.snippet-control[data-id='" + button_id + "']" ) ;
            $elem.css( "display", nat == player_nat ? "block" : "none" ) ;
        }
    }
}
