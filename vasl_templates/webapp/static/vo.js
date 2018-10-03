
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
        var buf2 = [ "<div class='" + div_class + "' data-index='" + opt.id + "'>",
            "<img src='" + _get_vo_image_url(vo_entry,null) + "' class='vasl-image'>",
            "<div class='content'><div>",
            vo_entry.name,
            vo_entry.type ? "&nbsp;<span class='vo-type'>("+vo_entry.type+")</span>" : "",
            "</div></div>",
            "</div>"
        ] ;
        $entry = $( buf2.join("") ) ;
        $entry.find( "img" ).data( "vo-image-id", null ) ;
        var vo_images = get_vo_images( vo_entry ) ;
        if ( vo_images.length > 1 ) {
            $entry.find( "img" ).data( "vo-images", vo_images ) ;
            var $btn = $( "<input type='image' class='select-vo-image' src='" + gImagesBaseUrl + "/select-vo-image.png'>" ) ;
            $entry.children( ".content" ).append( $btn ) ;
            $btn.click( function() {
                $(this).blur() ;
                on_select_vo_image( $(this) ) ;
            } ) ;
        }
        return $entry ;
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
                // FUDGE! $sel.select("data") returns the wrong thing if the entries are filtered?!?!
                var $elem = $( "#select-vo .select2-results__option--highlighted" ) ;
                if ( $elem.length === 0 )
                    return ;
                var sel_index = $elem.children( ".vo-entry" ).data( "index" ) ;
                var $img = $elem.find( "img[class='vasl-image']" ) ;
                var vo_image_id = $img.data( "vo-image-id" ) ;
                do_add_vo( vo_type, player_no, entries[sel_index], vo_image_id ) ;
                $(this).dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function do_add_vo( vo_type, player_no, vo_entry, vo_image_id )
{
    // add the specified vehicle/ordnance
    // NOTE: We set a fixed height for the sortable2 entries (based on the CSS settings in tabs-ob.css),
    // so that the vehicle/ordnance images won't get truncated if there are a lot of them.
    var $sortable2 = $( "#ob_" + vo_type + "-sortable_" + player_no ) ;
    var div_tag = "<div" ;
    var fixed_height = "3.75em" ;
    if ( is_small_vasl_piece( vo_entry ) ) {
        div_tag += " class='small-piece'" ;
        fixed_height = "2.5em" ;
    }
    div_tag += ">" ;
    var url = _get_vo_image_url( vo_entry, vo_image_id ) ;
    $sortable2.sortable2( "add", {
        content: $( div_tag + "<img src='"+url+"'>" + vo_entry.name + "</div>" ),
        data: { caption: vo_entry.name, vo_entry: vo_entry, vo_image_id: vo_image_id, fixed_height: fixed_height },
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

function get_vo_images( vo_entry )
{
    // NOTE: Mapping Chapter H vehicles/ordnance to VASL images is quite messy :-/ Most map one-to-one,
    // but some V/O have multiple GPID's, some GPID's have multiple images. Also, some V/O don't have
    // a matching GPID (are they in a VASL extension somewhere?), so we can't show an image for them at all.
    // So, we identify VASL images by a GPID plus index (if there are multiple images for that GPID).
    var images = [] ;
    function add_gpid_images( gpid ) {
        if ( ! gpid || !(gpid in gVaslPieceInfo) )
            return ;
        for ( var i=0 ; i < gVaslPieceInfo[gpid].front_images ; ++i )
            images.push( [gpid,i] ) ;
    }
    if ( $.isArray(vo_entry.gpid) ) {
        for ( var i=0 ; i < vo_entry.gpid.length ; ++i )
            add_gpid_images( vo_entry.gpid[i] ) ;
    } else
        add_gpid_images( vo_entry.gpid ) ;

    return images ;
}

function on_select_vo_image( $btn ) {

    // initialize
    var $img = $btn.parent().parent().find( "img.vasl-image" ) ;
    var vo_images = $img.data( "vo-images" ) ;
    var vo_image_id = $img.data( "vo-image-id" ) ;

    // NOTE: We need to do this after the dialog has opened, since we need to wait for all the images
    // to finish loading, so that we can figure out how big to make the dialog.
    function on_open_dialog() {

        // load the vehicle/ordnance images
        var $images = $( "#select-vo-image .vo-images" ) ;
        var n_images_loaded=0, total_width=0, max_height=0 ;
        function on_image_loaded() {
            total_width += $(this).width() ;
            max_height = Math.max( $(this).height(), max_height ) ;
            if ( ++n_images_loaded == vo_images.length ) {
                // all images have loaded - resize the dialog
                var width = 5 + total_width + 20*vo_images.length + 10*vo_images.length + 5 ;
                var height = 5 + 10+max_height+10 + 5 ;
                $( ".ui-dialog.select-vo-image" ).width( width ).height( height ) ;
            }
        }
        $images.empty() ;
        for ( var i=0 ; i < vo_images.length ; ++i ) {
            var $elem = $( "<img data-index='" + i + "'>" )
                .bind( "load", on_image_loaded )
                .attr( "src", _get_vo_image_url( null, vo_images[i] ) ) ;
            $images.append( $elem ) ;
        }

        // highlight the currently-selected image
        var sel_index = (vo_image_id === null) ? 0 : vo_images.indexOf(vo_image_id) ;
        if ( sel_index === -1 ) {
            console.log( "Couldn't find V/O image ID '" + vo_image_id + "' in V/O images: " + vo_images ) ;
            sel_index = 0 ;
        }
        $images.children( "img:eq("+sel_index+")" ).css( "background", "#5897fb" ) ;

        // highlight images on mouse-over
        var prev_bgd ;
        $images.children( "img" ).on( {
            "mouseenter": function() {
                prev_bgd = $(this).css( "backgroundColor" ) ;
                if ( $(this).data("index") != sel_index )
                    $(this).css( "background", "#ddd" ) ;
            },
            "mouseleave": function() { $(this).css( "backgroundColor", prev_bgd ) ; }
        } ) ;

        // handle image selection
        $images.children( "img" ).click( function() {
            vo_image_id = vo_images[ $(this).data("index") ] ;
            $img.attr( "src", _get_vo_image_url(vo_image_id) ) ;
            $img.data( "vo-image-id", vo_image_id ) ;
            $dlg.dialog( "close" ) ;
            // nb: if the user selected an image, we take that to mean they also want to add that vehicle/ordnance
            click_dialog_button( $("#select-vo"), "OK" ) ;
        } ) ;

    }

    // show the dialog
    var $dlg = $("#select-vo-image").dialog( {
        dialogClass: "select-vo-image",
        modal: true,
        position: { my: "left top", at: "left-50 bottom+5", of: $btn, "collision": "fit" },
        width: 1, height: 1, // nb: to avoid flicker; we set the size when the images have finished loading
        minWidth: 200,
        minHeight: 100,
        resizable: false,
        "open": on_open_dialog,
    } ) ;
}

function _get_vo_image_url( vo_entry, vo_image_id )
{
    if ( vo_image_id )
        return "/counter/" + vo_image_id[0] + "/front/" + vo_image_id[1] ;
    else {
        // no V/O image ID was provided, just use the first available image
        if ( $.isArray( vo_entry.gpid ) )
            return "/counter/" + vo_entry.gpid[0] + "/front" ;
        if ( vo_entry.gpid )
            return "/counter/" + vo_entry.gpid + "/front" ;
    }
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
