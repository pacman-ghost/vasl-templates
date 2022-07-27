// --------------------------------------------------------------------

function initTrumbowyg( $elem, buttons, $parentDlg )
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
    $elem.trumbowyg( {
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
    } ) ;
    var $parent = $elem.parent() ;
    var $btnPane = $parent.find( ".trumbowyg-button-pane" ) ;
    var $textarea = $parent.find( ".trumbowyg-textarea" ) ;

    // update the flags dropdown for the current players
    if ( $btnPane.find( ".trumbowyg-flags-button" ).length > 0 )
        updateTrumbowygFlagsDropdown( $elem ) ;

    // prepare for our jQuery event handlers
    var eventHandlers = $elem.data( "eventHandlers" ) ;
    if ( ! eventHandlers ) {
        eventHandlers = new jQueryHandlers() ;
        $elem.data( "eventHandlers", eventHandlers ) ;
    }

    // allow a hotkey to toggle the WYSIWYG editor
    // FUDGE! While we can create a custom button to manually toggle the control, it doesn't quite work :-/
    // Switching to HTML mode disables all buttons, including the "view HTML" button, and while we can
    // manually enable it, hotkeys don't seem to work when we're in HTML mode :-/ We hack around this by
    // adding a key handler and managing the whole process ourself. Sigh...
    function onKeyDown( evt ) {
        // check for Ctrl-M
        if ( evt.keyCode == 77 && evt.ctrlKey ) {
            $elem.trumbowyg( "toggle" ) ;
            setTimeout( function() {
                if ( $elem.parent().hasClass( "trumbowyg-editor-visible" ) )
                    $elem.focus() ;
                else
                    $elem.parent().find( ".trumbowyg-textarea" ).focus() ;
            }, 20 ) ;
            evt.preventDefault() ;
            return ;
        }
        // handle auto-dismiss if we are in a dialog
        if ( $parentDlg )
            auto_dismiss_dialog( $parentDlg, evt, "OK" ) ;
    }
    eventHandlers.addHandler( $elem, "keydown", onKeyDown ) ;
    eventHandlers.addHandler( $textarea, "keydown", onKeyDown ) ;
    // FUDGE! There should be spaces around the +, but this causes the tooltip to wrap on Windows :-/
    $btnPane.find( ".trumbowyg-viewHTML-button" ).attr( "title", "View HTML (Ctrl+M)" ) ;

    // handle resize events
    if ( ! $parent.data( "resizeObserver" ) ) {
        var resizeObserver = new ResizeObserver( function( entries ) {
            // FUDGE! Couldn't get Trumbowyg to sit nicely inside a flexbox, so we set the height dynamically :-/
            var height = "calc(100% - " + $btnPane.height() + "px)" ;
            $elem.css( { height: height } ) ;
            $textarea.css( { height: height } ) ;
            // limit the height of dropdown's
            if ( $parentDlg ) {
                $parent.find( ".trumbowyg-dropdown" ).css( {
                    "max-height": $elem.height() + 5
                } ) ;
            }
        } ) ;
        resizeObserver.observe( $parent[0] ) ;
        $parent.data( "resizeObserver", resizeObserver ) ;
    }
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function destroyTrumbowyg( $elem )
{
    // destroy the Trumbowyg control and clean up
    var eventHandlers = $elem.data( "eventHandlers" ) ;
    if ( eventHandlers ) {
        eventHandlers.cleanUp() ;
        $elem.removeData( "eventHandlers" ) ;
    }
    $elem.trumbowyg( "destroy" ) ;
}

// --------------------------------------------------------------------

function unloadTrumbowyg( $elem, removeFirstPara )
{
    // unload the Trumbowyg control
    var val = $elem.trumbowyg( "html" ).trim() ;

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

    // remove superfluous <br> tags
    val = strReplaceAll( val, "<br></p>", "</p>" ) ;
    while ( val.substring( val.length-4 ) === "<br>" )
        val = val.substring( 0, val.length-4 ).trim() ;
    return val ;
}

// --------------------------------------------------------------------

function initVictoryConditionsTrumbowyg()
{
    // initialize the Victory Conditions Trumbowyg control
    var $elem = $( "div.param[name='VICTORY_CONDITIONS']" ) ;
    initTrumbowyg( $elem, gAppConfig.trumbowyg["victory-conditions"], null ) ;
    if ( gPendingVictoryConditions )
        $elem.trumbowyg( "html", gPendingVictoryConditions ) ;

    // FUDGE! For some reason, we need to do this :shrug:
    $elem.trumbowyg().on( "tbwopenfullscreen", function() {
        $( "#menu" ).hide() ;
    } ).on( "tbwclosefullscreen", function() {
        $( "#menu" ).show() ;
    } ) ;
}

function updateTrumbowygFlagsDropdown( $elem )
{
    // FUDGE! For convenience, we show the flags for the current players at the start of the dropdown list,
    // and while we can do this in makeDropdown() in our plugin, this only happens once for the Victory Conditions
    // control. There doesn't seem to be a way to dynamically generate the list each time it drops down,
    // so we do it by modifying the DOM.

    // initialize
    var trumbowyg = $elem.data( "trumbowyg" ) ;
    if ( ! trumbowyg )
        return ;
    var plugin = trumbowyg.o.plugins.flags ;
    var nat1 = get_player_nat( 1 ) ;
    var nat2 = get_player_nat( 2 ) ;

    // locate the flags dropdown
    $dropdown = $elem.parent().find( ".trumbowyg-dropdown-flags" ) ;
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
