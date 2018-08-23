
// --------------------------------------------------------------------

$(document).ready( function() {

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
