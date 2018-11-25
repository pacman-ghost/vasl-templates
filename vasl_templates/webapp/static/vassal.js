
// --------------------------------------------------------------------

function on_update_vsav()
{
    // FOR TESTING PORPOISES! We can't control a file upload from Selenium (since
    // the browser will use native controls), so we get the data from a <textarea>).
    if ( getUrlParam( "vsav_persistence" ) ) {
        var $elem = $( "#_vsav-persistence_" ) ;
        var vsav_data = $elem.val() ;
        $elem.val( "" ) ; // nb: let the test suite know we've received the data
        do_update_vsav( vsav_data, "test.vsav" ) ;
        return ;
    }

    // if we are running inside the PyQt wrapper, let it handle everything
    if ( gWebChannelHandler ) {
        gWebChannelHandler.load_vsav( function( data ) {
            if ( ! data )
                return ;
            do_update_vsav( data.data, data.filename ) ;
        } ) ;
        return ;
    }

    // ask the user to upload the VSAV file
    $("#load-vsav").trigger( "click" ) ; // nb: this will call on_load_vsav_file_selected() when a file has been selected
}

function on_load_vsav_file_selected()
{
    // read the selected file
    var fileReader = new FileReader() ;
    var file = $("#load-vsav").prop( "files" )[0] ;
    fileReader.onload = function() {
        vsav_data = fileReader.result ;
        if ( vsav_data.substring(0,5) === "data:" )
            vsav_data = vsav_data.split( "," )[1] ;
        do_update_vsav( vsav_data, file.name ) ;
    } ;
    fileReader.readAsDataURL( file ) ;
}

function do_update_vsav( vsav_data, fname )
{
    // show the progress dialog
    var $dlg = $( "#update-vsav" ).dialog( {
        dialogClass: "update-vsav",
        modal: true,
        width: 300,
        height: 60,
        resizable: false,
        closeOnEscape: false,
    } ) ;

    // generate all the snippets
    var snippets = _generate_snippets() ;

    // send a request to update the VSAV
    var data = { "filename": fname, vsav_data: vsav_data, snippets: snippets } ;
    $.ajax( {
        url: gUpdateVsavUrl,
        type: "POST",
        data: JSON.stringify( data ),
        contentType: "application/json",
    } ).done( function( data ) {
        $dlg.dialog( "close" ) ;
        data = JSON.parse( data ) ;
        // check if there was an error
        if ( data.error ) {
            if ( getUrlParam( "vsav_persistence" ) ) {
                $("#_vsav-persistence_").val(
                    "ERROR: " + data.error + "\n\n=== STDOUT ===\n" + data.stdout + "\n=== STDERR ===\n" + data.stderr
                ) ;
                return ;
            }
            $("#vassal-shim-error").dialog( {
                dialogClass: "vassal-shim-error",
                title: "Scenario update error",
                modal: true,
                width: 600, height: "auto",
                open: function() {
                    $( "#vassal-shim-error .message" ).html( data.error ) ;
                    var log = "" ;
                    if ( data.stdout && data.stderr )
                        log = "=== STDOUT ===" + data.stdout + "\n=== STDERR ===\n" + data.stderr ;
                    else if ( data.stdout )
                        log = data.stdout ;
                    else if ( data.stderr )
                        log = data.stderr ;
                    if ( log )
                        $( "#vassal-shim-error .log" ).val( log ).show() ;
                    else
                        $( "#vassal-shim-error .log" ).hide() ;
                },
                buttons: {
                    Close: function() { $(this).dialog( "close" ) ; },
                },
            } ) ;
            return ;
        }
        // check if anything was changed
        if ( ! data.report.was_modified ) {
            showInfoMsg( "No changes were made to the VASL scenario." ) ;
            if ( getUrlParam( "vsav_persistence" ) )
                $("#_vsav-persistence_").val( btoa( "No changes." ) ) ;
            return ;
        }
        // save the updated VSAV file
        if ( gWebChannelHandler ) {
            gWebChannelHandler.save_updated_vsav( data.filename, data.vsav_data, function( resp ) {
                if ( resp )
                    _show_label_report_msg( data.report ) ;
            } ) ;
            return ;
        }
        _show_label_report_msg( data.report ) ;
        if ( getUrlParam( "vsav_persistence" ) ) {
            // FOR TESTING PORPOISES! We can't control a file download from Selenium (since
            // the browser will use native controls), so we store the result in a <textarea>
            // and the test suite will collect it from there).
            $("#_vsav-persistence_").val( data.vsav_data ) ;
            return ;
        }
        download( atob(data.vsav_data), data.filename, "application/octet-stream" ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        $dlg.dialog( "close" ) ;
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

    // show the message
    if ( report.labels_deleted > 0 )
        showWarningMsg( msg ) ;
    else
        showInfoMsg( msg ) ;
}

// --------------------------------------------------------------------

function _generate_snippets()
{
    // initialize
    var snippets = {} ;

    // figure out which templates we don't want to auto-create labels for
    var no_autocreate = {} ;
    for ( var nat in NATIONALITY_SPECIFIC_BUTTONS ) {
        for ( var i=0 ; i < NATIONALITY_SPECIFIC_BUTTONS[nat].length ; ++i ) {
            var template_id = NATIONALITY_SPECIFIC_BUTTONS[nat][i] ;
            if ( ["pf","atmm"].indexOf( template_id ) !== -1 ) {
                // NOTE: PF and ATMM are always available as an inherent part of a squad's capabilities (subject to date restrictions),
                // so we always auto-create these labels, unlike, say MOL or BAZ, which are only present by SSR or OB counter).
                continue ;
            }
            no_autocreate[template_id] = true ;
        }
    }

    function on_snippet_button( $btn, inactive ) {
        var template_id = $btn.attr( "data-id" ) ;
        if ( template_id.substr(0,7) === "extras/" ) {
            // NOTE: We don't handle extras templates, since they can be parameterized. We would need to store
            // the parameter values in the generated snippet, and extract them here so that we can re-generate
            // the snippet, which is more trouble than it's worth, at this point.
            return ;
        }
        var snippet_id = template_id ;
        var extra_params = {} ;
        var player_no = get_player_no_for_element( $btn ) ;
        if ( ["scenario_note","ob_setup","ob_note"].indexOf( template_id ) !== -1 ) {
            var data = $btn.parent().parent().data( "sortable2-data" ) ;
            if ( player_no )
                snippet_id = template_id + "_" + player_no + "." + data.id ;
            else
                snippet_id = template_id + "." + data.id ;
            extra_params = get_simple_note_snippet_extra_params( $btn ) ;
        }
        var raw_content = _get_raw_content( snippet_id, $btn ) ;
        if ( ["scenario","players","victory_conditions"].indexOf( snippet_id ) === -1 ) {
            // NOTE: We don't pass through a snippet for things that have no content,
            // except for important stuff, such as the scenario name and victory conditions.
            if ( raw_content === null || raw_content.length === 0 ) {
                return ;
            }
        }
        snippets[snippet_id] = {
            content: make_snippet( $btn, extra_params, false ),
            auto_create: ! no_autocreate[template_id] && ! inactive,
            raw_content: raw_content,
        } ;
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

function _get_raw_content( snippet_id, $btn )
{
    // NOTE: We pass the raw content, as entered by the user into the UI, through to the VASSAL shim,
    // so that it can locate legacy labels, that were created before we added snippet ID's to the templates.

    var raw_content = [] ;
    function get_values( names ) {
        for ( var i=0 ; i < names.length ; ++i ) {
            var val = $( ".param[name='" + names[i] + "']" ).val().trim() ;
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
    if ( snippet_id === "mol" )
        return [ "Molotov Cocktail", "MOL check:", "IFT DR original colored dr:" ] ;
    if ( snippet_id === "mol-p" )
        return [ "MOL Projector", "TH#", "X#", "B#" ] ;
    if ( snippet_id === "pf" )
        return [ "Panzerfaust", "PF check:", "non-AFV target", "TH#" ] ;
    if ( snippet_id === "psk" )
        return [ "Panzerschrek", "Range", "TH#", "X#", "TK#" ] ;
    if ( snippet_id === "atmm" )
        return [ "Anti-Tank Magnetic Mines", "ATMM check:", "vs. non-armored vehicle" ] ;
    if ( snippet_id === "piat" )
        return [ "PIAT", "Range", "TH#", "B#", "TK#" ] ;
    if ( snippet_id === "baz" )
        return [ "Bazooka", "Range", "TH#" ] ;

    // handle simple notes
    if ( $btn.prop( "tagName" ).toLowerCase() == "img" ) {
        var data = $btn.parent().parent().data( "sortable2-data" ) ;
        return [ data.caption ] ;
    }

    // handle vehicles/ordnance
    if ( snippet_id.substring(0,11) === "ob_vehicles" || snippet_id.substring(0,11) === "ob_ordnance" ) {
        var id = snippet_id.substring(0,11) + "-sortable" + snippet_id.substring(11) ;
        $( "#"+id + " > li" ).each( function() {
            var vo_entry = $(this).data( "sortable2-data" ).vo_entry ;
            raw_content.push( vo_entry.name ) ;
        } ) ;
        return raw_content ;
    }

    return null ;
}