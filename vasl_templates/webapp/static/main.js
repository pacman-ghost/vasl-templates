var gDefaultTemplates = {} ;

// NOTE: These fields aren't mandatory in the sense that snippet generation will fail
// if they're not set, but they're really, really, really expected to be there.
var _MANDATORY_PARAMS = {
    scenario: { "SCENARIO_NAME": "scenario name", "SCENARIO_DATE": "scenario date" },
} ;

// --------------------------------------------------------------------

$(document).ready( function () {

    // initialize
    $("#tabs").tabs( {
        heightStyle: "fill",
    } ).show() ;
    var navHeight = $("#tabs .ui-tabs-nav").height() ;

    // get the default templates
    $.getJSON( gGetTemplatesUrl, function(data) {
        gDefaultTemplates = data ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the default templates:<pre>" + escapeHTML(errorMsg) + "</pre>" ) ;
    } ) ;

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

    // handle requests to generate HTML snippets
    $("input[type='button'].generate").click( function() {
        generate_snippet( $(this) ) ;
    } ) ;

} ) ;

// --------------------------------------------------------------------

function generate_snippet( $btn )
{
    // collect all the template parameters
    var params = {} ;
    add_param = function($elem) { params[ $elem.attr("name").toUpperCase() ] = $elem.val() ; } ;
    $("input[type='text'].param").each( function() { add_param($(this)) ; } ) ;
    $("textarea.param").each( function() { add_param($(this)) ; } ) ;

    // check for mandatory parameters
    var template_id = $btn.data( "id" ) ;
    if ( template_id in _MANDATORY_PARAMS ) {
        var missing_params = [] ;
        for ( var param_id in _MANDATORY_PARAMS[template_id] ) {
            if ( ! (param_id in params && params[param_id].length > 0) )
                missing_params.push( _MANDATORY_PARAMS[template_id][param_id] ) ;
        }
        if ( missing_params.length > 0 ) {
            var buf = [ "Missing parameters:<ul>" ] ;
            for ( var i=0 ; i < missing_params.length ; ++i )
                buf.push( "<li>" + escapeHTML(missing_params[i]) ) ;
            buf.push( "</ul>" ) ;
            showWarningMsg( buf.join("") ) ;
        }
    }

    // get the template to generate the snippet from
    if ( ! (template_id in gDefaultTemplates) ) {
        showErrorMsg( "Unknown template: " + escapeHTML(template_id) ) ;
        return ;
    }
    var func, val ;
    try {
        func = jinja.compile( gDefaultTemplates[template_id] ).render ;
    }
    catch( ex ) {
        showErrorMsg( "Can't compile template:<pre>" + escapeHTML(ex) + "</pre>" ) ;
        return ;
    }

    // process the template
    try {
        val = func( params ) ;
    }
    catch( ex ) {
        showErrorMsg( "Can't process template <em>\"" + template_id + "\"</em>:<pre>" + escapeHTML(ex) + "</pre>" ) ;
        return ;
    }
    try {
        copyToClipboard( val ) ;
    }
    catch( ex ) {
        showErrorMsg( "Can't copy to the clipboard:<pre>" + escapeHTML(ex) + "</pre>" ) ;
        return ;
    }
    showInfoMsg( "The HTML snippet has been copied to the clipboard." ) ;
}
