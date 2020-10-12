( function() { // nb: put the entire file into its own local namespace, global stuff gets added to window.

var $gLogFilesToUpload ;
var gEventHandlers ;
var gDlgSizeAndPosition = {} ;
var gDisableClickToAddTimestamp = new Date() ;

// --------------------------------------------------------------------

window.on_analyze_vlog = function()
{
    // initialize
    var $dlg ;

    function onAddFile() {
        // FUDGE! Files can be removed from the upload list by using the mouse (e.g. Ctrl-Click,
        // or clicking on the "delete" icon), so we don't want to also trigger an "add" dialog.
        var delta = (new Date()).getTime() - gDisableClickToAddTimestamp.getTime() ;
        if ( delta <= 5 )
            return ;
        // add a file to the list of files to be analyzed
        if ( getUrlParam( "vlog_persistence" ) ) {
            // FOR TESTING PORPOISES! We can't control a file upload from Selenium (since
            // the browser will use native controls), so we get the data from a <textarea>).
            var $elem = $( "#_vlog-persistence_" ) ;
            var data = $elem.val() ;
            var pos = data.indexOf( "|" ) ;
            var fname = data.substring( 0, pos ) ;
            var vlog_data = data.substring( pos+1 ) ;
            $elem.val( "" ) ; // nb: let the test suite know we've received the data
            addFileToUploadList( fname, vlog_data ) ;
        } else {
            $("#load-vlog").trigger( "click" ) ; // nb: will call on_load_vlog_file_selected() when done
        }
    }

    // handle drag events for items already in the upload list
    var isDraggedOutside = null ;
    function onSortStart( evt, ui ) {
        isDraggedOutside = false ;
    }
    function onDragOutside( evt, ui ) { // nb: we get one of these even after a drag has ended :-/
        if ( isDraggedOutside === null )
            return ;
        isDraggedOutside = true ;
        ui.item.addClass( "dragOutside" ) ;
    }
    function onDragInside( evt, ui ) {
        isDraggedOutside = false ;
        ui.item.removeClass( "dragOutside" ) ;
    }
    function onDragEnd( evt, ui ) {
        if ( isDraggedOutside )
            removeFileFromUploadList( ui.item ) ;
        isDraggedOutside = null ;
    }

    // handle events for files being dragged in from outside the browser
    function initExternalDragDrop() {
        [ $gLogFilesToUpload, $dlg.find(".hint") ].forEach( function( $elem ) {
            gEventHandlers.addHandler( $elem, "dragenter", stopEvent ) ;
            gEventHandlers.addHandler( $elem, "dragleave", stopEvent ) ;
            gEventHandlers.addHandler( $elem, "dragover", stopEvent ) ;
            gEventHandlers.addHandler( $elem, "drop", function( evt ) {
                // add the files dragged in to the upload list
                addFilesToUploadList( evt.originalEvent.dataTransfer.files ) ;
                stopEvent( evt ) ;
            } ) ;
        } ) ;
    }

    // NOTE: We can't use the normal mechanism for handling Ctrl-Enter, since there are no input elements.
    // We do things using a document-level keydown event handler.
    function onKeyDown( evt ) {
        if ( $gLogFilesToUpload.find( "li" ).length === 0 ) {
            evt.preventDefault() ;
            return false ;
        }
        auto_dismiss_dialog( $dlg, evt, "OK" ) ;
    }

    // show the dialog
    gEventHandlers = new jQueryHandlers() ;
    $( "#lfa-upload" ).dialog( {
        title: "Analyze log files",
        dialogClass: "lfa-upload",
        modal: true,
        width: Math.min( gDlgSizeAndPosition.width || 400, $(window).innerWidth() ),
        minWidth: 400,
        height: Math.min( gDlgSizeAndPosition.height || 300, $(window).innerHeight() ),
        minHeight: 300,
        position: { my: "center", at: "center", of: window },
        create: function() {
            // initialize the dialog
            init_dialog( $(this), "OK", false ) ;
        },
        open: function() {
            // initialize the dialog
            $dlg = $(this) ;
            on_dialog_open( $(this) ) ;
            gEventHandlers.addHandler( $(document), "keydown", onKeyDown ) ;
            $gLogFilesToUpload = $( "#lfa-upload .files" ) ;
            $gLogFilesToUpload.sortable( {
                start: onSortStart,
                out: onDragOutside,
                over: onDragInside,
                beforeStop: onDragEnd,
            } ).empty() ;
            initExternalDragDrop() ;
            gEventHandlers.addHandler( $gLogFilesToUpload, "click", onAddFile ) ;
            gEventHandlers.addHandler( $dlg.find(".hint"), "click", onAddFile ) ;
            updateUi() ;
        },
        beforeClose: function() {
            // save the current size and position
            gDlgSizeAndPosition = getElemSizeAndPosition( $(".ui-dialog.lfa-upload") ) ;
        },
        close: function() {
            // clean up handlers
            gEventHandlers.cleanUp() ;
        },
        buttons: {
            OK: function() {
                // unload the files to be analyzed
                var vlog_data = [] ;
                $gLogFilesToUpload.children( "li" ).each( function() {
                    vlog_data.push( [ $(this).attr("data-filename"), $(this).attr("data-vlog") ] ) ;
                } ) ;
                // analyze the log files
                $(this).dialog( "close" ) ;
                analyzeLogFiles( vlog_data ) ;
            },
            Cancel: function() { $(this).dialog( "close" ) ; },
        },
    } ) ;
} ;

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

window.on_load_vlog_file_selected = function() {
    // add the selected files to the upload list
    addFilesToUploadList( $( "#load-vlog" ).prop( "files" ) ) ;
} ;

function addFilesToUploadList( files )
{
    // initialize
    var currFileNo = 0 ;
    var fileReader = new FileReader() ;

    // add each log file to the list
    function loadNextFile() {
        if ( currFileNo >= files.length )
            return ;
        var currFile = files[ currFileNo ] ;
        fileReader.onload = function() {
            // get the file data
            vlog_data = removeBase64Prefix( fileReader.result ) ;
            // add the file to the list
            addFileToUploadList( currFile.name, vlog_data ) ;
            // read the next file
            ++ currFileNo ;
            loadNextFile() ;
        } ;
        fileReader.readAsDataURL( currFile ) ;
    }
    loadNextFile() ;
}

function addFileToUploadList( fname, vlog_data )
{
    // add the file to the upload list
    var buf = [ "<li>",
        "<img src='" + gImagesBaseUrl+"/lfa/file.png" + "' class='file'>",
        "<span class='filename'>", fname, "</span>",
        "<img src='" + gImagesBaseUrl+"/cross.png" + "' class='delete'>",
        "</li>"
    ] ;
    var $item = $( buf.join("") ) ;
    $item.attr( "data-filename", fname ) ;
    $item.attr( "data-vlog", vlog_data ) ;
    $gLogFilesToUpload.append( $item ) ;
    updateUi() ;

    // add click handlers to remove the file from the list
    gEventHandlers.addHandler( $item.children( ".delete" ), "click", function() {
        gDisableClickToAddTimestamp = new Date() ;
        removeFileFromUploadList( $(this).parent() ) ;
    } ) ;
    gEventHandlers.addHandler( $item, "click", function( evt ) {
        if ( evt.ctrlKey ) {
            gDisableClickToAddTimestamp = new Date() ;
            removeFileFromUploadList( $(this) ) ;
        }
    } ) ;
}

function removeFileFromUploadList( $item ) {
    // remove the file from the upload list
    $item.remove() ;
    setTimeout( updateUi, 100 ) ; // nb: we need this after a drag-out :-/
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function updateUi()
{
    // update the UI
    var nFiles = $gLogFilesToUpload.find( "li" ).length ;
    var $btn = $( ".ui-dialog.lfa-upload button.ok" ) ;
    var $hint = $( ".ui-dialog.lfa-upload .hint" ) ;
    if ( nFiles > 0 ) {
        $btn.button( "enable" ) ;
        $hint.hide() ;
    } else {
        $btn.button( "disable" ) ;
        $hint.show() ;
    }
}

// --------------------------------------------------------------------

function analyzeLogFiles( vlog_data )
{
    // send a request to analyze the log files
    var objName = pluralString( vlog_data.length, "log file", "log files" ) ;
    var $pleaseWait = showPleaseWaitDialog( "Analyzing your " + objName + "...", { width: 255 } ) ;
    $.ajax( {
        url: gAnalyzeVlogsUrl,
        type: "POST",
        data: JSON.stringify( vlog_data ),
        contentType: "application/json",
    } ).done( function( data ) {
        $pleaseWait.dialog( "close" ) ;
        resp = checkResponse( data, objName ) ;
        if ( ! resp )
            return ;
        show_lfa_dialog( resp ) ;
    } ).fail( function( xhr, status, errorMsg ) {
        $pleaseWait.dialog( "close" ) ;
        showErrorMsg( "Can't analyze the " + objName + ":<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
    } ) ;
}

function checkResponse( resp, objName )
{
    // check if there was an error
    if ( resp.error ) {
        // yup - report it
        if ( getUrlParam( "vlog_persistence" ) ) {
            $( "#_vlog-persistence_" ).val(
                "ERROR: " + resp.error + "\n\n=== STDOUT ===\n" + resp.stdout + "\n=== STDERR ===\n" + resp.stderr
            ) ;
        } else {
            show_vassal_shim_error_dlg( resp,  "Can't analyze the " + objName + "." ) ;
        }
        return null ;
    }

    // check if anything was extracted
    if ( resp.logFiles ) {
        var totalEvents = 0 ;
        resp.logFiles.forEach( function( logFile ) {
            totalEvents += logFile.events.length ;
        } ) ;
        if ( totalEvents === 0 ) {
            showWarningMsg( "Couldn't find anything in the " + objName + "." +
                "<p> " + pluralString(resp.logFiles.length,"It's","They're") + " probably either not a log file, or from an old version of VASL."
            ) ;
            return null ;
        }
    }

    return resp ;
}

// --------------------------------------------------------------------

} )() ; // end local namespace
