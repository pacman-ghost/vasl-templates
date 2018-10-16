
function edit_ob_vehicle( $entry, player_no ) { _do_edit_ob_vo( $entry, player_no, "vehicle" ) ; }
function edit_ob_ordnance( $entry, player_no ) { _do_edit_ob_vo( $entry, player_no, "ordnance" ) ; }

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function _do_edit_ob_vo( $entry, player_no, vo_type )
{
    // get the vehicle/ordnance's capabilities
    var params = unload_snippet_params( true ) ;
    var vo_entry = $entry.data( "sortable2-data" ).vo_entry ;
    var default_capabilities = make_capabilities(
        vo_entry,
        params[ "PLAYER_"+player_no ],
        params.SCENARIO_THEATER,
        params.SCENARIO_YEAR, params.SCENARIO_MONTH, false,
        false
    ) ;
    var capabilities = $entry.data( "sortable2-data" ).custom_capabilities ;
    if ( ! capabilities )
        capabilities = default_capabilities.slice() ;

    // load the dialog
    var vo_image_id = $entry.data( "sortable2-data" ).vo_image_id ;
    var url = get_vo_image_url( vo_entry, vo_image_id, true ) ;
    var buf = [ "<div class='header'>",
        "<img src='" + url + "' class='vasl-image'>",
        "<div class='content'>",
        "<span class='vo-name'>" + vo_entry.name + "</span>",
        "</div>",
    "</div" ] ;
    $header = $( buf.join("") ) ;
    var $img = $header.find( "img" ).data( "vo-image-id", vo_image_id ) ;
    if ( is_small_vasl_piece( vo_entry ) )
        $img.addClass( "small-piece" ) ;
    var vo_images = get_vo_images( vo_entry ) ;
    if ( vo_images.length > 1 ) {
        $header.find( "img" ).data( "vo-images", vo_images ) ;
        var $btn = $( "<input type='image' class='select-vo-image' src='" + gImagesBaseUrl + "/select-vo-image.png'>" ) ;
        $header.children( ".content" ).append( $btn ) ;
        $btn.click( function() {
            $(this).blur() ;
            on_select_vo_image( $(this) ) ;
        } ) ;
    }
    $( "#edit-vo .header" ).replaceWith( $header ) ;

    // initialize
    var $capabilities = $( "#vo_capabilities-sortable" ) ;
    function add_capability( val ) {
        var $elem = $( "<div>" +
            "<img class='dragger' src='" + gImagesBaseUrl + "/dragger.png'>" +
            "<input type='text'>" +
            "</div>"
        ) ;
        $elem.children( "input[type='text']" ).val( val ).keydown( function(evt) {
            auto_dismiss_dialog( $dlg, evt, "OK" ) ;
        } ) ;
        return $capabilities.sortable2( "add", {
            content: $elem,
            data: { fixed_height: "1.4em" },
        } ) ;
    }

    // show the dialog
    var $dlg = $( "#edit-vo" ).dialog( {
        dialogClass: "edit-vo",
        title: "Edit "+vo_type,
        minWidth: 350,
        minHeight: 340,
        modal: true,
        create: function() {
            // initialize the dialog
            init_dialog( $(this), "OK", false ) ;
            $capabilities.sortable2( "init", {
                add: function() {
                    $elem = add_capability( "" ) ;
                    $elem.find( "input[type='text']" ).focus() ;
                    $elem[0].scrollIntoView() ;
                },
                no_confirm_delete: true,
            } ) ;
        },
        open: function() {
            // initialize
            on_dialog_open( $(this) ) ;
            // set the titlebar color
            var colors = get_player_colors( player_no ) ;
            $( ".ui-dialog.edit-vo .ui-dialog-titlebar" ).css( {
                background: colors[0],
                border: "1px solid "+colors[2],
            } ) ;
            // load the dialog
            $capabilities.sortable2( "delete-all" ) ;
            for ( var i=0 ; i < capabilities.length ; ++i )
                add_capability( capabilities[i] ) ;
        },
        buttons: {
            OK: function() {
                // save the V/O image ID
                var $img = $dlg.find( "img[class='vasl-image']" ) ;
                vo_image_id = $img.data( "vo-image-id" ) ;
                if ( vo_image_id )
                    $entry.data( "sortable2-data" ).vo_image_id = vo_image_id ;
                // unload the capabilities
                var capabilities = [] ;
                $capabilities.find( "input[type='text']" ).each( function() {
                    var val = $(this).val().trim() ;
                    if ( val )
                        capabilities.push( val ) ;
                } ) ;
                if ( capabilities.length > 0 ) {
                    if ( capabilities.join() !== default_capabilities.join() )
                        $entry.data( "sortable2-data" ).custom_capabilities = capabilities ;
                    else {
                        // the capabilities are the same as the default - no need to retain these custom settings
                        delete $entry.data( "sortable2-data" ).custom_capabilities ;
                    }
                } else {
                    // NOTE: We treat "no capabilities" as meaning "revert back to the default capabilities".
                    // This means that the user can never have a V/O that actually has no capabilities, but then
                    // why would they want to include that V/O in a label in the scenario? :shrug: If they
                    // really want it there, they can always include a dummy capability of "none" or "-"...
                    delete $entry.data( "sortable2-data" ).custom_capabilities ;
                }
                // update the original V/O entry to reflect the changes
                $entry.find( "img.vasl-image" ).attr( "src", $img.attr("src") ) ;
                $(this).dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}
