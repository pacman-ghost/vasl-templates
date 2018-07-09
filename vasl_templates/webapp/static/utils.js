
// --------------------------------------------------------------------

function copyToClipboard( val )
{
    // IE-specific code path to prevent textarea being shown while dialog is visible
    if ( window.clipboardData && window.clipboardData.setData ) {
        clipboardData.setData( "Text", val ) ;
        return ;
    }

    if ( document.queryCommandSupported && document.queryCommandSupported("copy") ) {
        // create a textarea to hold the content
        var textarea = document.createElement( "textarea" ) ;
        textarea.style.position = "fixed" ; // prevent scrolling to bottom in MS Edge
        document.body.appendChild( textarea ) ;
        textarea.textContent = val ;
        // copy the textarea content to the clipboard
        textarea.select() ;
        try {
            document.execCommand( "copy" ) ;
            if ( getUrlParam("log-clipboard") )
                console.log( "CLIPBOARD:", val ) ;
        }
        catch( ex ) {
            showErrorMsg( "Can't copy to the clipboard:<pre>" + escapeHTML(ex) + "</pre>" ) ;
        }
        finally {
            document.body.removeChild( textarea ) ;
        }
    }
}

// --------------------------------------------------------------------

function ask( title, msg, args )
{
    // ask a question
    var $dlg = $("#ask") ;
    $dlg.html( msg ) ;
    $dlg.dialog( {
        modal: true,
        title: title,
        buttons: {
            OK: function() {
                $(this).dialog( "close" ) ;
                if ( "ok" in args )
                    args.ok() ;
            },
            Cancel: function() {
                $(this).dialog( "close" ) ;
                if ( "cancel" in args )
                    args.cancel() ;
            },
        },
        close: function() {
            if ( "close" in args )
                args.close() ;
        },
    } ) ;

    return false ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function showInfoMsg( msg )
{
    // show the informational message
    $.growl( {
        style: "notice",
        title: null,
        message: msg,
        location: "tr",
    } ) ;
    storeMsgForTestSuite( "_last-info_", msg ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function showWarningMsg( msg )
{
    // show the warning message
    $.growl( {
        style: "warning",
        title: null,
        message: msg,
        location: "tr",
    } ) ;
    storeMsgForTestSuite( "_last-warning_", msg ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function showErrorMsg( msg )
{
    // show the error message
    $.growl( {
        style: "error",
        title: null,
        message: msg,
        location: "tr",
        fixed: true,
    } ) ;
    storeMsgForTestSuite( "_last-error_", msg ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function storeMsgForTestSuite( id, msg )
{
    // store a message for the test suite
    if ( ! getUrlParam( "store_msgs" ) )
        return ;
    var $elem = $( "#"+id ) ;
    if ( $elem.length === 0 ) {
        // NOTE: The <div> we store the message in must be visible, otherwise
        // Selenium doesn't return any text for it :-/
        $elem = $( "<div id='" + id + "' style='z-index-999;'></div>" ) ;
        $("body").append( $elem ) ;
    }
    $elem.html( msg ) ;
}

// --------------------------------------------------------------------

function getUrlParam( param )
{
    // look for the specified URL parameter
    var url = window.location.search.substring( 1 ) ;
    var params = url.split( "&" ) ;
    for ( var i=0 ; i < params.length ; i++ ) {
        var keyval = params[i].split( "=" ) ;
        if ( keyval[0] == param )
            return keyval[1] ;
    }
}

function escapeHTML( val )
{
    // escape HTML
    return new Option(val).innerHTML ;
}
