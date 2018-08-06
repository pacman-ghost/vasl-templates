
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
            showErrorMsg( "Can't copy to the clipboard:<div class='pre'>" + escapeHTML(ex) + "</div>" ) ;
        }
        finally {
            document.body.removeChild( textarea ) ;
        }
    }
}

// --------------------------------------------------------------------

// Connect a text box to a select box, and filter the available options.
jQuery.fn.filterByText = function( $textbox ) {

    function compressSpaces( val ) { return val.replace( /\s/g, "" ).trim() ; }

    return this.each( function() {

        // initialize
        var $select = $(this) ;
        var $options = [] ;
        $select.find( "option" ).each( function() {
            $options.push( { value: $(this).val(), text: $(this).text() } ) ;
        } ) ;
        $select.data( "options", $options ) ;

        $textbox.bind( "input", function() {
            // prepare the value we will filter on
            var val = $(this).val() ;
            var adjustCase ;
            if ( val !== val.toLowerCase() )
                adjustCase = function(val) { return val ; } ; // nb: mixed-case => case-sensitive filtering
            else
                adjustCase = function(val) { return val.toLowerCase() ; } ;
            val = compressSpaces( adjustCase( val ) ) ;
            // filter the options
            var $options = $select.empty().scrollTop(0).data( "options" ) ;
            $.each( $options, function(i) {
                var $opt = $options[i] ;
                var optVal = compressSpaces( adjustCase( $opt.text ) ) ;
                if ( optVal.indexOf( val ) !== -1 ) {
                    $select.append(
                        $("<option>").text( $opt.text ).val( $opt.value )
                    ) ;
                }
            } ) ;
            // auto-select if there's only one option
            if ( $select.children().length === 1 )
                $select.children().get(0).selected = true ;
        } ) ;
    } ) ;
} ;

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
        location: "br",
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
        location: "br",
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
        location: "br",
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

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function makeBulletListMsg( caption, items, li_class )
{
    // generate a message
    var buf = [] ;
    for ( i=0 ; i < items.length ; ++i ) {
        buf.push( "<li" ) ;
        if ( li_class )
            buf.push( " class='" + li_class + "'" ) ;
        buf.push( ">" ) ;
        buf.push( escapeHTML(items[i]) ) ;
        buf.push( "</li>" ) ;
    }
    return caption + "<ul>" + buf.join("") + "</ul>" ;
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

function pluralString( n, str1, str2 )
{
    return (n == 1) ? str1 : str2 ;
}

function isIE()
{
    // check if we're running in IE :-/
    if ( navigator.userAgent.indexOf("MSIE") !== -1 )
        return true ;
    if ( navigator.appVersion.indexOf("Trident/") !== -1 )
        return true ;
    return false ;
}
