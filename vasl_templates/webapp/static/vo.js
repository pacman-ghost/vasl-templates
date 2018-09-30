
// --------------------------------------------------------------------

function add_vo( vo_type, player_no )
{
    // get the vehicles/ordnance already added
    var $sortable2 = $( "#ob_" + vo_type + "-sortable_" + player_no ) ;
    var vo_present = [];
    $sortable2.children("li").each( function() {
        var vo_entry = $(this).data( "sortable2-data" ).vo_entry ;
        vo_present.push( vo_entry.id ) ;
    } ) ;

    // load the available vehicles/ordnance
    var nat = $( "select[name='PLAYER_" + player_no + "']" ).val() ;
    var entries = gVehicleOrdnanceListings[vo_type][nat] ;
    if ( entries === undefined ) {
        showErrorMsg( "There are no " + get_nationality_display_name(nat) + " " + vo_type + " listings." ) ;
        return ;
    }
    var buf = [] ;
    for ( var i=0 ; i < entries.length ; ++i ) {
        if ( vo_present.indexOf( entries[i].id ) !== -1 )
            continue ;
        buf.push( "<option value='" + i + "'>" + entries[i].name + "</option>" ) ;
    }
    function format_vo_entry( opt ) {
        if ( ! opt.id )
            return opt.text ;
        var vo_entry = entries[opt.id] ;
        var div_class = "vo-entry" ;
        if ( is_small_vasl_piece( vo_entry ) )
            div_class += " small-piece" ;
        var buf2 = ["<div class='" + div_class + "'>",
            "<img src='" + _get_vo_image_url(vo_entry) + "'>",
            vo_entry.name,
            vo_entry.type ? "&nbsp;<span class='vo-type'>("+vo_entry.type+")</span>" : "",
            "</div>"
        ] ;
        return $( buf2.join("") ) ;
    }
    var $sel = $( "#select-vo select" ) ;
    $sel.html( buf.join("") ).select2( {
        width: "100%",
        templateResult: format_vo_entry,
        dropdownParent: $("#select-vo"), // FUDGE! need this for the searchbox to work :-/
        closeOnSelect: false ,
    } ) ;

    // stop the select2 droplist from closing up
    $sel.on( "select2:closing", function(evt) {
        evt.preventDefault() ;
    } ) ;

    // let the user select a vehicle/ordnance
    function on_resize( $dlg ) {
        $( ".select2-results ul" ).height( $dlg.height() - 50 ) ;
    }
    $("#select-vo").dialog( {
        title: "Add " + SORTABLE_DISPLAY_NAMES["ob_"+vo_type][0],
        dialogClass: "select-vo",
        modal: true,
        minWidth: 300,
        minHeight: 300,
        create: function() {
            init_dialog( $(this), "OK", false ) ;
            // handle ESCAPE
            $(this).keydown( function(evt) {
                if ( evt.keyCode == $.ui.keyCode.ESCAPE )
                    $(this).dialog( "close" ) ;
            } ) ;
        },
        open: function() {
            // initialize
            on_dialog_open( $(this) ) ;
            $sel.select2( "open" ) ;
            // set the titlebar color
            var colors = get_player_colors_for_element( $sortable2 ) ;
            $(".ui-dialog.select-vo .ui-dialog-titlebar").css( {
                background: colors[0],
                border: "1px solid "+colors[2],
            } ) ;
            // update the UI
            on_resize( $(this) ) ;
        },
        resize: function() { on_resize( $(this) ) ; },
        buttons: {
            OK: function() {
                // add the new vehicle/ordnance
                var data = $sel.select2( "data" ) ;
                if ( ! data )
                    return ;
                do_add_vo( vo_type, player_no, entries[data[0].id] ) ;
                $(this).dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function do_add_vo( vo_type, player_no, vo_entry )
{
    // add the specified vehicle/ordnance
    // NOTE: We set a fixed height for the sortable2 entries (based on the CSS settings in tabs-ob.css),
    // so that the vehicle/ordnance images won't get truncated if there are a lot of them.
    var $sortable2 = $( "#ob_" + vo_type + "-sortable_" + player_no ) ;
    var div_tag = "<div" ;
    var fixed_height = 3.25 * gEmSize ;
    if ( is_small_vasl_piece( vo_entry ) ) {
        div_tag += " class='small-piece'" ;
        fixed_height = 2.25 * gEmSize ;
    }
    div_tag += ">" ;
    $sortable2.sortable2( "add", {
        content: $( div_tag + "<img src='"+_get_vo_image_url(vo_entry)+"'>" + vo_entry.name + "</div>" ),
        data: { caption: vo_entry.name, vo_entry: vo_entry, fixed_height: fixed_height },
    } ) ;
}

// --------------------------------------------------------------------

function find_vo( vo_type, nat, vo_id )
{
    // find the specificed vehicle/ordnance
    var entries = gVehicleOrdnanceListings[vo_type][nat] ;
    for ( var i=0 ; i < entries.length ; ++i ) {
        if ( entries[i].id === vo_id )
            return entries[i] ;
    }
    return null ;
}

function find_vo_by_name( vo_type, nat, name )
{
    // find the specificed vehicle/ordnance by name
    var entries = gVehicleOrdnanceListings[vo_type][nat] ;
    for ( var i=0 ; i < entries.length ; ++i ) {
        if ( entries[i].name === name )
            return entries[i] ;
    }
    return null ;
}

// --------------------------------------------------------------------

function _get_vo_image_url( vo_entry )
{
    if ( $.isArray( vo_entry.gpid ) ) // FIXME! if > 1 image available, let the user pick which one
        return "/counter/" + vo_entry.gpid[0] + "/front" ;
    if ( vo_entry.gpid )
        return "/counter/" + vo_entry.gpid + "/front" ;
    return gImagesBaseUrl + "/missing-image.png" ;
}

function is_small_vasl_piece( vo_entry )
{
    var gpid = vo_entry.gpid ;
    if ( $.isArray( gpid ) ) // FIXME! if > 1 image available, need to be smarter here
        gpid = gpid[0] ;
    if ( !( gpid in gVaslPieceInfo ) )
        return false ;
    return gVaslPieceInfo[gpid].is_small ;
}
