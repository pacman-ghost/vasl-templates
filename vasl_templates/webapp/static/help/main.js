
// --------------------------------------------------------------------

$(document).ready( function() {

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

    // initialize the tabs
    if ( getUrlParam( "embedded" ) ) {
        $( "#helptabs li:eq(0)" ).remove() ;
        $( "#helptabs-installation" ).remove() ;
    }
    $("#helptabs").tabs().show() ;
    $("#helptabs .ui-tabs-nav a").click( function() { $(this).blur() ; } ) ;

    // check if we should auto-select a tab
    var tab_id = getUrlParam( "tab" ) ;
    if ( tab_id )
        $( "a[href='#helptabs-" + tab_id + "']" ).click() ;
} ) ;