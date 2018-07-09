var gNationalities = {} ;
var gDefaultTemplates = {} ;

// --------------------------------------------------------------------

$(document).ready( function () {

    // initialize
    $("#tabs").tabs( {
        heightStyle: "fill",
    } ).show() ;
    var navHeight = $("#tabs .ui-tabs-nav").height() ;
    $("input[name='scenario_name']").focus().focus() ;

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
    $("select[name='player_1_elr']").html( buf ).val( 5 ) ;
    $("select[name='player_2_elr']").html( buf ).val( 5 ) ;
    buf = [ "<option></option>" ] ; // nb: allow scenarios that have no SAN
    for ( i=2 ; i <= 7 ; ++i ) // nb: A14.1: SAN is 2-7
        buf.push( "<option value='" + i + "'>" + i + "</option>" ) ;
    buf = buf.join( "" ) ;
    $("select[name='player_1_san']").html( buf ).val( 2 ) ;
    $("select[name='player_2_san']").html( buf ).val( 2 ) ;

    // load the nationalities
    $.getJSON( gGetNationalitiesUrl, function(data) {
        gNationalities = data ;
        var buf = [] ;
        for ( var id in gNationalities )
            buf.push( "<option value='" + id + "'>" + gNationalities[id].display_name + "</option>" ) ;
        on_player_change(
            $("select[name='player_1']").html( buf ).val( "german" )
        ) ;
        on_player_change(
            $("select[name='player_2']").html( buf ).val( "russian" )
        ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the nationalities:<pre>" + escapeHTML(errorMsg) + "</pre>" ) ;
    } ) ;

    // add handlers for player changes
    $("select[name='player_1']").change( function() { on_player_change($(this)) ; } ) ;
    $("select[name='player_2']").change( function() { on_player_change($(this)) ; } ) ;

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
    var nat = $select.find( "option:selected" ).val() ;
    var $elem = $("#tabs .ui-tabs-nav a[href='#tabs-ob" + player_id + "']") ;
    $elem.text( gNationalities[nat].display_name + " OB" ) ;
}
