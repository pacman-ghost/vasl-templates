
// --------------------------------------------------------------------

function init_sortable( $sortable, on_add, on_edit )
{
    // initialize the support elements
    var $add = _find_sortable_helper( $sortable, "add" ) ;
    $add.click( on_add ) ;
    $sortable.data( "on_edit", on_edit ) ;

    // handle dragging entries to the trash
    var $trash = _find_sortable_helper( $sortable, "trash" ) ;
    $sortable.sortable( { connectWith: $trash, cursor: "move" } ) ;
    $trash.sortable( {
        receive: function( evt, ui ) {
            ui.item.remove() ;
            update_sortable_hint($sortable) ;
        }
    } ) ;
}

// --------------------------------------------------------------------

function add_sortable( $sortable, $content, sortable_data )
{
    // add a new entry to the sortable
    var $entry = $( "<li></li>" ) ;
    $entry.append( $content ) ;
    $entry.data( "sortable-data", sortable_data ) ;
    $sortable.append( $entry ) ;
    init_sortable_entry( $entry ) ;

    // update the hint
    update_sortable_hint( $sortable ) ;

    return $entry ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function init_sortable_entry( $entry )
{
    // initialize the sortable entry
    var $sortable = $entry.parent() ;
    $entry.dblclick( function() {
        $sortable.data("on_edit")( $sortable, $entry ) ;
    } ) ;
    $entry.click( function( evt ) {
        if ( evt.ctrlKey )
            delete_sortable_entry( $(this) ) ;
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function update_sortable_hint( $sortable )
{
    // show/hide the hint
    var $hint = _find_sortable_helper( $sortable, "hint" ) ;
    if ( $sortable.children("li").length === 0 ) {
        $sortable.hide() ;
        $hint.show() ;
    } else {
        $sortable.show() ;
        $hint.hide() ;
    }
}

// --------------------------------------------------------------------

function delete_sortable_entry( $entry )
{
    // initialize
    var $sortable = $entry.parent() ;

    // ask if it's OK to delete the entry
    $entry.addClass( "highlighted" ) ;
    var caption = $entry.data("sortable-data").caption ;
    if ( ! caption )
        caption = $entry.html() ;
    ask( "OK to delete?", escapeHTML(caption), {
        "ok": function() {
            // yup - make it so
            $entry.remove() ;
            update_sortable_hint( $sortable ) ;
        },
        "close": function() { $entry.removeClass("highlighted") ; },
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function delete_all_sortable_entries( $sortable )
{
    // delete all entries from the sortable
    $sortable.children("li").each( function() {
        $(this).remove() ;
    } ) ;
    update_sortable_hint( $sortable ) ;
}

// --------------------------------------------------------------------

function _find_sortable_helper( $sortable, type )
{
    // find a support element for the specified sortable
    var id = $sortable.prop( "id" ) ;
    var pos = id.indexOf( "sortable" ) ;
    return $( "#" + id.substring(0,pos) + type+ id.substring(pos+8) ) ;
}
