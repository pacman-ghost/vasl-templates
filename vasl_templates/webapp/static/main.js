
// --------------------------------------------------------------------

$(document).ready( function () {
    $("form").submit( function( evt ) {
        evt.preventDefault() ;
        var data = { val: $("form input[name='val']").val() } ;
        $.post( {
            url: gGenerateURL,
            data: data,
            success: function( data ) {
                $("#response").text( data ) ;
            },
            error: function( xhr, status, errorMsg ) {
                $("#response").text( "ERROR: "+errorMsg ) ;
            },
        } ) ;
    } ) ;
} ) ;
