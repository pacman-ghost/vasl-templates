
// --------------------------------------------------------------------

function make_app_url( url, for_snippet )
{
    // generate a URL that accesses this webapp
    var base_url = window.location.origin ;
    if ( for_snippet && gAppConfig.ALTERNATE_WEBAPP_BASE_URL )
        base_url = gAppConfig.ALTERNATE_WEBAPP_BASE_URL ;
    return base_url + url ;
}

function get_nationality_display_name( nat_id )
{
    // get the nationality's display name
    if ( ! gTemplatePack.nationalities || ! gTemplatePack.nationalities[nat_id] )
        return null ;
    return gTemplatePack.nationalities[ nat_id ].display_name ;
}

function get_player_nat( player_no )
{
    // get the player's nationality
    if ( player_no === null )
        return null ;
    return $( "select[name='PLAYER_" + player_no + "']" ).val() ;
}

function get_sorted_nats()
{
    // sort the nationalities by display name
    var nats = Object.keys( gTemplatePack.nationalities ) ;
    nats.sort( function( lhs, rhs ) {
        lhs = gTemplatePack.nationalities[lhs].display_name.toUpperCase() ;
        rhs = gTemplatePack.nationalities[rhs].display_name.toUpperCase() ;
        if ( lhs < rhs )
            return -1 ;
        else if ( lhs > rhs )
            return +1 ;
        else
            return 0 ;
    } ) ;
    return nats ;
}

function get_player_colors( player_no )
{
    // get the colors for the specified player
    // NOTE: The returned color array holds the following values:
    //   [ background, hover background, border ]
    var player_nat = get_player_nat( player_no ) ;
    return gTemplatePack.nationalities[ player_nat ].ob_colors ;
}

function get_player_colors_for_element( $elem )
{
    // get the player colors (if any) for the specified element
    if ( $elem.attr( "id" ).substr( 0, 18 ) === "ob_notes-sortable_" )
        return null ;
    var player_no = get_player_no_for_element(  $elem ) ;
    if ( player_no === null )
        return null ;
    return get_player_colors( player_no ) ;
}

function make_player_flag_url( nat, for_snippet, force_local_image ) {
    if ( ! gTemplatePack.nationalities )
        return null ;
    if ( for_snippet && gUserSettings["scenario-images-source"] == SCENARIO_IMAGES_SOURCE_INTERNET && !force_local_image )
        return gAppConfig.ONLINE_IMAGES_URL_BASE + "/flags/" + nat + ".png" ;
    else {
        var url = "/flags/" + nat ;
        return make_app_url( url, for_snippet ) ;
    }
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
    // NOTE: Returning a Javascript Date object creates massive headaches since it is adjusted
    // for the current timezone, so we avoid problems by extracting the date fields here, and
    // discarding the time fields.
    var date=scenario_date.getDate(), month=1+scenario_date.getMonth(), year=scenario_date.getFullYear() ;
    return [
        date, month, year,
        year + "-" + pad(month,2,"0") + "-" + pad(date,2,"0"),
        date + " " + get_month_name(month) + ", " + year
    ] ;
}

function is_template_available( template_id )
{
    // check if the specified template is available
    if ( template_id.match( /^ob_(vehicles|ordnance).*_[12]$/ ) )
        template_id = template_id.substring( 0, template_id.length-2 ) ;
    else if ( template_id === "nat_caps_1" || template_id === "nat_caps_2" )
        template_id = "nat_caps" ;
    return gTemplatePack.templates[ template_id ] !== undefined ;
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

    // FUDGE! If a dialog is open, the overlay will stop the copy command from working,
    // so we attach the <textarea> to the dialog instead. Setting the z-index to something
    // large is also supposed to work, but apparently not... :-/
    var $topmost = findTopmostDialog() ;
    var target = $topmost ? $topmost[0] : document.body ;

    if ( document.queryCommandSupported && document.queryCommandSupported("copy") ) {
        // create a textarea to hold the content
        var textarea = document.createElement( "textarea" ) ;
        textarea.style.position = "fixed" ; // prevent scrolling to bottom in MS Edge
        target.appendChild( textarea ) ;
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
            target.removeChild( textarea ) ;
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
        $dlg.find( "input[type='text']" ).keydown( function(evt) {
            auto_dismiss_dialog( $dlg, evt, ok_button_text ) ;
        } ) ;
        $dlg.find( "input[type='checkbox']" ).keydown( function(evt) {
            auto_dismiss_dialog( $dlg, evt, ok_button_text ) ;
        } ) ;
        $dlg.find( "select" ).keydown( function(evt) {
            auto_dismiss_dialog( $dlg, evt, ok_button_text ) ;
        } ) ;
        $dlg.find( "textarea" ).keydown( function(evt) {
            auto_dismiss_dialog( $dlg, evt, ok_button_text ) ;
        } ) ;
    }
}

function on_dialog_open( $dlg, $focus )
{
    // initialize the dialog
    var ok_button_text = $dlg.data( "ok-button-text" ) ;
    $( ".ui-dialog-buttonpane button:contains(" + ok_button_text + ")" ).addClass( "ok" ) ;
    $( ".ui-dialog-buttonpane button:contains(Cancel)" ).addClass( "cancel" ) ;

    // set initial focus
    if ( ! $focus )
        $focus = $( ".ui-dialog-buttonpane button:contains(Cancel)" ) ;
    setTimeout( function() {
        $focus.focus() ;
    }, 20 ) ;
}

function auto_dismiss_dialog( $dlg, evt, btn_text )
{
    // check if the user pressed Ctrl-Enter
    if ( evt.keyCode == $.ui.keyCode.ENTER && evt.ctrlKey ) {
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
    // initialize
    var $dlg = $( "#ask" ) ;
    buttons = {} ;
    var ok_caption = args.ok_caption || "OK" ;
    buttons[ ok_caption ] = function() {
        $dlg.dialog( "close" ) ;
        if ( "ok" in args )
            args.ok() ;
    } ;
    buttons.Cancel = function() {
        $dlg.dialog( "close" ) ;
        if ( "cancel" in args )
            args.cancel() ;
    } ;

    // ask a question
    $dlg.html( msg ).dialog( {
        dialogClass: "ask",
        modal: true,
        closeOnEscape: false, // nb: handle_escape() has a special case for this dialog
        title: title,
        width: args.width || 400,
        minWidth: 250,
        maxHeight: window.innerHeight,
        buttons: buttons,
        create: function() {
            init_dialog( $(this), "OK", false ) ;
            // we handle ESCAPE ourself, to make it the same as clicking Cancel, not just closing the dialog
            $(this).closest( ".ui-dialog" ).keydown( function( evt ) {
                if ( evt.keyCode == $.ui.keyCode.ESCAPE ) {
                    $(".ui-dialog.ask button:contains(Cancel)").click() ;
                    stopEvent( evt ) ;
                }
            } ) ;
        },
        open: function() {
            $(this).data( "ok-button-text", ok_caption ) ;
            on_dialog_open( $(this) ) ;
        },
        close: function() {
            if ( "close" in args )
                args.close() ;
        },
    } ) ;
}

function showMsgDialog( title, msg, width )
{
    // show the message in a dialog
    $( "#ask" ).dialog( {
        dialogClass: "ask",
        modal: true,
        title: title,
        width: width, minWidth: 250,
        open: function() {
            $(this).html( msg ) ;
        },
        buttons: {
            OK: function() {
                $(this).dialog( "close" ) ;
            },
        },
    } ) ;
}

function showPleaseWaitDialog( msg, args )
{
    if ( ! args )
        args = {} ;

    // show the "please wait" dialog
    var $dlg = $( "#please-wait" ) ;
    $dlg.find( ".message .content" ).text( msg ) ;
    return $( "#please-wait" ).dialog( {
        dialogClass: "please-wait",
        modal: true,
        closeOnEscape: false, // nb: handle_escape() has a special case to ignore this dialog
        width: args.width || 300,
        height: args.height || 60,
        resizable: false,
        open: function() {
            if ( args.height )
                $(this).find( ".message" ).css( "justify-content", "flex-start" ) ;
        },
    } ) ;
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
    if ( ! player_nat || ! gHasPlayerFlag[ player_nat ] )
        return ;
    var $titlebar = $dlg.dialog( "instance" ).uiDialogTitlebar ;
    var url = make_player_flag_url( player_nat, false ) ;
    $titlebar.find( ".ui-dialog-title" ).prepend(
        $( "<img src='" + url + "' class='flag'>" )
    ).css( { display: "flex", "align-items": "center" } ) ;
}

function addSplitterGripper( $gutter, horz, gutterSize, gutterStyle )
{
    // add a gripper image to a splitter
    var key = (horz ? "h" : "v") + "splitter-gripper" ;
    var $gripper = $(
        "<img src='" + gImagesBaseUrl+"/"+key+".png" + "' class='"+key+"'>"
    ) ;
    $gutter.append( $gripper ) ;
    if ( horz ) {
        $gutter.css( "min-width", gutterSize ) ;
        var gripperLeft = - Math.floor( (8 - gutterSize) / 2 ) ;
        $gripper.css( "left", gripperLeft ) ;
    } else {
        $gutter.css( { "min-height": gutterSize } ) ;
         var gripperTop = - Math.floor( (8 - gutterSize) / 2 ) ;
        $gripper.css( { "top": gripperTop } ) ;
    }
    if ( gutterStyle )
        $gutter.css( gutterStyle ) ;
}

function makeSnippetHotHover( $sel )
{
    $sel.hover(
        function() { $(this).attr( "src", gImagesBaseUrl + "/snippet-hot.png" ) ; },
        function() { $(this).attr( "src", gImagesBaseUrl + "/snippet.png" ) ; }
    ) ;
}

// --------------------------------------------------------------------

var _MONTH_NAMES = [ // nb: we assume English :-/
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
] ;
var _DAY_OF_MONTH_POSTFIXES = { // nb: we assume English :-/
    0: "th",
    1: "st", 2: "nd", 3: "rd", 4: "th", 5: "th", 6: "th", 7: "th", 8: "th", 9: "th", 10: "th",
    11: "th", 12: "th", 13: "th"
} ;

function make_formatted_day_of_month( dom )
{
    // generate the formatted day of month
    if ( dom in _DAY_OF_MONTH_POSTFIXES )
        return dom + _DAY_OF_MONTH_POSTFIXES[ dom ] ;
    else
        return dom + _DAY_OF_MONTH_POSTFIXES[ dom % 10 ] ;
}

function get_month_name( month )
{
    // get the name of the month
    return _MONTH_NAMES[ month-1 ] ;
}

// --------------------------------------------------------------------

function fixup_external_links( $root, fixAll )
{
    // NOTE: We want to open externals links in a new browser window, but simply adding target="_blank"
    // breaks the desktop app's ability to intercept clicks (in AppWebPage.acceptNavigationRequest()),
    // so we do it dynamically here.
    var regex = new RegExp(  "^https?://" ) ;
    $root.find( "a" ).each( function() {
        var url = $(this).attr( "href" ) ;
        if ( fixAll || ( url && url.match( regex ) ) )
            $(this).attr( "target", gWebChannelHandler?"":"_blank" ) ;
    } ) ;
}

function wrapExcWithSpan( val )
{
    // wrap an EXC block with a <span>
    var excRegex = new RegExp( /\[EXC: .*?\]/g ) ;
    return wrapSubstrings( val, excRegex, "<span class='exc'>", "</span>" ) ;
}

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

function addUrlParam( url, param, val )
{
    // add a parameter to a URL
    var sep =  url.indexOf( "?" ) === -1 ? "?" : "&" ;
    return url + "?" + param + "=" + encodeURIComponent(val) ;
}

function toUTF8( val )
{
    // convert the value to UTF-8 (nb: returns a Uint8Array)
    return (new TextEncoder()).encode( val ) ;
}

function escapeHTML( val ) { return new Option(val).innerHTML ; }
function trimString( val ) { return val ? val.trim() : val ; }
function fpFmt( val, nDigits ) { return val.toFixed( nDigits ) ; }

function pad( val, len, ch )
{
    // left-pad the value
    val = val.toString() ;
    while( val.length < len )
        val = ch + val ;
    return val ;
}

function pluralString( n, str1, str2, combine )
{
    var val = (n == 1) ? str1 : str2 ;
    return combine ? n + " " + val : val ;
}

function percentString( val )
{
    val = Math.round( val ) ;
    if ( val < 0 )
        val = 0 ;
    else if ( val > 100 )
        val = 100 ;
    return val + "%" ;
}

function strReplaceAll( val, searchFor, replaceWith )
{
    // str.replace() only replaces a single instance!?!? :wtf:
    if ( ! searchFor )
        return val ;
    var pos = 0 ;
    for ( ; ; ) {
        pos = val.indexOf( searchFor, pos ) ;
        if ( pos === -1 )
            return val ;
        val = val.substr(0,pos) + replaceWith + val.substr(pos+searchFor.length) ;
        pos += replaceWith.length ;
    }
}

function findDelimitedSubstring( val, delim1, delim2 )
{
    // search for a substring delimited by the 2 specified markers
    if ( val === null || val === undefined )
        return null ;
    var pos = val.indexOf( delim1 ) ;
    if ( pos === -1 )
        return val ;
    var pos2 = val.indexOf( delim2, pos ) ;
    if ( pos2 === -1 )
        return val ;
    // found it - return the prefix/middle/postfix parts
    return [
        val.substring( 0, pos ),
        val.substring( pos+delim1.length, pos2 ),
        val.substring( pos2+delim2.length )
    ] ;
}

function wrapSubstrings( val, searchFor, delim1, delim2 )
{
    // search for a substring and wrap it with the specified delimeters
    if ( val === null || val === undefined )
        return null ;
    // FUDGE! matchAll() isn't available in the PyQt embedded browser :-/
    var matches = [] ;
    while ( ( match = searchFor.exec( val ) ) !== null )
        matches.push( match ) ;
    for ( var i=matches.length-1 ; i >= 0 ; --i ) {
        val = val.substring( 0, matches[i].index ) +
              delim1 + matches[i][0] + delim2 +
              val.substring( matches[i].index + matches[i][0].length ) ;
    }
    return val ;
}

function getFilenameExtn( fname )
{
    // get the filename extension
    var pos = fname.lastIndexOf( "." ) ;
    if ( pos !== -1 )
        return fname.substr( pos ) ;
    else
        return null ;
}

function removeBase64Prefix( val )
{
    // remove the base64 prefix from the start of the string
    // - data: MIME-TYPE ; base64 , ...
    return val.replace( /^data:.*?;base64,/, "" ) ;
}

function stopEvent( evt )
{
    // stop further processing for the event
    evt.preventDefault() ;
    evt.stopPropagation() ;
}

function makeBlob( data, mimeType )
{
    // create a Blob from a binary string
    var bytes ;
    if ( typeof data === "object" )
        bytes = data ; // i.e. output from TextEncoder.encode()
    else if ( typeof data === "string" ) {
        bytes = new Uint8Array( data.length ) ;
        for ( var i=0 ; i < data.length ; ++i )
            bytes[i] = data.charCodeAt( i ) ;
    } else
        return null ;
    return new Blob( [bytes], {
        type: mimeType || "application/octet-stream"
    } ) ;
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

isKeyDown = ( function( key ) {
    var keyState = {} ;
    window.addEventListener( "keyup", function(e) { keyState[e.key] = false ; } ) ;
    window.addEventListener( "keydown", function(e) { keyState[e.key] = true ; } ) ;
    return function( key ) { return keyState.hasOwnProperty(key) && keyState[key] || false ; } ;
} )() ;

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
