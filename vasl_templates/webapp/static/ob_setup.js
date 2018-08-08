
// --------------------------------------------------------------------

function add_ob_setup( player_id )
{
    // add a new OB setup
    edit_ob_setup( $("#ob_setup-sortable_"+player_id), null ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function edit_ob_setup( $sortable, $entry )
{
    var $caption, $width ;

    // let the user edit the OB setup
    $("#edit-ob_setup").dialog( {
        dialogClass: "edit-ob_setup",
        modal: true,
        minWidth: 400,
        minHeight: 150,
        open: function() {
            $caption = $(this).children( "textarea" ) ;
            $width = $(this).children( "input[type='text']" ) ;
            if ( $entry ) {
                var data = $entry.data( "sortable-data" ) ;
                $caption.val( data.caption ) ;
                $width.val( data.width ) ;
            }
            else {
                $caption.val( "" ) ;
                $width.val( "" ) ;
            }
            $(this).height( $(this).height() ) ; // fudge: force the textarea to resize
        },
        buttons: {
            OK: function() {
                var caption = $caption.val().trim() ;
                var width = $width.val().trim() ;
                if ( $entry ) {
                    // update the existing OB setup
                    if ( caption === "" )
                        delete_sortable_entry( $entry ) ;
                    else {
                        $entry.data("sortable-data").caption = caption ;
                        $entry.data("sortable-data").width = width ;
                        $entry.empty().append( _make_sortable_entry( caption ) ) ;
                    }
                }
                else {
                    // create a new OB setup
                    if ( caption !== "" ) {
                        data = { caption: caption, width: width } ;
                        do_add_ob_setup( $sortable, data ) ;
                    }
                }
                $(this).dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function do_add_ob_setup( $sortable, data )
{
    // add a new sortable entry
    add_sortable( $sortable, _make_sortable_entry(data.caption), data ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function _make_sortable_entry( caption )
{
    // generate the sortable entry
    var $content = $( "<div><input type='button' data-id='ob_setup' value='Snippet'>" + caption + "</div>" ) ;

    // add a handler for the snippet button
    $content.children("input[type='button']").click( function() {
        var data = $(this).parent().parent().data( "sortable-data" ) ;
        var extra_params = { OB_SETUP: data.caption, OB_SETUP_WIDTH: data.width } ;
        generate_snippet( $(this), extra_params ) ;
    } ) ;

    return $content ;
}
