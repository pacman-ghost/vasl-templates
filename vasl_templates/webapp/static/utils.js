
function get_player_colors( player_no )
{
    // get the colors for the specified player
    var player_nat = $( "select[name='PLAYER_" + player_no + "']" ).val() ;
    return gTemplatePack.nationalities[ player_nat ].ob_colors ;
}

function get_player_colors_for_element( $elem )
{
    // get the player colors (if any) for the specified element
    if ( $.contains( $("#tabs-ob1")[0], $elem[0] ) )
        return get_player_colors( 1 ) ;
    else if ( $.contains( $("#tabs-ob2")[0], $elem[0] ) )
        return get_player_colors( 2 ) ;
    return null ;
}

// --------------------------------------------------------------------

function copyToClipboard( val )
{
    if ( getUrlParam( "store_clipboard" ) ) {
        // store the value where the tests can retrieve it
        $("#_clipboard_").text( val ) ;
        return ;
    }

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
( function( $ ) {
$.fn.filterByText = function( $textbox )
{
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
} ) ( jQuery ) ;

// --------------------------------------------------------------------

function enable_ctrl_enter( $dlg, btn_text )
{
    // allow Ctrl-Enter to dismiss a dialog
    $dlg.find("textarea").keydown( function(evt) {
        auto_dismiss_dialog( evt, btn_text ) ;
    } ) ;
}

function auto_dismiss_dialog( evt, btn_text )
{
    // check if the user pressed Ctrl-Enter
    if ( evt.keyCode == 13 && evt.ctrlKey ) {
        // yup - locate the target button and click it
        $( ".ui-dialog-buttonpane button:contains('"+btn_text+"')" ).click() ;
        evt.preventDefault() ;
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
        open: function() {
            $(".ui-dialog button:contains(Cancel)").focus();
        },
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

function showInfoMsg( msg ) { doShowNotificationMsg( "info", msg ) ; }
function showWarningMsg( msg ) { doShowNotificationMsg( "warning", msg ) ; }
function showErrorMsg( msg ) { doShowNotificationMsg( "error", msg ) ; }

function doShowNotificationMsg( msg_type, msg )
{
    if ( getUrlParam( "store_msgs" ) ) {
        // store the message for the test suite
        $( "#_last-" + msg_type + "_" ).val( msg ) ;
        return ;
    }

    // show the notification message
    $.growl( {
        style: (msg_type === "info") ? "notice" : msg_type,
        title: null,
        message: msg,
        location: "br",
        fixed: (msg_type == "error"),
    } ) ;
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

// --------------------------------------------------------------------

( function( scope ) {
    // create a new stylesheet to hold our CSS rules
    var style = document.createElement( "style" ) ;
    document.head.appendChild( style ) ;
    var stylesheet = style.sheet ;
    scope.dynamic_css = function( sel, prop, val ) {
        // add the rule
        try {
            stylesheet.insertRule(
                sel + " {" + prop + ":" + val + "}",
                stylesheet.cssRules.length
            ) ;
        } catch( ex ) {
            console.log( "Couldn't add CSS style:", sel, prop, val ) ;
        }
    } ;
} ) ( window ) ;
