// This custom plugin allows player flags to be inserted into the HTML content.
// It was adapted from the standard "template" plugin (which we can't use, since it *replaces*
// the whole of the HTML content, instead of *inserting* an HTML fragment). This version
// also allows the inserted content to be generated dynamically (to account for where images
// should be loaded from).

( function( $ ) {
    "use strict" ;

    // register the plugin
    $.extend( true, $.trumbowyg, {
        plugins: {
            flags: {
                init: function( trumbowyg ) {
                    trumbowyg.addBtnDef( "flags", {
                        dropdown: makeDropdown( trumbowyg ),
                        // FUDGE! While we can provide custom icons, they have to be SVG,
                        // so we just do it using CSS :-/
                        hasIcon: false, text: " ",
                        title: "Flags",
                    } ) ;
                }
            }
        }
    } ) ;

    function makeDropdown( trumbowyg ) {

        // initialize
        var plugin = trumbowyg.o.plugins.flags ;
        var flags = [] ;

        // add an entry for each nationality
        $.each( plugin.nationalities, function( index, nat ) {
            var displayName = get_nationality_display_name( nat ) ;
            trumbowyg.addBtnDef( nat, {
                fn: function () {
                    var url = plugin.makeFlagHtml( nat, false ) ;
                    var size = 11 ;
                    var html = "<img src='" + url + "?prefh=" + size + "' width='" + size + "' height='" + size + "'>" ;
                    trumbowyg.execCmd( "insertHtml", html ) ;
                },
                hasIcon: false,
                title: "<img src='" + plugin.makeFlagHtml(nat,true) + "'" +
                         " title='" + displayName + "'" +
                         " data-nat='" + nat + "'" +
                         ">" ,
            } ) ;
            flags.push( nat ) ;
        } ) ;

        return flags ;
    }
} ) ( jQuery ) ;
