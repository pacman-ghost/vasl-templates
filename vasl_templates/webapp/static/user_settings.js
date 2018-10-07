gUserSettings = Cookies.getJSON( "user-settings" ) || {} ;

USER_SETTINGS = {
    "include-vasl-images-in-snippets": "checkbox",
} ;

// --------------------------------------------------------------------

function user_settings()
{
    function load_settings() {
        // load each user setting
        for ( var name in USER_SETTINGS ) {
            var $elem = $( ".ui-dialog.user-settings [name='" + name + "']" ) ;
            var func = handlers[ "load_" + USER_SETTINGS[name] ] ;
            func( $elem, gUserSettings[name] ) ;
        }
    }

    function unload_settings() {
        // unload each user setting
        var settings = {} ;
        for ( var name in USER_SETTINGS ) {
            var $elem = $( ".ui-dialog.user-settings [name='" + name + "']" ) ;
            func = handlers[ "unload_" + USER_SETTINGS[name] ] ;
            settings[name] = func( $elem ) ;
        }
        return settings ;
    }

    var handlers = {
        load_checkbox: function( $elem, val ) { $elem.prop( "checked", val?true:false ) ; },
        unload_checkbox: function( $elem ) { return $elem.prop( "checked" ) ; },
    } ;

    function update_ui() {
        // update the UI
        var $dlg = $( ".ui-dialog.user-settings" ) ;
        var is_checked = $dlg.find( "input[name='include-vasl-images-in-snippets']" ).prop( "checked" ) ;
        $dlg.find( ".include-vasl-images-in-snippets-hint" ).css(
            "color", is_checked ? "#444" : "#aaa"
        ) ;
    }

    // show the "user settings" dialog
    $( "#user-settings" ).dialog( {
        title: "User settings",
        dialogClass: "user-settings",
        modal: true,
        width: 450,
        height: 150,
        resizable: false,
        create: function() {
            init_dialog( $(this), "OK", false ) ;
            $(this).find( "input[name='include-vasl-images-in-snippets']" ).change( update_ui ) ;
        },
        open: function() {
            // load the current user settings
            load_settings( $(this) ) ;
            update_ui() ;
        },
        buttons: {
            OK: function() {
                // unload and install the new user settings
                var settings = unload_settings() ;
                gUserSettings = settings ;
                Cookies.set( "user-settings", settings, { expires: 999 } ) ;
                if ( gWebChannelHandler )
                    gWebChannelHandler.on_user_settings_change( JSON.stringify( settings ) ) ;
                $(this).dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// --------------------------------------------------------------------

function install_user_settings( user_settings ) // nb: this is called by the PyQT desktop application
{
    gUserSettings = JSON.parse( user_settings ) ;
}
