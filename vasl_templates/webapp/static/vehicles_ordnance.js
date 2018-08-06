function add_vo( vo_type, player_id )
{
    // get the vehicles/ordnance already added
    var vo_present = [];
    $("#"+vo_type+"-sortable_"+player_id+" li").each( function() {
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
        title: "Add " + vo_type,
        dialogClass: "select-vo",
        modal: true,
        minWidth: 200,
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
                do_add_vo( nat, vo_type, player_id, entries[val].name ) ;
                update_vo_hint( vo_type, player_id ) ;
                $(this).dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

function do_add_vo( nat, vo_type, player_id, vo_name )
{
    // find the specified vehicle/ordnance
    var vo_key = make_vo_key( nat, vo_type, vo_name ) ;
    if ( ! find_vo( vo_key ) )
        return false ;

    // add a new vehicle/ordnance entry
    var $sortable = $( "#" + vo_type + "-sortable_" + player_id ) ;
    var $elem = $( "<li></li>" ) ;
    $elem.text( vo_name ) ;
    $elem.data( "vo-key", vo_key ) ;
    $sortable.append( $elem ) ;
    init_vo( vo_type, player_id, $elem ) ;

    return true ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function init_vo( vo_type, player_id, $elem )
{
    // initialize vehicle/ordnance element(s)
    $elem.click( function( evt ) {
        if ( evt.ctrlKey )
            delete_vo( vo_type, player_id, $(this) ) ;
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function update_vo_hint( vo_type, player_id )
{
    // show/hide the vehicle/ordnance hint
    if ( $("#"+vo_type+"-sortable_"+player_id+" li").length === 0 ) {
        $("#"+vo_type+"-sortable_"+player_id).hide() ;
        $("#"+vo_type+"-hint_"+player_id).show() ;
    } else {
        $("#"+vo_type+"-sortable_"+player_id).show() ;
        $("#"+vo_type+"-hint_"+player_id).hide() ;
    }
}

// --------------------------------------------------------------------

function delete_vo( vo_type, player_id, $elem )
{
    // delete the vehicle/ordnance
    $elem.addClass( "highlighted" ) ;
    ask( "Delete this "+vo_type+"?", escapeHTML($elem.text()), {
        "ok": function() {
            $elem.remove() ;
            update_vo_hint( vo_type, player_id ) ;
        },
        "close": function() { $elem.removeClass("highlighted") ; },
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function delete_all_vo( vo_type, player_id )
{
    // delete all vehicles/ordnance
    $("#"+vo_type+"-sortable_"+player_id+" li").each( function() {
        $(this).remove() ;
    } ) ;
    update_vo_hint( vo_type, player_id ) ;
}

// --------------------------------------------------------------------

var gVehicleOrdnanceIndex = null ;

function find_vo( vo_key )
{
    // check if we need to build the index
    function build_vo_index( vo_type ) {
        for ( var nat in gVehicleOrdnanceListings[vo_type] ) {
            for ( var i=0 ; i < gVehicleOrdnanceListings[vo_type][nat].length ; ++i ) {
                var entry = gVehicleOrdnanceListings[vo_type][nat][i] ;
                gVehicleOrdnanceIndex[ make_vo_key(nat,vo_type,entry.name) ] = entry ;
            }
        }
    }
    if ( gVehicleOrdnanceIndex === null ) {
        // yup - make it so
        gVehicleOrdnanceIndex = {} ;
        build_vo_index( "vehicle" ) ;
        build_vo_index( "ordnance" ) ;
    }

    // find a vehicle/ordnance entry
    return gVehicleOrdnanceIndex[ vo_key ] ;
}

function make_vo_key( nat, vo_type, name ) {
    // generate a key use to identify each vehicle/ordnance
    return nat + ":" + vo_type + ":" + name ;
}
