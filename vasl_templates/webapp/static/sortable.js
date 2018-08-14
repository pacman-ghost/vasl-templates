SORTABLE_DISPLAY_NAMES = {
    scenario_notes: [ "scenario note", "scenario notes", "a" ],
    ssr: [ "SSR", "SSR's", "a" ],
    ob_setups: [ "OB setup note", "OB setup notes", "an" ],
    ob_notes: [ "OB setup note", "OB setup notes", "an" ],
    vehicles: [ "vehicle", "vehicles", "a" ],
    ordnance: [ "ordnance", "ordnance", "an" ],
} ;

SORTABLE_HINTS = {
    scenario_notes: "Add miscellaneous scenario notes here.",
    ssr: "Add scenario SSR's here.",
    ob_setups: "Add setup notes for the player's OB here.",
    ob_notes: "Add miscellaneous setup notes here.",
    vehicles: "Add vehicles in the player's OB here.",
    ordnance: "Add ordnance in the player's OB here.",
} ;

// --------------------------------------------------------------------

( function( $ ) {
$.fn.sortable2 = function( action, args )
{
    var actions = {

        "init": function( $sortable2 ) {
            // get the display name
            var display_name = SORTABLE_DISPLAY_NAMES[ get_sortable2_type($sortable2) ] ;
            // initialize the sortable2 and support elements
            $sortable2.data( "on_edit", args.edit ) ;
            var $add_btn = find_helper( $sortable2, "add" ) ;
            $add_btn.prepend( $( "<div><img src='" + gImagesBaseUrl + "/sortable-add.png' class='sortable-add'> Add</div>" ) )
                .addClass( "ui-button" ) ;
            var $add = find_helper( $sortable2, "add" ) ;
            $add.prop( "title", "Add a new " + display_name[0] )
                .click( args.add ) ;
            // handle dragging entries to the trash
            var $trash = find_helper( $sortable2, "trash" ) ;
            $trash.prop( "src", gImagesBaseUrl + "/trash.png" )
                .prop( "title", "Drag " + display_name[2] + " " + display_name[0] + " here to delete it." ) ;
            $sortable2.sortable( { connectWith: $trash, cursor: "move" } ) ;
            $trash.sortable( {
                receive: function( evt, ui ) {
                    ui.item.remove() ;
                    update_hint( $sortable2 ) ;
                }
            } ) ;
        },

        "add": function( $sortable2 ) {
            // add a new entry to the sortable2
            var $entry = $( "<li></li>" ) ;
            $entry.append( args.content ) ;
            $entry.data( "sortable2-data", args.data ) ;
            $sortable2.append( $entry ) ;
            init_entry( $sortable2, $entry ) ;
            // update the hint
            update_hint( $sortable2 ) ;
        },

        "delete": function( $sortable2 ) {
            // delete the entry from the sortable2
            delete_entry( $sortable2, args.entry ) ;
        },

        "delete-all": function( $sortable2 ) {
            // delete all entries from the sortable2
            $sortable2.children( "li" ).each( function() {
                $(this).remove() ;
            } ) ;
            update_hint( $sortable2 ) ;
        },

        "get-entry-data": function( $sortable2 ) {
            // get the data associated with each sortable2 entry
            var entry_data = [] ;
            $sortable2.children( "li" ).each( function() {
                entry_data.push( $(this).data( "sortable2-data" ) ) ;
            } ) ;
            return entry_data ;
        },

    } ;

    function init_entry( $sortable2, $entry )
    {
        // initialize the sortable2 entry
        var on_edit = $sortable2.data( "on_edit" ) ;
        if ( on_edit ) {
            $entry.dblclick( function() { // double-click => edit the entry
                on_edit( $sortable2, $entry ) ;
            } ) ;
        }
        $entry.click( function( evt ) { // ctrl-click => delete the entry
            if ( evt.ctrlKey )
                delete_entry( $sortable2, $(this) ) ;
        } ) ;

        // style the entry
        // NOTE: Colors aren't going to work when we're using the test template pack!
        var colors = get_player_colors_for_element( $sortable2 ) ;
        if ( colors ) {
            $entry.css( {
                "background": "#"+colors[0],
                "border-bottom": "1px solid #"+colors[1],
                "border-right": "1px solid #"+colors[1],
            } ) ;
        }
    }

    function delete_entry( $sortable2, $entry )
    {
        // ask if it's OK to delete the entry
        $entry.addClass( "highlighted" ) ;
        var caption = $entry.data( "sortable2-data" ).caption ;
        if ( ! caption )
            caption = $entry.html() ;
        ask( "OK to delete?", escapeHTML(caption), {
            "ok": function() {
                // yup - make it so
                $entry.remove() ;
                update_hint( $sortable2 ) ;
            },
            "close": function() { $entry.removeClass("highlighted") ; },
        } ) ;
    }

    function update_hint( $sortable2 ) {
        // show/hide the hint
        var $hint = find_helper( $sortable2, "hint" ) ;
        if ( $sortable2.children("li").length === 0 ) {
            $sortable2.hide() ;
            var display_name = SORTABLE_DISPLAY_NAMES[ get_sortable2_type($sortable2) ] ;
            var img = "<img src='" + gImagesBaseUrl + "/sortable-add.png' style='height:1em;'>" ;
            var buf = [
                SORTABLE_HINTS[ get_sortable2_type($sortable2) ],
                "<ul class='instructions'>",
                "<li>Click on the " + img + " below to add a new " + display_name[0] + ".",
                "<li>To re-order the " + display_name[1] + ", use the mouse to drag them around.",
                "<li>Ctrl-click on " + display_name[2] + " " + display_name[0] + " to delete it, or drag it into the trashcan below.",
                "</ul>",
            ] ;
            $hint.html( buf.join("") ) ;
            $hint.show() ;
        } else {
            $sortable2.show() ;
            $hint.hide() ;
        }
    }

    function find_helper( $sortable2, type ) {
        // find a helper element for the sortable2
        var id = $sortable2.prop( "id" ) ;
        var pos = id.indexOf( "-sortable" ) ;
        return $( "#" + get_sortable2_type($sortable2) + "-" + type + id.substring(pos+9) ) ;
    }

    function get_sortable2_type( $sortable2 ) {
        // get the sortable2 type
        var id = $sortable2.prop( "id" ) ;
        var pos = id.indexOf( "-sortable" ) ;
        return id.substring( 0, pos ) ;
    }

    // execute the specified action
    var retval = actions[action]( this ) ;

    return (retval !== undefined) ? retval : this ;
} ;
} ) ( jQuery ) ;
