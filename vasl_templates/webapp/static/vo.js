
// --------------------------------------------------------------------

function add_vo( vo_type, player_no )
{
    // get the vehicles/ordnance already added
    var $sortable2 = $( "#ob_" + vo_type + "-sortable_" + player_no ) ;
    var vo_present = [];
    $sortable2.children("li").each( function() {
        vo_present.push( $(this).text() ) ;
    } );

    // load the available vehicles/ordnance
    var nat = $( "select[name='PLAYER_" + player_no + "']" ).val() ;
    var entries = gVehicleOrdnanceListings[vo_type][nat] ;
    if ( entries === undefined ) {
        showErrorMsg( "There are no " + gTemplatePack.nationalities[nat].display_name + " " + vo_type + " listings." ) ;
        return ;
    }
    var buf = [] ;
    for ( var i=0 ; i < entries.length ; ++i ) {
        if ( vo_present.indexOf( entries[i].name ) !== -1 )
            continue ;
        // TODO: It'd be nice to be able to use HTML in the option text (e.g. PzKpfw IVF 1/2)
        buf.push( "<option value='" + i + "'>" + entries[i].name + "</option>" ) ;
    }
    var $listbox = $( "#select-vo select" ) ;
    $listbox.html( buf.join("") ) ;
    $listbox.prop( "selectedIndex", 0 ).animate({ scrollTop: 0 }) ;

    // let the user select a vehicle/ordnance
    $("#select-vo").dialog( {
        title: "Add " + SORTABLE_DISPLAY_NAMES["ob_"+vo_type][0],
        dialogClass: "select-vo",
        modal: true,
        minWidth: 300,
        minHeight: 300,
        create: function() {
            init_dialog( $(this), "OK", false ) ;
        },
        open: function() {
            // initialize
            on_dialog_open( $(this) ) ;
            $("#select-vo input[type='text']").val( "" ).focus() ;
            $(this).height( $(this).height() ) ; // fudge: force the select to resize
            $("#select-vo select").filterByText( $("#select-vo input[type='text']") ) ;
            // set the titlebar color
            var colors = get_player_colors_for_element( $sortable2 ) ;
            $(".ui-dialog.select-vo .ui-dialog-titlebar").css( {
                background: colors[0],
                border: "1px solid "+colors[1],
            } ) ;
        },
        buttons: {
            OK: function() {
                // add the new vehicle/ordnance
                var val = $listbox.val() ;
                if ( ! val )
                    return ;
                do_add_vo( vo_type, player_no, entries[val] ) ;
                $(this).dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function do_add_vo( vo_type, player_no, entry )
{
    // add the specified vehicle/ordnance
    var $sortable2 = $( "#ob_" + vo_type + "-sortable_" + player_no ) ;
    $sortable2.sortable2( "add", {
        content: $( "<div>" + entry.name + "</div>" ),
        data: { caption: entry.name, vo_entry: entry },
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
