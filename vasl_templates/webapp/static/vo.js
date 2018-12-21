
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
            "<img src='" + get_vo_image_url(vo_entry,null,true) + "' class='vasl-image'>",
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
                on_select_vo_image(
                    $(this),
                    function() { click_dialog_button( $("#select-vo"), "OK" ) ; }
                ) ;
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
            add_flag_to_dialog_titlebar( $(this), get_player_no_for_element($sortable2) ) ;
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
                var usedIds = {};
                $sortable2.find( "li" ).each( function() {
                    usedIds[ $(this).data( "sortable2-data" ).id ] = true ;
                } ) ;
                var seq_id = auto_assign_id( usedIds, "seq_id" ) ;
                do_add_vo( vo_type, player_no, entries[sel_index], vo_image_id, null, seq_id ) ;
                $(this).dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function do_add_vo( vo_type, player_no, vo_entry, vo_image_id, custom_capabilities, seq_id )
{
    // add the specified vehicle/ordnance
    // NOTE: We set a fixed height for the sortable2 entries (based on the CSS settings in tabs-ob.css),
    // so that the vehicle/ordnance images won't get truncated if there are a lot of them.
    var nat = get_player_nat( player_no ) ;
    var $sortable2 = $( "#ob_" + vo_type + "-sortable_" + player_no ) ;
    var div_tag = "<div class='vo-entry" ;
    var fixed_height = "3.25em" ;
    if ( is_small_vasl_piece( vo_entry ) ) {
        div_tag += " small-piece" ;
        fixed_height = "2.25em" ;
    }
    div_tag += "'>" ;
    var data = {
        caption: vo_entry.name,
        vo_entry: vo_entry,
        vo_image_id: vo_image_id,
        fixed_height: fixed_height
    } ;
    if ( custom_capabilities )
        data.custom_capabilities = custom_capabilities ;
    data.id = seq_id ;
    var buf = [ div_tag,
        "<img class='vasl-image'>",
        "<div class='detail'>",
            "<div class='vo-name'></div>",
            "<div class='vo-capabilities'></div>",
        "</div>"
    ] ;
    var vo_note_key = get_vo_note_key( vo_entry ) ;
    var vo_nat ;
    if ( is_known_vo_note_key( vo_type, nat, vo_note_key ) )
        vo_nat = nat ;
    else {
        // NOTE: Note numbers seem to be distinct across all Allied Minor or all Axis Minor vehicles/ordnance,
        // so if we don't find a note in a given nationality's normal vehicles/ordnance, we can get away with
        // just checking their corresponding common vehicles/ordnance.
        var nat_type = gTemplatePack.nationalities[ nat ].type ;
        if ( ["allied-minor","axis-minor"].indexOf( nat_type ) !== -1 ) {
            if ( is_known_vo_note_key( vo_type, nat_type, vo_note_key ) )
                vo_nat = nat_type ;
        }
    }
    if ( vo_nat ) {
        var template_id = (vo_type === "vehicles") ? "ob_vehicle_note" : "ob_ordnance_note" ;
        buf.push(
            "<img src='" + gImagesBaseUrl + "/snippet.png'",
            " class='snippet' data-id='" + template_id + "' title='Generate a snippet.'>"
        ) ;
        data.vo_note_url = APP_URL_BASE + "/" + vo_type + "/" + vo_nat + "/note/" + vo_note_key ;
    }
    buf.push( "</div>" ) ;
    var $content = $( buf.join("") ) ;
    var $entry = $sortable2.sortable2( "add", {
        content: $content,
        data: data,
    } ) ;
    update_vo_sortable2_entry( $entry ) ;

    // add a handler for the snippet button
    $content.children("img.snippet").click( function() {
        generate_snippet( $(this), {} ) ;
    } ) ;
}

function update_vo_sortable2_entry( $entry, snippet_params )
{
    // initialize
    if ( ! snippet_params )
        snippet_params = unload_snippet_params( true, null ) ;
    var vo_entry = $entry.data( "sortable2-data" ).vo_entry ;
    var vo_image_id = $entry.data( "sortable2-data" ).vo_image_id ;
    var capabilities = $entry.data( "sortable2-data" ).custom_capabilities ;
    if ( capabilities )
        capabilities = capabilities.slice() ;
    else {
        var player_no = get_player_no_for_element( $entry ) ;
        capabilities = make_capabilities(
            false,
            vo_entry,
            snippet_params[ "PLAYER_"+player_no ],
            snippet_params.SCENARIO_THEATER, snippet_params.SCENARIO_YEAR, snippet_params.SCENARIO_MONTH,
            false
        ) ;
    }

    // update the vehicle/ordnance's sortable2 entry
    var url = get_vo_image_url( vo_entry, vo_image_id, true ) ;
    var $content = $entry.children( ".vo-entry" ) ;
    $content.find( "img.vasl-image" ).attr( "src", url ) ;
    $content.find( "div.vo-name" ).html( vo_entry.name ) ;
    for ( var i=0 ; i < capabilities.length ; ++i )
        capabilities[i] = "<span class='vo-capability'>" + capabilities[i] + "</span>" ;
    $content.find( "div.vo-capabilities" ).html( capabilities.join("") ) ;
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

function on_select_vo_image( $btn, on_ok ) {

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
                .attr( "src", get_vo_image_url( null, vo_images[i], true ) ) ;
            $images.append( $elem ) ;
        }

        // highlight the currently-selected image
        var sel_index = _find_vo_image_id( vo_images, vo_image_id ) ;
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
            $img.attr( "src", get_vo_image_url(null,vo_image_id,true) ) ;
            $img.data( "vo-image-id", vo_image_id ) ;
            $dlg.dialog( "close" ) ;
            if ( on_ok )
                on_ok() ;
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

function _find_vo_image_id( vo_images, vo_image_id )
{
    // find the specified V/O image ID (because indexOf() doesn't handle arrays :-/)
    if ( vo_image_id === null )
        return 0 ;
    vo_image_id = vo_image_id.join( ":" ) ;
    for ( var i=0 ; i < vo_images.length ; ++i ) {
        if ( vo_images[i].join( ":" ) === vo_image_id )
            return i ;
    }
    return -1 ;
}

function get_vo_image_url( vo_entry, vo_image_id, allow_missing_image )
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
    return allow_missing_image ? gImagesBaseUrl + "/missing-image.png" : null ;
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
