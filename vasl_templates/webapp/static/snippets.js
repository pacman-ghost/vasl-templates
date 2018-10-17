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

var gDefaultScenario = null ;
var gLastSavedScenario = null ;
var gLastSavedScenarioFilename = null;

// --------------------------------------------------------------------

function generate_snippet( $btn, extra_params )
{
    // unload the template parameters
    var template_id = $btn.data( "id" ) ;
    var params = unload_snippet_params( true, true ) ;

    // set player-specific parameters
    var curr_tab = $("#tabs .ui-tabs-active a").attr( "href" ) ;
    var colors ;
    if ( curr_tab === "#tabs-ob1" ) {
        params.PLAYER_NAME = get_nationality_display_name( params.PLAYER_1 ) ;
        colors = get_player_colors( 1 ) ;
        params.OB_COLOR = colors[0] ;
        params.OB_COLOR_2 = colors[2] ;
    } else if ( curr_tab === "#tabs-ob2" ) {
        params.PLAYER_NAME = get_nationality_display_name( params.PLAYER_2 ) ;
        colors = get_player_colors( 2 ) ;
        params.OB_COLOR = colors[0] ;
        params.OB_COLOR_2 = colors[2] ;
    }

    // set player-specific parameters
    if ( template_id == "ob_vehicles_1" ) {
        template_id = "ob_vehicles" ;
        params.OB_VEHICLES = params.OB_VEHICLES_1 ;
        params.OB_VEHICLES_WIDTH = params.OB_VEHICLES_WIDTH_1 ;
    } else if ( template_id == "ob_vehicles_2" ) {
        template_id = "ob_vehicles" ;
        params.OB_VEHICLES = params.OB_VEHICLES_2 ;
        params.OB_VEHICLES_WIDTH = params.OB_VEHICLES_WIDTH_2 ;
    }
    if ( template_id == "ob_ordnance_1" ) {
        template_id = "ob_ordnance" ;
        params.OB_ORDNANCE = params.OB_ORDNANCE_1 ;
        params.OB_ORDNANCE_WIDTH = params.OB_ORDNANCE_WIDTH_1 ;
    } else if ( template_id == "ob_ordnance_2" ) {
        template_id = "ob_ordnance" ;
        params.OB_ORDNANCE = params.OB_ORDNANCE_2 ;
        params.OB_ORDNANCE_WIDTH = params.OB_ORDNANCE_WIDTH_2 ;
    }

    // include the player display names
    params.PLAYER_1_NAME = get_nationality_display_name( params.PLAYER_1 ) ;
    params.PLAYER_2_NAME = get_nationality_display_name( params.PLAYER_2 ) ;

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
    if ( template_id === "pf" && ! is_pf_available() )
        showWarningMsg( "PF are only available after September 1943." ) ;
    if ( template_id === "psk" && ! is_psk_available() )
        showWarningMsg( "PSK are only available after September 1943." ) ;
    if ( template_id === "baz" && ! is_baz_available() )
        showWarningMsg( "BAZ are only available from November 1942." ) ;
    if ( template_id === "atmm" && ! is_atmm_available() )
        showWarningMsg( "ATMM are only available from 1944." ) ;

    // add in any extra parameters
    if ( extra_params )
        $.extend( true, params, extra_params ) ;

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

function unload_snippet_params( unpack_scenario_date, show_warnings )
{
    var params = {} ;

    // extract the scenario date components
    if ( unpack_scenario_date ) {
        var scenario_date = $( "input[name='SCENARIO_DATE']" ).datepicker( "getDate" ) ;
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
    }

    // collect all the template parameters
    add_param = function($elem) { params[ $elem.attr("name") ] = $elem.val() ; } ;
    $("input[type='text'].param").each( function() { add_param($(this)) ; } ) ;
    $("textarea.param").each( function() { add_param($(this)) ; } ) ;
    $("select.param").each( function() { add_param($(this)) ; } ) ;

    // collect the SSR's
    params.SSR = [] ;
    var data = $("#ssr-sortable").sortable2( "get-entry-data" ) ;
    for ( var i=0 ; i < data.length ; ++i )
        params.SSR.push( data[i].caption ) ;

    // collect the vehicles/ordnance
    function get_vo( vo_type, player_no, key ) {
        var $sortable2 = $( "#ob_" + vo_type + "-sortable_" + player_no ) ;
        var objs = [] ;
        $sortable2.children( "li" ).each( function() {
            var vo_entry = $(this).data( "sortable2-data" ).vo_entry ;
            var vo_image_id = $(this).data( "sortable2-data" ).vo_image_id ;
            var obj = {
                id: vo_entry.id,
                image_id: (vo_image_id !== null) ? vo_image_id[0]+"/"+vo_image_id[1] : null,
                name: vo_entry.name,
                note_number: vo_entry.note_number,
                notes: vo_entry.notes
            } ;
            if ( gUserSettings["include-vasl-images-in-snippets"] ) {
                var url = get_vo_image_url( vo_entry, vo_image_id ) ;
                if ( url )
                    obj.image = APP_URL_BASE + url ;
            }
            // NOTE: It would be nice to have a Jinja2 filter that inserted the raw capabilities or selected
            // the correct one for the scenario date e.g.
            //   {% for c in veh.capabilities %} {{c|selcap}} {%endif%}}
            // but the problem is that if a capability is not available, we want nothing to appear,
            // but by the time the filter gets called, it's too late :-( Instead, we provide a "raw_capabilities"
            // parameter that people can use in their templates - ugly, but probably not something that will
            // get a lot of use :-/
            var nat = params[ "PLAYER_"+player_no ] ;
            var capabilities = $(this).data( "sortable2-data" ).custom_capabilities ;
            if ( capabilities ) {
                obj.capabilities = capabilities ;
                obj.custom_capabilities = capabilities.slice() ;
            } else {
                // NOTE: We don't show warnings here; if there's something wrong,
                // we will show the warnings when we make the raw capabilities.
                capabilities = make_capabilities(
                    false,
                    vo_entry, nat,
                    params.SCENARIO_THEATER, params.SCENARIO_YEAR, params.SCENARIO_MONTH,
                    false
                ) ;
                if ( capabilities )
                    obj.capabilities = capabilities ;
            }
            capabilities = make_capabilities(
                true,
                vo_entry, nat,
                params.SCENARIO_THEATER, params.SCENARIO_YEAR, params.SCENARIO_MONTH,
                show_warnings
            ) ;
            if ( capabilities )
                obj.raw_capabilities = capabilities ;
            objs.push( obj ) ;
        } ) ;
        if ( objs.length > 0 )
            params[key] = objs ;
    }
    get_vo( "vehicles", 1, "OB_VEHICLES_1" ) ;
    get_vo( "vehicles", 2, "OB_VEHICLES_2" ) ;
    get_vo( "ordnance", 1, "OB_ORDNANCE_1" ) ;
    get_vo( "ordnance", 2, "OB_ORDNANCE_2" ) ;

    return params ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function make_capabilities( raw, vo_entry, nat, scenario_theater, scenario_year, scenario_month, show_warnings )
{
    var capabilities = [] ;

    // check if the vehicle has no radio
    if ( vo_entry.no_radio )
        capabilities.push( vo_entry.no_radio ) ;

    // check if the vehicle has no intensive fire
    if ( vo_entry.no_if ) {
        var no_if = "no IF" ;
        if ( typeof(vo_entry.no_if) === "string" ) { // nb: only for the French B1-bis :-/
            no_if = vo_entry.no_if ;
            if ( no_if.substring(no_if.length-1) == "\u2020" )
                no_if = "no IF<sup>"+no_if.substring(0,no_if.length-1)+"</sup>\u2020" ;
            else
                no_if = "no IF<sup>"+no_if+"</sup>" ;
        }
        capabilities.push( no_if ) ;
    }

    // extract the static capabilities
    var i ;
    if ( "capabilities" in vo_entry ) {
        for ( i=0 ; i < vo_entry.capabilities.length ; ++i )
            capabilities.push( vo_entry.capabilities[i] ) ;
    }

    // extract the variable capabilities
    if ( "capabilities2" in vo_entry ) {
        var indeterminate_caps=[], unexpected_caps=[], invalid_caps=[] ;
        for ( var key in vo_entry.capabilities2 ) {
            // check if the capability is dependent on the scenario date
            if ( !( vo_entry.capabilities2[key] instanceof Array ) ) {
                capabilities.push( key + vo_entry.capabilities2[key] ) ;
                continue ;
            }
            // check for LF
            if ( key == "LF" ) {
                var caps = $.extend( true, [], vo_entry.capabilities2[key] ) ;
                if ( caps[caps.length-1] == "\u2020" ) {
                    caps.pop() ;
                    capabilities.push( "LF\u2020" ) ;
                } else
                    capabilities.push( "LF" ) ;
                capabilities[ capabilities.length-1 ] += " [" + caps.join(", ") + "]" ;
                continue ;
            }
            if ( $.inArray( key, ["HE","AP","A","D","C","H","B","s","sM","sD","sN","WP","IR","Towed"] ) === -1 ) {
                unexpected_caps.push( key ) ;
                continue ;
            }
            // check if we should return the raw capability, or select the one for the scenario date
            if ( ! scenario_year ) {
                indeterminate_caps.push( key ) ;
                raw = true ;
            }
            if ( raw ) {
                capabilities.push( make_raw_capability( key, vo_entry.capabilities2[key] ) ) ;
            }
            else {
                var cap = _select_capability_by_date( vo_entry.capabilities2[key], nat, scenario_theater, scenario_year, scenario_month ) ;
                if ( cap === null )
                    continue ;
                if ( cap == "<invalid>" ) {
                    invalid_caps.push( vo_entry.name + ": " + key + ": " + vo_entry.capabilities2[key] ) ;
                    continue ;
                }
                capabilities.push( key + cap ) ;
            }
        }
        // check if there were any capabilities not set
        if ( show_warnings && indeterminate_caps.length > 0 ) {
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
    if ( "capabilities_other" in vo_entry ) {
        for ( i=0 ; i < vo_entry.capabilities_other.length ; ++i )
            capabilities.push( vo_entry.capabilities_other[i] ) ;
    }

    // include damage points (for Landing Craft)
    if ( "damage_points" in vo_entry )
        capabilities.push( "DP " + vo_entry.damage_points ) ;

    // include crew survival
    var crew_survival = make_crew_survival( vo_entry ) ;
    if ( crew_survival )
        capabilities.push( crew_survival ) ;

    return capabilities ;
}

function make_raw_capability( name, capability )
{
    // NOTE: The capability can sometimes not have a # e.g. Tetrarch CS has a s# of "ref1".
    if ( capability[0] === null ) {
        var cap = capability[1] ;
        if ( cap.match( /^\d\+?$/ ) )
            cap = "<sup>" + cap + "</sup>" ;
        return name + cap ;
    }

    // generate the raw capability string
    var buf = [ name ] ;
    for ( var i=0 ; i < capability.length ; ++i ) {
        if ( typeof(capability[i]) === "string" )
            buf.push( capability[i] ) ;
        else {
            if ( capability[i][0] )
                buf.push( escapeHTML( capability[i][0] ) ) ;
            if ( capability[i][1] )
                buf.push( "<sup>", escapeHTML( capability[i][1] ), "</sup>" ) ;
        }
    }
    return buf.join( "" ) ;
}

function _select_capability_by_date( capabilities, nat, scenario_theater, scenario_year, scenario_month )
{
    // NOTE: The capability can sometimes not have a number e.g. Tetrarch CS s# = "ref1", Stuart III(a) = "HE(4+)"
    var timestamp, val ;
    if ( capabilities[0] === null ) {
        timestamp = capabilities[1] ;
        if ( timestamp.match( /^\d\+?$/ ) ) {
            val = _check_capability_timestamp( capabilities, timestamp, nat, scenario_theater, scenario_year, scenario_month ) ;
            if ( val === "<ignore>" )
                return null ;
            return "";
        }
        return timestamp ;
    }

    // initialize
    capabilities = capabilities.slice() ;
    var ref = has_ref( capabilities ) ;

    // check all the capability timestamps
    var retval = "???" ;
    for ( var i=0 ; i < capabilities.length ; ++i ) {
        timestamp = capabilities[i][1].toString() ;
        val = _check_capability_timestamp( capabilities[i], timestamp, nat, scenario_theater, scenario_year, scenario_month ) ;
        if ( val === "<invalid>" )
            return val ;
        if ( val === "<ignore>" )
            continue ;
        retval = val ;
    }
    if ( retval === "???" )
        return null ;
    if ( retval === null )
        retval = "" ; // nb: this can happen for IR
    return ref ? retval+ref : retval ;
}

function _check_capability_timestamp( capabilities, timestamp, nat, scenario_theater, scenario_year, scenario_month )
{
    var MONTH_NAMES = { F:2, J:6, A:8, S:9, N:11 } ;

    // check for a theater flag
    if ( timestamp.substring( timestamp.length-1 ) === "E" ) {
        if ( scenario_theater != "ETO" )
            return "<ignore>" ;
        timestamp = timestamp.substring( 0, timestamp.length-1 ) ;
    }
    if ( timestamp.substring( timestamp.length-1 ) === "P" ) {
        if ( scenario_theater != "PTO" )
            return "<ignore>" ;
        timestamp = timestamp.substring( 0, timestamp.length-1 ) ;
    }
    if ( timestamp.substring( timestamp.length-1 ) === "B" ) {
        if ( scenario_theater != "BURMA" )
            return "<ignore>" ;
        timestamp = timestamp.substring( 0, timestamp.length-1 ) ;
    }
    if ( timestamp.substring( timestamp.length-1 ) === "R" ) {
        if ( nat != "romanian" )
            return "<ignore>" ;
        timestamp = timestamp.substring( 0, timestamp.length-1 ) ;
    }
    if ( timestamp.substring( timestamp.length-2 ) === "CS" ) {
        if ( nat != "croatian" && nat != "slovakian" )
            return "<ignore>" ;
        timestamp = timestamp.substring( 0, timestamp.length-2 ) ;
    }
    if ( timestamp.substring( timestamp.length-1 ) === "S" ) {
        if ( nat != "slovakian" )
            return "<ignore>" ;
        timestamp = timestamp.substring( 0, timestamp.length-1 ) ;
    }

    // remove any trailing "+" (FIXME! What does it even mean? Doesn't make sense :-/)
    if ( timestamp.substring( timestamp.length-1 ) == "+" )
        timestamp = timestamp.substring( 0, timestamp.length-1 ) ;

    // check if there is anything left
    if ( ! timestamp ) {
        // nope - the capability is always available
        return capabilities[0] ;
    }

    // parse the month/year the capability becomes available
    var month = MONTH_NAMES[ timestamp.substring(0,1) ] ;
    if ( month )
        timestamp = timestamp.substring( 1 ) ;
    if ( /^\d$/.test( timestamp ) ) {
        // this is a single year
        timestamp = parseInt( timestamp ) ;
        // check if the capabilitity is available
        if ( scenario_year > 1940 + timestamp )
            return capabilities[0] ;
        else if ( scenario_year == 1940 + timestamp ) {
            if( !month || scenario_month >= month )
                return capabilities[0] ;
        }
    } else if ( /^\d-\d$/.test( timestamp ) ) {
        // this is a range of years
        var timestamp1 = parseInt( timestamp[0] ) ;
        var timestamp2 = parseInt( timestamp[timestamp.length-1] ) ;
        // check if the capabilitity is available
        if ( 1940+timestamp1 <= scenario_year && scenario_year <= 1940+timestamp2 )
            return capabilities[0] ;
    }
    else
        return "<invalid>" ;

    return "<ignore>" ;
}

function has_ref( val )
{
    var last = val[ val.length-1 ] ;
    if ( typeof(last) === "string" && last.match( /^\u2020(<sup>\d<\/sup>)?$/ ) ) {
        val.pop() ;
        return last ;
    }
    return null ;
}

function make_crew_survival( vo_entry )
{
    function make_cs_string( prefix, val ) {
        if ( val.length === 2 && val[0] === null && val[1] === "\u2020" )
            return "\u2020" ;
        else
            return prefix + " " + val ;
    }

    // check if the vehicle has a crew survival field
    var crew_survival = null ;
    if ( "CS#" in vo_entry )
        crew_survival = make_cs_string( "CS", vo_entry["CS#"] ) ;
    else if ( "cs#" in vo_entry )
        crew_survival = make_cs_string( "cs", vo_entry["cs#"] ) ;
    if ( crew_survival === null )
        return null ;

    // check if the vehicle is subject to brew up
    var pos = crew_survival.indexOf( ":brewup" ) ;
    if ( pos !== -1 )
        crew_survival = crew_survival.substring(0,pos) + " <small><i>(brew up)</i></small>" + crew_survival.substring(pos+7) ;

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
    if ( template_id.substring(0,12) == "ob_ordnance_" )
        template_id = "ob_ordnance" ;
    else if ( template_id.substring(0,12) == "ob_vehicles_" )
        template_id = "ob_vehicles" ;
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
        create: function() {
            init_dialog( $(this), "Close", true ) ;
        },
        open: function() {
            on_dialog_open( $(this) ) ;
            $(this).height( $(this).height() ) ; // fudge: force the textarea to resize
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
    // check if the scenario is dirty
    if ( ! is_scenario_dirty() )
        do_on_load_scenario() ;
    else {
        // yup - confirm the operation
        ask( "Load scenario", "<p>This scenario has been changed.<p>Do you want load another scenario, and lose your changes?", {
            ok: do_on_load_scenario,
            cancel: function() {},
        } ) ;
    }

    function do_on_load_scenario() {
        // FOR TESTING PORPOISES! We can't control a file upload from Selenium (since
        // the browser will use native controls), so we get the data from a <textarea>).
        if ( getUrlParam( "scenario_persistence" ) ) {
            var $elem = $( "#_scenario-persistence_" ) ;
            do_load_scenario( $elem.val(), null ) ;
            showInfoMsg( "The scenario was loaded." ) ; // nb: the tests are looking for this
            return ;
        }

        // if we are running inside the PyQt wrapper, let it handle everything
        if ( gWebChannelHandler ) {
            gWebChannelHandler.load_scenario( function( data ) {
                if ( ! data )
                    return ;
                do_load_scenario( data, null ) ;
            } ) ;
            return ;
        }

        // ask the user to upload the scenario file
        $("#load-scenario").trigger( "click" ) ;
    }
}

function on_load_scenario_file_selected()
{
    // read the selected file
    var fileReader = new FileReader() ;
    var file = $("#load-scenario").prop( "files" )[0] ;
    fileReader.onload = function() {
        do_load_scenario( fileReader.result, file.name ) ;
    } ;
    fileReader.readAsText( file ) ;
}

function do_load_scenario( data, fname )
{
    // NOTE: We reset the scenario first, in case the loaded scenario is missing fields,
    // so that those fields will be reset to their default values (instead of just staying unchanged).
    do_on_new_scenario() ;

    // load the scenario
    try {
        data = JSON.parse( data ) ;
    } catch( ex ) {
        showErrorMsg( "Can't load the scenario file:<div class='pre'>" + escapeHTML(ex) + "</div>" ) ;
        return ;
    }
    do_load_scenario_data( data ) ;
    gLastSavedScenarioFilename = fname ;
    showInfoMsg( "The scenario was loaded." ) ;
}

function do_load_scenario_data( params )
{
    // reset the scenario
    reset_scenario() ;

    // load the scenario parameters
    var params_loaded = {} ;
    var warnings = [] ;
    var unknown_vo = [] ;
    var set_param = function( $elem, key ) {
        if ( key === "SCENARIO_DATE" ) {
            try {
                var scenario_date = $.datepicker.parseDate( "yy-mm-dd", params[key] ) ;
                $elem.datepicker( "setDate", scenario_date ) ;
            } catch( ex ) {
                warnings.push( "Invalid scenario date: " + escapeHTML( params[key] ) ) ;
            }
        }
        else
            $elem.val( params[key] ) ;
        if ( $elem[0].nodeName.toLowerCase() === "select" )
            $elem.selectmenu( "refresh" ) ;
        params_loaded[key] = true ;
        return $elem ;
    } ;
    // FUDGE! We must set the players first, since changing these will reset the OB tabs.
    if ( "PLAYER_1" in params ) {
        set_param( $("select[name='PLAYER_1']"), "PLAYER_1" ) ;
        on_player_change( 1 ) ;
    }
    if ( "PLAYER_2" in params ) {
        set_param( $("select[name='PLAYER_2']"), "PLAYER_2" ) ;
        on_player_change( 2 ) ;
    }
    var i ;
    for ( var key in params ) {
        var player_no, $sortable2 ;
        if ( key === "SSR" ) {
            $sortable2 = $( "#ssr-sortable" ) ;
            for ( i=0 ; i < params[key].length ; ++i )
                do_add_scenario_note( $sortable2, { caption: params[key][i] } ) ;
            params_loaded[key] = true ;
            continue ;
        }
        if ( key === "SCENARIO_NOTES" ) {
            $sortable2 = $( "#scenario_notes-sortable" ) ;
            for ( i=0 ; i < params[key].length ; ++i )
                do_add_scenario_note( $sortable2, params[key][i] ) ;
            params_loaded[key] = true ;
            continue ;
        }
        if ( key === "OB_SETUPS_1" || key === "OB_SETUPS_2" ) {
            player_no = key.substring( key.length-1 ) ;
            $sortable2 = $( "#ob_setups-sortable_" + player_no ) ;
            for ( i=0 ; i < params[key].length ; ++i )
                do_add_ob_setup( $sortable2, params[key][i] ) ;
            params_loaded[key] = true ;
            continue ;
        }
        if ( key === "OB_NOTES_1" || key === "OB_NOTES_2" ) {
            player_no = key.substring( key.length-1 ) ;
            $sortable2 = $( "#ob_notes-sortable_" + player_no ) ;
            for ( i=0 ; i < params[key].length ; ++i )
                do_add_ob_note( $sortable2, params[key][i] ) ;
            params_loaded[key] = true ;
            continue ;
        }
        if ( key === "OB_VEHICLES_1" || key === "OB_ORDNANCE_1" || key === "OB_VEHICLES_2" || key === "OB_ORDNANCE_2" ) {
            player_no = key.substring( key.length-1 ) ;
            var nat = params[ "PLAYER_" + player_no ] ;
            var vo_type = (key.substring(0,12) === "OB_VEHICLES_") ? "vehicles" : "ordnance" ;
            for ( i=0 ; i < params[key].length ; ++i ) {
                var vo_id = params[key][i].id ;
                var vo_entry ;
                if ( vo_id )
                    vo_entry = find_vo( vo_type, nat, vo_id ) ;
                else {
                    // FUDGE! Early versions stored vehicles/ordnance by name, but these are not unique (even within
                    // a single nationality :-/), so we switched to manually-assigned unique ID's. For legacy save files,
                    // if there is no ID field, we load vehicles/ordnance by name.
                    vo_id = params[key][i].name ; // nb: we store the name in the ID variable, in case we have to log an error below
                    vo_entry = find_vo_by_name( vo_type, nat, vo_id ) ;
                }
                var vo_image_id = null ;
                if ( "image_id" in params[key][i] ) {
                    var matches = params[key][i].image_id.match( /^(\d{3,4})\/(\d)$/ ) ;
                    if ( matches )
                        vo_image_id = [ parseInt(matches[1]), parseInt(matches[2]) ] ;
                    else
                        warnings.push( "Invalid V/O image ID for '" + params[key][i].name + "': " + params[key][i].image_id ) ;
                }
                if ( vo_entry )
                    do_add_vo( vo_type, player_no, vo_entry, vo_image_id, params[key][i].custom_capabilities ) ;
                else
                    unknown_vo.push( vo_id || "(not set)" ) ;
            }
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
        if ( !(key in params_loaded) && key.substring(0,1) !== "_" )
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

    // show any other warnings
    if ( warnings.length == 1 )
        showWarningMsg( warnings[0] ) ;
    else if ( warnings.length > 1 ) {
        showWarningMsg( makeBulletListMsg(
            "", warnings
        ) ) ;
    }

    // remember the state of this scenario
    gLastSavedScenario = unload_params_for_save() ;

    // update the UI
    $("#tabs").tabs( "option", "active", 0 ) ;
    on_scenario_name_change() ;
    on_scenario_date_change() ;
}

// --------------------------------------------------------------------

function on_save_scenario()
{
    // unload the template parameters
    var params = unload_params_for_save() ;
    var data = JSON.stringify( params ) ;

    // FOR TESTING PORPOISES! We can't control a file download from Selenium (since
    // the browser will use native controls), so we store the result in a <textarea>
    // and the test suite will collect it from there).
    if ( getUrlParam( "scenario_persistence" ) ) {
        $("#_scenario-persistence_").val( data ) ;
        gLastSavedScenario = params ;
        return ;
    }

    // if we are running inside the PyQt wrapper, let it handle everything
    if ( gWebChannelHandler ) {
        gWebChannelHandler.save_scenario( data, function( result ) {
            if ( ! result )
                return ;
            gLastSavedScenario = params ;
            showInfoMsg( "The scenario was saved." ) ;
        } ) ;
        return ;
    }

    // return the parameters to the user as a downloadable file
    download( data,
        gLastSavedScenarioFilename ? gLastSavedScenarioFilename : "scenario.json",
        "application/json"
    ) ;
    // NOTE: We get no indication if the download was successful, so we can't show feedback :-/
    // Also, if the download didn't actually happen (e.g. because it was cancelled), then setting
    // the last saved scenario here is not quite the right thing to do, since subsequent checks
    // for a dirty scenario will return the wrong result, since they assume that the scenario
    // was saved properly here :-/
    gLastSavedScenario = params ;
}

function unload_params_for_save()
{
    function extract_vo_entries( key ) {
        if ( !(key in params) )
            return ;
        var entries = [] ;
        for ( var i=0 ; i < params[key].length ; ++i ) {
            var entry = {
                id: params[key][i].id,
                name: params[key][i].name, // nb: not necessary, but convenient
            } ;
            if ( params[key][i].image_id !== null )
                entry.image_id = params[key][i].image_id ;
            if ( params[key][i].custom_capabilities )
                entry.custom_capabilities = params[key][i].custom_capabilities ;
            entries.push( entry ) ;
        }
        params[key] = entries ;
    }

    // unload the template parameters
    var params = unload_snippet_params( false, false ) ;
    params.SCENARIO_NOTES = $("#scenario_notes-sortable").sortable2( "get-entry-data" ) ;
    params.OB_SETUPS_1 = $("#ob_setups-sortable_1").sortable2( "get-entry-data" ) ;
    params.OB_SETUPS_2 = $("#ob_setups-sortable_2").sortable2( "get-entry-data" ) ;
    params.OB_NOTES_1 = $("#ob_notes-sortable_1").sortable2( "get-entry-data" ) ;
    params.OB_NOTES_2 = $("#ob_notes-sortable_2").sortable2( "get-entry-data" ) ;
    extract_vo_entries( "OB_VEHICLES_1" ) ;
    extract_vo_entries( "OB_ORDNANCE_1" ) ;
    extract_vo_entries( "OB_VEHICLES_2" ) ;
    extract_vo_entries( "OB_ORDNANCE_2" ) ;

    // save the scenario date in ISO-8601 format
    var scenario_date = $("input[name='SCENARIO_DATE']").datepicker( "getDate" ) ;
    if ( scenario_date )
        params.SCENARIO_DATE = scenario_date.toISOString().substring( 0, 10 ) ;

    return params ;
}

// --------------------------------------------------------------------

function on_new_scenario()
{
    // check if the scenario is dirty
    if ( ! is_scenario_dirty() )
        do_on_new_scenario( true ) ;
    else {
        // yup - confirm the operation
        ask( "New scenario", "<p>This scenario has been changed.<p>Do you want to reset it, and lose your changes?", {
            ok: function() { do_on_new_scenario( true ) ; },
            cancel: function() {},
        } ) ;
    }
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function do_on_new_scenario( verbose ) {
    // load the default scenario
    if ( gDefaultScenario )
        do_load_scenario_data( gDefaultScenario ) ;
    else {
        $.getJSON( gGetDefaultScenarioUrl, function(data) {
            gDefaultScenario = data ;
            do_load_scenario_data( data ) ;
            update_page_load_status( "default-scenario" ) ;
        } ).fail( function( xhr, status, errorMsg ) {
            showErrorMsg( "Can't get the default scenario:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
            return ;
        } ) ;
    }

    // flag that we have a new scenario
    gLastSavedScenarioFilename = null ;
    if ( gWebChannelHandler )
        gWebChannelHandler.on_new_scenario() ;

    // provide some feedback to the user
    if ( verbose )
        showInfoMsg( "The scenario was reset." ) ;
}

function reset_scenario()
{
    // reset all the template parameters
    $("input[type='text'].param").each( function() { $(this).val("") ; } ) ;
    $("textarea.param").each( function() { $(this).val("") ; } ) ;

    // reset all the template parameters
    // nb: there's no way to reset the player droplist's
    var player_no ;
    for ( player_no=1 ; player_no <= 2 ; ++player_no ) {
        on_player_change( player_no ) ;
        $("select[name='PLAYER_" + player_no + "_ELR']").val( 0 ).selectmenu( "refresh" ) ;
        $("select[name='PLAYER_" + player_no + "_SAN']").val( "" ).selectmenu( "refresh" ) ;
    }

    // reset all the template parameters
    $("#scenario_notes-sortable").sortable2( "delete-all" ) ;
    $("#ssr-sortable").sortable2( "delete-all" ) ;
}

// --------------------------------------------------------------------

function is_scenario_dirty()
{
    // nb: confirming operations is insanely annoying during development :-/
    if ( getUrlParam( "disable-dirty-scenario-check" ) )
        return false ;

    // check if the scenario has been changed since it was loaded, or last saved
    if ( gLastSavedScenario === null )
        return false ;
    var params = unload_params_for_save() ;
    return (JSON.stringify(params) != JSON.stringify(gLastSavedScenario) ) ;
}

// --------------------------------------------------------------------

function on_template_pack()
{
    // FOR TESTING PORPOISES! We can't control a file upload from Selenium (since
    // the browser will use native controls), so we store the result in a <div>).
    if ( getUrlParam( "template_pack_persistence" ) ) {
        var data = $( "#_template-pack-persistence_" ).val() ;
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
    var file = $("#load-template-pack").prop( "files" )[0] ;
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

// --------------------------------------------------------------------

function _is_scenario_after( month, year ) {
    // check if the scenario is after the specified month/year
    var scenario_date = $("input[name='SCENARIO_DATE']").datepicker( "getDate" ) ;
    if ( ! scenario_date )
        return false ;
    if ( scenario_date.getFullYear() > year )
        return true ;
    if ( scenario_date.getFullYear() < year )
        return false ;
    return (scenario_date.getMonth() >= month) ;
}

function is_pf_available() { return _is_scenario_after( 9, 1943 ) ; }
function is_psk_available() { return _is_scenario_after( 9, 1943 ) ; }
function is_baz_available() { return _is_scenario_after( 10, 1942 ) ; }
function is_atmm_available() { return _is_scenario_after( 0, 1944 ) ; }

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function on_scenario_date_change()
{
    // NOTE: We update the visual appearance of the buttons to indicate whether
    // the support weapons are available, but leave the buttons active since
    // the date restrictions are not strict, and the SW are sometimes available
    // (by SSR) even outside the normal time.
    function update_ui( id, is_available ) {
        var $btn = $( "button.generate[data-id='" + id + "']" ) ;
        $btn.css( "color", is_available?"#000":"#aaa" ) ;
        $btn.children( "img" ).each( function() {
            $(this).attr( "src", gImagesBaseUrl + (is_available?"/snippet.png":"/snippet-disabled.png") ) ;
        } ) ;
    }
    update_ui( "pf", is_pf_available() ) ;
    update_ui( "psk", is_psk_available() ) ;
    update_ui( "baz", is_baz_available() ) ;
    update_ui( "atmm", is_atmm_available() ) ;

    var snippet_params = unload_snippet_params( true, false ) ;
    function update_vo( $sortable2 ) {
        $sortable2.children( "li" ).each( function() {
            update_vo_sortable2_entry( $(this), snippet_params ) ;
        } ) ;
    }
    for ( var player_no=1 ; player_no <= 2 ; ++player_no ) {
        update_vo( $( "#ob_vehicles-sortable_" + player_no ) ) ;
        update_vo( $( "#ob_ordnance-sortable_" + player_no ) ) ;
    }
}

// --------------------------------------------------------------------

function on_scenario_name_change()
{
    // update the document title to include the scenario name
    var val = $("input[name='SCENARIO_NAME']").val().trim() ;
    document.title = (val.length > 0) ? gAppName+" - "+val : gAppName ;

    // notify the PyQt wrapper application
    if ( gWebChannelHandler )
        gWebChannelHandler.on_scenario_name_change( val ) ;
}
