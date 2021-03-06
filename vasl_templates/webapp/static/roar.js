/* jshint esnext: true */

( function() { // nb: put the entire file into its own local namespace, global stuff gets added to window.

// --------------------------------------------------------------------

window.selectRoarScenario = function( onSelected )
{
    function formatEntry( scenario ) {
        // generate the HTML for a scenario
        var buf = [ "<div class='scenario' data-roarid='", scenario.roar_id , "'>",
            scenario.name
        ] ;
        if ( scenario.scenario_id ) {
            buf.push( " <span class='scenario-id'>[",
                strReplaceAll( scenario.scenario_id, " ", "&nbsp;" ),
                "]</span>"
            ) ;
        }
        buf.push(
            " <span class='publication'>", scenario.publication, "</span>",
            "</div>"
        ) ;
        return $( buf.join("") ) ;
    }

    // get the scenario index, then open the dialog
    getRoarScenarioIndex( function( scenarios ) {

        // initialize the select2
        var $sel = $( "#select-roar-scenario select" ) ;
        $sel.select2( {
            width: "100%",
            templateResult: function( opt ) {
                return opt.id ? formatEntry( scenarios[opt.id] ) : opt.text ;
            },
            dropdownParent: $("#select-roar-scenario"), // FUDGE! need this for the searchbox to work :-/
            closeOnSelect: false,
        } ) ;

        // stop the select2 droplist from closing up
        $sel.on( "select2:closing", function( evt ) {
            stopEvent( evt ) ;
        } ) ;

        function onResize( $dlg ) {
            $( ".select2-results ul" ).height( $dlg.height() - 50 ) ;
        }

        // let the user select a scenario
        var $dlg = $( "#select-roar-scenario" ).dialog( {
            title: "Connect scenario to ROAR",
            dialogClass: "select-roar-scenario",
            modal: true,
            closeOnEscape: false, // nb: handled in handle_escape()
            minWidth: 400,
            minHeight: 350,
            create: function() {
                // initialize the dialog
                init_dialog( $(this), "OK", false ) ;
                loadScenarios( $sel, scenarios ) ;
                // handle ENTER and double-click
                function autoSelectScenario( evt ) {
                    if ( $sel.val() ) {
                        $( ".ui-dialog.select-roar-scenario button.ok" ).click() ;
                        stopEvent( evt ) ;
                    }
                }
                $(this).keydown( function( evt ) {
                    if ( evt.keyCode == $.ui.keyCode.ENTER )
                        autoSelectScenario( evt ) ;
                } ).dblclick( function( evt ) {
                    autoSelectScenario( evt ) ;
                } ) ;
            },
            open: function() {
                // initialize
                on_dialog_open( $(this), $(this).find("select[type='search']") ) ;
                $sel.select2( "open" ) ;
                // update the UI
                onResize( $(this) ) ;
            },
            resize: onResize,
            buttons: {
                OK: { text: "OK", class: "ok", click: function() {
                    // notify the caller about the selected scenario
                    // FIXME! Clicking on the OK button doesn't result in the correct scenario being returned,
                    // but pressing ENTER or double-clicking, which triggers a click on OK, does?!
                    // The select2 docs say to use $sel.select2("data") or $sel.find(":selected"),
                    // but they both return the wrong thing :-/
                    var roarId = $sel.select2("data")[0].id ;
                    onSelected( roarId ) ;
                    $dlg.dialog( "close" ) ;
                } },
                Cancel: function() { $(this).dialog( "close" ) ; },
            },
        } ) ;

    } ) ;

} ;

function loadScenarios( $sel, scenarios )
{
    function removeQuotes( name, lquote, rquote ) {
        var len = name.length ;
        if ( name.substr( 0, lquote.length ) === lquote && name.substr( len-rquote.length ) === rquote )
            name = name.substr( lquote.length, len-lquote.length-rquote.length ) ;
        if ( name.substr( 0, lquote.length ) == lquote )
            name = name.substr( lquote.length ) ;
        return name ;
    }

    // prepare the scenarios
    var roarIds=[], roarId, scenario ;
    for ( roarId in scenarios ) {
        if ( roarId[0] === "_" )
            continue ;
        roarIds.push( roarId ) ;
        scenario = scenarios[ roarId ] ;
        var name = scenario.name ;
        name = removeQuotes( name, '"', '"' ) ;
        name = removeQuotes( name, "'", "'" ) ;
        name = removeQuotes( name, "&quot;", "&quot;" ) ;
        name = removeQuotes( name, "\u2018", "\u2019" ) ;
        name = removeQuotes( name, "\u201c", "\u201d" ) ;
        if ( name.substring(0,3) === "..." )
            name = name.substr( 3 ) ;
        scenario._sortName = name.trim().toUpperCase() ;
    }

    // sort the scenarios
    roarIds.sort( function( lhs, rhs ) {
        lhs = scenarios[ lhs ]._sortName ;
        rhs = scenarios[ rhs ]._sortName ;
        if ( lhs < rhs )
            return -1 ;
        else if ( lhs > rhs )
            return +1 ;
        return 0 ;
    } ) ;

    // load the select
    var buf = [] ;
    for ( var i=0 ; i < roarIds.length ; ++i ) {
        roarId = roarIds[ i ] ;
        scenario = scenarios[ roarId ] ;
        // NOTE: The <option> text is what gets searched (formatEntry() generates what gets shown),
        // so we include the scenario ID here, so that it also becomes searchable.
        buf.push( "<option value='" + roarId + "'>",
            scenario.name + " " + scenario.scenario_id,
            "</option>"
        ) ;
    }
    $sel.html( buf.join("") ) ;
}

// --------------------------------------------------------------------

var _roarScenarioIndex = null ; // nb: don't access this directly, use getRoarScenarioIndex()
var _roarScenarioIndexETag ;

function getRoarScenarioIndex( onReady )
{
    // nope - download it
    $.ajax( {
        url: gGetRoarScenarioIndexUrl,
        type: "GET",
        datatype: "json",
        beforeSend: function( xhr ) {
            if ( _roarScenarioIndexETag )
                xhr.setRequestHeader( "If-None-Match", _roarScenarioIndexETag ) ;
        },
        success: function( resp, status, xhr ) {
            if ( xhr.status == 304 ) {
                // our cached copy is still valid
                onReady( _roarScenarioIndex ) ;
                return ;
            }
            // check if a warning was issued
            if ( resp.warning ) {
                var msg = resp.warning ;
                if ( resp.message )
                    msg += "<div class='pre'>" + escapeHTML(resp.message) + "</div>" ;
                showWarningMsg( msg ) ;
                return ;
            }
            // save a copy of the data, then notify the caller
            _roarScenarioIndex = resp ;
            _roarScenarioIndexETag = xhr.getResponseHeader( "ETag" ) ;
            onReady( resp ) ;
        },
        error: function( xhr, status, errorMsg ) {
            showErrorMsg( "Can't get the ROAR scenario index:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
            return ;
        },
    } ) ;
}

// --------------------------------------------------------------------

} )() ; // end local namespace
