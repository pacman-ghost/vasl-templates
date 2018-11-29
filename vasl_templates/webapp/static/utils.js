
// --------------------------------------------------------------------

function get_nationality_display_name( nat_id )
{
    // get the nationality's display name
    return gTemplatePack.nationalities[ nat_id ].display_name ;
}

function get_player_nat( player_no )
{
    // get the player's nationality
    if ( player_no === null )
        return null ;
    return $( "select[name='PLAYER_" + player_no + "']" ).val() ;
}

function get_player_colors( player_no )
{
    // get the colors for the specified player
    var player_nat = get_player_nat( player_no ) ;
    return gTemplatePack.nationalities[ player_nat ].ob_colors ;
}

function get_player_colors_for_element( $elem )
{
    // get the player colors (if any) for the specified element
    var player_no = get_player_no_for_element(  $elem ) ;
    if ( player_no === null )
        return null ;
    return get_player_colors( player_no ) ;
}

function make_player_flag_url( player_nat ) {
    return APP_URL_BASE + "/flags/" + player_nat ;
}

function get_player_no_for_element( $elem )
{
    // get the player that owns the specified element
    if ( $.contains( $("#tabs-ob1")[0], $elem[0] ) )
        return 1 ;
    if ( $.contains( $("#tabs-ob2")[0], $elem[0] ) )
        return 2 ;
    return null ;
}

function get_scenario_date()
{
    // get the scenario date
    var scenario_date = $("input[name='SCENARIO_DATE']").datepicker( "getDate" ) ;
    if ( ! scenario_date )
        return null ;
    scenario_date.setMinutes( scenario_date.getMinutes() - scenario_date.getTimezoneOffset() ) ;
    return scenario_date ;
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

function init_dialog( $dlg, ok_button_text, auto_dismiss )
{
    // initialize the dialog
    $dlg.data( "ok-button-text", ok_button_text ) ;

    // allow Ctrl-Enter to dismiss the dialog
    if ( auto_dismiss ) {
        $dlg.find("input[type='text']").keydown( function(evt) {
            auto_dismiss_dialog( $dlg, evt, ok_button_text ) ;
        } ) ;
        $dlg.find("textarea").keydown( function(evt) {
            auto_dismiss_dialog( $dlg, evt, ok_button_text ) ;
        } ) ;
    }
}

function on_dialog_open( $dlg )
{
    // initialize the dialog
    var ok_button_text = $dlg.data( "ok-button-text" ) ;
    $( ".ui-dialog-buttonpane button:contains(" + ok_button_text + ")" ).addClass( "ok" ) ;
    $( ".ui-dialog-buttonpane button:contains(Cancel)" ).addClass( "cancel" ) ;

    // set initial focus
    var $cancel = $( ".ui-dialog-buttonpane button:contains(Cancel)" ) ;
    $cancel.focus() ;
}

function auto_dismiss_dialog( $dlg, evt, btn_text )
{
    // check if the user pressed Ctrl-Enter
    if ( evt.keyCode == 13 && evt.ctrlKey ) {
        // yup - locate the target button and click it
        click_dialog_button( $dlg, btn_text ) ;
        evt.preventDefault() ;
    }
}

function click_dialog_button( $dlg, btn_text )
{
    // locate the target button and click it
    var $dlg2 = $( ".ui-dialog." + $dlg.dialog("option","dialogClass") ) ;
    $( $dlg2.find( ".ui-dialog-buttonpane button:contains('" + btn_text + "')" ) ).click() ;
}

// --------------------------------------------------------------------

function ask( title, msg, args )
{
    // ask a question
    var $dlg = $("#ask") ;
    $dlg.html( msg ) ;
    $dlg.dialog( {
        dialogClass: "ask",
        modal: true,
        closeOnEscape:false,
        title: title,
        create: function() {
            init_dialog( $(this), "OK", false ) ;
            // we handle ESCAPE ourself, to make it the same as clicking Cancel, not just closing the dialog
            $(this).closest( ".ui-dialog" ).keydown( function( evt ) {
                if ( evt.keyCode == $.ui.keyCode.ESCAPE )
                    $(".ui-dialog.ask button:contains(Cancel)").click() ;
            } ) ;
        },
        open: function() {
            on_dialog_open( $(this) ) ;
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
        duration: (msg_type == "warning") ? 15*1000 : 5*1000,
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

function init_select2( $sel, width, search_box, format )
{
    // initialize the select2 droplist
    var name = $sel.attr( "name" ) ;
    args = { width: width, height: "22px" } ;
    if ( ! search_box )
        args.minimumResultsForSearch = Infinity ; // nb: this disables the search box :-/
    if ( format ) {
        args.templateResult = format ;
        args.templateSelection = format ;
    }
    $sel = $sel.select2( args ) ;
    $sel.data( "select2" ).$container.attr( "name", name ) ;
    $sel.addClass( "app-select2" ) ;

    return $sel ;
}

function restrict_droplist_height( $sel )
{
    // restrict the select2's droplist height to the available space
    // NOTE: The user can circumvent this by resizing the window after opening
    // the droplist, but we can live with that... :-/

    // figure out how much space is available
    var $droplist = $sel.data( "select2" ).$dropdown ;
    var avail = $(window).height() - $droplist.offset().top - 5 ;

    // set the max-height for the droplist
    var $results = $sel.data( "select2" ).$results ;
    $results.css( "max-height", Math.floor(avail)+"px" ) ;
}

// --------------------------------------------------------------------

function add_flag_to_dialog_titlebar( $dlg, player_no )
{
    // add a flag to the dialog's titlebar
    var player_nat = get_player_nat( player_no ) ;
    if ( ! player_nat )
        return ;
    var $titlebar = $dlg.dialog( "instance" ).uiDialogTitlebar ;
    var url = gImagesBaseUrl + "/flags/" + player_nat + ".png" ;
    $titlebar.find( ".ui-dialog-title" ).prepend(
        $( "<img src='" + url + "' class='flag'>" )
    ).css( { display: "flex", "align-items": "center" } ) ;
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
