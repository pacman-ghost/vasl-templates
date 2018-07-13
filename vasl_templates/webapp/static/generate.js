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

    // unload the template parameters
    var params = unload_params() ;
    var template_id = $btn.data( "id" ) ;
    if ( template_id === "ob_setup_1" ) {
        template_id = "ob_setup" ;
        params.OB_SETUP = params.OB_SETUP_1 ;
        params.OB_SETUP_COLOR = gNationalities[params.PLAYER_1].ob_colors[0] ;
        params.OB_SETUP_COLOR_2 = gNationalities[params.PLAYER_1].ob_colors[1] ;
        params.OB_SETUP_WIDTH = params.OB_SETUP_WIDTH_1 ;
    }
    else if ( template_id === "ob_setup_2" ) {
        template_id = "ob_setup" ;
        params.OB_SETUP = params.OB_SETUP_2 ;
        params.OB_SETUP_COLOR = gNationalities[params.PLAYER_2].ob_colors[0] ;
        params.OB_SETUP_COLOR_2 = gNationalities[params.PLAYER_2].ob_colors[1] ;
        params.OB_SETUP_WIDTH = params.OB_SETUP_WIDTH_2 ;
    }

    // extract the scenario date components
    var scenario_date = $("input[name='SCENARIO_DATE']").datepicker( "getDate" ) ;
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

    // check for date-specific parameters
    if ( template_id === "pf" ) {
        if ( params.SCENARIO_DATE === "" || params.SCENARIO_YEAR <= 1942 || (params.SCENARIO_YEAR == 1943 && params.SCENARIO_MONTH <= 9) )
            showWarningMsg( "PF are only available after September 1943." ) ;
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
        val = val.trim() ;
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

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function unload_params()
{
    // collect all the template parameters
    var params = {} ;
    add_param = function($elem) { params[ $elem.attr("name") ] = $elem.val() ; } ;
    $("input[type='text'].param").each( function() { add_param($(this)) ; } ) ;
    $("textarea.param").each( function() { add_param($(this)) ; } ) ;
    $("select.param").each( function() { add_param($(this)) ; } ) ;

    // collect the SSR's
    params.SSR = [] ;
    $("#ssr-sortable li").each( function() {
        params.SSR.push( $(this).text() ) ;
    } ) ;

    return params ;
}

// --------------------------------------------------------------------

function on_load_scenario()
{
    // FIXME! confirm this operation if the scenario is dirty

    // FOR TESTING PORPOISES! We can't control a file upload from Selenium (since
    // the browser will use native controls), so we store the result in a <div>).
    var $elem ;
    if ( getUrlParam( "scenario_persistence" ) ) {
        $elem = $( "#scenario_persistence" ) ; // nb: must have already been created
        do_load_scenario( JSON.parse( $elem.val() ) ) ;
        return ;
    }

    // ask the user to upload the scenario file
    $("#load-scenario").trigger( "click" ) ;
}

function on_load_scenario_file_selected()
{
    // read the selected file
    var fileReader = new FileReader() ;
    fileReader.onload = function() {
        var data ;
        try {
            data = JSON.parse( fileReader.result ) ;
        } catch( ex ) {
            showErrorMsg( "Can't load the scenario file:<div>" + escapeHTML(ex) + "</div>" ) ;
            return ;
        }
        do_load_scenario( data ) ;
        showInfoMsg( "The scenario was loaded." ) ;
    } ;
    fileReader.readAsText( $("#load-scenario").prop("files")[0] ) ;
}

function do_load_scenario( params )
{
    // load the scenario parameters
    on_new_scenario( false ) ;
    var params_loaded = {} ;
    var set_param = function( $elem, key ) { $elem.val(params[key]) ; params_loaded[key]=true ; return $elem ; } ;
    for ( var key in params ) {
        if ( key === "SSR" ) {
            for ( var i=0 ; i < params[key].length ; ++i ) {
                var $ssr = $( "<li></li>" ) ;
                $ssr.text( params[key][i] ) ;
                $("#ssr-sortable").append( $ssr ) ;
                init_ssr( $ssr ) ;
            }
            update_ssr_hint() ;
            params_loaded[key] = true ;
            continue ;
        }
        //jshint loopfunc: true
        $elem = $("input[type='text'][name='"+key+"'].param").each( function() {
            set_param( $(this), key ) ;
        } ) ;
        $elem = $("textarea[type='text'][name='"+key+"'].param").each( function() {
            set_param( $(this), key ) ;
        } ) ;
        $elem = $("select[name='"+key+"'].param").each( function() {
            set_param( $(this), key ).trigger( "change" ) ;
        } ) ;
    }

    // look for unrecognized keys
    var buf = [] ;
    for ( key in params ) {
        if ( ! (key in params_loaded) )
            buf.push( "<li>" + key + " = '" + escapeHTML(params[key]) + "'" ) ;
    }
    if ( buf.length > 0 )
        showWarningMsg( "Unknown keys in the scenario file:<ul>" + buf.join("") + "</ul>" ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function on_save_scenario()
{
    // unload the template parameters
    var params = unload_params() ;
    var data = JSON.stringify( params ) ;

    // FOR TESTING PORPOISES! We can't control a file download from Selenium (since
    // the browser will use native controls), so we store the result in a <div>).
    if ( getUrlParam( "scenario_persistence" ) ) {
        var $elem = $( "#scenario_persistence" ) ;
        if ( $elem.length === 0 ) {
            // NOTE: The <div> we store the message in must be visible, otherwise
            // Selenium doesn't return any text for it :-/
            $elem = $( "<textarea id='scenario_persistence' style='z-index-999;'></textarea>" ) ;
            $("body").append( $elem ) ;
        }
        $elem.val( data ) ;
        return ;
    }

    // return the parameters to the user as a downloadable file
    download( data, "scenario.json", "application/json" ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function on_new_scenario( verbose )
{
    // FIXME! confirm this operation if the scenario is dirty

    // reset all the template parameters
    $("input[type='text'].param").each( function() { $(this).val("") ; } ) ;
    $("textarea.param").each( function() { $(this).val("") ; } ) ;

    // reset all the template parameters
    on_player_change( $("select[name='PLAYER_1']").val( "german" ) ) ;
    $("select[name='PLAYER_1_ELR']").val( 5 ) ;
    $("select[name='PLAYER_1_SAN']").val( 2 ) ;
    on_player_change( $("select[name='PLAYER_2']").val( "russian" ) ) ;
    $("select[name='PLAYER_2_ELR']").val( 5 ) ;
    $("select[name='PLAYER_2_SAN']").val( 2 ) ;

    // reset all the template parameters
    $("#ssr-sortable li").each( function() {
        $(this).remove() ;
    } ) ;
    update_ssr_hint() ;
    if ( verbose )
        showInfoMsg( "The scenario was reset." ) ;
}
