/* jshint esnext: true */

( function() { // nb: put the entire file into its own local namespace, global stuff gets added to window.

var gIsFirstSearch ;
var $gDialog, $gScenariosSelect, $gSearchQueryInputBox, $gScenarioCard, $gFooter ;
var $gImportControl, $gDownloadsButton, $gImportScenarioButton, $gConfirmImportButton, $gCancelImportButton, $gImportWarnings ;

// At time of writing, there are ~8600 scenarios, and loading them all into a select2 makes it a bit sluggish.
// The problem is when the user types the first 1 or 2 characters of the search query, which can result in
// thousands of results being loaded into the DOM. We work-around this by limiting the number of results
// shown for these very short query strings.
// An index is built of search results for very short query strings (e.g. "a" or "th"), with the additional
// requirement that the query string must appear at the start of a word (so "th" will match "the", but not "with").
// This index also means that we can return results for these short query strings quickly, since we don't
// have to scan through all the scenarios looking for matches.
// The only down-side is that the search results shown to the user may change radically when we switch
// from using the prefix index to a normal substring search, but we can live with that.
var gPrefixIndex = null ;
const PREFIX_SIZE = 3 ;

// --------------------------------------------------------------------

window.searchForScenario = function()
{
    // initialize
    var $dlg ;
    var eventHandlers = new jQueryHandlers() ;

    // NOTE: We have to get the scenario index before we can do anything.
    getScenarioIndex( function( scenarios ) {

        // show the dialog
        $( "#scenario-search" ).dialog( {
            title: "Search for scenarios",
            dialogClass: "scenario-search",
            modal: true,
            closeOnEscape: false, // nb: handled in handle_escape()
            width: $(window).width() * 0.8,
            minWidth: 750,
            height: $(window).height() * 0.8,
            minHeight: 400,
            position: { my: "center center", at: "center center", of: window },
            create: function() {
                initPrefixIndex( scenarios ) ;
                initDialog( $(this), scenarios ) ;
                // FUDGE! This works around a weird layout problem. The very first time the dialog opens,
                // the search input box (the whole .select2-dropdown, actually) is too far left. The layout
                // fixes itself on the first keypress, but we adjust the initial position here.
                $(this).find( ".select2-dropdown" ).css( "left", 10 ) ;
            },
            open: function() {
                // initialize
                $dlg = $(this) ;
                // reset everything
                $gSearchQueryInputBox.val( "" ) ;
                $gDialog.find( ".select2-results__option" ).remove() ;
                updateForSearchResults() ;
                $gScenarioCard.empty() ;
                $gFooter.hide() ;
                $gImportWarnings.empty().hide() ;
                $gDownloadsButton.button( "disable" ) ;
                $gImportScenarioButton.show() ;
                $gConfirmImportButton.hide() ;
                $gCancelImportButton.hide() ;
                updateLayout() ;
                gIsFirstSearch = true ;
                gActiveScenaridCardRequest = null ;
                gScenarioCardRequestTimerId = null ;
            },
            close: function() {
                // clean up
                eventHandlers.cleanUp() ;
            },
            resize: updateLayout,
        } ) ;
    } ) ;
} ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function initDialog( $dlg, scenarios )
{
    // initialize
    $gDialog = $dlg ;
    fixup_external_links( $dlg ) ;
    $gScenarioCard = $dlg.find( ".scenario-card" ) ;
    $gImportControl = $dlg.find( ".import-control" ) ;
    $gDownloadsButton = $dlg.find( "button.downloads" ).button()
        .on( "click", onDownloads ) ;
    $gImportScenarioButton = $dlg.find( "button.import" ).button()
        .on( "click", function() {
            if ( ! is_scenario_dirty() )
                onImportScenario() ;
            else {
                ask( "Import scenario",
                    "<p> Your scenario has been changed. <p> Do you want to import a new scenario, and lose your changes?", {
                    width: 470,
                    ok: onImportScenario,
                } ) ;
            }
    } ) ;
    $gConfirmImportButton = $dlg.find( "button.confirm-import" ).button()
        .on( "click", onConfirmImportScenario ) ;
    $gCancelImportButton = $dlg.find( "button.cancel-import" ).button()
        .on( "click", onCancelImportScenario ) ;
    $gImportWarnings = $dlg.find( ".import-control .warnings" ) ;
    $gFooter = $dlg.find( ".footer" ) ;

    // initialize the splitter
    Split( [ $dlg.find( ".left" )[0], $dlg.find( ".right" )[0] ], {
        sizes: [ 30, 70 ],
        direction: "horizontal",
        gutterSize: 3,
        onDrag: updateLayout,
    } ) ;
    var $gripper = $( "<img src='" + gImagesBaseUrl + "/gripper-vert.png'>" ) ;
    $dlg.find( ".gutter.gutter-horizontal" ).append( $gripper ) ;

    // initialize the select2
    var options = [] ;
    scenarios.forEach( function( scenario ) {
        options.push( {
            id: scenario.scenario_id,
            text: scenario.scenario_name, // nb: this will always have something
            scenario: scenario,
        } ) ;
    } ) ;
    sortScenarios( options ) ;
    $gScenariosSelect = $dlg.find( ".scenarios select" ) ;
    $gScenariosSelect.select2( {
        data: options,
        matcher: isMatchingItem, sorter: sortItems, templateResult: formatItem,
        width: "100%",
        closeOnSelect: false,
        dropdownParent: $dlg.find( ".scenarios" ),
    } ) ;

    // stop the select2 droplist from closing up
    $gScenariosSelect.select2( "open" ) ;
    $gScenariosSelect.on( "select2:closing", function( evt ) {
        stopEvent( evt ) ;
    } ) ;

    // keep the UI up-to-date as items are selected
    $gScenariosSelect.on( "select2:select", function( evt ) {
        onItemSelected( evt.params.data.id ) ;
    } ) ;
    $gSearchQueryInputBox = $dlg.find( ".select2-search__field" ) ;
    $gSearchQueryInputBox.on( "input", function() {
        // FUDGE! select2 rebuilds the list of matching items, and selects the first one,
        // but doesn't send us a "select" event for it - we do things manually here :-/
        var $elem = $( ".select2-results__option--highlighted .search-result" ) ;
        onItemSelected( $elem.attr( "data-id" ) ) ;
        updateForSearchResults() ;
        // FUDGE! Undo the positioning hack we did in the "create" handler.
        $dlg.find( ".select2-dropdown" ).css( "left", 0 ) ;
    } ) ;

    // handle Up and Down key-presses
    $gSearchQueryInputBox.on( "keydown", function( evt ) {
        if ( evt.keyCode == $.ui.keyCode.UP || evt.keyCode == $.ui.keyCode.DOWN ) {
            // NOTE: We don't want to refresh the scenario card if it's not necessary (e.g. after the user
            // presses UP when already at the top of the list), since it causes flickering (because some
            // elements in the scenario card fade in/out). We seem to get this event *after* the selection
            // has already changed in the search result, so we compare the currently-selected item
            // with what's currently showing in the scenario card to decide if anything's changed.
            var currId = $dlg.find( ".scenario-card" ).data( "scenario" ).scenario_id ;
            var $elem = $( ".select2-results__option--highlighted .search-result" ) ;
            if ( $elem.attr( "data-id" ) != currId )
                onItemSelected( $elem.attr( "data-id" ) ) ;
        }
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function initPrefixIndex( scenarios )
{
    function addEntry( key, scenario ) {
        if ( gPrefixIndex[ key ] === undefined )
            gPrefixIndex[ key ] = {} ;
        gPrefixIndex[ key ][ scenario.scenario_id ] = true ;
    }

    // build the prefix index
    gPrefixIndex = {} ;
    scenarios.forEach( function( scenario ) {

        // get the searchable text for the next scenario (and cache it)
        scenario._searchText = makeSearchText( scenario ) ;

        // add each word to the prefix index
        var words = scenario._searchText.split( " " ) ;
        words.forEach( function( word ) {
            if ( word.length < 3 )
                return ; // nb: ignore short words
            for ( var i=1 ; i <= PREFIX_SIZE ; ++i )
                addEntry( word.substring(0,i).toLowerCase(), scenario ) ;
        } ) ;

    } ) ;
}

// --------------------------------------------------------------------

function isMatchingItem( params, item )
{
    // NOTE: This function is called by the select2 to decide if an item should be shown.

    // check if an item should be shown
    if ( ! params.term )
        return null ; // nb: we don't show anything if there is no query string
    var termLC = params.term.trim().toLowerCase() ;
    if ( termLC.length <= PREFIX_SIZE ) {
        // seaerch the prefix index
        if ( gPrefixIndex[termLC] && gPrefixIndex[termLC][item.id] )
            return item ;
    } else {
        // search for a matching substring
        if ( item.scenario._searchText.indexOf( termLC ) !== -1 )
            return item ;
    }
    return null ;
}

function makeSearchText( scenario )
{
    // return the text that will be searched upon
    var val = scenario.scenario_name.trim().toLowerCase() ;
    val = val.replace( /\s{2,}/g, " " ) ;
    return val ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function sortItems( items )
{
    // NOTE: This function is called by the select2 to sort the items being shown.

    // NOTE: We used to sort the items alphabetically here, but this could cause a new item to appear
    // at the top of the list, which we want to be selected. It was ridiculously difficult to figure out
    // how to select an item:
    //     $gScenariosSelect.select2( "trigger", "select", {
    //         data: { id: items[0].id }
    //     } ) ;
    // but unfortunately, this slows things down a lot in Chrome (everything flies in Firefox).
    // We really need to present the scenarios in alphabetical order (so that scenarios with the same name
    // are grouped together), but we can achieve that same effect by loading them into the select2
    // in alphabetical order.

    return items ;
}

function sortScenarios( options )
{
    // NOTE See sortItems() for why we load the scenarios in alphabetical order.
    function getSortVal( text ) {
        text = text.trim().toLowerCase() ;
        if ( text[0] == '"' || text[0] == "'" )
            text = text.substring( 1 ) ;
        if ( text[0] == "\u00a1" || text[0] == "\u00bf" ) // nb: inverted ! and ?
            text = text.substring( 1 ) ;
        if ( text.substring( 0, 3 ) == "..." )
            text = text.substring( 3 ) ;
        return text ;
    }
    options.sort( function( lhs, rhs ) {
        return getSortVal( lhs.text ).localeCompare( getSortVal( rhs.text ) ) ;
    } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function formatItem( opt )
{
    // NOTE: This function is called by the select2 to format items being shown.

    // initialize
    if ( ! opt.id )
        return opt.text ;
    var scenario = opt.scenario ;

    function addVal( val, className, prefix, postfix ) {
        if ( val ) {
            buf.push( "<span class='"+className+"'>" ) ;
            if ( prefix )
                buf.push( prefix ) ;
            buf.push( val ) ;
            if ( postfix )
                buf.push( postfix ) ;
            buf.push( "</span>" ) ;
        }
    }

    // generate the search result
    const nowrap = "white-space:nowrap;overflow:hidden;text-overflow:ellipsis;" ;
    var buf = [ "<div class='search-result' data-id='", scenario.scenario_id, "'>" ] ;
    buf.push( "<div>" ) ;
    addVal( scenario.scenario_name ) ;
    addVal( scenario.scenario_display_id, "scenario-id", " (", ")" ) ;
    buf.push( "</div>" ) ;
    if ( scenario.scenario_location ) {
        buf.push( "<div style='" + nowrap + "'>" ) ;
        addVal( scenario.scenario_location, "scenario-location" ) ;
        addVal( scenario.scenario_date, "scenario-date", " (", ")" ) ;
        buf.push( "</div>" ) ;
    }
    if ( scenario.publication_name ) {
        buf.push( "<div style='" + nowrap + "'>" ) ;
        addVal( scenario.publication_name, "publication-name" ) ;
        addVal( scenario.publisher_name, "publisher-name", " (", ")" ) ;
        if ( scenario.publication_date ) {
            addVal( scenario.publication_date.substring(5,7) + "/" + scenario.publication_date.substring(0,4),
                "publication-date", " (", ")"
            ) ;
        }
        buf.push( "</div>" ) ;
    }
    buf.push( "</div>" ) ;

    // check if this is the first time we're showing search results
    if ( gIsFirstSearch ) {
        $gFooter.fadeIn( 5*1000 ) ;
        gIsFirstSearch = false ;
    }

    return $( buf.join("") ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function updateForSearchResults()
{
    // check if there were any search results
    $gDialog.find( ".select2-results__message" ).each( function() {
        if ( $(this).text() == "No results found" ) {
            // nope - update the UI
            $(this).hide() ;
            onItemSelected( null ) ;
        }
    } ) ;

    // update the import control
    var hasSearchResults = $gDialog.find( ".select2-results .search-result" ).length  > 0 ;
    $gImportScenarioButton.button( hasSearchResults ? "enable" : "disable" ) ;
    $gImportControl.css( { "border-top-color": hasSearchResults ? "#666": "#ccc" } ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function onItemSelected( scenarioId )
{
    // update the UI
    onCancelImportScenario() ;

    // load the specified scenario
    if ( ! scenarioId ) {
        $gScenarioCard.empty().data( "scenario", null ) ;
        $gDownloadsButton.button( "disable" ) ;
        return ;
    }
    // NOTE: We pass "auto-match" as the ROAR override, to tell the server to try to find
    // a matching ROAR scenario.
    loadScenarioCard( $gScenarioCard, scenarioId, true, null, "auto-match", false,
        function( scenario ) {
            if ( scenario.downloads && scenario.downloads.length > 0 )
                $gDownloadsButton.button( "enable" ).data( "scenario", $gScenarioCard.data("scenario") ) ;
            else
                $gDownloadsButton.button( "disable" ) ;
            // update the layout
            updateLayout() ;
            // NOTE: We set focus to the query input box so that UP/DOWN will work
            // after clicking on a search result.
            $gSearchQueryInputBox.focus() ;
        },
        function( xhr, status, errorMsg ) {
            $gScenarioCard.html( "Can't get the scenario card:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        }
    ) ;
}

// --------------------------------------------------------------------

// It's quite easy for there to be multiple requests for scenario cards in progress at the same time
// e.g. if the user holds down the arrow keys to scroll through the search results. We try to optimize
// the process by ignoring all responses except for the most recently requested scenario card. We could
// count the number of active requests pending, but this will end up showing the wrong scenario card
// if the responses come back in a different order.
// So, we instead remember the ID of the most recently requested scenario card, and load that
// into the UI when it arrives. We will load the "wrong" response if the user requests, for example,
// scenarios 1, 2, 3, 2 (i.e. we will load the first "2" response, not the second one), but since
// these things never change, it doesn't actually matter.
var gActiveScenaridCardRequest = null ;
var gScenarioCardRequestTimerId ;

function loadScenarioCard( $target, scenarioId, briefMode, scenarioDateOverride, roarOverride, showRoarButtons, onDone, onError )
{
    // NOTE: Loading scenario cards is usually quick, but it can occasionally take some time (especially
    // if the query string has just been changed). We show a "loading" spinner if a response hasn't arrived
    // within a short amount of time.
    if ( ! gScenarioCardRequestTimerId ) {
        gScenarioCardRequestTimerId = setTimeout( function() {
            $target.html( "<img src='" + gImagesBaseUrl+"/loader.gif" + "'" +
                " style='position:absolute;left:45%;top:45%;'>"
            ) ;
        }, 500 ) ;
    }
    gActiveScenaridCardRequest = scenarioId ;

    // initialize
    // NOTE: We tag the scenario card with a seq# for the benefit of the test suite, so that it can tell
    // when a scenario card has finished loading, and it's safe to read values out of the UI.
    // It won't work under load, but we only need it for the simple case of a single request coming in,
    // and waiting for it to load completely.
    var seqNo = $target.attr( "data-seqNo" ) || 1 ;

    // load the specified scenario
    var url = gGetScenarioCardUrl.replace( "ID", scenarioId ) ;
    if ( briefMode )
        url = addUrlParam( url, "brief", 1 ) ;
    $.get( url, function( resp ) {

        // check if this response is for the most recently requested scenario card
        if ( scenarioId != gActiveScenaridCardRequest )
            return ;
        gActiveScenaridCardRequest = null ;
        clearTimeout( gScenarioCardRequestTimerId ) ;
        gScenarioCardRequestTimerId = null ;

        // NOTE: We used to load the received HTML into the UI here, then get the scenario details,
        // but updating the UI with the details when they arrive can cause the layout to change.
        // Instead, we hold everything and only update the UI when it's all ready.
        var $card = $( resp ) ;
        fixup_external_links( $card ) ;
        $card.find( ".overview .more" ).on( "click", function() {
            $(this).hide() ;
            $(this).siblings( ".brief" ).hide() ;
            $(this).siblings( ".full" ).fadeIn( 250 ) ;
            $gSearchQueryInputBox.focus() ;
        } ) ;

        function showBoardPreviews( $elem, scenario ) {
            // initialize the image gallery
            var data = [] ;
            scenario.map_images.forEach( function( mapImage ) {
                var url = mapImage.screenshot ;
                var buf = [] ;
                if ( mapImage.user ) {
                    buf.push( "Contributed by <em>", mapImage.user, "</em>" ) ;
                    if ( mapImage.timestamp ) {
                        var tstamp = new Date( mapImage.timestamp ) ;
                        buf.push( "<div style='font-size:80%;font-style:italic;color:#ccc;'>",
                            tstamp.toLocaleDateString( undefined, { day: "numeric", month: "long", year: "numeric" } ),
                            "</div>"
                        ) ;
                    }
                }
                data.push( {
                    src: url, thumb: url,
                    subHtml: buf.length > 0 ? buf.join("") : url.split("/").pop(),
                } ) ;
            } ) ;
            $elem.lightGallery( { dynamic: true, dynamicEl: data, speed: 250 } ) ;
        }

        // get the scenario details
        getScenarioData( scenarioId, roarOverride, function( scenario ) {
            // add the details to the scenario card
            insertPlayerFlags( $card, scenario ) ;
            makeBalanceGraphs( $card, scenario, showRoarButtons ) ;
            loadObaInfo( $card, scenario, scenarioDateOverride ) ;
            // initialize the map previews
            var $btn = $card.find( ".boards .map-previews" ) ;
            if ( ! scenario.map_images || scenario.map_images.length === 0 )
                $btn.hide() ;
            else {
                if ( scenario.map_images.length > 1 )
                    $btn.after( " <span class='map-preview-count'>(" + scenario.map_images.length + ")</span>" ) ;
                $btn.on( "click", function() {
                    showBoardPreviews( $(this), scenario ) ;
                } ) ;
            }
            // all done - load the card into the UI and notify the caller
            $target.data( "scenario", scenario ) ;
            $target.html( $card ).fadeIn( 100 ) ;
            onDone( scenario ) ;
            $target.attr( "data-seqNo", parseInt(seqNo)+1 ) ;
        } ) ;

    } ).fail( onError ) ;
}

function insertPlayerFlags( $target, scenario )
{
    // insert flags for each player
    [ "defender", "attacker" ].forEach( function( playerType ) {
        var effectiveNat = getEffectivePlayerNat( scenario[ playerType+"_name" ] ) ;
        if ( ! effectiveNat )
            return ;
        var url = make_player_flag_url( effectiveNat[0], false ) ;
        $target.find( ".player-info ." + playerType + " .flag" ).html(
            $( "<img src='" + url + "'>" )
        ) ;
    } ) ;
}

function loadObaInfo( $target, scenario, scenarioDateOverride )
{
    // initialize
    var theater =  getEffectiveTheater( scenario.theater ) ;
    var scenarioDate = scenario.scenario_date_iso ;
    if ( ! theater || ( !scenarioDate && !scenarioDateOverride ) )
        return ;
    if ( scenarioDateOverride ) {
        scenarioDateOverride = scenarioDateOverride.toISOString().substring( 0, 10 ) ;
        if ( scenarioDateOverride.substring(0,7) == scenarioDate.substring(0,7) )
            scenarioDateOverride = null ;
        else
            scenarioDate = scenarioDateOverride ;
    }
    var params = {
        SCENARIO_THEATER: theater,
        SCENARIO_YEAR: scenarioDate.substring( 0, 4 ),
        SCENARIO_MONTH: scenarioDate.substring( 5, 7 ),
    } ;

    // show the OBA info for the defender/attacker
    function showInfo( playerType ) {

        // get the OBA info
        var effectiveNat = getEffectivePlayerNat( scenario[ playerType+"_name" ] ) ;
        if ( ! effectiveNat )
            return ;
        delete params.NAT_CAPS ;
        set_nat_caps_params( effectiveNat[0], params ) ;
        if ( params.NAT_CAPS === undefined )
            params.NAT_CAPS = {} ;

        // load the OBA into the scenario card
        $target.find( ".oba ." + playerType + " .black" ).text( params.NAT_CAPS.OBA_BLACK || "-" ) ;
        $target.find( ".oba ." + playerType + " .red" ).text( params.NAT_CAPS.OBA_RED || "-" ) ;

        // show any OBA comments
        var $comments = $target.find( ".oba ." + playerType + " .comments" ) ;
        if ( params.NAT_CAPS.OBA_COMMENTS ) {
            var buf = [] ;
            params.NAT_CAPS.OBA_COMMENTS.forEach( function( cmt ) {
                buf.push( "<div>", cmt, "</div>" ) ;
            } ) ;
            $comments.html( buf.join("") ).show() ;
        } else {
            $comments.hide() ;
        }

        // update the date warning
        if ( scenarioDateOverride ) {
            $target.find( ".date-warning .val" ).text(
                parseInt( scenarioDateOverride.substring(5,7) ) + "/" + scenarioDateOverride.substring(2,4)
            ) ;
            $target.find( ".date-warning" ).show() ;
        }
    }
    showInfo( "defender" ) ;
    showInfo( "attacker" ) ;

    // NOTE: To stop the OBA panel from flickering on-screen, it is configured to be hidden
    // in the template, and we show it here after it has been loaded.
    $target.find( ".oba" ).show() ;
}

// --------------------------------------------------------------------

const IMPORT_FIELDS = [
    { key: "scenario_name", name: "scenario name", paramName: "SCENARIO_NAME", type: "text" },
    { key: "scenario_display_id", name: "scenario ID", paramName: "SCENARIO_ID", type: "text" },
    { key: "scenario_location", name: "location", paramName: "SCENARIO_LOCATION", type: "text" },
    { key: "scenario_date_iso", name: "scenario date", paramName: "SCENARIO_DATE", type: "date" },
    { key: "theater", name: "theater", paramName: "SCENARIO_THEATER", type: "select2" },
    { key: "defender_name", name: "defender", paramName: "PLAYER_1", type: "player" },
    { key: "defender_desc", name: "defender description", paramName: "PLAYER_1_DESCRIPTION", type: "text" },
    { key: "attacker_name", name: "attacker", paramName: "PLAYER_2", type: "player" },
    { key: "attacker_desc", name: "attacker description", paramName: "PLAYER_2_DESCRIPTION", type: "text" },
] ;

function onImportScenario()
{
    var warnings=[], warnings2=[] ;

    function getWarnings( scenario ) {

        // check if it's OK to import each field
        var buf ;
        IMPORT_FIELDS.forEach( function( importField ) {

            // check for warnings for the next field
            var newVal = trimString( scenario[ importField.key ] ) ;
            if ( newVal ) {
                var msg = eval( "checkImportField_" + importField.type )( importField, newVal ) ; // jshint ignore: line
                if ( msg ) {
                    if ( msg.substring(0,2) == "!=" )
                        newVal = msg.substring( 2 ) ;
                    else {
                        buf = [ "<div class='warning2'>",
                            "<img src='" + gImagesBaseUrl + "/warning.gif'>",
                            msg,
                            "</div>"
                        ] ;
                        warnings2.push( $( buf.join("") ) ) ;
                        return ;
                    }
                }
            }

            // get the next field's current value
            var currVal = eval( "getImportFieldCurrVal_" + importField.type )( importField ) ; // jshint ignore: line
            if ( ! currVal )
                return ;
            var displayCurrVal, extraMsg ;
            if ( $.isArray( currVal ) ) {
                displayCurrVal = currVal[1] ;
                extraMsg = currVal[2] ;
                currVal = currVal[0].trim() ;
            } else {
                currVal = currVal.trim() ;
                displayCurrVal = currVal ;
            }

            // compare the field's current value with what it will be changed to
            if ( currVal != newVal ) {
                // add a warning that the current value will be changed
                var checked = extraMsg ? "" : " checked" ;
                buf = [ "<div style='display:flex;align-items:center;'>",
                    "<input type='checkbox' name='" + importField.key + "'" + checked + ">",
                    "<span>", "Update the " + importField.name, "</span>"
                ] ;
                if ( displayCurrVal.length <= 20 ) {
                    buf.push( "&nbsp;", "<span class='hint'>", "(from \"" + displayCurrVal + "\")", "</span>" ) ;
                    buf.push( "</div>" ) ;
                } else {
                    buf.push( "</div>" ) ;
                    buf.push( "<div class='hint'>", "Currently \"" + displayCurrVal + "\".", "</div>" ) ;
                }
                if ( extraMsg )
                    buf.push( "<div class='hint'>", "<img src='"+gImagesBaseUrl+"/warning.gif'>", extraMsg, "</div>" ) ;
                warnings.push( $( buf.join("") ) ) ;
            }
        } ) ;
    }

    // check if it will be a clean import
    var scenario = $gScenarioCard.data( "scenario" ) ;
    getWarnings( scenario ) ;
    if ( warnings.length === 0 && warnings2.length === 0 ) {
        // yup - do the import
        doImportScenario( scenario ) ;
    } else {
        // nope - show the warnings
        if ( warnings.length > 0 ) {
            var buf = [
                "<div class='header'>",
                "<img src='" + gImagesBaseUrl + "/warning.gif'>",
                "<div class='caption'> Some values in your scenario will be changed: </div>",
                "</div>"
            ] ;
            warnings.unshift( $( buf.join("") ) ) ;
        }
        if ( warnings2.length > 0 ) {
            if ( warnings.length > 0 )
                warnings2[0].css( "margin-top", "0.5em" ) ;
            $.merge( warnings, warnings2 ) ;
        }
        $gImportWarnings.empty().append( warnings ).slideToggle( 100 ) ;
        $gConfirmImportButton.data( "scenario", scenario ).show() ;
        $gCancelImportButton.show() ;
        $gDownloadsButton.hide() ;
        $gImportScenarioButton.hide() ;
    }
}

function doImportScenario( scenario )
{
    // import each field
    IMPORT_FIELDS.forEach( function( importField ) {
        var $elem = $gDialog.find( ".import-control .warnings input[name='" + importField.key + "']" ) ;
        if ( $elem.length > 0 && ! $elem.prop("checked") )
            return ;
        var newVal = scenario[ importField.key ] ;
        eval( "doImportField_" + importField.type )( importField, newVal ) ; // jshint ignore: line
    } ) ;

    // update for the newly-connected scenario
    // NOTE: We could reset the ELR/SAN here, but if the user is importing on top of an existing setup,
    // the most likely reason is because they want to connect it to an ASA scenario, not because
    // they want to import a whole set of new details, so clearing the ELR/SAN wouldn't make sense.
    updateForConnectedScenario(
        scenario.scenario_id,
        scenario.roar ? scenario.roar.scenario_id : null
    ) ;

    // all done - we can now close the dialog
    $gDialog.dialog( "close" ) ;
}

function onConfirmImportScenario()
{
    // import the scenario
    var scenario = $gConfirmImportButton.data( "scenario" ) ;
    doImportScenario( scenario ) ;
}

function onCancelImportScenario()
{
    // remove all the warnings and cancel/confirm buttons, and revert back to the "import" state
    // NOTE: Because we "cancel" the import every time the scenario card is updated, we only
    // call slideToggle() if we actually need to.
    if ( $gImportWarnings.css( "display" ) != "none" ) {
        $gImportWarnings.slideToggle( 100, function() {
            // FUDGE! If the content box is short enough to not need a vertical scrollbar, but the warning box
            // causes one to appear, it doesn't go away when the warning box disappears. Triggering resizes
            // doesn't seem to help, so we force the content box to be taller, which accumulates, but stops
            // once the bottom reaches the bottom of the flex box. Sigh...
            var $content = $gScenarioCard.find( ".content" ) ;
            $content.css( "height", $content.outerHeight() + 100 ) ;
        } ) ;
    }
    $gConfirmImportButton.hide() ;
    $gCancelImportButton.hide() ;
    $gDownloadsButton.show() ;
    $gImportScenarioButton.show() ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function checkImportField_text( importField, newVal, warnings2 ) {
    return null ;
}

function getImportFieldCurrVal_text( importField ) {
    // get the current field value
    return $( "input[name='" + importField.paramName + "']" ).val().trim() ;
}

function doImportField_text( importField, newVal ) {
    // update the field in the scenario
    $( "input[name='" + importField.paramName + "']" ).val( newVal ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function checkImportField_select2( importField, newVal, warnings2 ) {
    if ( importField.paramName == "SCENARIO_THEATER" ) {
        // check if we will be able to import this theater
        if ( newVal && ! getEffectiveTheater( newVal ) ) {
            // nope - issue a warning
            return "Unknown theater: " + newVal ;
        }
    }
    return null ;
}

function getImportFieldCurrVal_select2( importField ) {
    // get the current field value
    if ( importField.paramName == "SCENARIO_THEATER" )
        return null ; // nb: this will always be updated without warning
    return $( "select[name='" + importField.paramName + "']" ).val().trim() ;
}

function doImportField_select2( importField, newVal ) {
    // update the field in the scenario
    if ( importField.paramName == "SCENARIO_THEATER" ) {
        if ( newVal ) {
            newVal = getEffectiveTheater( newVal ) ;
            if ( ! newVal )
                newVal = "other" ;
        }
    }
    var $elem = $( "select[name='" + importField.paramName + "']" ) ;
    $elem.val( newVal || "ETO" ).trigger( "change" ) ;
}

function getEffectiveTheater( theater ) {
    if ( gAppConfig.THEATERS.indexOf( theater ) !== -1 )
        return theater ;
    theater = gAppConfig.SCENARIOS_CONFIG["theater-mappings"][ theater ] ;
    if ( theater )
        return theater ;
    return null ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function checkImportField_date( importField, newVal, warnings2 ) {
    return null ;
}

function getImportFieldCurrVal_date( importField ) {
    // get the current field value
    if ( importField.paramName != "SCENARIO_DATE" )
        return null ; // nb: shouldn't get here!
    var scenarioDate = get_scenario_date() ;
    if ( ! scenarioDate )
        return null ;
    return [
        scenarioDate.toISOString().substring( 0, 10 ),
        scenarioDate.getDate() + " " + get_month_name(scenarioDate.getMonth()) + ", " + scenarioDate.getFullYear()
    ] ;
}

function doImportField_date( importField, newVal ) {
    // update the field in the scenario
    var $elem = $( "input[name='" + importField.paramName + "']" ) ;
    $elem.datepicker( "setDate",
        newVal ? $.datepicker.parseDate( "yy-mm-dd", newVal ) : null
    ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function checkImportField_player( importField, newVal, warnings2 ) {
    // check if we will be able to import this player
    if ( newVal ) {
        var effectiveNat = getEffectivePlayerNat( newVal ) ;
        if ( ! effectiveNat ) {
            // nope - issue a warning
            return "Unknown player: " + newVal ;
        }
        return "!=" + effectiveNat[0] ; // nb: tell the caller to update its "newVal"
    }
    return null ;
}

function getImportFieldCurrVal_player( importField ) {
    // get the current field value
    // NOTE: Player nationalities will be changed without warning, *if* they have no OB.
    // If they have OB, no warning will be issued if the nationality is the same.
    if ( importField.paramName == "PLAYER_1" && is_player_ob_empty( 1 ) )
        return null ;
    if ( importField.paramName == "PLAYER_2" && is_player_ob_empty( 2 ) )
        return null ;
    var currVal = $( "select[name='" + importField.paramName + "']" ).val() ;
    // NOTE: The extra warning will only show if the new player is different from the current player.
    return [ currVal, get_nationality_display_name(currVal), "This player's OB will be removed." ] ;
}

function doImportField_player( importField, newVal ) {
    // update the player's nationality in the scenario
    var effectiveNat = getEffectivePlayerNat( newVal ) ;
    if ( ! effectiveNat )
        return ; // nb: unknown nationality - ignore it
    newVal = effectiveNat[0] ;
    var $elem = $( "select[name='" + importField.paramName + "']" ) ;
    if ( $elem.val() != newVal ) {
        // NOTE: We manually call on_player_change() to reset the player's OB, so that the user
        // doesn't get a warning about losing OB settings when the player droplist is changed.
        var playerNo = importField.paramName.substring( importField.paramName.length-1 ) ;
        on_player_change( playerNo ) ;
        $elem.val( newVal ).trigger( "change" ) ;
    }
}

window.getEffectivePlayerNat = function( playerName ) {

    if ( ! playerName )
        return null ;

    // try to find an exact match with one of our nationalities
    var playerNameLC = playerName.toLowerCase() ;
    for ( var nat in gTemplatePack.nationalities ) {
        if ( gTemplatePack.nationalities[nat].display_name.toLowerCase() == playerNameLC )
            return [ nat, "exactMatch", playerName ] ;
    }

    // try to find a mapping (exact match)
    var nat2 = gAppConfig.SCENARIOS_CONFIG["nat-mappings"][ playerNameLC ] ;
    if ( nat2 )
        return [ nat2, "exactMapping", playerName ] ;

    // try to find a partial match with one of our nationalities
    for ( nat in gTemplatePack.nationalities ) {
        var natDisplayName = gTemplatePack.nationalities[ nat ].display_name ;
        if ( playerName.match( new RegExp( "\\b"+natDisplayName+"\\b" ), "i" ) )
            return [ nat, "partialMatch", natDisplayName ] ;
    }

    // try to find a mapping (partial match)
    var mappings = gAppConfig.SCENARIOS_CONFIG[ "nat-mappings" ] ;
    for ( var key in mappings ) {
        if ( playerName.match( new RegExp( "\\b"+key+"\\b", "i" ) ) )
            return [ mappings[key], "partialMapping", key ] ;
    }

    return null ;
} ;

// --------------------------------------------------------------------

function onDownloads() {

    // initialize
    var scenario = $gScenarioCard.data( "scenario" ) ;
    var eventHandlers = new jQueryHandlers() ;
    var $dlg ;

    function loadFileGroups( $fgroups ) {
        var $items = [] ;
        scenario.downloads.forEach( function( fgroup ) {
            var buf = [] ;
            var url = fgroup.screenshot || gImagesBaseUrl+"/missing-image.png" ;
            buf.push( "<div class='screenshot'>", "<img src='"+url+"'>", "</div>" ) ;
            buf.push( "<div>" ) ;
            if ( fgroup.user )
                buf.push( "<div class='contrib'>", "Contributed by <span class='user'>"+fgroup.user+"</span>", "</div>" ) ;
            if ( fgroup.timestamp ) {
                var tstamp = new Date( fgroup.timestamp ) ;
                tstamp = tstamp.toLocaleDateString( undefined, { day: "numeric", month: "long", year: "numeric" } ) ;
                buf.push( "<div class='timestamp'>", tstamp, "</div>" ) ;
            }
            if ( fgroup.vt_setup ) {
                buf.push( "<button class='vt_setup' data-url='" + fgroup.vt_setup + "' title='Import the vasl-templates setup'>",
                    "<img src='"+gImagesBaseUrl+"/sortable-add.png'>", "Import",
                    "</button>"
                ) ;
            }
            if ( fgroup.vasl_setup ) {
                buf.push( "<button class='vasl_setup' data-url='" + fgroup.vasl_setup + "' title='Download the VASL setup'>",
                    "<img src='"+gImagesBaseUrl+"/download.png'>", "Download",
                    "</button>"
                ) ;
            }
            buf.push( "</div>" ) ;
            var $item = $( "<li class='fgroup'>" + buf.join("") + "</li>" ) ;
            $item.find( "button.vt_setup" ).on( "click", function() {
                if ( ! is_scenario_dirty() )
                    onDownloadVtSetup( fgroup.vt_setup ) ;
                else {
                    ask( "Import scenario",
                        "<p> Your scenario has been changed. <p> Do you want to import a new scenario, and lose your changes?", {
                        width: 470,
                        ok: function() { onDownloadVtSetup( fgroup.vt_setup ) ; },
                    } ) ;
                }
            } ) ;
            $item.find( "button.vasl_setup" ).on( "click", function() {
                onDownloadVaslSetup( fgroup.vasl_setup ) ;
            } ) ;
            fixup_external_links( $item ) ;
            $items.push( $item ) ;
        } ) ;
        $fgroups.html( $items ) ;
    }

    function onDownloadVtSetup( url ) {
        // download the vasl-templates setup
        var $pleaseWait = showPleaseWaitDialog( "Downloading the scenario..." ) ;
        $.ajax( {
            url: url, type: "GET",
        } ).done( function( resp ) {
            $pleaseWait.dialog( "close" ) ;
            // the file was downloaded OK - load it into the UI
            var fname = url.split( "/" ).pop() ;
            if ( ! do_load_scenario( JSON.stringify(resp), fname ) )
                return ;
            // all done - we can now close the downloads popup *and* the parent search dialog
            $dlg.dialog( "close" ) ;
            $gDialog.dialog( "close" ) ;
        } ).fail( function( xhr, status, errorMsg ) {
            $pleaseWait.dialog( "close" ) ;
            showErrorMsg( "Can't download the <em>vasl-templates</em> setup:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        } ) ;
    }

    function onDownloadVaslSetup( url ) {
        // download the VASL setup
        // FUDGE! Triggering a download (that works in both a browser window and the desktop app)
        // is depressingly tricky :-( We don't want to mess with window.location, since the download
        // could end up replacing the webapp in the browser :-/ Wrapping the button with an <a> tag
        // sorta works, but it can cause an external browser window to open, and remain open :-/
        // We download the file ourself and then ask the user to save it.
        var $pleaseWait = showPleaseWaitDialog( "Downloading the VASL scenario...", { width: 320 } ) ;
        $.ajax( {
            url: url, type: "GET",
            xhrFields: { responseType: "arraybuffer" }
        } ).done( function( resp ) {
            $pleaseWait.dialog( "close" ) ;
            // the file was downloaded OK - give it to the user to save
            var fname = url.split( "/" ).pop().split( "|" ).pop() ;
            if ( gWebChannelHandler ) {
                var vsavData = new Uint8Array( resp ) ;
                gWebChannelHandler.save_downloaded_vsav( fname,
                    btoa( String.fromCharCode.apply( null, vsavData ) )
                ) ;
            } else {
                download( resp, fname, "application/octet-stream" ) ;
            }
            // all done - we can now close the downloads popup
            $dlg.dialog( "close" ) ;
        } ).fail( function( xhr, status, errorMsg ) {
            $pleaseWait.dialog( "close" ) ;
            showErrorMsg( "Can't download the VASL scenario:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        } ) ;
    }

    // show the dialog
    $( "#scenario-downloads-dialog" ).dialog( {
        dialogClass: "scenario-downloads",
        title: "Downloads for this scenario:",
        modal: true,
        width: 450, minWidth: 300,
        height: 200, minHeight: 150,
        draggable: false,
        closeOnEscape: false, // nb: handled in handle_escape()
        open: function() {
            $dlg = $(this) ;
            $dlg.parent().draggable() ;
            eventHandlers.addHandler( $(".ui-widget-overlay"), "click", function( evt ) {
                $dlg.dialog( "close" ) ; // nb: clicking outside the popup closes it
            } ) ;
            // load the available downloads
            var $fgroups = $dlg.find( ".fgroups" ) ;
            loadFileGroups( $fgroups ) ;
            $(this).css( "height", Math.min( $fgroups.outerHeight(), 400 ) ) ;
            var $parentDlg = $( ".ui-dialog.scenario-search" ) ;
            $( ".ui-dialog.scenario-downloads" ).position( {
                my: "right bottom", at: "right top-2", of: $parentDlg.find( "button.downloads" )
            } ) ;
        },
        close: function() {
            // clean up
            eventHandlers.cleanUp() ;
        },
    } ) ;
}

// --------------------------------------------------------------------

function updateLayout()
{
    // resize and position the search select2
    var $dlg = $( "#scenario-search" ) ;
    var $sel = $dlg.find( ".select2-container" ) ;
    $dlg.find( ".select2-dropdown" ).css( "width",
        $dlg.find( ".scenarios" ).width()
    ) ;
    var newHeight = $dlg.find( ".scenarios" ).height() - $dlg.find( ".select2-search" ).height() - 15 ;
    $sel.find( ".select2-results__options" ).css( {
        height: newHeight,
        "max-height": newHeight,
    } ) ;

    // resize and position the info box
    updateInfoBox( $dlg ) ;
}

function updateInfoBox( $parent )
{
    // resize and position the info box
    var $header = $parent.find( ".scenario-card .header" ) ;
    var $info = $parent.find( ".scenario-card .info" ) ;
    if ( $header.length > 0 && $info.length > 0 ) {
        $header.css( { "padding-right": $info.width() + 30 } ) ;
        var newTop = $header.outerHeight() + 5 - $info.outerHeight() ;
        $info.css( { top: Math.max( newTop, 10 ), right: 10 } ) ;
        // NOTE: To stop the info box from jumping around visibly, it is configured to be hidden
        // in the template, and we show it here after it has been moved into position.
        $info.show() ;
    }
}

// --------------------------------------------------------------------

function makeBalanceGraphs( $target, scenario, showRoarButtons )
{
    // NOTE: If we have balance graphs for both the ASL Scenario Archive and ROAR, we try to show
    // the players in the same order for both. Since the player nationalities may be unknown to us,
    // we just do a simple text comparison on the display names.
    // NOTE: If we only have the ROAR balance, it would be nice to order the players so that they match
    // the ASL Scenario Archive's attacker/defender order, but would be more trouble than it's worth :-/
    var asaBalance = scenario.balance ;
    var roarBalance = scenario.roar ? scenario.roar.balance : null ;
    var roar_url = scenario.roar ? scenario.roar.url : null ;
    if ( asaBalance && roarBalance ) {
        if ( ( asaBalance[0].name.toLowerCase() == roarBalance[1].name.toLowerCase() ) ||
             ( asaBalance[1].name.toLowerCase() == roarBalance[0].name.toLowerCase() ) ) {
            var tmp = roarBalance[0] ;
            roarBalance[0] = roarBalance[1] ;
            roarBalance[1] = tmp ;
        }
    }

    // make the balance graphs
    var rc1 = doMakeBalanceGraph( $target.find( ".balance-graph.asa" ),
        asaBalance, scenario.scenario_url, false,
        "Balance at the ASL Scenario Archive"
    ) ;
    var rc2 = doMakeBalanceGraph( $target.find( ".balance-graph.roar" ),
        roarBalance, roar_url, true,
        "Balance at ROAR"
    ) ;

    // update the UI
    if ( showRoarButtons && ! rc2 )
        $target.find( ".connect-roar" ).show() ;
    else
        $target.find( ".connect-roar" ).hide() ;
    if ( rc1 || rc2 )
        return true ;
    else {
        if ( ! showRoarButtons )
            $target.find( ".balance-graphs" ).hide() ;
        return false ;
    }

    function doMakeBalanceGraph( $bgraph, balance, url, isRoar, tooltip )
    {
        // initialize
        if ( ! balance ) {
            $bgraph.hide() ;
            return false ;
        }
        var buf = [] ;
        var link1 = url ? "<a href='" + url + "'>" : "" ;
        var link2 = url ? "</a>" : "" ;

        // add the the 1st player's details
        buf.push( "<div class='player player1'>", balance[0].name, "</div>" ) ;
        buf.push( "&nbsp;" ) ;
        buf.push( "<div class='wins player1'>", "("+balance[0].wins+")", "</div>" ) ;
        buf.push( "&nbsp;", "&nbsp;" ) ;
        // NOTE: The wrapper div contains both progress bars (to work-around a Chromium rendering problem :-/).
        buf.push( "<div class='wrapper'>", link1, "<nobr>",
            "<div class='progressbar player1'>", "<div class='score'></div>", "</div>"
        ) ;

        // add the the 2nd player's details
        buf.push(
            "<div class='progressbar player2'>", "<div class='score'></div>", "</div>",
            "</nobr>", link2, "</div>"
        ) ;
        buf.push( "&nbsp;", "&nbsp;" ) ;
        buf.push( "<div class='wins player2'>", "("+balance[1].wins+")", "</div>" ) ;
        buf.push( "&nbsp;" ) ;
        buf.push( "<div class='player player2'>", balance[1].name, "</div>" ) ;

        // show the "disconnect from ROAR" button
        if ( showRoarButtons && isRoar ) {
            buf.push( "<div class='disconnect-roar'>",
                "<img src='" + gImagesBaseUrl+"/cross.png" + "' title='Disconnect from ROAR'>",
                "</div>"
            ) ;
        }

        // load the balance graph
        $bgraph.empty().append( buf.join("") ).show() ;
        fixup_external_links( $bgraph ) ;

        // configure the progressbar's
        $bgraph.find( ".progressbar" ).each( function() {
            var isPlayer1 = $(this).hasClass( "player1" ) ;
            var score =  balance[ isPlayer1 ? 0 : 1 ].percentage ;
            if ( score === undefined )
                score = 0 ;
            else
                score = parseInt( score ) ;
            $(this).progressbar( {
                value: isPlayer1 ? 100-score : score
            } ) ;
            $(this).children( ".score" ).text( score+"%" ) ;
            $(this).attr( "title", tooltip ) ;
        } ) ;

        // show the progressbar's in grey if there are not many playings
        var threshold = gAppConfig.BALANCE_GRAPH_THRESHOLD || 20 ;
        var totalGames = parseInt(balance[0].wins) + parseInt(balance[1].wins) ;
        if ( totalGames < threshold ) {
            var alpha = Math.max( totalGames / threshold, 0.5 ) ;
            var color = "rgba( 224, 224, 224, " + fpFmt(alpha,1) + ")" ;
            var borderColor = "#d0d0d0" ;
            $bgraph.find( ".progressbar.player1" ).css( "background", color ) ;
            $bgraph.find( ".progressbar.player2 .ui-progressbar-value" ).css( "background", color ) ;
            $bgraph.find( ".progressbar.player1" ).css( {
                border: "1px solid "+borderColor,
                "border-right": 0
            } ) ;
            $bgraph.find( ".progressbar.player2" ).css( "border", "1px solid "+borderColor ) ;
        }

        // add a click handler for "disconnect from ROAR"
        $bgraph.find( ".disconnect-roar" ).on( "click", function() {
            updateForConnectedScenario( scenario.scenario_id, null ) ;
            getScenarioData( scenario.scenario_id, null, function( newScenario ) {
                // NOTE: We enable "showRoarButtons" so that the "connect to ROAR" button appears.
                makeBalanceGraphs( $target, newScenario, true ) ;
                $target.find( ".connect-roar" ).show() ;
            } ) ;
        } ) ;

        return true ;
    }
}

// --------------------------------------------------------------------

window.showScenarioInfo = function()
{
    // initialize
    var $dlg ;
    var eventHandlers = new jQueryHandlers() ;
    var scenarioId = $( "input[name='ASA_ID']" ).val() ;
    var scenarioDate = get_scenario_date() ;

    function onResize() { updateInfoBox( $dlg ) ; }

    // request the scenario card
    var roarOverride = $( "input[name='ROAR_ID']" ).val() ;
    loadScenarioCard( $("#scenario-info-dialog .scenario-card"), scenarioId, false, scenarioDate, roarOverride, true,
        function( scenario ) {

            // show the dialog
            $( "#scenario-info-dialog" ).dialog( {
                dialogClass: "scenario-info",
                modal: true,
                closeOnEscape: false, // nb: handled in handle_escape()
                width: $(window).width() * 0.8,
                minWidth: 500,
                height: $(window).height() * 0.8,
                minHeight: 300,
                create: function() {
                    addAsaCreditPanel( $(".ui-dialog.scenario-info"), null ) ;
                },
                open: function() {
                    // initialize
                    $dlg = $(this) ;
                    var $draggable = $dlg.parent().draggable() ;
                    // add a click handler for "connect to ROAR"
                    $(this).find( ".connect-roar" ).on( "click", function() {
                        connectToRoar( $dlg.find(".scenario-card"), scenario ) ;
                    } ) ;
                    // change the credit link
                    var url = gAppConfig.ASA_SCENARIO_URL.replace( "{ID}", scenarioId ) ;
                    var $btnPane = $( ".ui-dialog.scenario-info .ui-dialog-buttonpane" ) ;
                    $btnPane.find( ".credit a" ).attr( "href", url ) ;
                    // configure the "upload scenario" button
                    var $btn = $btnPane.find( "button.upload" ) ;
                    $btn.prepend(
                        $( "<img src='" + gImagesBaseUrl+"/upload.png" + "' style='height:0.9em;margin:0 0.35em -1px 0;'>" )
                    ) ;
                    var creditWidth = $btnPane.find( ".credit" ).outerWidth() ;
                    $btn.css( { position: "absolute", left: creditWidth+20, padding: "2px 5px" } ) ;
                    $btn.attr( "title", "Upload your setup to the ASL Scenario Archive" ) ;
                    // configure the "unlink scenario" button
                    var $btn2 = $btnPane.find( "button.unlink" ) ;
                    $btn2.prepend(
                        $( "<img src='" + gImagesBaseUrl+"/cross.png" + "' style='height:0.6em;margin-right:0.35em;padding-bottom:1px;'>" )
                    ) ;
                    $btn2.css( { position: "absolute", left: creditWidth+40+$btn.outerWidth(), padding: "2px 5px" } ) ;
                    $btn2.attr( "title", "Unlink your scenario from the ASL Scenario Archive" ) ;
                    // update the layout
                    onResize() ;
                    eventHandlers.addHandler( $(document), "keydown", function( evt ) {
                        if ( evt.keyCode == 16 ) { // nb: checking evt.shiftKey is unreliable
                            window.getSelection().empty() ;
                            $draggable.draggable( "disable" ) ;
                        }
                    } ) ;
                    eventHandlers.addHandler( $(document), "keyup", function( evt ) {
                        if ( evt.keyCode == 16 )
                            $draggable.draggable( "enable" ) ;
                    } ) ;
                    // set initial focus
                    $btnPane.find( "button.ok" ).focus() ;
                },
                close: function() {
                    // clean up
                    eventHandlers.cleanUp() ;
                },
                resize: onResize,
                draggable: false,
                buttons: {
                    OK: { text: "OK", class: "ok", click: function() {
                        $dlg.dialog( "close" ) ;
                    } },
                    Unlink: { text: "Unlink", class: "unlink", click: function() {
                        updateForConnectedScenario( null, null ) ;
                        $dlg.dialog( "close" ) ;
                    } },
                    Upload: { text: "Upload", class: "upload", click: function() {
                        $dlg.dialog( "close" ) ;
                        uploadScenario() ;
                    } },
                },
            } ) ;
        },

        function( xhr, status, errorMsg ) {
            showErrorMsg( "Can't get the scenario card:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        }

    ) ;
} ;

function connectToRoar( $target, scenario )
{
    // ask the user to select a ROAR scenario
    selectRoarScenario( function( roarId ) {
        // save the selected ROAR scenario and update the UI
        updateForConnectedScenario( scenario.scenario_id, roarId ) ;
        getScenarioData( scenario.scenario_id, roarId, function( newScenario ) {
            if ( ! newScenario.roar || ! newScenario.roar.balance ) {
                showWarningMsg( "There are no playing results for this ROAR scenario." ) ;
                return ;
            }
            makeBalanceGraphs( $target, newScenario, true ) ;
        } ) ;
    } ) ;
}

// --------------------------------------------------------------------

window.updateForConnectedScenario = function( scenarioId, roarId )
{
    // save the scenario ID's
    $( "input[name='ASA_ID']" ).val( scenarioId ) ;
    $( "input[name='ROAR_ID']" ).val( roarId ) ;

    // update the UI
    var $btn = $( "button.scenario-search" ) ;
    if ( scenarioId ) {
        $btn.find( "img" ).attr( "src", gImagesBaseUrl+"/info.gif" ) ;
        $btn.attr( "title", "Scenario details" ) ;
    } else {
        $btn.find( "img" ).attr( "src", gImagesBaseUrl+"/search.png" ) ;
        $btn.attr( "title", "Search for scenarios" ) ;
    }
} ;

// --------------------------------------------------------------------

var _scenarioIndex ; // nb: don't access this directly, use getScenarioIndex()

function getScenarioIndex( onReady )
{
    // check if we already have the scenario index
    if ( _scenarioIndex ) {

        // yup - just do it
        onReady( _scenarioIndex ) ;

    } else {

        // nope - download it (nb: we do this on-demand, instead of during startup,
        // to give the backend time if it wants to download a fresh copy).
        $.getJSON( gGetScenarioIndexUrl, function( resp ) {
            if ( resp.warning ) {
                var msg = resp.warning ;
                if ( resp.message )
                    msg += "<div class='pre'>" + escapeHTML(resp.message) + "</div>" ;
                showWarningMsg( msg ) ;
                return ;
            }
            _scenarioIndex = resp ;
            onReady( resp ) ;
        } ).fail( function( xhr, status, errorMsg ) {
            showErrorMsg( "Can't get the scenario index:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
            return ;
        } ) ;

    }
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function getScenarioData( scenarioId, roarOverride, onReady )
{
    // get the scenario data
    var url = gGetScenarioUrl.replace( "ID", scenarioId ) ;
    if ( roarOverride )
        url = addUrlParam( url, "roar", roarOverride) ;
    $.getJSON( url, function( resp ) {
        onReady( resp ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        showErrorMsg( "Can't get the scenario details:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        return ;
    } ) ;
}

// --------------------------------------------------------------------

window.addAsaCreditPanel = function( $dlg, scenarioId )
{
    // create the credit panel
    var url = scenarioId ? gAppConfig.ASA_SCENARIO_URL.replace( "{ID}", scenarioId ) : "https://aslscenarioarchive.com" ;
    var buf = [ "<div class='credit'>",
        "<a href='"+url+"'>", "<img src='" + gImagesBaseUrl+"/asl-scenario-archive.png" + "'>", "</a>",
        "<div class='caption'>",
        "<a href='"+url+"'>", "Information provided by", "<br>", "the ASL Scenario Archive.", "</a>",
        "</div>",
        "</div>"
    ] ;
    var $credit = $( buf.join("") ) ;
    $credit.css( { float: "left", "margin-right": "0.5em", display: "flex", "align-items": "center" } ) ;
    $credit.find( "img" ).css( { height: "1.4em", "margin-right": "0.5em", opacity: 0.7 } ) ;
    $credit.find( ".caption" ).css( { "font-size": "70%", "line-height": "1em", "margin-top": "-4px" } ) ;
    $credit.find( "a" ).css( { "text-decoration": "none", "font-style": "italic", color: "#666" } ) ;
    $credit.find( "a" ).on( "click", function() { $(this).blur() ; } ) ;

    // add the credit panel to the dialog's button pane
    fixup_external_links( $credit ) ;
    var $btnPane = $dlg.find( ".ui-dialog-buttonpane" ) ;
    $btnPane.find( ".credit" ).remove() ;
    $btnPane.prepend( $credit ) ;
} ;

// --------------------------------------------------------------------

} )() ; // end local namespace
