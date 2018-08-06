// NOTE: These fields aren't mandatory in the sense that snippet generation will fail
// if they're not set, but they're really, really, really expected to be there.
var _MANDATORY_PARAMS = {
    scenario: { "SCENARIO_NAME": "scenario name", "SCENARIO_DATE": "scenario date" },
} ;

var _MONTH_NAMES = [ // nb: we assume English :-/
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
] ;
var _DAY_OF_MONTH_POSTFIXES = { // nb: we assume English :-/
    0: "th",
    1: "st", 2: "nd", 3: "rd", 4: "th", 5: "th", 6: "th", 7: "th", 8: "th", 9: "th", 10: "th",
    11: "th", 12: "th", 13: "th"
} ;

// --------------------------------------------------------------------

function generate_snippet( $btn )
{
    // initialize
    storeMsgForTestSuite( "_last-info_", "" ) ;
    storeMsgForTestSuite( "_last-warning_", "" ) ;
    storeMsgForTestSuite( "_last-error_", "" ) ;

    // extract the scenario date components
    var params = {} ;
    var scenario_date = $("input[name='SCENARIO_DATE']").datepicker( "getDate" ) ;
    if ( scenario_date ) {
        params.SCENARIO_DAY_OF_MONTH = scenario_date.getDate() ;
        var postfix ;
        if ( params.SCENARIO_DAY_OF_MONTH in _DAY_OF_MONTH_POSTFIXES )
            postfix = _DAY_OF_MONTH_POSTFIXES[ params.SCENARIO_DAY_OF_MONTH ] ;
        else
            postfix = _DAY_OF_MONTH_POSTFIXES[ params.SCENARIO_DAY_OF_MONTH % 10 ] ;
        params.SCENARIO_DAY_OF_MONTH_POSTFIX = params.SCENARIO_DAY_OF_MONTH + postfix ;
        params.SCENARIO_MONTH = 1 + scenario_date.getMonth() ;
        params.SCENARIO_MONTH_NAME = _MONTH_NAMES[scenario_date.getMonth()] ;
        params.SCENARIO_YEAR = scenario_date.getFullYear() ;
    }

    // unload the template parameters
    var template_id = $btn.data( "id" ) ;
    unload_params( params, true ) ;

    // set player-specific parameters
    // NOTE: We used to delete the player-specific parameters (e.g. OB_SETUP_1/2)
    // and just return a generic player-independent one (e.g. OB_SETUP), but now,
    // we just leave them in place, in case a user-defined template wants them both.
    if ( template_id === "ob_setup_1" ) {
        template_id = "ob_setup" ;
        params.OB_SETUP = params.OB_SETUP_1 ;
        params.OB_SETUP_WIDTH = params.OB_SETUP_WIDTH_1 ;
    } else if ( template_id === "ob_setup_2" ) {
        template_id = "ob_setup" ;
        params.OB_SETUP = params.OB_SETUP_2 ;
        params.OB_SETUP_WIDTH = params.OB_SETUP_WIDTH_2 ;
    }
    var nationalities = gTemplatePack.nationalities ;
    var curr_tab = $("#tabs .ui-tabs-active a").attr( "href" ) ;
    if ( curr_tab === "#tabs-ob1" ) {
        params.PLAYER_NAME = nationalities[params.PLAYER_1].display_name ;
        params.OB_COLOR = nationalities[params.PLAYER_1].ob_colors[0] ;
        params.OB_COLOR_2 = nationalities[params.PLAYER_1].ob_colors[1] ;
    } else if ( curr_tab === "#tabs-ob2" ) {
        params.PLAYER_NAME = nationalities[params.PLAYER_2].display_name ;
        params.OB_COLOR = nationalities[params.PLAYER_2].ob_colors[0] ;
        params.OB_COLOR_2 = nationalities[params.PLAYER_2].ob_colors[1] ;
    }

    // set player-specific parameters
    if ( template_id == "vehicles_1" ) {
        template_id = "vehicles" ;
        params.VEHICLES = params.VEHICLES_1 ;
        params.VEHICLES_WIDTH = params.VEHICLES_WIDTH_1 ;
    } else if ( template_id == "vehicles_2" ) {
        template_id = "vehicles" ;
        params.VEHICLES = params.VEHICLES_2 ;
        params.VEHICLES_WIDTH = params.VEHICLES_WIDTH_2 ;
    }
    if ( template_id == "ordnance_1" ) {
        template_id = "ordnance" ;
        params.ORDNANCE = params.ORDNANCE_1 ;
        params.ORDNANCE_WIDTH = params.ORDNANCE_WIDTH_1 ;
    } else if ( template_id == "ordnance_2" ) {
        template_id = "ordnance" ;
        params.ORDNANCE = params.ORDNANCE_2 ;
        params.ORDNANCE_WIDTH = params.ORDNANCE_WIDTH_2 ;
    }

    // include the player display names
    params.PLAYER_1_NAME = nationalities[params.PLAYER_1].display_name ;
    params.PLAYER_2_NAME = nationalities[params.PLAYER_2].display_name ;

    // generate PF parameters
    if ( params.SCENARIO_YEAR < 1944 || (params.SCENARIO_YEAR == 1944 && params.SCENARIO_MONTH < 6) )
        params.PF_RANGE = 1 ;
    else if ( params.SCENARIO_YEAR == 1944 )
        params.PF_RANGE = 2 ;
    else
        params.PF_RANGE = 3 ;
    if ( params.SCENARIO_YEAR < 1943 || (params.SCENARIO_YEAR == 1943 && params.SCENARIO_MONTH <= 9) ) {
        params.PF_CHECK_DRM = "+1" ;
        params.PF_CHECK_DR = 2 ;
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
        if ( missing_params.length > 0 )
            showWarningMsg( makeBulletListMsg( "Missing parameters:", missing_params, li_class="pre" ) ) ;
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
    if ( template_id === "atmm" ) {
        if ( params.SCENARIO_DATE === "" || params.SCENARIO_YEAR < 1944 )
            showWarningMsg( "ATMM are only available from 1944." ) ;
    }

    // check that the players have different nationalities
    if ( params.PLAYER_1 === params.PLAYER_2 )
        showWarningMsg( "Both players have the same nationality!" ) ;

    // get the template to generate the snippet from
    var templ = get_template( template_id ) ;
    if ( templ === null )
        return ;
    var func ;
    try {
        func = jinja.compile( templ ).render ;
    }
    catch( ex ) {
        showErrorMsg( "Can't compile template:<div class='pre'>" + escapeHTML(ex) + "</div>" ) ;
        return ;
    }

    // process the template
    var val ;
    try {
        // NOTE: While it's generally not a good idea to disable auto-escaping, the whole purpose
        // of this application is to generate HTML snippets, and so virtually every single
        // template parameter would have to be piped through the "safe" filter :-/ We never render
        // any of the generated HTML, so any risk exists only when the user pastes the HTML snippet
        // into a VASL scenario, which uses an ancient HTML engine (with probably no Javascript)...
        val = func( params, {
            autoEscape: false,
            filters: {
                join: function(val,sep) { return val.join(sep) ; }
            } ,
        } ) ;
        val = val.trim() ;
    }
    catch( ex ) {
        showErrorMsg( "Can't process template: <span class='pre'>" + template_id + "</span><div class='pre'>" + escapeHTML(ex) + "</div>" ) ;
        return ;
    }
    try {
        copyToClipboard( val ) ;
    }
    catch( ex ) {
        showErrorMsg( "Can't copy to the clipboard:<div class'pre'>" + escapeHTML(ex) + "</div>" ) ;
        return ;
    }
    showInfoMsg( "The HTML snippet has been copied to the clipboard." ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function unload_params( params, check_date_capabilities )
{
    // collect all the template parameters
    add_param = function($elem) { params[ $elem.attr("name") ] = $elem.val() ; } ;
    $("input[type='text'].param").each( function() { add_param($(this)) ; } ) ;
    $("textarea.param").each( function() { add_param($(this)) ; } ) ;
    $("select.param").each( function() { add_param($(this)) ; } ) ;

    // collect the SSR's
    params.SSR = [] ;
    $("#ssr-sortable li").each( function() {
        params.SSR.push( $(this).text() ) ;
    } ) ;

    // collect the vehicles/ordnance
    function get_vo( vo_type, player_id, paramName )
    {
        var objs = [] ;
        $("#"+vo_type+"-sortable_"+player_id+" li").each( function() {
            var entry = find_vo( $(this).data("vo-key") ) ;
            var obj = {
                name: entry.name,
                note_number: entry.note_number,
                notes: entry.notes
            } ;
            if ( entry.no_radio )
                obj.no_radio = entry.no_radio ;
            // NOTE: It would be nice to have a Jinja2 filter that inserted the raw capabilities or selected
            // the correct one for the scenario date e.g.
            //   {% for c in veh.capabilities %} {{c|selcap}} {%endif%}}
            // but the problem is that if a capability is not available, we want nothing to appear,
            // but by the time the filter gets called, it's too late :-( Instead, we provide a "raw_capabilities"
            // parameter that people can use in their templates - ugly, but probably not something that will
            // get a lot of use :-/
            var capabilities = make_capabilities( entry, params.SCENARIO_YEAR, params.SCENARIO_MONTH, check_date_capabilities, false ) ;
            if ( capabilities )
                obj.capabilities = capabilities ;
            capabilities = make_capabilities( entry, params.SCENARIO_YEAR, params.SCENARIO_MONTH, check_date_capabilities, true ) ;
            if ( capabilities )
                obj.raw_capabilities = capabilities ;
            var crew_survival = make_crew_survival( entry ) ;
            if ( crew_survival )
                obj.crew_survival = crew_survival ;
            objs.push( obj ) ;
        } ) ;
        if ( objs.length > 0 )
            params[paramName] = objs ;
    }
    get_vo( "vehicle", 1, "VEHICLES_1" ) ;
    get_vo( "vehicle", 2, "VEHICLES_2" ) ;
    get_vo( "ordnance", 1, "ORDNANCE_1" ) ;
    get_vo( "ordnance", 2, "ORDNANCE_2" ) ;

    return params ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function make_capabilities( entry, scenario_year, scenario_month, check_date_capabilities, raw )
{
    var capabilities = [] ;

    // extract the static capabilities
    var i ;
    if ( "capabilities" in entry ) {
        for ( i=0 ; i < entry.capabilities.length ; ++i )
            capabilities.push( entry.capabilities[i] ) ;
    }

    // extract the variable capabilities
    if ( "capabilities2" in entry ) {
        var indeterminate_caps=[], unexpected_caps=[], invalid_caps=[] ;
        for ( var key in entry.capabilities2 ) {
            // check if the capability is dependent on the scenario date
            if ( !( entry.capabilities2[key] instanceof Array ) ) {
                capabilities.push( key + entry.capabilities2[key] ) ;
                continue ;
            }
            // check for LF
            if ( key == "LF" ) {
                capabilities.push( "LF [" + entry.capabilities2[key].join(", ") + "]" ) ;
                continue ;
            }
            if ( $.inArray( key, ["HE","A","D","sD","sN","WP"] ) === -1 ) {
                unexpected_caps.push( key ) ;
                continue ;
            }
            // check if we should return the raw capability, or select the one for the scenario date
            if ( ! scenario_year ) {
                indeterminate_caps.push( key ) ;
                raw = true ;
            }
            if ( raw ) {
                capabilities.push( make_raw_capability( key, entry.capabilities2[key] ) ) ;
            }
            else {
                var cap = select_capability_by_date( entry.capabilities2[key], scenario_year, scenario_month ) ;
                if ( ! cap )
                    continue ;
                if ( cap == "<invalid>" ) {
                    invalid_caps.push( entry.name + ": " + key + " " + entry.capabilities2[key] ) ;
                    continue ;
                }
                capabilities.push( key + cap ) ;
            }
        }
        // check if there were any capabilities not set
        if ( check_date_capabilities && indeterminate_caps.length > 0 ) {
            showWarningMsg( makeBulletListMsg(
                "Can't determine capabilities without a scenario year:",
                indeterminate_caps
            ) ) ;
        }
        // check if there were any unexpected capabilities
        if ( unexpected_caps.length > 0 ) {
            showErrorMsg( makeBulletListMsg(
                "Internal error: unexpected date-based capabilities:",
                unexpected_caps
            ) ) ;
        }
        // check if there were any invalid capabilities
        if ( invalid_caps.length > 0 ) {
            showErrorMsg( makeBulletListMsg(
                "Internal error: invalid date-based capabilities:",
                invalid_caps
            ) ) ;
        }
    }

    // extract any other capabilities
    if ( "capabilities_other" in entry ) {
        for ( i=0 ; i < entry.capabilities_other.length ; ++i )
            capabilities.push( entry.capabilities_other[i] ) ;
    }

    return capabilities.length > 0 ? capabilities : null ;
}

function make_raw_capability( name, capability )
{
    // generate the raw capability string
    var buf = [ name ] ;
    for ( var i=0 ; i < capability.length ; ++i )
        buf.push( escapeHTML(capability[i][0]), "<sup>"+escapeHTML(capability[i][1])+"</sup>" ) ;
    return buf.join( "" ) ;
}

function select_capability_by_date( capabilities, scenario_year, scenario_month )
{
    var MONTH_NAMES = { F: 2, J: 6, } ;

    var val = null ;
    for ( var i=0 ; i < capabilities.length ; ++i ) {
        if ( capabilities[i] == "\u2020" )
            continue ;
        // remove any trailing "+" (why is it even there?)
        var cap = capabilities[i][1].toString() ;
        if ( cap.substring( cap.length-1 ) == "+" )
            cap = cap.substring( 0, cap.length-1 ) ;
        // parse the month/year the capability becomes available
        var month = MONTH_NAMES[ cap.substring(0,1) ] ;
        if ( month )
            cap = cap.substring( 1 ) ;
        if ( ! /^\d$/.test( cap ) )
            return "<invalid>" ;
        cap = parseInt( cap ) ;
        // check if the capabilitity is available
        if ( scenario_year > 1940 + cap )
            val = capabilities[i][0] ;
        else if ( scenario_year == 1940 + cap ) {
            if( !month || scenario_month >= month )
                val = capabilities[i][0] ;
        }
    }
    return val ;
}

function make_crew_survival( entry )
{
    // check if the vehicle has a crew survival field
    var crew_survival = null ;
    if ( "CS#" in entry )
        crew_survival = "CS " + entry["CS#"] ;
    else if ( "cs#" in entry )
        crew_survival = "cs " + entry["cs#"] ;
    if ( crew_survival === null )
        return null ;

    // check if the vehicle is subject to brew up
    if ( crew_survival.substring(crew_survival.length-7) == ":brewup" )
        crew_survival = crew_survival.substring(0,crew_survival.length-7) + " <small><i>(brew up)</i></small>" ;

    return crew_survival ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function get_template( template_id )
{
    // get the specified template
    if ( template_id in gTemplatePack.templates )
        return gTemplatePack.templates[template_id] ;
    showErrorMsg( "Unknown template: <span class='pre'>" + escapeHTML(template_id) + "</span>" ) ;
    return null ;
}

// --------------------------------------------------------------------

function edit_template( template_id )
{
    // get the specified template
    if ( template_id.substring(0,9) == "ordnance_" )
        template_id = "ordnance" ;
    else if ( template_id.substring(0,9) == "vehicles_" )
        template_id = "vehicles" ;
    var template = get_template( template_id ) ;
    if ( template === null )
        return ;

    function on_template_change() {
        // install the new template
        gTemplatePack.templates[template_id] = $("#edit-template textarea").val() ;
    }

    // let the user edit the template
    $("#edit-template textarea").val( template ) ;
    $("#edit-template").dialog( {
        dialogClass: "edit-template",
        title: "Editing template: " + escapeHTML(template_id),
        modal: false,
        minWidth: 400, minHeight: 200,
        open: function() {
            $(this).height( $(this).height() ) ; // fudge: force the textarea to resize
            $("#edit-template").css( "overflow", "hidden" ) ;
            $("#edit-template textarea").change( on_template_change ) ;
        },
        close: function() {
            $("#edit-template textarea").off( "change", on_template_change ) ;
        },
        buttons: {
            Close: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// --------------------------------------------------------------------

function on_load_scenario()
{
    // FIXME! confirm this operation if the scenario is dirty

    // FOR TESTING PORPOISES! We can't control a file upload from Selenium (since
    // the browser will use native controls), so we store the result in a <div>).
    if ( getUrlParam( "scenario_persistence" ) ) {
        var $elem = $( "#scenario_persistence" ) ; // nb: must have already been created
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
            showErrorMsg( "Can't load the scenario file:<div class='pre'>" + escapeHTML(ex) + "</div>" ) ;
            return ;
        }
        do_load_scenario( data ) ;
        showInfoMsg( "The scenario was loaded." ) ;
    } ;
    fileReader.readAsText( $("#load-scenario").prop("files")[0] ) ;
}

function do_load_scenario( params )
{
    // reset the scenario
    on_new_scenario( false ) ;

    // load the scenario parameters
    var params_loaded = {} ;
    var unknown_vo = [] ;
    var set_param = function( $elem, key ) { $elem.val(params[key]) ; params_loaded[key]=true ; return $elem ; } ;
    // FUDGE! We must set the players first, since changing these will reset the OB tabs.
    if ( "PLAYER_1" in params )
        set_param( $("select[name='PLAYER_1']"), "PLAYER_1" ).trigger( "change" ) ;
    if ( "PLAYER_2" in params )
        set_param( $("select[name='PLAYER_2']"), "PLAYER_2" ).trigger( "change" ) ;
    var i ;
    for ( var key in params ) {
        if ( key === "SSR" ) {
            for ( i=0 ; i < params[key].length ; ++i ) {
                var $ssr = $( "<li></li>" ) ;
                $ssr.text( params[key][i] ) ;
                $("#ssr-sortable").append( $ssr ) ;
                init_ssr( $ssr ) ;
            }
            update_ssr_hint() ;
            params_loaded[key] = true ;
            continue ;
        }
        if ( key === "VEHICLES_1" || key === "ORDNANCE_1" || key === "VEHICLES_2" || key === "ORDNANCE_2" ) {
            var player_id = key.substring( key.length-1 ) ;
            var nat = params[ "PLAYER_" + player_id ] ;
            var vo_type = key.substring(0,9) === "VEHICLES_" ? "vehicle" : "ordnance" ;
            for ( i=0 ; i < params[key].length ; ++i ) {
                if ( ! do_add_vo( nat, vo_type, player_id, params[key][i] ) )
                    unknown_vo.push( params[key][i] ) ;
            }
            update_vo_hint( vo_type, player_id ) ;
            params_loaded[key] = true ;
            continue ;
        }
        //jshint loopfunc: true
        var $elem = $("input[type='text'][name='"+key+"'].param").each( function() {
            set_param( $(this), key ) ;
        } ) ;
        $elem = $("textarea[type='text'][name='"+key+"'].param").each( function() {
            set_param( $(this), key ) ;
        } ) ;
        $elem = $("select[name='"+key+"'].param").each( function() {
            if ( key !== "PLAYER_1" && key !== "PLAYER_2" )
                set_param( $(this), key ).trigger( "change" ) ;
        } ) ;
    }

    // look for unrecognized keys
    var buf = [] ;
    for ( key in params ) {
        if ( ! (key in params_loaded) )
            buf.push( key + " = " + params[key] ) ;
    }
    if ( buf.length > 0 ) {
        showWarningMsg( makeBulletListMsg(
            "Unknown keys in the scenario file:",
            buf, li_class="pre"
        ) ) ;
    }

    // report any unknown vehicles/ordnance
    if ( unknown_vo.length > 0 ) {
        showWarningMsg( makeBulletListMsg(
            "Unknown vehicles/ordnance:", unknown_vo
        ) ) ;
    }
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function on_save_scenario()
{
    // unload the template parameters
    function extract_vo_names( key ) { // nb: we only need to save the vehicle/ordnance name
        if ( !(key in params) )
            return ;
        var names = [] ;
        for ( var i=0 ; i < params[key].length ; ++i )
            names.push( params[key][i].name ) ;
        params[key] = names ;
    }
    var params = {};
    unload_params( params, false ) ;
    extract_vo_names( "VEHICLES_1" ) ;
    extract_vo_names( "ORDNANCE_1" ) ;
    extract_vo_names( "VEHICLES_2" ) ;
    extract_vo_names( "ORDNANCE_2" ) ;
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
    $("#ssr-sortable li").each( function() { $(this).remove() ; } ) ;
    update_ssr_hint() ;

    // reset all the template parameters
    delete_all_vo( "vehicle", 1 ) ;
    delete_all_vo( "ordnance", 1 ) ;
    delete_all_vo( "vehicle", 2 ) ;
    delete_all_vo( "ordnance", 2 ) ;

    // provide some feedback to the user
    if ( verbose )
        showInfoMsg( "The scenario was reset." ) ;
}

// --------------------------------------------------------------------

function on_template_pack()
{
    // FOR TESTING PORPOISES! We can't control a file upload from Selenium (since
    // the browser will use native controls), so we store the result in a <div>).
    if ( getUrlParam( "template_pack_persistence" ) ) {
        var data = $( "#template_pack_persistence" ).val() ; // nb: must have already been created
        var pos = data.indexOf( "|" ) ;
        var fname = data.substring( 0, pos ).trim() ;
        data = data.substring( pos+1 ).trim() ;
        if ( fname.substring(fname.length-4) == ".zip" )
            data = atob( data ) ;
        do_load_template_pack( fname, data ) ;
        return ;
    }

    // ask the user to upload the template pack
    $("#load-template-pack").trigger( "click" ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function on_template_pack_file_selected()
{
    // read the selected file
    var MAX_FILE_SIZE = 2 ; // nb: MB
    var file = $("#load-template-pack").prop("files")[0] ;
    if ( file.size > 1024*1024*MAX_FILE_SIZE ) {
        showErrorMsg( "Template pack is too large (must be no larger than " + MAX_FILE_SIZE + "MB)." ) ;
        return ;
    }
    var fileReader = new FileReader() ;
    fileReader.onload = function() {
        var data = fileReader.result ;
        do_load_template_pack( file.name, data ) ;
    } ;
    fileReader.readAsArrayBuffer( file ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function do_load_template_pack( fname, data )
{
    // initialize
    var invalid_filename_extns = [] ;
    var unknown_template_ids = [] ;
    var template_pack = {
        nationalities: $.extend( true, {}, gDefaultNationalities ),
        templates: {},
    } ;

    // initialize
    function on_template_pack_file( fname, data ) {
        // make sure the filename is valid
        if ( fname.toLowerCase() === "nationalities.json" ) {
            var nationalities = null ;
            try {
                nationalities = JSON.parse( data ) ;
            } catch( ex ) {
                showWarningMsg( "Can't parse the nationalities JSON data:<div class='pre'>" + escapeHTML(ex) + "</div>" ) ;
                return ;
            }
            $.extend( true, template_pack.nationalities, nationalities ) ;
            return ;
        }
        if ( fname.substring(fname.length-3) != ".j2" ) {
            invalid_filename_extns.push( fname ) ;
            return ;
        }
        var template_id = fname.substring( 0, fname.length-3 ).toLowerCase() ;
        if ( gValidTemplateIds.indexOf( template_id ) === -1 ) {
            unknown_template_ids.push( fname ) ;
            return ;
        }
        // save the template pack file
        template_pack.templates[template_id] = data ;
    }

    // initialize
    function install_new_template_pack( success_msg ) {
        // check if there were any errors
        var ok = true ;
        var buf, tid, i ;
        if ( invalid_filename_extns.length > 0 ) {
            buf = [] ;
            buf.push(
                "Invalid template ",
                pluralString( invalid_filename_extns.length, "extension:", "extensions:" ),
                "<div class='pre'>"
            ) ;
            for ( i=0 ; i < invalid_filename_extns.length ; ++i )
                buf.push( escapeHTML(invalid_filename_extns[i]) + "<br>" ) ;
            buf.push( "</div>" ) ;
            buf.push( 'Must be <span class="pre">".zip"</span> or <span class="pre">".j2"</span>.' ) ;
            showErrorMsg( buf.join("") ) ;
            ok = false ;
        }
        if ( unknown_template_ids.length > 0 ) {
            buf = [] ;
            buf.push(
                "Invalid template ",
                pluralString( unknown_template_ids.length, "filename:", "filenames:" ),
                "<div class='pre'>"
            ) ;
            for ( i=0 ; i < unknown_template_ids.length ; ++i )
                buf.push( escapeHTML(unknown_template_ids[i]) + "<br>" ) ;
            buf.push( "</div>" ) ;
            var buf2 = [] ;
            for ( i=0 ; i < gValidTemplateIds.length ; ++i )
                buf2.push( gValidTemplateIds[i] + ".j2" ) ;
            buf.push( makeBulletListMsg( "Must be one of:<div class='pre'>", buf2 ) ) ;
            buf.push( "</div>" ) ;
            showErrorMsg( buf.join("") ) ;
            ok = false ;
        }
        if ( ! ok )
            return ;
        // all good - install the new template pack
        install_template_pack( template_pack ) ;
        showInfoMsg( success_msg ) ;
    }

    // check if we have a ZIP file
    fname = fname.toLowerCase() ;
    if ( fname.substring(fname.length-4) == ".zip" ) {
        // yup - process each file in the ZIP
        var nFiles = 0 ;
        JSZip.loadAsync( data ).then( function( zip ) {
            zip.forEach( function( relPath, zipEntry ) {
                ++ nFiles ;
                zipEntry.async( "string" ).then( function( data ) {
                    // extract the filename (i.e. we ignore sub-directories)
                    fname = zipEntry.name ;
                    var pos = Math.max( fname.lastIndexOf("/"), fname.lastIndexOf("\\") ) ;
                    if ( pos === fname.length-1 )
                        return ; // nb: ignore directory entries
                    if ( pos !== -1 )
                        fname = fname.substring( pos+1 ) ;
                    on_template_pack_file( fname, data ) ;
                } ).then( function() {
                    if ( --nFiles === 0 ) {
                        install_new_template_pack( "The template pack was loaded." ) ;
                    }
                } ) ;
            } ) ;
        } ).catch( function(ex) {
            showErrorMsg( "Can't unpack the ZIP:<div class='pre'>" + escapeHTML(ex) + "</div>" ) ;
        } ) ;
    }
    else {
        // nope - assume an individual template file
        if ( data instanceof ArrayBuffer )
            data = String.fromCharCode.apply( null, new Uint8Array(data) ) ;
        on_template_pack_file( fname, data ) ;
        install_new_template_pack( "The template file was loaded." ) ;
    }

}
