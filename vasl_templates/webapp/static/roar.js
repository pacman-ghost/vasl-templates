gRoarScenarioIndex = null ;

// --------------------------------------------------------------------

function _get_roar_scenario_index( on_ready )
{
    // check if we already have the ROAR scenario index
    if ( gRoarScenarioIndex  && Object.keys(gRoarScenarioIndex).length > 0 ) {
        // yup - just do it
        on_ready() ;
    } else {
        // nope - download it (nb: we do this on-demand, instead of during startup,
        // to give the backend time if it wants to download a fresh copy).
        // NOTE: We will also get here if we downloaded the scenario index, but it's empty.
        // This can happen if the cached file is not there, and the server is still downloading
        // a fresh copy, in which case, we will keep retrying until we get something.
        $.getJSON( gGetRoarScenarioIndexUrl, function(data) {
            gRoarScenarioIndex = data ;
            on_ready() ;
        } ).fail( function( xhr, status, errorMsg ) {
            showErrorMsg( "Can't get the ROAR scenario index:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        } ) ;
    }
}

// --------------------------------------------------------------------

function search_roar()
{
    var unknown_nats = [] ;
    function on_scenario_selected( roar_id ) {
        // update the UI for the selected ROAR scenario
        set_roar_scenario( roar_id ) ;
        // populate the scenario name/ID
        var scenario = gRoarScenarioIndex[ roar_id ] ;
        if ( $("input[name='SCENARIO_NAME']").val() === "" && $("input[name='SCENARIO_ID']").val() === "" ) {
            $("input[name='SCENARIO_NAME']").val( scenario.name ) ;
            $("input[name='SCENARIO_ID']").val( scenario.scenario_id ) ;
        }
        // update the player nationalities
        // NOTE: The player order as returned by ROAR is undetermined (and could change from call to call),
        // so what we set here might not match what's in the scenario card, but we've got a 50-50 chance of being right... :-/
        update_player( scenario, 1 ) ;
        update_player( scenario, 2 ) ;
        if ( unknown_nats.length > 0 ) {
            var buf = [ "Unrecognized nationality in ROAR:", "<ul>" ] ;
            for ( var i=0 ; i < unknown_nats.length ; ++i )
                buf.push( "<li>" + unknown_nats[i] ) ;
            buf.push( "</ul>" ) ;
            showWarningMsg( buf.join("") ) ;
        }
    }

    function update_player( scenario, player_no ) {
        var roar_nat = scenario.results[ player_no-1 ][0] ;
        var nat = convert_roar_nat( roar_nat ) ;
        if ( ! nat ) {
            unknown_nats.push( roar_nat ) ;
            return ;
        }
        if ( nat === get_player_nat( player_no ) )
            return ;
        if ( ! is_player_ob_empty( player_no ) )
            return ;
        $( "select[name='PLAYER_" + player_no + "']" ).val( nat ).trigger( "change" ) ;
        on_player_change( player_no ) ;
    }

    // ask the user to select a ROAR scenario
    _get_roar_scenario_index( function() {
        do_search_roar( on_scenario_selected ) ;
    } ) ;
}

function do_search_roar( on_ok )
{
    // initialize the select2
    var $sel = $( "#select-roar-scenario select" ) ;
    $sel.select2( {
        width: "100%",
        templateResult: function( opt ) { return opt.id ? _format_entry(opt.id) : opt.text ; },
        dropdownParent: $("#select-roar-scenario"), // FUDGE! need this for the searchbox to work :-/
        closeOnSelect: false,
    } ) ;

    // stop the select2 droplist from closing up
    $sel.on( "select2:closing", function(evt) {
        evt.preventDefault() ;
    } ) ;

    // let the user select a scenario
    function on_resize( $dlg ) {
        $( ".select2-results ul" ).height( $dlg.height() - 50 ) ;
    }
    var $dlg = $("#select-roar-scenario").dialog( {
        title: "Search ROAR",
        dialogClass: "select-roar-scenario",
        modal: true,
        minWidth: 400,
        minHeight: 350,
        create: function() {
            // initialize the dialog
            init_dialog( $(this), "OK", false ) ;
            // handle ENTER and double-click
            function auto_select_scenario( evt ) {
                if ( $sel.val() ) {
                    $( ".ui-dialog.select-roar-scenario button:contains('OK')" ).click() ;
                    evt.preventDefault() ;
                }
            }
            $("#select-roar-scenario").keydown( function(evt) {
                if ( evt.keyCode == $.ui.keyCode.ENTER )
                    auto_select_scenario( evt ) ;
                else if ( evt.keyCode == $.ui.keyCode.ESCAPE )
                    $(this).dialog( "close" ) ;
            } ).dblclick( function(evt) {
                auto_select_scenario( evt ) ;
            } ) ;
        },
        open: function() {
            // initialize
            // NOTE: We do this herem instead of in the "create" handler, to handle the case
            // where the scenario index was initially unavailable but the download has since completed.
            _load_select2( $sel ) ;
            on_dialog_open( $(this) ) ;
            $sel.select2( "open" ) ;
            // update the UI
            on_resize( $(this) ) ;
        },
        resize: function() { on_resize( $(this) ) ; },
        buttons: {
            OK: function() {
                // notify the caller about the selected scenario
                var roar_id = $sel.select2("data")[0].id ;
                on_ok(  roar_id ) ;
                $dlg.dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

function _load_select2( $sel )
{
    function remove_quotes( lquote, rquote ) {
        var len = name.length ;
        if ( name.substr( 0, lquote.length ) === lquote && name.substr( len-rquote.length ) === rquote )
            name = name.substr( lquote.length, len-lquote.length-rquote.length ) ;
        if ( name.substr( 0, lquote.length ) == lquote )
            name = name.substr( lquote.length ) ;
        return name ;
    }

    // sort the scenarios
    var roar_ids=[], roar_id, scenario ;
    for ( roar_id in gRoarScenarioIndex ) {
        if ( roar_id[0] === "_" )
            continue ;
        roar_ids.push( roar_id ) ;
        scenario = gRoarScenarioIndex[ roar_id ] ;
        var name = scenario.name ;
        name = remove_quotes( '"', '"' ) ;
        name = remove_quotes( "'", "'" ) ;
        name = remove_quotes( "&quot;", "&quot;" ) ;
        name = remove_quotes( "\u2018", "\u2019" ) ;
        name = remove_quotes( "\u201c", "\u201d" ) ;
        if ( name.substring(0,3) === "..." )
            name = name.substr( 3 ) ;
        scenario._sort_name = name.trim().toUpperCase() ;
    }
    roar_ids.sort( function( lhs, rhs ) {
        lhs = gRoarScenarioIndex[ lhs ]._sort_name ;
        rhs = gRoarScenarioIndex[ rhs ]._sort_name ;
        if ( lhs < rhs )
            return -1 ;
        else if ( lhs > rhs )
            return +1 ;
        return 0 ;
    } ) ;

    // get the currently-active ROAR scenario
    var curr_roar_id = $("input[name='ROAR_ID']").val() ;

    // load the select2
    var buf = [] ;
    for ( var i=0 ; i < roar_ids.length ; ++i ) {
        roar_id = roar_ids[ i ] ;
        scenario = gRoarScenarioIndex[ roar_id ] ;
        // NOTE: The <option> text is what gets searched (_format_entry() generates what gets shown),
        // so we include the scenario ID here, so that it also becomes searchable.
        buf.push( "<option value='" + roar_id + "'" ) ;
        if ( roar_id === curr_roar_id ) {
            // FIXME! How can we scroll this into view? Calling scrollIntoView(),
            // even in the "open" handler, causes weird problems.
            buf.push( " selected" ) ;
        }
        buf.push( ">" ) ;
        buf.push( scenario.name + " " + scenario.scenario_id,
            "</option>"
        ) ;
    }
    $sel.html( buf.join("") ) ;
}

function _format_entry( roar_id ) {
    // generate the HTML for a scenario
    var scenario = gRoarScenarioIndex[ roar_id ] ;
    var buf = [ "<div class='scenario' data-roarid='", roar_id , "'>",
        scenario.name,
        " <span class='scenario-id'>[", strReplaceAll(scenario.scenario_id," ","&nbsp;"), "]</span>",
        " <span class='publication'>", scenario.publication, "</span>",
        "</div>"
    ] ;
    return $( buf.join("") ) ;
}

// --------------------------------------------------------------------

function disconnect_roar()
{
    // disconnect from the ROAR scenario
    set_roar_scenario( null ) ;
}

// --------------------------------------------------------------------

function go_to_roar_scenario()
{
    // go the currently-active ROAR scenario
    var roar_id = $( "input[name='ROAR_ID']" ).val() ;
    var url = gRoarScenarioIndex[ roar_id ].url ;
    if ( gWebChannelHandler )
        window.location = url ; // nb: AppWebPage will intercept this and launch a new browser window
    else
        window.open( url ) ;
}

// --------------------------------------------------------------------

function set_roar_scenario( roar_id )
{
    var total_playings ;
    function safe_score( nplayings ) { return total_playings === 0 ? 0 : nplayings / total_playings ; }
    function get_label( score ) { return total_playings === 0 ? "" : percentString( score ) ; }

    function do_set_roar_scenaro() {
        if ( roar_id ) {
            // save the ROAR ID
            $( "input[name='ROAR_ID']" ).val( roar_id ) ;
            // update the progress bars
            var scenario = gRoarScenarioIndex[ roar_id ] ;
            if ( ! scenario )
                return ;
            var results = scenario.results ;
            if ( convert_roar_nat(results[0][0]) === get_player_nat(2) || convert_roar_nat(results[1][0]) === get_player_nat(1) ) {
                // FUDGE! The order of players returned by ROAR is indeterminate (and could change from call to call),
                // so we try to show the results in the way that best matches what's on-screen.
                results = [ results[1], results[0] ] ;
            }
            total_playings = results[0][1] + results[1][1] ;
            $( "#roar-info .name.player1" ).html( results[0][0] ) ;
            $( "#roar-info .count.player1" ).html( "(" + results[0][1] + ")" ) ;
            var score = 100 * safe_score( results[0][1] ) ;
            $( "#roar-info .progressbar.player1" ).progressbar( { value: 100-score } )
                .find( ".label" ).text( get_label( score ) ) ;
            $( "#roar-info .name.player2" ).html( results[1][0] ) ;
            $( "#roar-info .count.player2" ).html( "(" + results[1][1] + ")" ) ;
            score = 100 * safe_score( results[1][1] ) ;
            $( "#roar-info .progressbar.player2" ).progressbar( { value: score } )
                .find( ".label" ).text( get_label( score ) ) ;
            // show the ROAR scenario details
            $( "#go-to-roar" ).attr( "title", scenario.name+" ["+scenario.scenario_id+"]\n" + scenario.publication ) ;
            // NOTE: We see the fade in if the panel is already visible and we load a scenario that has a ROAR ID,
            // because we reset the scenario the scenario before loading another one, which causes the panel
            // to be hidden. Fixing this is more trouble than it's worth... :-/
            $( "#roar-info" ).fadeIn( 1*1000 ) ;
        } else {
            // there is no associated ROAR scenario - hide the info panel
            $( "input[name='ROAR_ID']" ).val( "" ) ;
            $( "#roar-info" ).hide() ;
        }
    }

    // set the ROAR scenario
    _get_roar_scenario_index( do_set_roar_scenaro ) ;
}

// --------------------------------------------------------------------

function convert_roar_nat( roar_nat )
{
    // clean up the ROAR nationality
    roar_nat = roar_nat.toUpperCase() ;
    var pos = roar_nat.indexOf( "/" ) ;
    if ( pos > 0 )
        roar_nat = roar_nat.substr( 0, pos ) ; // e.g. "British/Partisan" -> "British"
    else {
        var match = roar_nat.match( /\(.*\)$/ ) ;
        if ( match )
            roar_nat = roar_nat.substr( 0, roar_nat.length-match[0].length ).trim() ; // e.g. "Thai (Chinese)" -> "Thai"
    }

    // try to match the ROAR nationality with one of ours
    for ( var nat in gTemplatePack.nationalities ) {
        if ( roar_nat === gTemplatePack.nationalities[nat].display_name.toUpperCase() )
            return nat ;
    }

    return null ;
}
