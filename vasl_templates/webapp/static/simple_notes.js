// NOTE: This module manage simple notes (some text and an optional width),
// which is used by OB setups and OB notes (which differ only in their templates,
// the code to manage them is almost identical).

var gEditSimpleNoteDlgState = null ;

// --------------------------------------------------------------------

function add_scenario_note() { _do_edit_simple_note( "scenario_note", null, $("#scenario_notes-sortable"), null, gDefaultScenario._SCENARIO_NOTE_WIDTH, false ) ; }
function do_add_scenario_note( $sortable2, data ) { _do_add_simple_note($sortable2,data) ; }
function edit_scenario_note( $sortable2, $entry ) { _do_edit_simple_note( "scenario_note", null, $sortable2, $entry, null, false ) ; }

function add_ssr() { _do_edit_simple_note( "ssr", null, $("#ssr-sortable"), null, null, true ) ; }
function do_add_ssr( $sortable2, data ) { _do_add_simple_note($sortable2,data) ; }
function edit_ssr( $sortable2, $entry ) { _do_edit_simple_note( "ssr", null, $sortable2, $entry, null, true ) ; }

function add_ob_setup( player_no ) { _do_edit_simple_note( "ob_setup", player_no, $("#ob_setups-sortable_"+player_no), null, gDefaultScenario._OB_SETUP_WIDTH, true ) ; }
function do_add_ob_setup( $sortable2, data ) { _do_add_simple_note($sortable2,data) ; }
function edit_ob_setup( $sortable2, $entry ) { _do_edit_simple_note( "ob_setup", get_player_no_for_element($sortable2), $sortable2, $entry, null, true ) ; }

function add_ob_note( player_no ) { _do_edit_simple_note( "ob_note", player_no, $("#ob_notes-sortable_"+player_no), null, gDefaultScenario._OB_NOTE_WIDTH, false ) ; }
function do_add_ob_note( $sortable2, data ) { _do_add_simple_note($sortable2,data) ; }
function edit_ob_note( $sortable2, $entry ) { _do_edit_simple_note( "ob_note", get_player_no_for_element($sortable2), $sortable2, $entry, null, false ) ; }

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function _do_edit_simple_note( template_id, player_no, $sortable2, $entry, default_width, remove_first_para )
{
    // figure out what we're editing
    var note_type = _get_note_type_for_sortable( $sortable2 ) ;
    var note_type0 = note_type.substring( 0, note_type.length-1 ) ; // plural -> singular :-/

    // determine the next available ID
    var usedIds = {} ;
    $sortable2.children( "li" ).each( function() {
        usedIds[ $(this).data("sortable2-data").id ] = true ;
    } ) ;
    var nextAvailableId = auto_assign_id( usedIds, "id" ) ;

    function makeSimpleSnippet( evt ) {
        // initialize
        var $btnPane = $( ".ui-dialog.edit-simple_note .ui-dialog-buttonpane" ) ;
        var $btn = $btnPane.find( "button.snippet" ) ;
        var data = unloadData() ;
        // prepare the template parameters
        // NOTE: We don't bother handling the case of an empty caption.
        var extraParams = {} ;
        if ( template_id === "ssr" ) {
            // NOTE: All the SSR's are combined into a single snippet, so it doesn't actually make sense
            // to have a snippet button for individual SSR's, but it's convenient. We unload all the SSR's
            // from the UI, then update the content for the one being edited (if it already exists), or
            // add it to the end of the list (if it's a new one).
            var ssrs = unload_ssrs() ;
            if ( $entry ) {
                // find and update the SSR being edited
                $( "#ssr-sortable > li" ).each( function( index ) {
                    if ( $(this)[0] === $entry[0] )
                        ssrs[ index ] = data.caption ;
                } ) ;
            } else {
                // add the new SSR to the end of the list
                ssrs.push( data.caption ) ;
            }
            extraParams.SSR = ssrs ;
        } else {
            // override the template parameters unloaded from the UI with the current values from the dialog
            var paramKey = template_id.toUpperCase() ;
            extraParams[ paramKey ] = data.caption ;
            extraParams[ paramKey+"_WIDTH" ] = data.width ;
        }
        // generate the snippet
        generate_snippet( $btn, evt.shiftKey, extraParams ) ;
    }

    function unloadData() {
        // unload the snippet data
        return {
            caption: unloadTrumbowyg( $caption, remove_first_para ),
            width: $width.val().trim(),
        } ;
    }

    // let the user edit the note
    var dlgTitle = ($entry ? "Edit " : "Add ") + SORTABLE_DISPLAY_NAMES[note_type][0] ;
    var $caption, $width, origData ;
    var $dlg = $("#edit-simple_note").dialog( {
        dialogClass: "edit-simple_note",
        title: dlgTitle,
        modal: true,
        closeOnEscape: false,
        position: gEditSimpleNoteDlgState ? gEditSimpleNoteDlgState.position : { my: "center", at: "center", of: window },
        width: gEditSimpleNoteDlgState ? gEditSimpleNoteDlgState.width : $(window).width() * 0.4,
        // NOTE: Simple notes don't normally have a lot of content, but we need space for the Trumbowyg dropdowns.
        height: gEditSimpleNoteDlgState ? gEditSimpleNoteDlgState.height : Math.max( $(window).height() * 0.5, 325 ),
        minWidth: 600,
        minHeight: 250,
        create: function() {
            init_dialog( $(this), "OK", true ) ;
        },
        open: function() {
            // initialize
            $caption = $(this).find( "div.caption" ) ;
            on_dialog_open( $(this), $caption ) ;
            add_flag_to_dialog_titlebar( $(this), get_player_no_for_element($sortable2) ) ;
            var $btn_pane = $(".ui-dialog.edit-simple_note .ui-dialog-buttonpane") ;
            var $btn = $btn_pane.find( "button.snippet" ) ;
            $btn.prepend(
                $( "<img src='" + gImagesBaseUrl+"/snippet.png" + "' style='height:0.9em;margin:0 0 -2px -2px;'>" )
            ) ;
            $width = $btn_pane.find( "input[name='width']" ) ;
            if ( $width.length === 0 ) {
                // create the width controls
                $btn_pane.prepend( $( "<div style='position:absolute;left:19px;height:28px;display:flex;align-items:center;'>" +
                    "<label for='width'>Width:</label>&nbsp;<input type='text' name='width' size='4' style='margin-top:-1px;'>" +
                "</div>" ) ) ;
                $width = $btn_pane.find( "input[name='width']" ) ;
            }
            // initialize the Trumbowyg HTML editor
            if ( ! gEditSimpleNoteDlgState ) // nb: check if this is the first time the dialog has been opened
                initTrumbowyg( $caption, gAppConfig.trumbowyg["simple-note-dialog"], $(this) ) ;
            else {
                // always start non-maximized, and in HTML mode
                if ( $caption.parent().hasClass( "trumbowyg-fullscreen" ) )
                    $caption.trumbowyg( "execCmd", { cmd: "fullscreen" } ) ;
                if ( $caption.parent().hasClass( "trumbowyg-editor-hidden" ) )
                    $caption.trumbowyg( "toggle" ) ;
            }
            // tweak the SNIPPETS button so that snippets will work
            $btn.data( { id: template_id, "player-no": player_no } ) ;
            var snippet_id = template_id ;
            if ( player_no )
                snippet_id += "_" + player_no ;
            var entryData = $entry ? $entry.data("sortable2-data") : null ;
            if ( template_id !== "ssr" )
                snippet_id += "." + (entryData ? entryData.id : nextAvailableId) ;
            $btn.data( "snippet-id", snippet_id ) ;
            $btn.button( is_template_available( template_id ) ? "enable" : "disable" ) ;
            // show/hide the width controls (nb: SSR's have a separate width setting that affects all of them)
            var show = (note_type !== "ssr") ;
            $btn_pane.find( "label[for='width']" ).css( "display", show?"inline":"none" ) ;
            $width.css( "display", show?"inline":"none" ) ;
            $btn.css( { position: "absolute", left:
                show ? $width.offset().left + $width.width() - $btn_pane.find("label[for='width']").offset().left + 25 : 15
            } ) ;
            // enable auto-dismiss for the dialog
            var $dlg = $(this) ;
            $width.keydown( function(evt) { auto_dismiss_dialog( $dlg, evt, "OK" ) ; } ) ;
            // set the titlebar color
            var colors = get_player_colors_for_element($sortable2) || ["#d0d0d0","#c0c0c0","#a0a0a0"] ;
            $(".ui-dialog.edit-simple_note .ui-dialog-titlebar").css( {
                background: colors[0],
                border: "1px solid "+colors[2]
            } ) ;
            // load the dialog
            $caption.trumbowyg( "html", entryData ? entryData.caption : "" ) ;
            $width.val( entryData ? entryData.width : default_width ) ;
            origData = unloadData() ;
            $(this).height( $(this).height() ) ; // fudge: force everything to resize
        },
        beforeClose: function() {
            gEditSimpleNoteDlgState = getDialogState( $(this) ) ;
        },
        buttons: {
            Snippet: { text:" Snippet", class: "snippet", click: makeSimpleSnippet },
            OK: function() {
                var data = unloadData() ;
                if ( $entry ) {
                    // update the existing note
                    if ( data.caption === "" )
                        $sortable2.sortable2( "delete", { entry: $entry } ) ;
                    else {
                        $entry.data("sortable2-data").caption = data.caption ;
                        $entry.data("sortable2-data").width = data.width ;
                        $entry.empty().append( _make_simple_note( note_type, data.caption ) ) ;
                    }
                }
                else {
                    // create a new note
                    if ( data.caption !== "" ) {
                        data = { caption: data.caption, width: data.width } ;
                        if ( note_type === "scenario_notes" || note_type === "ob_setups" || note_type === "ob_notes" )
                            data.id = nextAvailableId ;
                        $entry = _do_add_simple_note( $sortable2, data ) ;
                    }
                }
                // check if we should automatically generate a snippet
                if ( isKeyDown( "Shift" ) && data.caption !== "" ) {
                    var $elem = $entry.find( "img.snippet" ) ;
                    if ( $elem.length !== 0 )
                        $elem.click() ;
                }
                $(this).dialog( "close" ) ;
            },
            Cancel: function() {
                if ( JSON.stringify( unloadData() ) != JSON.stringify( origData ) ) {
                    ask( dlgTitle, "Discard your changes?", {
                        ok: function() { $dlg.dialog( "close" ) ; },
                    } ) ;
                    return ;
                }
                $(this).dialog( "close" ) ;
            },
        },
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function _do_add_simple_note( $sortable2, data )
{
    // add a new sortable2 entry
    var note_type = _get_note_type_for_sortable( $sortable2 ) ;
    return $sortable2.sortable2( "add", {
        content: _make_simple_note( note_type, data.caption ),
        data: data,
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function _make_simple_note( note_type, caption )
{
    // generate the sortable entry
    var buf = [ "<div>" ] ;
    if ( ["scenario_notes","ob_setups","ob_notes"].indexOf( note_type ) !== -1 ) {
        var note_type0 = note_type.substring( 0, note_type.length-1 ) ;
        if ( is_template_available( note_type0 ) ) {
            buf.push(
                "<img src='" + gImagesBaseUrl + "/snippet.png'",
                " class='snippet' data-id='" + note_type0 + "' title='" + GENERATE_SNIPPET_HINT + "'>"
            ) ;
        }
    }
    buf.push( caption, "</div>" ) ;
    var $content = $( buf.join("") ) ;
    fixup_external_links( $content ) ;
    makeSnippetHotHover( $content.children( "img" ) ) ;

    // add a handler for the snippet button
    $content.children("img.snippet").click( function( evt ) {
        var extra_params = get_simple_note_snippet_extra_params( $(this) ) ;
        generate_snippet( $(this), evt.shiftKey, extra_params ) ;
        return false ;
    } ) ;

    return $content ;
}

function get_simple_note_snippet_extra_params( $img )
{
    // get the extra parameters needed to generate the simple note's snippet
    var extra_params = {} ;
    var $sortable2 = $img.closest( ".sortable" ) ;
    var note_type = _get_note_type_for_sortable( $sortable2 ) ;
    var key ;
    if ( note_type === "scenario_notes" )
        key = "SCENARIO_NOTE" ;
    else if ( note_type === "ob_setups" )
        key = "OB_SETUP" ;
    else if ( note_type == "ob_notes" )
        key = "OB_NOTE" ;
    var data = $img.parent().parent().data( "sortable2-data" ) ;
    extra_params[key] = data.caption ;
    extra_params[key+"_WIDTH"] = data.width ;
    return extra_params ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function _get_note_type_for_sortable( $sortable2 )
{
    // figure out what type of note the sortable has
    var id = $sortable2.prop( "id" ) ;
    var match = /^((scenario_notes|ssr|ob_vehicles|ob_ordnance|ob_setups|ob_notes))-sortable(_\d)?$/.exec( id ) ;
    return match[1] ;
}
