
// --------------------------------------------------------------------

function add_vo( vo_type, player_no )
{
    // load the available vehicles/ordnance
    var nat = $( "select[name='PLAYER_" + player_no + "']" ).val() ;
    var entries = gVehicleOrdnanceListings[vo_type][nat] ;
    if ( entries === undefined ) {
        showWarningMsg( "There are no " + get_nationality_display_name(nat) + " " + vo_type + " listings." ) ;
        return ;
    }
    var buf = [] ;
    for ( var i=0 ; i < entries.length ; ++i )
        buf.push( "<option value='" + i + "'>" + entries[i].name + "</option>" ) ;
    function format_vo_entry( opt ) {
        if ( ! opt.id )
            return opt.text ;
        var vo_entry = entries[opt.id] ;
        var div_class = "vo-entry" ;
        if ( is_small_vasl_piece( vo_entry ) )
            div_class += " small-piece" ;
        var buf2 = [ "<div class='" + div_class + "' data-index='" + opt.id + "'>",
            "<img src='" + get_vo_image_url(vo_entry,null,true,false) + "' class='vasl-image'>",
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
    var $sortable2 = $( "#ob_" + vo_type + "-sortable_" + player_no ) ;
    function on_resize( $dlg ) {
        $( ".select2-results ul" ).height( $dlg.height() - 50 ) ;
    }
    var $dlg = $("#select-vo").dialog( {
        title: "Add " + SORTABLE_DISPLAY_NAMES["ob_"+vo_type][0],
        dialogClass: "select-vo",
        modal: true,
        minWidth: 400,
        minHeight: 350,
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
                // get the selected vehicle/ordnance
                // FUDGE! $sel.select("data") returns the wrong thing if the entries are filtered?!?!
                var $elem = $( "#select-vo .select2-results__option--highlighted" ) ;
                if ( $elem.length === 0 )
                    return ;
                var sel_index = $elem.children( ".vo-entry" ).data( "index" ) ;
                var sel_entry = entries[ sel_index ] ;
                var usedVoIds=[], usedSeqIds={} ;
                $sortable2.find( "li" ).each( function() {
                    usedVoIds.push( $(this).data( "sortable2-data" ).vo_entry.id ) ;
                    usedSeqIds[ $(this).data( "sortable2-data" ).id ] = true ;
                } ) ;
                // check for duplicates
                function add_sel_entry() {
                    var $img = $elem.find( "img[class='vasl-image']" ) ;
                    var vo_image_id = $img.data( "vo-image-id" ) ;
                    var seq_id = auto_assign_id( usedSeqIds, "seq_id" ) ;
                    do_add_vo( vo_type, player_no, sel_entry, vo_image_id, false, null, null, seq_id ) ;
                    $dlg.dialog( "close" ) ;
                }
                if ( usedVoIds.indexOf( sel_entry.id ) !== -1 ) {
                    var vo_type2 = SORTABLE_DISPLAY_NAMES[ "ob_" + vo_type ][0] ;
                    ask( "Add "+vo_type2, "<p>This "+vo_type2+" is already in the OB<p>Do you want to add it again?", {
                        ok: add_sel_entry,
                    } ) ;
                    return ;
                }
                // add the new vehicle/ordnance
                add_sel_entry() ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function do_add_vo( vo_type, player_no, vo_entry, vo_image_id, elite, custom_capabilities, custom_comments, seq_id )
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
        elite: elite,
        fixed_height: fixed_height
    } ;
    if ( custom_capabilities )
        data.custom_capabilities = custom_capabilities ;
    if ( custom_comments )
        data.custom_comments = custom_comments ;
    data.id = seq_id ;
    var buf = [ div_tag,
        "<img class='vasl-image'>",
        "<div class='detail'>",
            "<div class='vo-name'></div>",
            "<div class='vo-capabilities'></div>",
        "</div>"
    ] ;
    var vo_note_key = get_vo_note_key( vo_entry ) ;
    var vo_note = get_vo_note( vo_type, nat, vo_note_key ) ;
    var vo_note_image_url = null ;
    if ( vo_note )
        vo_note_image_url = APP_URL_BASE + "/" + vo_type + "/" + nat + "/note/" + vo_note_key ;
    else {
        // NOTE: Note numbers seem to be distinct across all Allied Minor or all Axis Minor vehicles/ordnance,
        // so if we don't find a note in a given nationality's normal vehicles/ordnance, we can get away with
        // just checking their corresponding common vehicles/ordnance.
        var nat_type = gTemplatePack.nationalities[ nat ].type ;
        if ( ["allied-minor","axis-minor"].indexOf( nat_type ) !== -1 ) {
            vo_note = get_vo_note( vo_type, nat_type, vo_note_key ) ;
            if ( vo_note )
                vo_note_image_url = APP_URL_BASE + "/" + vo_type + "/" + nat_type + "/note/" + vo_note_key ;
        }
    }
    if ( vo_note ) {
        var template_id = (vo_type === "vehicles") ? "ob_vehicle_note" : "ob_ordnance_note" ;
        if ( is_template_available( template_id ) ) {
            buf.push(
                "<img src='" + gImagesBaseUrl + "/snippet.png'",
                " class='snippet' data-id='" + template_id + "' title='" + GENERATE_SNIPPET_HINT + "'>"
            ) ;
        }
        data.vo_note = vo_note ;
        data.vo_note_image_url = vo_note_image_url ;
    }
    buf.push( "</div>" ) ;
    var $content = $( buf.join("") ) ;
    var $entry = $sortable2.sortable2( "add", {
        content: $content,
        data: data,
    } ) ;
    update_vo_sortable2_entry( $entry ) ;

    // add a handler for the snippet button
    $content.children("img.snippet").click( function( evt ) {
        generate_snippet( $(this), evt, {} ) ;
        return false ;
    } ) ;
}

function update_vo_sortable2_entry( $entry, snippet_params )
{
    // initialize
    if ( ! snippet_params )
        snippet_params = unload_snippet_params( true, null ) ;
    var data = $entry.data( "sortable2-data" ) ;
    var vo_entry = data.vo_entry ;
    var vo_image_id = data.vo_image_id ;
    var capabilities = data.custom_capabilities ;
    if ( capabilities )
        capabilities = capabilities.slice() ;
    else {
        var player_no = get_player_no_for_element( $entry ) ;
        capabilities = make_capabilities(
            false,
            vo_entry,
            snippet_params[ "PLAYER_"+player_no ],
            data.elite,
            snippet_params.SCENARIO_THEATER, snippet_params.SCENARIO_YEAR, snippet_params.SCENARIO_MONTH,
            false
        ) ;
    }

    // update the vehicle/ordnance's sortable2 entry
    var url = get_vo_image_url( vo_entry, vo_image_id, true, false ) ;
    var $content = $entry.children( ".vo-entry" ) ;
    $content.find( "img.vasl-image" ).attr( "src", url ) ;
    var name = vo_entry.name ;
    if ( data.elite )
        name += " \u24ba" ;
    $content.find( "div.vo-name" ).html( name ) ;
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
                .attr( "src", get_vo_image_url( null, vo_images[i], true, false ) ) ;
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
            $img.attr( "src", get_vo_image_url(null,vo_image_id,true,false) ) ;
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

function get_vo_image_url( vo_entry, vo_image_id, allow_missing_image, for_snippet )
{
    // generate the image URL for the specified vehicle/ordnance
    var gpid, index=null ;
    if ( vo_image_id ) {
        gpid = vo_image_id[0] ;
        index = vo_image_id[1] ;
    } else {
        // no V/O image ID was provided, just use the first available image
        gpid = $.isArray( vo_entry.gpid ) ? vo_entry.gpid[0] : vo_entry.gpid ;
    }
    if ( gpid ) {
        if ( for_snippet && gUserSettings["use-online-images"] )
            return make_online_counter_image_url( gpid, index ) ;
        else
            return make_local_counter_image_url( gpid, index ) ;
    }

    // couldn't find an image
    if ( allow_missing_image ) {
        if ( for_snippet && gUserSettings["use-online-images"] )
            return gAppConfig.ONLINE_IMAGES_URL_BASE + "/missing-image.png" ;
        else
            return gImagesBaseUrl + "/missing-image.png" ;
    }
    return null ;
}

function make_local_counter_image_url( gpid, index )
{
    url = APP_URL_BASE + "/counter/" + gpid + "/front" ;
    if ( index !== null )
        url += "/" + index ;
    return url ;
}

function make_online_counter_image_url( gpid, index )
{
    // check if we have a piece from the core VASL module or an extension
    var url, extn_id ;
    var pos = gpid.toString().indexOf( ":" ) ;
    if ( pos === -1 )
        url = gAppConfig.ONLINE_COUNTER_IMAGES_URL_TEMPLATE ;
    else {
        url = gAppConfig.ONLINE_EXTN_COUNTER_IMAGES_URL_TEMPLATE ;
        extn_id = gpid.substr( 0, pos ) ;
    }

    // generate the URL
    url = strReplaceAll( url, "{{GPID}}", gpid ) ;
    if ( index === null )
        index = 0 ;
    url = strReplaceAll( url, "{{INDEX}}", index ) ;
    url = strReplaceAll( url, "{{PATH}}", gVaslPieceInfo[gpid].paths[index] ) ;
    if ( extn_id )
        url = strReplaceAll( url, "{{EXTN_ID}}", extn_id ) ;

    return url ;
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
