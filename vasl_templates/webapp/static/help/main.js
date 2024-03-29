
// --------------------------------------------------------------------

$(document).ready( function() {

    // set the application name
    var $caption = $( "#app-name" ) ;
    var version = getUrlParam( "version" ) ;
    if ( version )
        $( "#app-version" ).text( " (" + version +")" ) ;
    $caption.fadeIn( 500 ) ;

    // catch clicks on links
    // FUDGE! We have to do a bit of stuffing around to open links in an external window,
    // so that things will work when we're inside the desktop app.
    if ( ! getUrlParam( "pyqt" ) ) {
        $( "a" ).each( function() {
            $(this).click( function(evt) {
                var url = $(this).attr( "href" ) ;
                if ( url[0] !== "#" && url.substring(0,16) !== "http://localhost" && url.substring(0,16) !== "http://127.0.0.1" ) {
                    window.open( url ) ;
                    evt.preventDefault() ;
                    return false ;
                }
            } ) ;
        } ) ;
    }

    // initialize image previews
    $( "img.preview" ).each( function() {
        // check if the image is floating and add a margin
        var float = $(this).css( "float" ) ;
        if ( float === "left" )
            $(this).css( "margin-right", "1em" ) ;
        else if ( float === "right" )
            $(this).css( "margin-left", "1em" ) ;
        // wrap the image in a link
        var url = $(this).attr( "src" ) ;
        $(this).attr( "src", url.substring(0,url.length-4)+".small.png" ) ;
        $(this).wrap( "<a href='" + url + "'></a>" ).imageZoom( $ ) ;
    } ) ;

    // load the license
    var is_github = ( window.parent.location.hostname === "github.com" || window.parent.location.hostname === "rawgit.com" ) ;
    if ( window.parent.location.protocol !== "file:" && !is_github ) {
        var url = window.parent.location.protocol + "//" + window.parent.location.hostname ;
        if ( window.parent.location.port )
            url += ":" + window.parent.location.port ;
        url += "/license" ;
        $.get( url, function(data) {
            $( "#helptabs-license .content" ).text( data ) ;
        } ).fail( function( xhr, status, errorMsg ) {
            $( "#helptabs-license .content" ).text( "Couldn't get the license: " + errorMsg ) ;
        } ) ;
    } else {
        $( "#helptabs li:contains('License')" ).hide() ;
        $( "#helptabs-license" ).hide() ;
    }

    // initialize the tabs
    $("#loader").fadeOut( 500 ) ;
    $("#helptabs").tabs().fadeIn( 500 ) ;
    $("#helptabs .ui-tabs-nav a").click( function() { $(this).blur() ; } ) ;

    // check if we should auto-select a tab
    var tab_id = getUrlParam( "tab" ) ;
    if ( tab_id )
        $( "a[href='#helptabs-" + tab_id + "']" ).click() ;

    // check if we should scroll to an anchor
    var anchor = window.location.hash.substring( 1 ) ;
    if ( anchor )
        $( "a[name='" + anchor + "']" )[0].scrollIntoView() ;
} ) ;

// --------------------------------------------------------------------

function select_tab( tab_id )
{
    // select the specified tab
    $( "a[href='#helptabs-" + tab_id + "']" ).click() ;
    $( "#helptabs-content" ).animate( { scrollTop: 0 }, 0 ) ;
}

function getUrlParam( param )
{
    // look for the specified URL parameter
    var url = window.location.search.substring( 1 ) ;
    var params = url.split( "&" ) ;
    for ( var i=0 ; i < params.length ; i++ ) {
        var keyval = params[i].split( "=" ) ;
        if ( keyval[0] == param )
            return keyval[1] ;
    }
}
