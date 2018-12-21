// NOTE: This module manage simple notes (some text and an optional width),
// which is used by OB setups and OB notes (which differ only in their templates,
// the code to manage them is almost identical).

// --------------------------------------------------------------------

function add_scenario_note() { _do_edit_simple_note( $("#scenario_notes-sortable"), null, gDefaultScenario._SCENARIO_NOTE_WIDTH ) ; }
function do_add_scenario_note( $sortable2, data ) { _do_add_simple_note($sortable2,data) ; }
function edit_scenario_note( $sortable2, $entry ) { _do_edit_simple_note( $sortable2, $entry, null ) ; }

function add_ssr() { _do_edit_simple_note( $("#ssr-sortable"), null, null ) ; }
function do_add_ssr( $sortable2, data ) { _do_add_simple_note($sortable2,data) ; }
function edit_ssr( $sortable2, $entry ) { _do_edit_simple_note( $sortable2, $entry, null ) ; }

function add_ob_setup( player_no ) { _do_edit_simple_note( $("#ob_setups-sortable_"+player_no), null, gDefaultScenario._OB_SETUP_WIDTH ) ; }
function do_add_ob_setup( $sortable2, data ) { _do_add_simple_note($sortable2,data) ; }
function edit_ob_setup( $sortable2, $entry ) { _do_edit_simple_note( $sortable2, $entry, null ) ; }

function add_ob_note( player_no ) { _do_edit_simple_note( $("#ob_notes-sortable_"+player_no), null, gDefaultScenario._OB_NOTE_WIDTH ) ; }
function do_add_ob_note( $sortable2, data ) { _do_add_simple_note($sortable2,data) ; }
function edit_ob_note( $sortable2, $entry ) { _do_edit_simple_note( $sortable2, $entry, null ) ; }

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function _do_edit_simple_note( $sortable2, $entry, default_width )
{
    // figure out what we're editing
    var note_type = _get_note_type_for_sortable( $sortable2 ) ;
    var note_type0 = note_type.substring( 0, note_type.length-1 ) ; // plural -> singular :-/

    // let the user edit the note
    var $caption, $width ;
    $("#edit-simple_note").dialog( {
        dialogClass: "edit-simple_note",
        title: ($entry ? "Edit " : "Add ") + SORTABLE_DISPLAY_NAMES[note_type][0],
        modal: true,
        minWidth: 400,
        minHeight: 150,
        create: function() {
            init_dialog( $(this), "OK", true ) ;
        },
        open: function() {
            // initialize
            on_dialog_open( $(this) ) ;
            add_flag_to_dialog_titlebar( $(this), get_player_no_for_element($sortable2) ) ;
            $caption = $(this).children( "textarea" ) ;
            var $btn_pane = $(".ui-dialog.edit-simple_note .ui-dialog-buttonpane") ;
            $width = $btn_pane.children( "input[name='width']" ) ;
            if ( $width.length === 0 ) {
                // create the width controls
                $btn_pane.prepend( $("<label for='width'>Width:</label>&nbsp;<input type='text' name='width' size='5'>") ) ;
                $width = $btn_pane.children( "input[name='width']" ) ;
            }
            // show/hide the width controls (nb: SSR's have a separate width setting that affects all of them)
            var show = (note_type !== "ssr") ;
            $btn_pane.children( "label[for='width']" ).css( "display", show?"inline":"none" ) ;
            $width.css( "display", show?"inline":"none" ) ;
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
            var data = $entry ? $entry.data("sortable2-data") : null ;
            $caption.val( data ? data.caption : "" ).focus() ;
            $width.val( data ? data.width : default_width ) ;
            $(this).height( $(this).height() ) ; // fudge: force the textarea to resize
        },
        buttons: {
            OK: function() {
                var caption = $caption.val().trim() ;
                var width = $width.val().trim() ;
                if ( $entry ) {
                    // update the existing note
                    if ( caption === "" )
                        $sortable2.sortable2( "delete", { entry: $entry } ) ;
                    else {
                        $entry.data("sortable2-data").caption = caption ;
                        $entry.data("sortable2-data").width = width ;
                        $entry.empty().append( _make_simple_note( note_type, caption ) ) ;
                    }
                }
                else {
                    // create a new note
                    if ( caption !== "" ) {
                        data = { caption: caption, width: width } ;
                        if ( note_type === "scenario_notes" || note_type === "ob_setups" || note_type === "ob_notes" ) {
                            var usedIds = {} ;
                            $sortable2.find( "li" ).each( function() {
                                usedIds[ $(this).data("sortable2-data").id ] = true ;
                            } ) ;
                            data.id = auto_assign_id( usedIds, "id" ) ;
                        }
                        _do_add_simple_note( $sortable2, data ) ;
                    }
                }
                $(this).dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function _do_add_simple_note( $sortable2, data )
{
    // add a new sortable2 entry
    var note_type = _get_note_type_for_sortable( $sortable2 ) ;
    $sortable2.sortable2( "add", {
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
        buf.push(
            "<img src='" + gImagesBaseUrl + "/snippet.png'",
            " class='snippet' data-id='" + note_type0 + "' title='" + GENERATE_SNIPPET_HINT + "'>"
        ) ;
    }
    buf.push( caption, "</div>" ) ;
    var $content = $( buf.join("") ) ;
    $content.children( "img" ).hover(
        function() { $(this).attr( "src", gImagesBaseUrl + "/snippet-hot.png" ) ; },
        function() { $(this).attr( "src", gImagesBaseUrl + "/snippet.png" ) ; }
    ) ;

    // add a handler for the snippet button
    $content.children("img.snippet").click( function( evt ) {
        var extra_params = get_simple_note_snippet_extra_params( $(this) ) ;
        generate_snippet( $(this), evt, extra_params ) ;
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
