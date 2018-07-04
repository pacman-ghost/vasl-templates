
// --------------------------------------------------------------------

$(document).ready( function () {

    // initialize
    $("#tabs").tabs( {
        heightStyle: "fill",
    } ) ;
    var navHeight = $("#tabs .ui-tabs-nav").height() ;

    // FUDGE! CSS grids don't seem to update their layout vertically when
    // inside a jQuery tab control - we do it manually :-/
    var prevHeight = [] ;
    $(window).resize( function() {
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
} ) ;
