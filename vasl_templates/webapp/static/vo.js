
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
        showErrorMsg( "There are no " + get_nationality_display_name(nat) + " " + vo_type + " listings." ) ;
        return ;
    }
    var buf = [] ;
    for ( var i=0 ; i < entries.length ; ++i ) {
        if ( vo_present.indexOf( entries[i].name ) !== -1 )
            continue ;
        // TODO: It'd be nice to be able to use HTML in the option text (e.g. PzKpfw IVF 1/2)
        buf.push( "<option value='" + i + "'>" + entries[i].name + "</option>" ) ;
    }
    function format_vo_entry( opt ) {
        if ( ! opt.id )
            return opt.text ;
        var div_class = "vo-entry" ;
        if ( is_small_vasl_piece( entries[opt.id] ) )
            div_class += " small-piece" ;
        return $( "<div class='" + div_class + "'><img src='" + _get_vo_image_url(entries[opt.id]) + "'>" + opt.text + "</div>" ) ;
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

function do_add_vo( vo_type, player_no, entry )
{
    // add the specified vehicle/ordnance
    var $sortable2 = $( "#ob_" + vo_type + "-sortable_" + player_no ) ;
    var div_tag = "<div" ;
    if ( is_small_vasl_piece( entry ) )
        div_tag += " class='small-piece'" ;
    div_tag += ">" ;
    $sortable2.sortable2( "add", {
        content: $( div_tag + "<img src='"+_get_vo_image_url(entry)+"'>" + entry.name + "</div>" ),
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

// --------------------------------------------------------------------

function _get_vo_image_url( vo_entry )
{
    if ( $.isArray( vo_entry._gpid_ ) ) // FIXME! if > 1 image available, let the user pick which one
        return "/counter/" + vo_entry._gpid_[0] + "/front" ;
    if ( vo_entry._gpid_ )
        return "/counter/" + vo_entry._gpid_ + "/front" ;
    return gImagesBaseUrl + "/missing-image.png" ;
}

function is_small_vasl_piece( vo_entry )
{
    var gpid = vo_entry._gpid_ ;
    if ( $.isArray( gpid ) ) // FIXME! if > 1 image available, need to be smarter here
        gpid = gpid[0] ;
    if ( !( gpid in gVaslPieceInfo ) )
        return false ;
    return gVaslPieceInfo[gpid].is_small ;
}
