// NOTE: These fields aren't mandatory in the sense that snippet generation will fail
// if they're not set, but they're really, really, really expected to be there.
var _MANDATORY_PARAMS = {
    scenario: { "SCENARIO_NAME": "scenario name", "SCENARIO_DATE": "scenario date" },
} ;

var _MONTH_NAMES = [ // nb: we assume English :-/
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
] ;

// --------------------------------------------------------------------

function generate_snippet( $btn )
{
    // initialize
    storeMsgForTestSuite( "_last-info_", "" ) ;
    storeMsgForTestSuite( "_last-warning_", "" ) ;
    storeMsgForTestSuite( "_last-error_", "" ) ;

    // collect all the template parameters
    var params = {} ;
    add_param = function($elem) { params[ $elem.attr("name").toUpperCase() ] = $elem.val() ; } ;
    $("input[type='text'].param").each( function() { add_param($(this)) ; } ) ;
    $("textarea.param").each( function() { add_param($(this)) ; } ) ;
    $("select.param").each( function() { add_param($(this)) ; } ) ;

    // figure out which template to use
    var template_id = $btn.data( "id" ) ;
    if ( template_id === "ob_setup_1" ) {
        template_id = "ob_setup" ;
        params.OB_SETUP = params.OB_SETUP_1 ;
        params.OB_SETUP_COLOR = gNationalities[params.PLAYER_1].ob_colors[0] ;
        params.OB_SETUP_COLOR_2 = gNationalities[params.PLAYER_1].ob_colors[1] ;
    }
    else if ( template_id === "ob_setup_2" ) {
        template_id = "ob_setup" ;
        params.OB_SETUP = params.OB_SETUP_2 ;
        params.OB_SETUP_COLOR = gNationalities[params.PLAYER_2].ob_colors[0] ;
        params.OB_SETUP_COLOR_2 = gNationalities[params.PLAYER_2].ob_colors[1] ;
    }
    else if ( template_id === "ssr" ) {
        params.SSR = [] ;
        $("#ssr-sortable li").each( function() {
            params.SSR.push( $(this).text() ) ;
        } ) ;
    }

    // check for mandatory parameters
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

    // extract the scenario date components
    var scenario_date = $("input[name='scenario_date']").datepicker( "getDate" ) ;
    if ( scenario_date ) {
        params.SCENARIO_DAY_OF_MONTH = scenario_date.getDate() ;
        params.SCENARIO_MONTH = 1 + scenario_date.getMonth() ;
        params.SCENARIO_MONTH_NAME = _MONTH_NAMES[scenario_date.getMonth()] ;
        params.SCENARIO_YEAR = scenario_date.getFullYear() ;
    }

    // generate PF parameters
    if ( params.SCENARIO_YEAR < 1944 || (params.SCENARIO_YEAR == 1944 && params.SCENARIO_MONTH < 6) )
        params.PF_RANGE = 1 ;
    else if ( params.SCENARIO_YEAR == 1944 )
        params.PF_RANGE = 2 ;
    else
        params.PF_RANGE = 3 ;
    if ( params.SCENARIO_YEAR < 1943 || (params.SCENARIO_YEAR == 1943 && params.SCENARIO_MONTH <= 9) ) {
        params.PF_CHECK_DRM = "+1" ;
        params.PF_CHECK_DR = 4 ;
    } else if ( params.SCENARIO_YEAR >= 1945 ) {
        params.PF_CHECK_DRM = "-1" ;
        params.PF_CHECK_DR = 4 ;
    } else {
        params.PF_CHECK_DRM = "" ;
        params.PF_CHECK_DR = 3 ;
    }
    if ( template_id === "pf" ) {
        if ( params.SCENARIO_DATE === "" || params.SCENARIO_YEAR <= 1942 || (params.SCENARIO_YEAR == 1943 && params.SCENARIO_MONTH <= 9) )
            showWarningMsg( "PF are only available after September 1943." ) ;
    }

    // generate BAZ parameters
    if ( params.SCENARIO_YEAR >= 1945 ) {
        params.BAZ_TYPE = 45 ;
        params.BAZ_BREAKDOWN = 11 ;
        params.BAZ_TOKILL = 16 ;
        params.BAZ_WP = 6 ;
        params.BAZ_RANGE = 5 ;
    } else if ( params.SCENARIO_YEAR >= 1944 ) {
        params.BAZ_TYPE = 44 ;
        params.BAZ_BREAKDOWN = 11 ;
        params.BAZ_TOKILL = 16 ;
        params.BAZ_RANGE = 4 ;
    } else if ( params.SCENARIO_YEAR == 1943 || (params.SCENARIO_YEAR == 1942 && params.SCENARIO_MONTH >= 11) ) {
        params.BAZ_TYPE = 43 ;
        params.BAZ_BREAKDOWN = 10 ;
        params.BAZ_TOKILL = 13 ;
        params.BAZ_RANGE = 4 ;
    }
    if ( template_id === "baz" ) {
        if ( params.SCENARIO_DATE === "" || params.SCENARIO_YEAR <= 1941 || (params.SCENARIO_YEAR == 1942 && params.SCENARIO_MONTH < 11) )
        showWarningMsg( "BAZ are only available from November 1942." ) ;
    }

    // check that the players have different nationalities
    if ( params.PLAYER_1 === params.PLAYER_2 )
        showWarningMsg( "Both players have the same nationality!" ) ;

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
