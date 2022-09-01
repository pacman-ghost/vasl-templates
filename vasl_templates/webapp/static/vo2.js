var gEditVoDialogSplitter = null ;
var gPrevEditVoDialogEntry = null ;
var gEditVoDlgState = null ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function edit_ob_vehicle( $entry, player_no ) { _do_edit_ob_vo( $entry, player_no, "vehicle" ) ; }
function edit_ob_ordnance( $entry, player_no ) { _do_edit_ob_vo( $entry, player_no, "ordnance" ) ; }

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function _do_edit_ob_vo( $entry, player_no, vo_type )
{
    function get_default_capabilities( vo_entry, params, show_warnings ) {
        return make_capabilities(
            false,
            vo_entry, vo_type,
            params[ "PLAYER_"+player_no ],
            false,
            params.SCENARIO_THEATER, params.SCENARIO_YEAR, params.SCENARIO_MONTH,
            show_warnings
        ) ;
    }
    function get_default_comments( vo_entry ) {
        return vo_entry.comments ? vo_entry.comments : [] ;
    }

    function load_entries( $sortable, entries ) {
        $sortable.sortable2( "delete-all" ) ;
        for ( var i=0 ; i < entries.length ; ++i )
            add_entry( $sortable, entries[i], false ) ;
        $sortable.scrollTop( 0 ) ;
    }
    function unload_entries( $sortable ) {
        var entries = [] ;
        $sortable.find( "div.html-textbox" ).each( function() {
            var val = $(this).html().trim() ;
            while ( val.substr( val.length-4 ) === "<br>" )
                val = val.substr( 0, val.length-4 ) ;
            if ( val.length > 0 )
                entries.push( val ) ;
        } ) ;
        return entries ;
    }

    function make_vo_name( name, elite ) {
        if ( elite )
            name += " \u24ba" ;
        else {
            if ( name.substr( name.length-2 ) === " \u24ba" )
                name = name.substr( 0, name.length-2 ) ;
        }
        return name ;
    }

    // get the vehicle/ordnance's capabilities/comments
    var params = unload_snippet_params( true, null ) ;
    var vo_entry = $entry.data( "sortable2-data" ).vo_entry ;
    var capabilities = $entry.data( "sortable2-data" ).custom_capabilities ;
    if ( ! capabilities )
        capabilities = get_default_capabilities( vo_entry, params, true ).slice() ;
    var elite = $entry.data( "sortable2-data" ).elite ;
    var comments = $entry.data( "sortable2-data" ).custom_comments ;
    if ( ! comments )
        comments = get_default_comments( vo_entry ) ;

    // load the dialog
    var vo_image_id = $entry.data( "sortable2-data" ).vo_image_id ;
    var url = get_vo_image_url( vo_entry, vo_image_id, true, false ) ;
    var buf = [ "<div class='header'>",
        "<img src='" + url + "' class='vasl-image'>",
        "<div class='content'>",
        "<span class='vo-name'>" + make_vo_name( vo_entry.name, elite ) + "</span>",
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
    var $elite = $( "#edit-vo .capabilities input.elite" ) ;
    var $comments = $( "#vo_comments-sortable" ) ;
    function add_entry( $sortable, val, focus ) {
        var $elem = $( "<div>" +
            "<img class='dragger' src='" + gImagesBaseUrl + "/dragger.png'>" +
            "<div class='html-textbox'></div>" +
            "</div>"
        ) ;
        var $htmlTextbox = $elem.children( "div.html-textbox" ) ;
        $htmlTextbox.html( val ).keydown( function( evt ) {
            auto_dismiss_dialog( $dlg, evt, "OK" ) ;
        } ) ;
        var $entry = $sortable.sortable2( "add", {
            content: $elem,
            data: { fixed_height: "1.5em" },
        } ) ;
        var objName ;
        if ( $sortable === $capabilities )
            objName = vo_type + " capability" ;
        else if ( $sortable === $comments )
            objName = vo_type + " comment" ;
        initHtmlTextbox( $htmlTextbox, objName, false ) ;
        // FUDGE! This works around a weird presentation error if there are superscripts and daggers
        // in the content, where ths text won't be vertically aligned properly. Moving the cursor around
        // seems to fix the layout, so we move to the start of the content, which will be a "normal" character.
        $htmlTextbox.focus().trigger(
            { type: "keypress", keycode: $.ui.keyCode.HOME }
        ) ;
        // check if we should set focus to the entry
        if ( focus ) {
            $entry.find( "div.html-textbox" ).focus() ;
            $entry[0].scrollIntoView() ;
        }
    }

    // NOTE: on_reset_capabilities/comments() get bound when the sortable2 is *created*, so they need some way
    // to get the *current* vo_entry and params, otherwise they will use the values active when they were bound.
    var $reset_capabilities = $( "#vo_capabilities-reset" ) ;
    $reset_capabilities.data( { vo_entry: vo_entry, params: params } ) ;
    function on_reset_capabilities() {
        var curr_vo_entry = $reset_capabilities.data( "vo_entry" ) ;
        var curr_params = $reset_capabilities.data( "params" ) ;
        $dlg.find( ".header .vo-name" ).html( make_vo_name( curr_vo_entry.name, false ) ) ;
        load_entries( $capabilities,
            get_default_capabilities( curr_vo_entry, curr_params, false )
        ) ;
        $elite.prop( "checked", false ) ;
    }
    var $reset_comments = $( "#vo_comments-reset" ) ;
    $reset_comments.data( { vo_entry: vo_entry, params: params } ) ;
    function on_reset_comments() {
        var curr_vo_entry = $reset_capabilities.data( "vo_entry" ) ;
        load_entries( $comments, get_default_comments(curr_vo_entry) ) ;
    }

    function update_for_elite( delta ) {
        // update the capabilities
        var capabilities = unload_entries( $capabilities ) ;
        adjust_capabilities_for_elite( capabilities, delta ) ;
        load_entries( $capabilities, capabilities ) ;
        // update the vehicle/ordnance name
        var $name = $( "#edit-vo .header .vo-name" ) ;
        $name.html( make_vo_name( $name.html(), delta > 0 ) ) ;
    }

    // show the dialog
    var $dlg = $( "#edit-vo" ).dialog( {
        dialogClass: "edit-vo",
        title: "Edit "+vo_type,
        position: gEditVoDlgState ? gEditVoDlgState.position : { my: "left top", at: "left+30 top+30", of: window },
        width: gEditVoDlgState ? gEditVoDlgState.width : $(window).width() * 0.4,
        height: gEditVoDlgState ? gEditVoDlgState.height : $(window).height() - 60,
        minWidth: 480,
        minHeight: 440,
        modal: true,
        create: function() {
            // initialize the dialog
            init_dialog( $(this), "OK", false ) ;
            // NOTE: We disable Control-Click deleting entries, because we want that to open the "edit HTML" dialog.
            $capabilities.sortable2( "init", {
                add: function() { add_entry( $capabilities, "", true ) ; },
                reset: on_reset_capabilities,
                no_confirm_delete: true,
            } ) ;
            $comments.sortable2( "init", {
                add: function() { add_entry( $comments, "", true ) ; },
                reset: on_reset_comments,
                no_confirm_delete: true,
            } ) ;
            // FUDGE! Making the entire entry draggable causes problems when clicking inside the HTML textbox
            // (presumably because the click event is being eaten somewhere). We can work around this by adding
            // a click handler that sets focus to the textbox, but the cursor is always placed at the start
            // of the content, not where the mouse was clicked. We work-around the problem by only allow entries
            // to be be dragged via the dragger icon.
            $capabilities.sortable( "option", "handle", ".dragger" ) ;
            $comments.sortable( "option", "handle", ".dragger" ) ;
            // handle changes to Elite status
            $elite.click( function() {
                update_for_elite( $(this).prop( "checked" ) ? +1 : -1 ) ;
            } ) ;
        },
        open: function() {
            // initialize
            on_dialog_open( $(this) ) ;
            add_flag_to_dialog_titlebar( $(this), player_no ) ;
            // set the titlebar color
            var colors = get_player_colors( player_no ) ;
            $( ".ui-dialog.edit-vo .ui-dialog-titlebar" ).css( {
                background: colors[0],
                border: "1px solid "+colors[2],
            } ) ;
            // load the dialog
            load_entries( $capabilities, capabilities ) ;
            $elite.prop( "checked", elite ? true : false ) ;
            load_entries( $comments, comments ) ;
            // initialize the spliiter
            // FUDGE! We should be able to do this in the dialog's "create" handler, but it doesn't
            // really work (setting the minSize doesn't work). Thing is, doing it here (once) also
            // doesn't work, but in a way that's more acceptable :-/
            if ( gEditVoDialogSplitter === null ) {
                gEditVoDialogSplitter = Split( [ "#edit-vo .capabilities", "#edit-vo .comments" ], {
                    "direction": "vertical",
                    gutterSize: 1
                } ) ;
                addSplitterGripper( $("#edit-vo .gutter"), false, 1, {
                    margin: "13px 8em -13px 8em"
                } ) ;
                // FUDGE! Work-around a weird layout problem with the splitter, where things don't work
                // until the dialog is resized, and then it's OK thereafter :-/ The height will be corrected
                // when the UI updates and the layout is re-calculated.
                $( ".split-container" ).css( { height: "1px" } ) ;
            }
            if ( $entry !== gPrevEditVoDialogEntry ) {
                var nEntriesAvail = ( $capabilities.height() + $comments.height() ) / 27 ;
                var nEntriesTotal = capabilities.length + comments.length ;
                if ( nEntriesTotal === 0 || (capabilities.length <= nEntriesAvail/2 && comments.length <= nEntriesAvail/2) )
                    gEditVoDialogSplitter.setSizes( [ 50, 50 ] ) ;
                else {
                    var ratio = Math.floor( 100 * capabilities.length / nEntriesTotal ) ;
                    gEditVoDialogSplitter.setSizes( [ ratio, 100-ratio ] ) ;
                }
                gPrevEditVoDialogEntry = $entry ;
            }
        },
        beforeClose: function() {
            gEditVoDlgState = getDialogState( $(this) ) ;
        },
        buttons: {
            OK: function() {
                // save the V/O image ID
                var $img = $dlg.find( "img[class='vasl-image']" ) ;
                vo_image_id = $img.data( "vo-image-id" ) ;
                if ( vo_image_id )
                    $entry.data( "sortable2-data" ).vo_image_id = vo_image_id ;
                // unload the capabilities
                var capabilities = unload_entries( $capabilities ) ;
                if ( capabilities.join() !== get_default_capabilities( vo_entry, params, false ).join() )
                    $entry.data( "sortable2-data" ).custom_capabilities = capabilities ;
                else {
                    // the capabilities are the same as the default - no need to retain these custom settings
                    delete $entry.data( "sortable2-data" ).custom_capabilities ;
                }
                $entry.data( "sortable2-data" ).elite = $elite.prop( "checked" ) ;
                // unload the comments
                var comments = unload_entries( $comments ) ;
                if ( comments.join() !== get_default_comments( vo_entry ).join() ) {
                    $entry.data( "sortable2-data" ).custom_comments = comments ;
                }
                else {
                    // the comments are the same as the default - no need to retain these custom settings
                    delete $entry.data( "sortable2-data" ).custom_comments ;
                }
                // update the original V/O entry to reflect the changes
                update_vo_sortable2_entry( $entry, vo_type ) ;
                $(this).dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}
