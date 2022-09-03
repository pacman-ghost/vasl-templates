gEditHtmlTextboxDlgState = null ;

// --------------------------------------------------------------------

function initTrumbowyg( $ctrl, buttons, $parentDlg )
{
    // initialize
    var nats = get_sorted_nats().filter(
        function( nat ) { return gHasPlayerFlag[ nat ] ; }
    ) ;

    // initialize the Trumbowyg control
    // NOTE: Trumbowyg uses the <div> we supply as the WYSIWYG editor, and creates an associated <textarea>
    // for the raw HTML view (and another <div> for the button pane). Our code originally used textarea's
    // to manage snippet content, so while we could transfer the "name" attribute (and "param" class)
    // from the WYSIWYG control to the raw HTML textarea, it doesn't really help, since manipulating
    // the content in the <textarea> directly doesn't work, we need to use Trumbowyg's "html" API, and that
    // works from the WYSIWYG control.
    $ctrl.trumbowyg( {
        btnsDef: {
            format: {
                dropdown: gAppConfig.trumbowyg[ "format-options" ],
                title: "Formatting",
                ico: "p"
            },
            align: {
                dropdown: [ "justifyLeft", "justifyCenter", "justifyRight", "justifyFull" ],
                title: "Alignment",
                ico: "justifyLeft",
            },
            fontfamily: { hasIcon: true, ico: "foreColor" },
            specialChars: { hasIcon: false, text: "\u25b3", title: "Special characters" },
            table: { title: "Table" },
            fullscreen: { title: "Full screen" },
            // FUDGE! While we can provide custom icons, they have to be SVG, so we do it in the CSS :-/
            foreColor: { hasIcon: false, text: " ", title: "Text color" },
            backColor: { hasIcon: false, text: " ", title: "Background color" },
            removeformat: { hasIcon: false, text: "\u2a2f", title: "Remove formatting" },
            emoji: { hasIcon: false, text: " ", title: "Emoji" },
            // FUDGE! The indent and outdent icons are not quite the same,
            // so we re-use the outdent image and flip it using CSS :-/
            indent: { ico: "outdent" },
            outdent: { title: "Un-indent" },
        },
        btns: buttons,
        semantic: false,
        plugins: {
            specialchars: {
                symbolList: gAppConfig.trumbowyg[ "special-chars" ],
            },
            flags: {
                nationalities: nats,
                makeFlagHtml: function( nat, force_local_image ) {
                    return make_player_flag_url( nat, true, force_local_image ) ;
                },
            },
        },
        tagsToRemove: gAppConfig.trumbowyg[ "tag-blacklist" ],
    } ) ;
    var $parent = $ctrl.parent() ;
    var $btnPane = $parent.find( ".trumbowyg-button-pane" ) ;
    var $textarea = $parent.find( ".trumbowyg-textarea" ) ;

    // update the flags dropdown for the current players
    if ( $btnPane.find( ".trumbowyg-flags-button" ).length > 0 )
        updateTrumbowygFlagsDropdown( $ctrl ) ;

    // prepare for our jQuery event handlers
    var eventHandlers = $ctrl.data( "eventHandlers" ) ;
    if ( ! eventHandlers ) {
        eventHandlers = new jQueryHandlers() ;
        $ctrl.data( "eventHandlers", eventHandlers ) ;
    }

    // allow a hotkey to toggle the WYSIWYG editor
    // FUDGE! While we can create a custom button to manually toggle the control, it doesn't quite work :-/
    // Switching to HTML mode disables all buttons, including the "view HTML" button, and while we can
    // manually enable it, hotkeys don't seem to work when we're in HTML mode :-/ We hack around this by
    // adding a key handler and managing the whole process ourself. Sigh...
    function onKeyDown( evt ) {
        // check for Ctrl-M
        if ( evt.keyCode == 77 && evt.ctrlKey ) {
            $ctrl.trumbowyg( "toggle" ) ;
            setTimeout( function() {
                if ( $ctrl.parent().hasClass( "trumbowyg-editor-visible" ) )
                    $ctrl.focus() ;
                else
                    $ctrl.parent().find( ".trumbowyg-textarea" ).focus() ;
            }, 20 ) ;
            evt.preventDefault() ;
            return ;
        }
        // handle auto-dismiss if we are in a dialog
        if ( $parentDlg )
            auto_dismiss_dialog( $parentDlg, evt, "OK" ) ;
    }
    eventHandlers.addHandler( $ctrl, "keydown", onKeyDown ) ;
    eventHandlers.addHandler( $textarea, "keydown", onKeyDown ) ;
    // FUDGE! There should be spaces around the +, but this causes the tooltip to wrap on Windows :-/
    $btnPane.find( ".trumbowyg-viewHTML-button" ).attr( "title", "View HTML (Ctrl+M)" ) ;

    // handle resize events
    if ( ! $parent.data( "resizeObserver" ) ) {
        var resizeObserver = new ResizeObserver( function( entries ) {
            // FUDGE! Couldn't get Trumbowyg to sit nicely inside a flexbox, so we set the height dynamically :-/
            var height = "calc(100% - " + $btnPane.height() + "px)" ;
            $ctrl.css( { height: height } ) ;
            $textarea.css( { height: height } ) ;
            // limit the height of dropdown's
            if ( $parentDlg ) {
                $parent.find( ".trumbowyg-dropdown" ).css( {
                    "max-height": $ctrl.height() + 5
                } ) ;
            }
            // FUDGE! We also need to stop the HTML textboxes that are in a flexbox from expanding out
            // if they contain long words with no spaces. The layout still isn't quite right, but this
            // isn't something that will happen often, so we just live with it :-/
            // NOTE: Things work when the SCENARIO panel gets wider, but not when it narrows (because
            // the HTML textbox has expanded out, and doesn't want to narrow when the parent element
            // narrows, and so the panel doesn't narrow). We work-around this by checking the width
            // of the SCENARIO NOTES panel, which will always be the same width as the SCENARIO panel.
            var $panel = $( "fieldset[name='scenario_notes']" ) ;
            $( ".row" ).css( "max-width", $panel.width() ) ;
        } ) ;
        resizeObserver.observe( $parent[0] ) ;
        $parent.data( "resizeObserver", resizeObserver ) ;
    }
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function destroyTrumbowyg( $ctrl )
{
    // destroy the Trumbowyg control and clean up
    var eventHandlers = $ctrl.data( "eventHandlers" ) ;
    if ( eventHandlers ) {
        eventHandlers.cleanUp() ;
        $ctrl.removeData( "eventHandlers" ) ;
    }
    $ctrl.trumbowyg( "destroy" ) ;
}

// --------------------------------------------------------------------

function resetTrumbowyg( $ctrl )
{
    // reset the Trumbowyg control
    if ( $ctrl.parent().hasClass( "trumbowyg-fullscreen" ) )
        $ctrl.trumbowyg( "execCmd", { cmd: "fullscreen" } ) ;
    if ( $ctrl.parent().hasClass( "trumbowyg-editor-hidden" ) )
        $ctrl.trumbowyg( "toggle" ) ;
}

function unloadTrumbowyg( $ctrl, removeFirstPara )
{
    // unload the Trumbowyg control
    var val = $ctrl.trumbowyg( "html" ).trim() ;

    // FUDGE! Trumbowyg really wants to wrap everything in <p> blocks, but this causes problems
    // since many of the templates are expecting a bit of plain old text, not blocks of content
    // e.g. OB setup notes start with a flag, and putting the content in a <p> block breaks
    // the layout. We hack around this by removing the *first* <p> block.
    if ( removeFirstPara ) {
        var match = val.match( /<p>.*?<\/p>/s ) ; //jshint ignore:line
        if ( match ) {
            var pos = match.index + match[0].length ; // nb: index to end of the </p>
            val = val.substring( 0, match.index ) +
                  val.substring( match.index+3, pos-4 ) +
                  val.substring( pos ) ;
        }
    }

    return _tidyHTML( val ) ;
}

// --------------------------------------------------------------------

function initVictoryConditionsTrumbowyg()
{
    // initialize the Victory Conditions Trumbowyg control
    var $ctrl = $( "div.param[name='VICTORY_CONDITIONS']" ) ;
    initTrumbowyg( $ctrl, gAppConfig.trumbowyg["victory-conditions"], null ) ;
    if ( gPendingVictoryConditions )
        $ctrl.trumbowyg( "html", gPendingVictoryConditions ) ;

    // FUDGE! For some reason, we need to do this :shrug:
    $ctrl.trumbowyg().on( "tbwopenfullscreen", function() {
        $( "#menu" ).hide() ;
    } ).on( "tbwclosefullscreen", function() {
        $( "#menu" ).show() ;
    } ) ;
}

function updateTrumbowygFlagsDropdown( $ctrl )
{
    // FUDGE! For convenience, we show the flags for the current players at the start of the dropdown list,
    // and while we can do this in makeDropdown() in our plugin, this only happens once for the Victory Conditions
    // control. There doesn't seem to be a way to dynamically generate the list each time it drops down,
    // so we do it by modifying the DOM.

    // initialize
    var trumbowyg = $ctrl.data( "trumbowyg" ) ;
    if ( ! trumbowyg )
        return ;
    var plugin = trumbowyg.o.plugins.flags ;
    var nat1 = get_player_nat( 1 ) ;
    var nat2 = get_player_nat( 2 ) ;

    // locate the flags dropdown
    $dropdown = $ctrl.parent().find( ".trumbowyg-dropdown-flags" ) ;
    if ( $dropdown.length === 0 )
        return ;

    // remove the dropdown's flag buttons from the DOM
    var $btns = {} ;
    $dropdown.find( "button" ).detach().each( function() {
        var nat = $(this).find( "img" ).data( "nat" ) ;
        $btns[ nat ] = $(this) ;
    } ) ;

    // add the flag buttons back into the DOM
    plugin.nationalities.forEach( function( nat ) {
        if ( nat === nat1 || nat === nat2 )
            return ;
        var $btn = $btns[ nat ] ;
        if ( $btn )
            $dropdown.append( $btn ) ;
    } ) ;
    var $btn = $btns[ nat2 ] ;
    if ( $btn )
        $dropdown.prepend( $btn ) ;
    $btn = $btns[ nat1 ] ;
    if ( $btn )
        $dropdown.prepend( $btn ) ;
}

// --------------------------------------------------------------------

var gNextHtmlTextboxId = 1 ;

function initHtmlTextbox( $ctrl, objName, small )
{
    // NOTE: It's tricky designing a UX that allows single-line textbox's to be editable as HTML.
    // Most of the time, fields such as scenario name and ID will be plain-text, so we present
    // a contenteditable div (so that the user can make simple edits directly), with a discreet option
    // to open a full WYSIWYG editor (in a dialog), if they want more complex content.

    function onActivate( evt ) {
        // show the "edit HTML" dialog
        onEditHtmlTextbox( $ctrl, objName ) ;
        evt.preventDefault() ;
    }

    // make the HTML textbox editable
    var htbId = gNextHtmlTextboxId ++ ;
    $ctrl.attr( {
        contenteditable: true,
        "data-htb-id": htbId,
    } ) ;
    $ctrl.click( function( evt ) {
        // check for Alt-Click (to open the edit dialog)
        // NOTE: We can't use Ctrl-Click, since that it used to delete caps/comments in the "edit v/o" dialog.
        // NOTE: Alt-Click doesn't trigger an even on Linux, but Ctrl-Alt-Click and Shift-Alt-Click work... :-/
        if ( evt.altKey )
            onActivate( evt ) ;
    } ).keydown( function( evt ) {
        if ( evt.keyCode == 77 && evt.ctrlKey ) {
            onActivate( evt ) ; // nb: Ctrl-M opens the "edit HTML" dialog
            evt.preventDefault() ;
        } else if ( evt.keyCode == $.ui.keyCode.ENTER )
            evt.preventDefault() ; // nb: disable ENTER
    } ) ;

    // add an icon to open the "edit html textbox" dialog
    var paramName = $ctrl.attr( "name" ) ;
    var $img = $( "<svg class='edit-html-textbox' data-htb-id='" + htbId + "'>" +
        "<use xlink:href='#trumbowyg-view-html'></use>" +
        "<title> Edit HTML (Ctrl-M) </title>" +
        "</svg>"
    ).css( {
        width: "10px", height: "15px",
        position: "relative", top: small?"-2px":"-4px", right: "13px",
        "margin-right": "-10px",
        opacity: 0.5,
        cursor: "pointer",
    } ) ;
    $ctrl.after( $img ) ;
    $img.click( function( evt ) {
        onActivate( evt ) ;
    } ) ;
}

function onEditHtmlTextbox( $ctrl, objName ) {

    // initialize
    var paramName = $ctrl.attr( "name" ) ; // nb: might be undefined e.g. vehicle/ordnance capabilities/comments
    var dlgTitle = "Edit " + (objName || "HTML") ;
    var $content, origVal ;

    function unloadData() {
        // unload the HTML content
        return unloadTrumbowyg( $content, true ).trim() ;
    }

    // show the dialog
    var $dlg = $( "#edit-html_textbox-dialog" ).dialog( {
        dialogClass: "edit-html_textbox",
        title: dlgTitle,
        modal: true,
        closeOnEscape: false,
        position: gEditHtmlTextboxDlgState ? gEditHtmlTextboxDlgState.position : { my: "center", at: "center", of: window },
        width: gEditHtmlTextboxDlgState ? gEditHtmlTextboxDlgState.width : $(window).width() * 0.5,
        height: gEditHtmlTextboxDlgState ? gEditHtmlTextboxDlgState.height : Math.max( $(window).height() * 0.5, 325 ),
        minWidth: 680, minHeight: 280,
        create: function() {
            init_dialog( $(this), "OK", true ) ;
        },
        open: function() {
            $content = $(this).find( "div.content" ) ;
            on_dialog_open( $(this), $content ) ;
            // initialize the Trumbowyg HTML editor
            if ( ! gEditHtmlTextboxDlgState ) // nb: check if this is the first time the dialog has been opened
                initTrumbowyg( $content, gAppConfig.trumbowyg["html-textbox-dialog"], $(this) ) ;
            else {
                // always start non-maximized, and in HTML mode
                resetTrumbowyg( $content ) ;
            }
            // load the dialog
            $content.trumbowyg( "html", $ctrl.html().trim() ) ;
            origVal = unloadData() ;
        },
        beforeClose: function() {
            gEditHtmlTextboxDlgState = getDialogState( $(this) ) ;
        },
        buttons: {
            OK: function() {
                $ctrl.html( unloadData() ) ;
                $(this).dialog( "close" ) ;
            },
            Cancel: function() {
                if ( unloadData() != origVal ) {
                    ask( dlgTitle, "Discard your changes?", {
                        ok: function() { $dlg.dialog( "close" ) ; },
                    } ) ;
                    return ;
                }
                $(this).dialog( "close" ) ;
            },
        },
    } ) ;
}

function unloadHtmlTextbox( $ctrl )
{
    // unload the HTML textbox
    return _tidyHTML( $ctrl.html() ) ;
}

// --------------------------------------------------------------------

function sanitizeParams( params )
{
    // recursively sanitize the scenario params
    for ( var key in params ) {
        if ( ! params.hasOwnProperty( key ) )
            continue ;
        if ( typeof params[key] === "object" )
            sanitizeParams( params[key] ) ;
        else if ( typeof params[key] === "string" ) {
            params[key] = sanitizeHTML( params[key] ) ;
        }
    }
}

function sanitizeHTML( val )
{
    // sanitize the HTML value
    return DOMPurify.sanitize(
        val,
        { USE_PROFILES: { html: true } }
    ) ;
}

// --------------------------------------------------------------------

var $gTranslateHtmlDiv = null ;

function translateHTML( val )
{
    // FUDGE! Allowing users to edit content in an HTML textbox introduced a problem when checking
    // if they had made any changes. We have a lot of HTML content in data files (e.g. vehicle/ordnance
    // capabilities and comments), and when we load them into an HTML textbox, we don't always get
    // exactly the same thing back e.g. "&times;2" comes back as "\xd72" :-/
    // Fixing up this kind of thing in the data files would be a big job, and wouldn't even be guaranteed
    // to work, since what happens is surely browser-dependent, and so the only way to detect if this
    // is happening is to load the content into a contenteditable and see what we get back. Sigh...

    if ( $gTranslateHtmlDiv === null ) {
        $gTranslateHtmlDiv = $( "<div contenteditable='true' style='display:none;'></div>" ) ;
        $( "body" ).append( $gTranslateHtmlDiv ) ;
    }
    $gTranslateHtmlDiv.html( val ) ;
    return $gTranslateHtmlDiv.html() ;
}

function _tidyHTML( val )
{
    val = val.trim() ;

    // remove superfluous <br> tags
    val = strReplaceAll( val, "<br></p>", "</p>" ) ;
    while ( val.substring( val.length-4 ) === "<br>" )
        val = val.substring( 0, val.length-4 ).trim() ;

    // remove superfluous <p> blocks
    if ( val.substring(0,3) === "<p>" && val.substring(val.length-4) === "</p>" && val.indexOf("<p>",1) === -1 )
        val = val.substring( 3, val.length-4 ) ;

    return val ;
}
