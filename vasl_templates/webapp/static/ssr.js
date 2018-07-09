
// --------------------------------------------------------------------

function add_ssr()
{
    // add a new SSR
    edit_ssr( null ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function edit_ssr( $elem )
{
    // let the user edit a SSR's content
    $("#edit-ssr textarea").val( $elem ? $elem.text() : "" ) ;
    $("#edit-ssr").dialog( {
        dialogClass: "edit-ssr",
        modal: true,
        minWidth: 400,
        minHeight: 150,
        open: function() {
            $(this).height( $(this).height() ) ; // fudge: force the textarea to resize
        },
        buttons: {
            OK: function() {
                var val = $("#edit-ssr textarea").val().trim() ;
                if ( $elem ) {
                    // update the existing SSR
                    if ( val !== "" )
                        $elem.text( val ) ;
                    else
                        delete_ssr( $elem ) ;
                }
                else {
                    // create a new SSR
                    if ( val !== "" ) {
                        var $new_ssr = $( "<li></li>" ) ;
                        $new_ssr.text( val ) ;
                        $("#ssr-sortable").append( $new_ssr ) ;
                        init_ssr( $new_ssr ) ;
                    }
                }
                update_ssr_hint() ;
                $(this).dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function delete_ssr( $elem )
{
    // delete the SSR
    $elem.addClass( "highlighted" ) ;
    ask( "Delete this SSR?", escapeHTML($elem.text()), {
        "ok": function() { $elem.remove() ; update_ssr_hint() ; },
        "close": function() { $elem.removeClass("highlighted") ; },
    } ) ;
}

// --------------------------------------------------------------------

function init_ssr( $elem )
{
    // initialize SSR element(s)
    $elem.dblclick( function() {
        edit_ssr( $(this) ) ;
    } ) ;
    $elem.click( function( evt ) {
        if ( evt.ctrlKey )
            delete_ssr( $(this) ) ;
    } ) ;
}

function update_ssr_hint()
{
    // show/hide the SSR hint
    if ( $("#ssr-sortable li").length === 0 ) {
        $("#ssr-sortable").hide() ;
        $("#ssr-hint").show() ;
    } else {
        $("#ssr-sortable").show() ;
        $("#ssr-hint").hide() ;
    }
}
