SORTABLE_DISPLAY_NAMES = {
    scenario_notes: [ "scenario note", "scenario notes", "a" ],
    ssr: [ "SSR", "SSR's", "a" ],
    ob_setups: [ "OB setup note", "OB setup notes", "an" ],
    ob_notes: [ "OB setup note", "OB setup notes", "an" ],
    ob_vehicles: [ "vehicle", "vehicles", "a" ],
    ob_ordnance: [ "ordnance", "ordnance", "an" ],
} ;

SORTABLE_HINTS = {
    scenario_notes: "Add miscellaneous scenario notes here.",
    ssr: "Add scenario SSR's here.",
    ob_setups: "Add setup notes for the player's OB here.",
    ob_notes: "Add miscellaneous setup notes here.",
    ob_vehicles: "Add vehicles in the player's OB here.",
    ob_ordnance: "Add ordnance in the player's OB here.",
} ;

// --------------------------------------------------------------------

( function( $ ) {
$.fn.sortable2 = function( action, args )
{
    var actions = {

        "init": init_sortable2,

        "add": function( $sortable2 ) {
            // add a new entry to the sortable2
            var $entry = $( "<li></li>" ) ;
            $entry.append( args.content ) ;
            $entry.data( "sortable2-data", args.data ) ;
            init_entry( $sortable2, $entry ) ;
            $sortable2.append( $entry ) ;
            adjust_entry_heights( $sortable2 ) ;
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

        "adjust-entry-heights": function( $sortable2 ) {
            adjust_entry_heights( $sortable2 ) ;
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

    function init_sortable2( $sortable2 )
    {
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

        // handle overflow when there are too many entries
        // NOTE: We do this by setting the height of the entry list fairly low; if there are
        // a lot of entries, they will render outside its box, but this triggers the v-scrollbar
        // on the parent .content box. There seems to be an odd interaction with the main flexbox
        // if there are 2 overflowing entry lists and the main browser v-scrollbar appears,
        // but we can live with that, for now...
        $sortable2.css( "height", "5em" ) ; // nb: also effectively acts as a min-height
        $sortable2.parent().css( "overflow-y", "auto" ) ;

        // handle dragging entries to the trash
        var $trash = find_helper( $sortable2, "trash" ) ;
        $trash.prop( "src", gImagesBaseUrl + "/trash.png" )
            .prop( "title", "Drag " + display_name[2] + " " + display_name[0] + " here to delete it." ) ;
        $sortable2.sortable( {
            stop: function( evt, ui ) { set_entry_colors( ui.item, false ) ; },
            connectWith: $trash, cursor: "move"
        } ) ;
        $trash.sortable( {
            receive: function( evt, ui ) {
                ui.item.remove() ;
                adjust_entry_heights( $sortable2 ) ;
                update_hint( $sortable2 ) ;
            }
        } ) ;
    }

    function init_entry( $sortable2, $entry )
    {
        // initialize the sortable2 entry
        var on_edit = $sortable2.data( "on_edit" ) ;
        if ( on_edit ) {
            $entry.dblclick( function() { // double-click => edit the entry
                on_edit( $sortable2, $entry ) ;
            } ) ;
        }
        $entry.click( function( evt ) {
            if ( evt.ctrlKey )
                delete_entry( $sortable2, $(this) ) ; // ctrl-click => delete the entry
            else if ( evt.shiftKey ) {
                var $elem = $(this).find( "img.snippet" ) ;
                if ( $elem.length !== 0 )
                    $elem.click() ; // shift-click => generate snippet
            }
        } ) ;

        // style the entry
        // NOTE: Colors aren't going to work when we're using the test template pack!
        var colors = get_player_colors_for_element($sortable2) || ["#f0f0f0","#e0e0e0","#c0c0c0"] ;
        $entry.data( "colors", colors ) ;
        set_entry_colors( $entry, false ) ;
        $entry.on( {
            "mouseenter": function() { set_entry_colors( $entry, true ) ; },
            "mouseleave": function() { set_entry_colors( $entry, false ) ; }
        } ) ;
    }

    function delete_entry( $sortable2, $entry )
    {
        // ask if it's OK to delete the entry
        set_entry_colors( $entry, true ) ;
        var caption = $entry.data( "sortable2-data" ).caption ;
        if ( ! caption )
            caption = $entry.html() ;
        var display_name = SORTABLE_DISPLAY_NAMES[ get_sortable2_type($sortable2) ] ;
        var buf = [
            "OK to delete this " + display_name[0] + "?",
            "<div style='margin-top:1em;font-size:80%;font-style:italic;'>",
            escapeHTML( caption ),
            "</div>"
        ] ;
        ask( "Delete "+display_name[0], buf.join(""), {
            ok: function() {
                // yup - make it so
                $entry.remove() ;
                adjust_entry_heights( $sortable2 ) ;
                update_hint( $sortable2 ) ;
            },
            close: function() { set_entry_colors( $entry, false ) ; },
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

    function adjust_entry_heights( $sortable2 ) {
        // adjust the max height of each item based on how many items there are
        var $entries = $sortable2.children( "li" ) ;
        if ( $entries.length === 0 )
            return ;
        // NOTE: We can't get height for sortable2's that are not visible (i.e. not in the active tab),
        // we update the heights dynamically as tabs are selected, and the window is resized.
        var available_height = $sortable2.parent().height() ;
        var max_height = Math.ceil( Math.max( available_height/$entries.length, 2*gEmSize ) ) ;
        $entries.each( function() {
            var fixed_height = $(this).data( "sortable2-data" ).fixed_height ;
            if ( fixed_height )
                $(this).css( "height", fixed_height+"px" ) ;
            else
                $(this).css({ "max-height": max_height+"px", "overflow-y": "hidden" }) ;
            // check for overflow
            var entry_height = $(this).height() ;
            var content_height = $(this).children("div").height() ;
            // FIXME! We should show a visual cue that the entry is truncated.
        } ) ;
    }

    function set_entry_colors( $entry, invert )
    {
        // set the entry colors
        var colors = $entry.data( "colors" ) ;
        if ( ! colors )
            return ;
        if ( $entry.hasClass( "ui-sortable-helper" ) )
            invert = true ; // nb: drag is in progress
        $entry.css( {
            "background": colors[invert?1:0],
            "border-bottom": "1px solid "+colors[2],
            "border-right": "1px solid "+colors[2],
        } ) ;
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
