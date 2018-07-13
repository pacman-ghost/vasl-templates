var gNationalities = {} ;
var gDefaultTemplates = {} ;

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
        new: { label: "New scenario", action: on_new_scenario },
        load: { label: "Load scenario", action: on_load_scenario },
        save: { label: "Save scenario", action: on_save_scenario },
    } ) ;
    // nb: we only show the popmenu on left click (not the normal right-click)
    $menu.off( "contextmenu" ) ;
    $menu.click( function() {
        var pos = $(this).offset() ;
        $(this).data( "PopMenu.contextmenu" ).data( "PopMenu.instance" ).show(
            pos.left+$(this).width()+4, pos.top+$(this).height()+4, "fade", 200
        ) ;
    } ) ;
    // nb: we dismiss the popmenu on ESCAPE
    $(document).keydown( function(evt) {
        if ( evt.keyCode == 27 )
            $menu.popmenu( "hide" ) ;
    } ) ;
    // add a handler for when the "load scenario" file has been selected
    $("#load-scenario").change( on_load_scenario_file_selected ) ;
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

    // load the nationalities
    $.getJSON( gGetNationalitiesUrl, function(data) {
        gNationalities = data ;
        var buf = [] ;
        for ( var id in gNationalities )
            buf.push( "<option value='" + id + "'>" + gNationalities[id].display_name + "</option>" ) ;
        $("select[name='PLAYER_1']").html( buf ) ;
        $("select[name='PLAYER_2']").html( buf ) ;
        on_new_scenario( false ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the nationalities:<pre>" + escapeHTML(errorMsg) + "</pre>" ) ;
    } ) ;

    // add handlers for player changes
    $("select[name='PLAYER_1']").change( function() { on_player_change($(this)) ; } ) ;
    $("select[name='PLAYER_2']").change( function() { on_player_change($(this)) ; } ) ;

    // get the default templates
    $.getJSON( gGetTemplatesUrl, function(data) {
        gDefaultTemplates = data ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the default templates:<pre>" + escapeHTML(errorMsg) + "</pre>" ) ;
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

    // handle requests to generate HTML snippets
    $("input[type='button'].generate").click( function() {
        generate_snippet( $(this) ) ;
    } ) ;

} ) ;

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
    $elem.html(
        "<img src='" + image_url + "'>&nbsp;" +
        "<span>" + escapeHTML(gNationalities[player_nat].display_name) + " OB</span>"
    ) ;

    // show/hide the nationality-specific buttons
    for ( var nat in _NATIONALITY_SPECIFIC_BUTTONS ) {
        for ( var i=0 ; i < _NATIONALITY_SPECIFIC_BUTTONS[nat].length ; ++i ) {
            var button_id = _NATIONALITY_SPECIFIC_BUTTONS[nat][i] ;
            $elem = $( "#panel-obsetup" + player_id + " input[type='button'][data-id='" + button_id + "']" ) ;
            $elem.css( "display", nat == player_nat ? "block" : "none" ) ;
        }
    }
}
