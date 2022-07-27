gLoadVsavHandler = null ;
gVassalShimErrorDlgState = null ;

// --------------------------------------------------------------------

function on_update_vsav() {
    // check if we should ask the user to confirm the settings
    if ( gUserSettings[ "confirm-update-vsav-settings" ] ) {
        // yup - make it so
        user_settings( function() {
            _load_and_process_vsav( _do_update_vsav ) ;
        }, "Confirm user settings" ) ;
    } else {
        // nope - just do it
        _load_and_process_vsav( _do_update_vsav ) ;
    }
}

function _do_update_vsav( vsav_data, fname )
{
    // generate all the snippets
    var $pleaseWait = showPleaseWaitDialog( "Updating your VASL scenario..." ) ;
    var snippets = _generate_snippets() ;

    // send a request to update the VSAV
    var data = {
        filename: fname,
        vsav_data: vsav_data,
        players: [ get_player_nat(1), get_player_nat(2) ],
        testMode: !! getUrlParam( "store_msgs" ),
        snippets: snippets
    } ;
    $.ajax( {
        url: gUpdateVsavUrl,
        type: "POST",
        data: JSON.stringify( data ),
        contentType: "application/json",
    } ).done( function( resp ) {
        $pleaseWait.dialog( "close" ) ;
        data = _check_vassal_shim_response( resp, "Can't update the VASL scenario." ) ;
        if ( ! data )
            return ;
        // check if anything was changed
        if ( ! data.report.was_modified ) {
            showInfoMsg( "No changes were made to the VASL scenario." ) ;
            if ( getUrlParam( "vsav_persistence" ) )
                $("#_vsav-persistence_").val( btoa( "No changes." ) ) ;
            return ;
        }
        // save the updated VSAV file
        _show_label_report_msg( data.report ) ;
        if ( gWebChannelHandler ) {
            setTimeout( function() { // nb: give the label report time to appear :-/
                gWebChannelHandler.save_updated_vsav( data.filename, data.vsav_data ) ;
            }, 1*1000 ) ;
            return ;
        }
        if ( getUrlParam( "vsav_persistence" ) ) {
            // FOR TESTING PORPOISES! We can't control a file download from Selenium (since
            // the browser will use native controls), so we store the result in a <textarea>
            // and the test suite will collect it from there).
            $("#_vsav-persistence_").val( data.vsav_data ) ;
            return ;
        }
        download( atob(data.vsav_data), data.filename, "application/octet-stream" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        $pleaseWait.dialog( "close" ) ;
        showErrorMsg( "Can't update the VASL scenario:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
    } ) ;
}

function _show_label_report_msg( report )
{
    // generate a message summarizing what the VASSAL shim did
    var buf = [ "The VASL scenario was updated:", "<ul>" ] ;
    var actions = [ "created", "updated", "deleted" ] ; // nb: we ignore "unchanged"
    for ( var i=0 ; i < actions.length ; ++i ) {
        var action = actions[i] ;
        var n = parseInt( report[ "labels_"+action ] ) ;
        if ( n == 1 )
            buf.push( "<li>1 label was " + action + "." ) ;
        else if ( n > 1 )
            buf.push( "<li>" + n + " labels were " + action + "." ) ;
    }
    buf.push( "</ul>" ) ;
    var msg = buf.join( "" ) ;

    // show the summary and any error messages
    for ( i=0 ; i < report.errors.length ; ++i )
        showErrorMsg( report.errors[i] ) ;
    if ( report.labels_deleted > 0 || report.errors.length > 0 )
        showWarningMsg( msg ) ;
    else
        showInfoMsg( msg ) ;
}

// --------------------------------------------------------------------

function _generate_snippets()
{
    // initialize
    var snippets = {} ;
    var vo_index = {} ;

    // figure out which templates we don't want to auto-create labels for
    var no_autocreate = {} ;
    for ( var template_id in NATIONALITY_SPECIFIC_BUTTONS ) {
        if ( ["pf","atmm","thh"].indexOf( template_id ) !== -1 || template_id.substring(0,3) === "pf-" ) {
            // NOTE: PF, ATMM, THH are always available as an inherent part of a squad's capabilities
            // (subject to date restrictions), so we always auto-create these labels, unlike, say MOL or BAZ,
            // which are only present by SSR or OB counter).
            continue ;
        }
        no_autocreate[template_id] = true ;
    }

    function on_snippet_button( $btn, inactive ) {
        var template_id = $btn.attr( "data-id" ) ;
        if ( ! is_template_available( template_id ) )
            return ;
        if ( template_id.substr(0,7) === "extras/" ) {
            // NOTE: We don't handle extras templates, since they can be parameterized. We would need to store
            // the parameter values in the generated snippet, and extract them here so that we can re-generate
            // the snippet, which is more trouble than it's worth, at this point.
            return ;
        }
        var params = unload_snippet_params( true, template_id ) ;
        var snippet_id = template_id ;
        var extra_params = {} ;
        var player_no ;
        if ( snippet_id.substring( 0, 9 ) === "nat_caps_" )
            player_no = snippet_id.substring( 9 ) ;
        else
            player_no = get_player_no_for_element( $btn ) ;
        var data ;
        if ( ["scenario_note","ob_setup","ob_note"].indexOf( template_id ) !== -1 ) {
            data = $btn.parent().parent().data( "sortable2-data" ) ;
            if ( player_no ) {
                snippet_id = template_id + "_" + player_no + "." + data.id ;
            } else
                snippet_id = template_id + "." + data.id ;
            extra_params = get_simple_note_snippet_extra_params( $btn ) ;
        }
        if ( ["ob_vehicle_note","ob_ordnance_note"].indexOf( template_id ) !== -1 ) {
            data = $btn.parent().parent().data( "sortable2-data" ) ;
            if ( data.vo_entry.id in vo_index ) {
                // NOTE: There are two ways we can end up creating duplicate snippets for vehicle/ordnance notes:
                //   (1) the OB contains multiple variants of the same vehicle/ordnance
                //   (2) the OB contains different vehicles/ordnance that happen to have the same note
                //       e.g. the German Opel Blitz and Buessing-NAG both have Vehicle Note 96.
                // Deuping the first case is a no-brainer, but the second is tricker. If we only create a snippet
                // for the Opel Blitz, it's not immediately clear to someone looking at the VASL scenario why
                // there is no snippet for the Buessing-NAG. However, this situation should be rare enough
                // for us to not worry about it... :-/
                return ;
            }
            vo_index[ data.vo_entry.id ] = true ;
            snippet_id = template_id + "_" + player_no + "." + data.id ;
        }
        if ( template_id === "turn_track" ) {
            if ( $( "select[name='TURN_TRACK_NTURNS']" ).val() === "" )
                return ;
        }
        var raw_content = _get_raw_content( snippet_id, $btn, params ) ;
        if ( ["scenario","players","victory_conditions"].indexOf( snippet_id ) === -1 ) {
            // NOTE: We don't pass through a snippet for things that have no content,
            // except for important stuff, such as the scenario name and victory conditions.
            if ( raw_content === false || raw_content === null || raw_content.length === 0 ) {
                return ;
            }
        }
        if ( player_no )
            snippet_id = get_player_nat(player_no) + "/" + snippet_id ;
        snippets[snippet_id] = {
            content: make_snippet( $btn, params, extra_params, false ).content,
            auto_create: ! no_autocreate[template_id] && ! inactive,
        } ;
        if ( raw_content !== true )
            snippets[snippet_id].raw_content = raw_content ;
        if ( player_no )
            snippets[snippet_id].label_area = "player" + player_no ;
    }
    $("button.generate").each( function() {
        if ( $(this).parent().css( "display" ) === "none" )
            return ;
        on_snippet_button( $(this), $(this).hasClass("inactive") ) ;
    } ) ;
    $("img.snippet").each( function() {
        on_snippet_button( $(this) ) ;
    } ) ;

    return snippets ;
}

function _get_raw_content( snippet_id, $btn, params )
{
    // NOTE: We pass the raw content, as entered by the user into the UI, through to the VASSAL shim,
    // so that it can locate legacy labels, that were created before we added snippet ID's to the templates.

    var raw_content = [] ;
    function get_values( names ) {
        for ( var i=0 ; i < names.length ; ++i ) {
            var $elem = $( ".param[name='" + names[i] + "']" ) ;
            var val = $elem.hasClass("trumbowyg-editor") ? unloadTrumbowyg($elem,false) : $elem.val() ;
            val = val.trim() ;
            if ( val )
                raw_content.push( val ) ;
        }
        return raw_content ;
    }

    // handle special cases
    if ( snippet_id === "scenario" )
        return get_values([ "SCENARIO_NAME", "SCENARIO_ID", "SCENARIO_LOCATION" ]) ;
    if ( snippet_id === "victory_conditions" )
        return get_values([ "VICTORY_CONDITIONS" ]) ;
    if ( snippet_id === "turn_track" )
        return true ;
    if ( snippet_id === "compass" && get_values(["COMPASS"]).length > 0 )
        return true ;
    if ( snippet_id === "players" ) {
        return [
            "ELR:", "SAN:",
            get_nationality_display_name( get_player_nat( 1 ) ) + ":",
            get_nationality_display_name( get_player_nat( 2 ) ) + ":",
        ] ;
    }
    if ( snippet_id === "ssr" ) {
        $( "#ssr-sortable > li" ).each( function() {
            var data = $(this).data( "sortable2-data" ) ;
            raw_content.push( data.caption ) ;
        } ) ;
        return raw_content ;
    }

    // handle simple cases
    // NOTE: These checks also have the side-effect of not deleting these labels if they are already in
    //  a scenario that is being updated.
    if ( snippet_id === "mol" )
        return [ "Molotov Cocktail", "MOL check:", "IFT DR original colored dr:" ] ;
    if ( snippet_id === "mol-p" )
        return [ "MOL Projector", "TH#", "X#", "B#" ] ;
    if ( snippet_id === "pf" || snippet_id.substring(0,3) === "pf-" )
        return [ "Panzerfaust", "PF check:", "non-AFV target", "TH#" ] ;
    if ( snippet_id === "psk" )
        return [ "Panzerschrek", "Range", "TH#", "X#", "TK#" ] ;
    if ( snippet_id === "atmm" )
        return [ "Anti-Tank Magnetic Mines", "ATMM check:", "vs. non-armored vehicle" ] ;
    if ( snippet_id === "piat" )
        return [ "PIAT", "Range", "TH#", "B#", "TK#" ] ;
    if ( snippet_id === "baz" || snippet_id === "baz45" || snippet_id === "baz50" || snippet_id.substr(0,8) === "baz-cpva" )
        return [ "Bazooka", "Range", "TH#" ] ;
    if ( snippet_id === "thh" )
        return [ "Tank-Hunter Heroes", "Banzai Charge" ] ;
    if ( snippet_id.substring( 0, 9 ) === "nat_caps_" )
        return [ "Capabilities" ] ;

    // handle vehicle/ordnance notes
    // NOTE: These were implemented after we added snippet ID's, so there's no need to support legacy labels.
    // NOTE: We get called in response to an img.snippet button, which implies there is a Chapter H snippet available,
    // so we don't have to check anything and just always return true.
    if ( snippet_id.substring(0,16) === "ob_vehicle_note_" )
        return true ;
    if ( snippet_id.substring(0,17) === "ob_ordnance_note_" )
        return true ;

    // handle simple notes
    if ( $btn.prop( "tagName" ).toLowerCase() == "img" ) {
        var data = $btn.parent().parent().data( "sortable2-data" ) ;
        return [ data.caption ] ;
    }

    function get_vo_entries( vo_type, player_no, names_only ) {
        var vo_entries = [] ;
        var id = "ob_" + vo_type + "-sortable_" + player_no ;
        $( "#"+id + " > li" ).each( function() {
            var vo_entry = $(this).data( "sortable2-data" ).vo_entry ;
            vo_entries.push( names_only ? vo_entry.name : vo_entry ) ;
        } ) ;
        return vo_entries ;
    }

    // handle multi-applicable vehicle/ordnance notes
    // NOTE: These were implemented after we added snippet ID's, so there's no need to support legacy labels.
    function check_ma_notes( vo_type, player_no ) {
        var nat = params[ "PLAYER_" + player_no ] ;
        // NOTE: The following test has to handle a number of subtleties:
        // - if no Chapter H data has been configured, we don't create the label
        // However, if Chapter data has been configured, we always create the label, even if:
        // - there are no notes whatsoever (e.g. Romania).
        // - there are notes, but no multi-applicable notes (e.g. Belgium)
        // It's tempting to think that it might be better to skip creating the label if there are no available
        // multi-applicable notes, but this will be confusing for the user, since the label will not appear
        // in the VASL scenario, and it won't be immediately clear why.
        if ( !( vo_type in gVehicleOrdnanceNotes && Object.keys(gVehicleOrdnanceNotes[vo_type]).length > 0 ) )
            return false ;
        vo_entries = get_vo_entries( vo_type, player_no, false ) ;
        var result = get_ma_notes_keys( nat, vo_entries, vo_type ) ;
        return (result[0] && result[0].length > 0) || (result[1] && result[1].length > 0) ;
    }
    var player_no, nat, vo_entries, keys ;
    if ( snippet_id.substring(0,21) === "ob_vehicles_ma_notes_" || snippet_id.substring(0,21) === "ob_ordnance_ma_notes_" )
        return check_ma_notes( snippet_id.substring(3,11), snippet_id.substring(21) ) ;

    // handle vehicles/ordnance
    if ( snippet_id.substring(0,12) === "ob_vehicles_" || snippet_id.substring(0,12) === "ob_ordnance_" )
        return get_vo_entries( snippet_id.substring(3,11), snippet_id.substring(12), true ) ;

    return null ;
}

// --------------------------------------------------------------------

function on_analyze_vsav()
{
    // check if there are any vehicles/ordnance already defined
    var voDefined1 = $( "#ob_vehicles-sortable_1 .vo-entry" ).length > 0 || $( "#ob_ordnance-sortable_1 .vo-entry" ).length > 0 ;
    var voDefined2 = $( "#ob_vehicles-sortable_2 .vo-entry" ).length > 0 || $( "#ob_ordnance-sortable_2 .vo-entry" ).length > 0 ;
    if ( voDefined1 || voDefined2 ) {
        // yup - confirm the operation
        ask( "Analyze VASL scenario",
            "<p> There are some vehicles/ordnance already configured. <p> They will be <i>replaced</i> with those found in the analyzed VASL scenario.", {
            width: 520,
            ok: function() { _load_and_process_vsav( _do_analyze_vsav ) ; },
        } ) ;
        return ;
    }

    // ask the user to select a VASL scenario, then analyze it
    _load_and_process_vsav( _do_analyze_vsav ) ;
}

function _do_analyze_vsav( vsav_data, fname )
{
    // show the progress dialog
    var $pleaseWait = showPleaseWaitDialog( "Analyzing the VASL scenario..." ) ;

    // send a request to analyze the VSAV
    var data = { filename: fname, vsav_data: vsav_data } ;
    $.ajax( {
        url: gAnalyzeVsavUrl,
        type: "POST",
        data: JSON.stringify( data ),
        contentType: "application/json",
    } ).done( function( resp ) {
        $pleaseWait.dialog( "close" ) ;
        data = _check_vassal_shim_response( resp, "Can't analyze the VASL scenario." ) ;
        if ( ! data )
            return ;
        _create_vo_entries_from_analysis( data ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        $pleaseWait.dialog( "close" ) ;
        showErrorMsg( "Can't analyze the VASL scenario:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
    } ) ;
}

function _create_vo_entries_from_analysis( report )
{
    // initialize
    var theater = $( "select.param[name='SCENARIO_THEATER']" ).val() ;

    function create_vo_entries( player_no, vo_type ) {

        var gpids, i ;

        // clear the existing vehicles/ordnance
        $( "#ob_" + vo_type + "-sortable_" + player_no ).sortable2( "delete-all" ) ;
        // build an index of GPID's that belong to the specified player and V/O type
        var entries_index = {} ;
        var entries = gVehicleOrdnanceListings[ vo_type ][ get_player_nat(player_no) ] ;
        if ( entries ) {
            for ( i=0 ; i < entries.length ; ++i ) {
                gpids = $.isArray( entries[i].gpid ) ? entries[i].gpid : [entries[i].gpid] ;
                for ( var j=0 ; j < gpids.length ; ++j ) {
                    if ( entries_index[ gpids[j] ] === undefined )
                        entries_index[ gpids[j] ] = [ entries[i] ] ;
                    else
                        entries_index[ gpids[j] ].push( entries[i] ) ;
                }
            }
        }

        // IMPORTANT: Adding support for the new K:FW counters in VASL 6.5.0 caused problems for
        // the "analyze scenario" feature, since quite a few of the new counters use images
        // from the old counter set e.g. the American "M2 60mm Mortar" has a K:FW variant (kfw-un-common/o:002)
        // that has GPID 849 (as well as 11391, 11359, 11440 for the ROK, BCFK, OUNC variants),
        // but GPID 849 is also used by the old American "M2 60mm Mortar" counter (am/o:000).
        // So, if we find GPID 849 in a .vsav file, we don't know if we should create the K:FW entry
        // or the normal American entry. To work around this, we added a new scenario theater for Korea,
        // and use that to decide.
        function chooseEntry( gpid ) {
            var entries = entries_index[ gpid ] ;
            if ( !entries || entries.length === 0 )
                return null ;
            if ( entries.length === 1 )
                return entries[0] ;
            var entries2 = [] ;
            for ( var i=0 ; i < entries.length ; ++i ) {
                var entry_id = entries[i].id ;
                var isKFW = entry_id.substr(0,4) === "kfw-" || entry_id.substr(0,3) === "ffs" ;
                if ( (theater == "Korea" && isKFW) || (theater != "Korea" && !isKFW) )
                    entries2.push( entries[i] ) ;
            }
            if ( entries2.length === 1 )
                return entries2[0] ;
            console.log( "WARNING: Found multiple entries for GPID " + gpid + " during analysis:", entries ) ;
            return entries[0] ;
        }

        // add a vehicle/ordnance for each relevant GPID
        var nCreated = 0 ;
        gpids = Object.keys( report.pieces ) ;
        for ( i=0 ; i < gpids.length ; ++i ) {
            var gpid = gpids[ i ] ;
            var entry = chooseEntry( gpid ) ;
            if ( ! entry )
                continue ;
            var image_id = $.isArray( entry.gpid ) ? [gpid,0] : null ;
            do_add_vo( vo_type, player_no, entry, image_id, false, null, null, null ) ;
            ++ nCreated ;
        }
        return nCreated ;
    }

    // import any vehicles/ordnance found
    var imported = [
        [ create_vo_entries( 1, "vehicles" ), create_vo_entries( 1, "ordnance" ) ],
        [ create_vo_entries( 2, "vehicles" ), create_vo_entries( 2, "ordnance" ) ]
    ] ;

    // report the VASSAL and VASL versions
    // NOTE: We don't do this during the test suite since it can only store 1 message at a time :-/
    // It would be nice to test this functionality, but the implemenation is simple, so we can live without it.
    if ( ! getUrlParam( "store_msgs" ) ) {
        showInfoMsg( "The scenario was created with: <ul style='margin-top:0;'>" +
            "<li> VASSAL " + report.vassal_version +
            " <li> VASL " + report.vasl_version +
            " </ul>"
        ) ;
    }

    // report what happened
    var report_strings = [] ;
    function make_report_string( nat, nVehicles, nOrdnance ) {
        var buf = [] ;
        if ( nVehicles > 0 )
            buf.push( nVehicles + "{{NAT}} " + pluralString(nVehicles,"vehicle","vehicles") ) ;
        if ( nOrdnance > 0 )
            buf.push( nOrdnance + "{{NAT}} ordnance" ) ;
        if ( buf.length == 1 ) {
            report_strings.push(
                "Imported " + buf[0].replace("{{NAT}}"," "+nat) + "."
            ) ;
        } else if ( buf.length == 2 ) {
            report_strings.push(
                "Imported " + buf[0].replace( "{{NAT}}", " "+nat ) + " and " + buf[1].replace( "{{NAT}}", "" ) + "."
            ) ;
        }
    }
    make_report_string( get_nationality_display_name(get_player_nat(1)), imported[0][0], imported[0][1] ) ;
    make_report_string( get_nationality_display_name(get_player_nat(2)), imported[1][0], imported[1][1] ) ;
    if ( report_strings.length === 0 )
        showWarningMsg( "<p>No vehicles/ordnance were imported. <p style='margin-top:0.25em;'>Have you set the player nationalities?" ) ;
    else
        showInfoMsg( report_strings.join( "<p style='margin-top:0.25em;'>" ) ) ;
}

// --------------------------------------------------------------------

function _load_and_process_vsav( handler )
{
    // FOR TESTING PORPOISES! We can't control a file upload from Selenium (since
    // the browser will use native controls), so we get the data from a <textarea>).
    if ( getUrlParam( "vsav_persistence" ) ) {
        var $elem = $( "#_vsav-persistence_" ) ;
        var vsav_data = $elem.val() ;
        $elem.val( "" ) ; // nb: let the test suite know we've received the data
        handler( vsav_data, "test.vsav" ) ;
        return ;
    }

    // if we are running inside the PyQt wrapper, let it handle everything
    if ( gWebChannelHandler ) {
        gWebChannelHandler.load_vsav( function( data ) {
            if ( ! data )
                return ;
            handler( data.data, data.filename ) ;
        } ) ;
        return ;
    }

    // ask the user to upload the VSAV file
    gLoadVsavHandler = handler ;
    $("#load-vsav").trigger( "click" ) ; // nb: this will call on_load_vsav_file_selected() when a file has been selected
}

function on_load_vsav_file_selected()
{
    // read the selected file
    var fileReader = new FileReader() ;
    var file = $("#load-vsav").prop( "files" )[0] ;
    fileReader.onload = function() {
        vsav_data = removeBase64Prefix( fileReader.result ) ;
        gLoadVsavHandler( vsav_data, file.name ) ;
        gLoadVsavHandler = null ;
    } ;
    fileReader.readAsDataURL( file ) ;
}

// --------------------------------------------------------------------

function _check_vassal_shim_response( resp, caption )
{
    // check if there was an error
    if ( ! resp.error )
        return resp ;

    // yup - report the error
    if ( getUrlParam( "vsav_persistence" ) ) {
        $( "#_vsav-persistence_" ).val(
            "ERROR: " + resp.error + "\n\n=== STDOUT ===\n" + resp.stdout + "\n=== STDERR ===\n" + resp.stderr
        ) ;
        return null ;
    }
    show_vassal_shim_error_dlg( resp, caption ) ;

    return null ;
}

function show_vassal_shim_error_dlg( resp, caption )
{
    // show the VASSAL shim error dialog
    if ( caption[ caption.length-1 ] == "." )
        caption = caption.substring( 0, caption.length-1 ) ;
    $( "#vassal-shim-error" ).dialog( {
        dialogClass: "vassal-shim-error",
        title: caption,
        modal: true,
        position: gVassalShimErrorDlgState ? gVassalShimErrorDlgState.position : { my: "center", at: "center", of: window },
        width: gVassalShimErrorDlgState ? gVassalShimErrorDlgState.width : $(window).width() * 0.8,
        height: gVassalShimErrorDlgState ? gVassalShimErrorDlgState.height : $(window).height() * 0.8,
        minWidth: 600,
        minHeight: 400,
        open: function() {
            $( "#vassal-shim-error .message" ).html( resp.error ) ;
            var log = "" ;
            if ( resp.stdout && resp.stderr )
                log = "=== STDOUT ===\n" + resp.stdout + "\n=== STDERR ===\n" + resp.stderr ;
            else if ( resp.stdout )
                log = resp.stdout ;
            else if ( resp.stderr )
                log = resp.stderr ;
            if ( log )
                $( "#vassal-shim-error .log" ).text( log ).show() ;
            else
                $( "#vassal-shim-error .log" ).hide() ;
        },
        beforeClose: function() {
            gVassalShimErrorDlgState = getDialogState( $(this) ) ;
        },
        buttons: {
            Close: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}
