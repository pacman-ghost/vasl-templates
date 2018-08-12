
// --------------------------------------------------------------------

function add_vo( vo_type, player_id )
{
    // get the vehicles/ordnance already added
    var $sortable2 = $( "#" + vo_type + "-sortable_" + player_id ) ;
    var vo_present = [];
    $sortable2.children("li").each( function() {
        vo_present.push( $(this).text() ) ;
    } );

    // load the available vehicles/ordnance
    var nat = $( "select[name='PLAYER_" + player_id + "']" ).val() ;
    var entries = gVehicleOrdnanceListings[vo_type][nat] ;
    if ( entries === undefined ) {
        showErrorMsg( "There are no " + gTemplatePack.nationalities[nat].display_name + " " + vo_type + " listings." ) ;
        return ;
    }
    var buf = [] ;
    for ( var i=0 ; i < entries.length ; ++i ) {
        if ( vo_present.indexOf( entries[i].name ) !== -1 )
            continue ;
        buf.push( "<option value='" + i + "'>" + escapeHTML(entries[i].name) + "</option>" ) ;
    }
    var $listbox = $( "#select-vo select" ) ;
    $listbox.html( buf.join("") ) ;
    $listbox.prop( "selectedIndex", 0 ).animate({ scrollTop: 0 }) ;

    // let the user select a vehicle/ordnance
    $("#select-vo").dialog( {
        title: "Add " + SORTABLE_DISPLAY_NAMES[vo_type][0],
        dialogClass: "select-vo",
        modal: true,
        minWidth: 300,
        minHeight: 300,
        open: function() {
            $("#select-vo input[type='text']").val( "" ) ;
            $(this).height( $(this).height() ) ; // fudge: force the select to resize
            $("#select-vo select").filterByText( $("#select-vo input[type='text']") ) ;
        },
        buttons: {
            OK: function() {
                // add the new vehicle/ordnance
                var val = $listbox.val() ;
                do_add_vo( vo_type, player_id, entries[val] ) ;
                $(this).dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function do_add_vo( vo_type, player_id, entry )
{
    // add the specified vehicle/ordnance
    var $sortable2 = $( "#" + vo_type + "-sortable_" + player_id ) ;
    $sortable2.sortable2( "add", {
        content: $( "<div>" + entry.name + "</div>" ),
        data: { caption: entry.name, vo_entry: entry }
    } ) ;
}

// --------------------------------------------------------------------

function find_vo( vo_type, nat, name )
{
    // find the specificed vehicle/ordnance
    var entries = gVehicleOrdnanceListings[vo_type][nat] ;
    for ( var i=0 ; i < entries.length ; ++i ) {
        if ( entries[i].name === name )
            return entries[i] ;
    }

    return null ;
}
