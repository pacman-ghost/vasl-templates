gUserSettings = Cookies.getJSON( "user-settings" ) || {} ;

USER_SETTINGS = {
    "date-format": "droplist",
    "use-online-images": "checkbox",
    "hide-unavailable-ma-notes": "checkbox",
    "include-vasl-images-in-snippets": "checkbox",
    "include-flags-in-snippets": "checkbox",
    "custom-list-bullets": "checkbox",
    "vo-notes-as-images": "checkbox",
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
        update_ui() ;
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

    function update_ui() {
        // update the UI
        var use_online_images = $( ".ui-dialog.user-settings input[name='use-online-images']" ).prop( "checked" ) ;
        $( ".ui-dialog.user-settings img.need-localhost.sometimes" ).css(
            "display", use_online_images ? "none" : "inline-block"
        ) ;
        // update the UI
        var rc = false ;
        $( ".ui-dialog.user-settings input.need-localhost:checked" ).each( function() {
            if ( $(this).hasClass( "sometimes" ) ) {
                if ( ! use_online_images )
                    rc = true ;
            }
            else
                rc = true ;
        } ) ;
        $( ".ui-dialog.user-settings div.need-localhost" ).css(
            "display", rc ? "block" : "none"
        ) ;
    }

    var handlers = {
        load_checkbox: function( $elem, val ) { $elem.prop( "checked", val?true:false ) ; },
        unload_checkbox: function( $elem ) { return $elem.prop( "checked" ) ; },
        load_droplist: function( $elem, val ) { if ( val ) $elem.val( val ) ; },
        unload_droplist: function( $elem ) { return $elem.children(":selected").val() ; },
    } ;

    // show the "user settings" dialog
    $( "#user-settings" ).dialog( {
        title: "User settings",
        dialogClass: "user-settings",
        modal: true,
        width: 440,
        height: 305,
        resizable: false,
        create: function() {
            init_dialog( $(this), "OK", true ) ;
            // initialize the "this program must be running" warnings
            $( "input.need-localhost" ).each( function() {
                var $img = $( "<img src='" + gImagesBaseUrl+"/warning.gif" + "'class='need-localhost'>" ) ;
                if ( $(this).hasClass( "sometimes" ) )
                    $img.addClass( "sometimes" ) ;
                $img.attr( "title", "If you turn this option on, this program must be running\nbefore you load the scenario into VASSAL." ) ;
                $(this).next().before( $img ) ;
            } ) ;
            var $btn_pane = $(".ui-dialog.user-settings .ui-dialog-buttonpane") ;
            $btn_pane.prepend( $(
                "<div class='need-localhost'><img src='" + gImagesBaseUrl+"/warning.gif" + "'>" +
                "This program must be running before<br>you load the scenario into VASSAL.</div>"
            ) ) ;
            // install handlers to keep the UI updated
            for ( var name in USER_SETTINGS ) {
                if ( USER_SETTINGS[name] === "checkbox" ) {
                    var $elem = $( ".ui-dialog.user-settings [name='" + name + "']" ) ;
                    $elem.click( update_ui ) ;
                }
            }
        },
        open: function() {
            on_dialog_open( $(this) ) ;
            // load the current user settings
            load_settings( $(this) ) ;
        },
        buttons: {
            OK: function() {
                // unload and install the new user settings
                var settings = unload_settings() ;
                gUserSettings = settings ;
                Cookies.set( "user-settings", settings, { expires: 999 } ) ;
                apply_user_settings() ;
                if ( gWebChannelHandler )
                    gWebChannelHandler.on_user_settings_change( JSON.stringify( settings ) ) ;
                $(this).dialog( "close" ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function apply_user_settings()
{
    // set the date format
    var date_format = gUserSettings["date-format"] || "mm/dd/yy" ;
    var $scenario_date = $( "input[name='SCENARIO_DATE']" ) ;
    var curr_date = $scenario_date.datepicker( "getDate" ) ;
    $scenario_date.datepicker( "option", "dateFormat", date_format ) ;
    $scenario_date.datepicker( "option", "defaultDate",
        $.datepicker.formatDate( date_format, new Date(1940,0,1) )
    ) ;
    if ( curr_date ) {
        $scenario_date.val(
            $.datepicker.formatDate( date_format, curr_date )
        ).trigger( "change" ) ;
    }
}

// --------------------------------------------------------------------

function install_user_settings( user_settings ) // nb: this is called by the PyQT desktop application
{
    gUserSettings = JSON.parse( user_settings ) ;
    apply_user_settings() ;
}
