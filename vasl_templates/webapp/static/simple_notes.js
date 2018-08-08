// NOTE: This module manage simple notes (some text and an optional width),
// which is used by OB setups and OB notes (which differ only in their templates,
// the code to manage them is almost identical).

// --------------------------------------------------------------------

function add_ob_setup( player_id ) { _do_edit_simple_note( $("#ob_setups-sortable_"+player_id), null ) ; }
function do_add_ob_setup( $sortable, data ) { _do_add_simple_note($sortable,data) ; }
function edit_ob_setup( $sortable, $entry ) { _do_edit_simple_note( $sortable, $entry ) ; }

function add_ob_note( player_id ) { _do_edit_simple_note( $("#ob_notes-sortable_"+player_id), null ) ; }
function do_add_ob_note( $sortable, data ) { _do_add_simple_note($sortable,data) ; }
function edit_ob_note( $sortable, $entry ) { _do_edit_simple_note( $sortable, $entry ) ; }

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function _do_edit_simple_note( $sortable, $entry )
{
    // figure out what we're editing
    var note_type = _get_note_type_for_sortable( $sortable ) ;
    var note_type0 = note_type.substring( 0, note_type.length-1 ) ; // plural -> singular :-/

    // let the user edit the note
    var $caption, $width ;
    $("#edit-simple_note").dialog( {
        dialogClass: "edit-simple_note",
        modal: true,
        minWidth: 400,
        minHeight: 150,
        open: function() {
            $caption = $(this).children( "textarea" ) ;
            $width = $(this).children( "input[type='text']" ) ;
            if ( $entry ) {
                var data = $entry.data( "sortable-data" ) ;
                $caption.val( data.caption ) ;
                $width.val( data.width ) ;
            }
            else {
                $caption.val( "" ) ;
                $width.val( "" ) ;
            }
            $(this).height( $(this).height() ) ; // fudge: force the textarea to resize
        },
        buttons: {
            OK: function() {
                var caption = $caption.val().trim() ;
                var width = $width.val().trim() ;
                if ( $entry ) {
                    // update the existing note
                    if ( caption === "" )
                        delete_sortable_entry( $entry ) ;
                    else {
                        $entry.data("sortable-data").caption = caption ;
                        $entry.data("sortable-data").width = width ;
                        $entry.empty().append( _make_simple_note( note_type, caption ) ) ;
                    }
                }
                else {
                    // create a new note
                    if ( caption !== "" ) {
                        data = { caption: caption, width: width } ;
                        _do_add_simple_note( $sortable, data ) ;
                    }
                }
                $(this).dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function _do_add_simple_note( $sortable, data )
{
    // add a new sortable entry
    var note_type = _get_note_type_for_sortable( $sortable ) ;
    var $entry = _make_simple_note( note_type, data.caption ) ;
    add_sortable( $sortable, $entry , data ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function _make_simple_note( note_type, caption )
{
    // generate the sortable entry
    var note_type0 = note_type.substring( 0, note_type.length-1 ) ;
    var buf = [] ;
    buf.push(
        "<div>",
        "<input type='button' data-id='" + note_type0 + "' value='Snippet'>",
        caption,
        "</div>"
    ) ;
    var $content = $( buf.join("") ) ;

    // add a handler for the snippet button
    $content.children("input[type='button']").click( function() {
        var data = $(this).parent().parent().data( "sortable-data" ) ;
        var prefix = (note_type === "ob_setups") ? "OB_SETUP" : "OB_NOTE" ;
        var extra_params = {} ;
        extra_params[prefix] = data.caption ;
        extra_params[prefix+"_WIDTH"] = data.width ;
        generate_snippet( $(this), extra_params ) ;
    } ) ;

    return $content ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function _get_note_type_for_sortable( $sortable )
{
    // figure out what type of note the sortable has
    var id = $sortable.prop( "id" ) ;
    var match = /^(ob_(setups|notes))-sortable_\d$/.exec( id ) ;
    return match[1] ;
}
