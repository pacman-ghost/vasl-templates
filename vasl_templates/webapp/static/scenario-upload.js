/* jshint esnext: true */

( function() { // nb: put the entire file into its own local namespace, global stuff gets added to window.

var gVsavData, gScreenshotData ;
var $gDialog, $gVsavContainer, $gScreenshotContainer ;

// --------------------------------------------------------------------

window.uploadScenario = function() {

    // initialize
    var asaScenarioId = $( "input[name='ASA_ID']" ).val() ;

    function onAddVsavFile() {
        if ( ! canAddVsavFile() )
            return ;
        if ( getUrlParam( "vsav_persistence" ) ) {
            // FOR TESTING PORPOISES! We can't control a file upload from Selenium (since
            // the browser will use native controls), so we get the data from a <textarea>).
            var $elem = $( "#_vsav-persistence_" ) ;
            var vsavData = $elem.val() ;
            $elem.val( "" ) ; // nb: let the test suite know we've received the data
            doSelectVsavData( "test.vsav", vsavData ) ;
            return ;
        }
        $( "#select-vsav-for-upload" ).trigger( "click" ) ; // nb: onSelectVsavFile() will be called
    }
    function canAddVsavFile() {
        return $gVsavContainer.find( ".hint" ).css( "display" ) !== "none" ;
    }
    function onSelectVsavFile( file ) {
        // read the selected file
        var fileReader = new FileReader() ;
        fileReader.onload = function() {
            var vsavData = fileReader.result ;
            var fname = file.name ;
            // check the file size
            var maxBytes = gAppConfig.ASA_MAX_VASL_SETUP_SIZE ;
            if ( maxBytes <= 0 )
                doSelectVsavData( fname, vsavData ) ;
            else {
                var vsavDataDecoded = atob( removeBase64Prefix( vsavData ) ) ;
                if ( vsavDataDecoded.length <= 1024*maxBytes )
                    doSelectVsavData( fname, vsavData ) ;
                else {
                    ask( "ASL Scenario Archive upload",
                        "VASL scenario files should be less than " + maxBytes + " KB.", {
                        ok: function() { doSelectVsavData( fname, vsavData ) ; },
                        ok_caption: "Continue",
                    } ) ;
                }
            }
        } ;
        fileReader.readAsDataURL( file ) ;
    }
    function doSelectVsavData( fname, vsavData ) {
        // show the file details in the UI
        $gVsavContainer.find( ".hint" ).hide() ;
        var $fileInfo = $gVsavContainer.find( ".file-info" ) ;
        $fileInfo.find( ".name" ).text( fname ) ;
        $fileInfo.show() ;
        // prepare the upload
        // NOTE: We do this here (rather than when the user clicks the "Upload" button),
        // so that we can show the generated screenshot.
        vsavData = removeBase64Prefix( vsavData ) ;
        prepareUploadFiles( fname, vsavData ) ;
    }

    function onAddScreenshotFile() {
        if ( ! canAddScreenshotFile() )
            return ;
        $( "#select-screenshot-for-upload" ).trigger( "click" ) ; // nb: onSelectScreenshotFile() will be called
    }
    function canAddScreenshotFile() {
        return $gScreenshotContainer.find( ".hint" ).css( "display" ) !== "none" ;
    }
    function onSelectScreenshotFile( file ) {
        // read the selected image file
        var fileReader = new FileReader() ;
        fileReader.onload = function() {
            var imageData = fileReader.result ;
            var fname = file.name ;
            // check the file size
            var maxBytes = gAppConfig.ASA_MAX_SCREENSHOT_SIZE ;
            if ( maxBytes <= 0 )
                doSelectScreenshotFile() ;
            else {
                var imageDataDecoded = atob( removeBase64Prefix( imageData ) ) ;
                if ( imageDataDecoded.length <= 1024*maxBytes )
                    doSelectScreenshotFile() ;
                else {
                    ask( "ASL Scenario Archive upload",
                        "Screenshots should be less than " + maxBytes + " KB.", {
                        ok: doSelectScreenshotFile,
                        ok_caption: "Continue",
                    } ) ;
                }
            }
            function doSelectScreenshotFile() {
                // show the image preview
                setScreenshotPreview( imageData, true ) ;
                imageData = removeBase64Prefix( imageData ) ;
                gScreenshotData = [ fname, atob(imageData) ] ;
            }
        } ;
        fileReader.readAsDataURL( file ) ;
    }

    function initExternalDragDrop() {
        // disable events we're not interested in
        [ $gVsavContainer, $gScreenshotContainer ].forEach( function( $elem ) {
            $elem.on( "dragenter", stopEvent ) ;
            $elem.on( "dragleave", stopEvent ) ;
            $elem.on( "dragover", stopEvent ) ;
        } ) ;
        // add handlers for files dropped in
        $gVsavContainer.on( "drop", function( evt ) {
            if ( ! canAddVsavFile() )
                return ;
            onSelectVsavFile( evt.originalEvent.dataTransfer.files[0] ) ;
            stopEvent( evt ) ;
        } ) ;
        $gScreenshotContainer.on( "drop", function( evt ) {
            if ( ! canAddScreenshotFile() )
                return ;
            onSelectScreenshotFile( evt.originalEvent.dataTransfer.files[0] ) ;
            stopEvent( evt ) ;
        } ) ;
    }

    function updateUi()
    {
        // update the UI
        var userName = $gDialog.find( ".auth .user" ).val().trim() ;
        var apiToken = $gDialog.find( ".auth .token" ).val().trim() ;
        $( ".ui-dialog.scenario-upload button.upload" ).button(
            userName !== "" && apiToken !== "" ? "enable" : "disable"
        ) ;
    }

    // shpw the upload dialog
    $( "#scenario-upload-dialog" ).dialog( {
        title: "Upload to the ASL Scenario Archive",
        dialogClass: "scenario-upload",
        modal: true,
        width: 800, minWidth: 800,
        height: 500, minHeight: 500,
        create: function() {
            // add handlers to add files to be uploaded
            $gVsavContainer = $(this).find( ".vsav-container" ) ;
            $gVsavContainer.on( "click", onAddVsavFile ) ;
            $( "#select-vsav-for-upload" ).on( "change", function() {
                onSelectVsavFile( $( "#select-vsav-for-upload" ).prop("files")[0] ) ;
            } ) ;
            $gScreenshotContainer = $(this).find( ".screenshot-container" ) ;
            $gScreenshotContainer.on( "click", onAddScreenshotFile ) ;
            $( "#select-screenshot-for-upload" ).on( "change", function() {
                onSelectScreenshotFile( $( "#select-screenshot-for-upload" ).prop("files")[0] ) ;
            } ) ;
            // add handlers to remove files to be uploaded
            $gVsavContainer.find( ".remove" ).on( "click", function( evt ) {
                gVsavData = null ;
                $gVsavContainer.find( ".file-info" ).hide() ;
                $gVsavContainer.find( ".remove" ).hide() ;
                $gVsavContainer.find( ".hint" ).show() ;
                setScreenshotPreview( null ) ;
                stopEvent( evt ) ;
            } ) ;
            $gScreenshotContainer.find( ".remove" ).on( "click", function( evt ) {
                setScreenshotPreview( null ) ;
                stopEvent( evt ) ;
            } ) ;
            // add keyboard handlers
            $(this).find( ".auth .user" ).on( "keyup", updateUi ) ;
            $(this).find( ".auth .token" ).on( "keyup", updateUi ) ;
            // initialize
            initExternalDragDrop() ;
        },
        open: function() {
            // initialize
            $gDialog = $(this) ;
            $gDialog.find( ".auth .user" ).val( gUserSettings["asa-user-name"] ) ;
            $gDialog.find( ".auth .token" ).val( gUserSettings["asa-api-token"] ? atob(gUserSettings["asa-api-token"]) : "" ) ;
            $gVsavContainer.find( ".hint" ).show() ;
            $gVsavContainer.find( ".file-info" ).hide() ;
            $gScreenshotContainer.find( ".hint" ).show() ;
            $gScreenshotContainer.find( ".preview" ).hide() ;
            // initialize
            gVsavData = gScreenshotData = null ;
            // load the dialog
            var scenarioName = $("input[name='SCENARIO_NAME']").val().trim() ;
            if ( scenarioName )
                $gDialog.find( ".scenario-name" ).text( scenarioName ) ;
            var scenarioId = $("input[name='SCENARIO_ID']").val().trim() ;
            if ( scenarioId )
                $gDialog.find( ".scenario-id" ).text( "(" + scenarioId + ")" ) ;
            $gDialog.find( ".asa-id" ).text( "(#" + asaScenarioId + ")" ) ;
            var url = gAppConfig.ASA_SCENARIO_URL.replace( "{ID}", asaScenarioId ) ;
            $gDialog.find( ".disclaimer a.asa-scenario" ).attr( "href", url ) ;
            // update the UI
            fixup_external_links( $gDialog ) ;
            addAsaCreditPanel( $(".ui-dialog.scenario-upload"), asaScenarioId ) ;
            var $btnPane = $( ".ui-dialog.scenario-upload .ui-dialog-buttonpane" ) ;
            var $btn = $btnPane.find( "button.upload" ) ;
            $btn.prepend(
                $( "<img src='" + gImagesBaseUrl+"/upload.png" + "' style='height:0.8em;margin:0 0.35em -1px 0;'>" )
            ) ;
            onResize() ;
            updateUi() ;
        },
        resize: onResize,
        buttons: {
            Upload: { text: "Upload", class: "upload", click: function() {
                uploadFiles( asaScenarioId ) ;
            } },
            Cancel: function() {
                $gDialog.dialog( "close" ) ;
            },
        },
    } ) ;
} ;

// --------------------------------------------------------------------

function uploadFiles( asaScenarioId )
{
    // check if a full set of files is being uploaded
    var warningMsg, width ;
    if ( ! gVsavData && ! gScreenshotData ) {
        warningMsg = "<p> Only the <em>" + gAppConfig.APP_NAME + "</em> setup will be uploaded." +
            "<p> Do you want to skip uploading a VASL setup and screenshot?" ;
        width = 480 ;
    } else if ( ! gVsavData )
        warningMsg = "Do you want to skip uploading a VASL setup?" ;
    else if ( ! gScreenshotData )
        warningMsg = "Do you want to skip uploading a screenshot of the VASL setup?" ;
    if ( ! warningMsg ) {
        // yup - just do it
        doUploadFiles() ;
    } else {
        // nope - confirm with the user first
        ask( "ASL Scenario Archive upload", warningMsg, {
            width: width,
            ok: doUploadFiles,
            ok_caption: "Continue",
        } ) ;
    }

    function doUploadFiles() {

        // unload the vasl-templates setup
        var vtSetup = unload_params_for_save( true ) ;
        delete vtSetup.VICTORY_CONDITIONS ;
        delete vtSetup.SSR ;

        // unload the authentication details
        var userName = $gDialog.find( ".auth .user" ).val().trim() ;
        var apiToken = $gDialog.find( ".auth .token" ).val().trim() ;
        gUserSettings["asa-user-name"] = userName ;
        gUserSettings["asa-api-token"] = btoa( apiToken ) ;
        save_user_settings() ;

        // generate a unique prefix for the filenames
        // NOTE: We want to upload the files as a group, so that when we get them back, we can tell
        // which screenshots go with which VASL/vasl-templates setups. The ASL Scenario Archive doesn't
        // provide a mechanism for doing this, so we do it by adding a prefix to the filenames.
        // This is separated from the real filename with a pipe character, so that we (and the website)
        // can figure out what the real filename is.
        // NOTE: This is not actually necssary any more, since the ASL Scenario Archive only maintains
        // the most recently uploaded group of files for a given user+scenario, but it's not a bad idea
        // for us to keep doing this.
        var prefix = userName + ":" + Math.floor(Date.now()/1000) ;

        // prepare the upload
        var formData = new FormData() ;
        formData.append( "vt_setup",
            makeBlob( JSON.stringify( vtSetup, null, 4 ), "application/json" ),
            prefix + "|" + "scenario.json"
        ) ;
        if ( gVsavData ) {
            formData.append( "vasl_setup",
                makeBlob( gVsavData[1] ),
                prefix + "|" + gVsavData[0]
            ) ;
        }
        if ( gScreenshotData ) {
            formData.append( "screenshot",
                makeBlob( gScreenshotData[1] ),
                prefix + "|" + gScreenshotData[0]
            ) ;
        }

        // upload the files
        var url = gAppConfig.ASA_UPLOAD_URL ;
        if ( getUrlParam( "vsav_persistence" ) ) {
            // NOTE: We are in test mode - always upload to our own test endpoint.
            url = "/test-asa-upload/{ID}?user={USER}&token={TOKEN}" ;
        }
        url = url.replace( "{ID}", asaScenarioId ).replace( "{USER}", userName ).replace( "{TOKEN}", apiToken ) ;
        var $pleaseWait = showPleaseWaitDialog( "Uploading your scenario...", { width: 260 } ) ;
        $.ajax( {
            url: url,
            method: "POST",
            data: formData,
            dataType: "json",
            contentType: false,
            processData: false,
        } ).done( function( resp ) {

            // check the response
            $pleaseWait.dialog( "close" ) ;
            if ( resp.result.status == "ok" ) {
                var msg = resp.result.message ? resp.result.message.replace("1 file(s)","1 file") : "The scenario was uploaded OK." ;
                showInfoMsg( msg ) ;
                // all done - we can close the dialog now
                // NOTE: While the uploaded files are available on the website immediately, we normally wouldn't
                // see them here for quite a while (since we need to wait until we download a new copy of the scenarios).
                // This is a little unsatisfactory - the user would like to see their uploads here immediately - so we
                // notify the back-end, and it will get a fresh copy of just this scenario. Other users still won't see
                // the new files until they download a new copy of the scenario index, but there's not much we can do
                // about that. Since this is all happening in the background, we can still close the dialog and return
                // to the user, and only show a notification if something goes wrong.
                onSuccessfulUpload() ;
                $gDialog.dialog( "close" ) ;
            } else if ( resp.result.status == "warning" )
                showWarningMsg( resp.result.message ) ;
            else if ( resp.result.status == "error" )
                showErrorMsg( resp.result.message ) ;
            else
                showErrorMsg( "Unknown response status: " + resp.result.status ) ;

        } ).fail( function( xhr, status, errorMsg ) {

            // the upload failed - report the error
            $pleaseWait.dialog( "close" ) ;
            showErrorMsg( "Can't upload the scenario:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;

        } ) ;

    }

    function onSuccessfulUpload() {
        // notify the backend that the files were uploaded successfully
        $.ajax( {
            url: gOnSuccessfulAsaUploadUrl.replace( "ID", asaScenarioId ),
        } ).done( function( resp ) {
            if ( resp.status !== "ok" ) {
                showWarningMsg( "Couldn't update the local scenario index:" +
                    "<div class='pre'>" + escapeHTML(resp.message) + "</div>"
                ) ;
            }
        } ).fail( function( xhr, status, errorMsg ) {
            showErrorMsg( "Couldn't update the local scenario index:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;
        } ) ;
    }
}

// --------------------------------------------------------------------

function prepareUploadFiles( vsavFilename, vsavData )
{
    function removeLoadingSpinner() {
        $gScreenshotContainer.find( ".preview" ).hide() ;
        $gScreenshotContainer.find( ".hint" ).show() ;
        // NOTE: This function is called if the prepare failed, so we want to show
        // the "remove" button, so the user can remove the (possibly) invalid VSAV file.
        $gVsavContainer.find( ".remove" ).show() ;
    }

    // send a request to the backend to prepare the files
    setScreenshotPreview( gImagesBaseUrl + "/loader.gif", false ) ;
    var data = {
        filename: vsavFilename,
        vsav_data: vsavData,
    } ;
    $.ajax( {
        url: gPrepareAsaUploadUrl,
        type: "POST",
        data: JSON.stringify( data ),
        contentType: "application/json",
    } ).done( function( resp ) {

        // check the response
        data = _check_vassal_shim_response( resp, "Can't prepare the VASL scenario." ) ;
        if ( ! data ) {
            removeLoadingSpinner() ;
            return ;
        }

        // save the prepared files
        gVsavData = [ resp.filename, atob(resp.stripped_vsav) ] ;
        $gVsavContainer.find( ".remove" ).show() ;
        if ( resp.screenshot ) {
            gScreenshotData = [ "auto-generated.jpg", atob(resp.screenshot) ] ;
            setScreenshotPreview( "data:image/png;base64,"+resp.screenshot, true ) ;
        } else {
            showMsgDialog( "Screenshot error",
                "<p> <img src='" + gImagesBaseUrl+"/vassal-screenshot-hint.png" + "' style='height:12em;float:left;margin-right:1em;'>" +
                "Couldn't automatically generate a screenshot for the scenario." +
                "<p> Load the scenario into VASSAL and create one manually, then add it here.",
                550
            ) ;
            removeLoadingSpinner() ;
        }

    } ).fail( function( xhr, status, errorMsg ) {

        // the prepare failed - report the error
        removeLoadingSpinner() ;
        showErrorMsg( "Can't prepare the VASL scenario:<div class='pre'>" + escapeHTML(errorMsg) + "</div>" ) ;

    } ) ;
}

// --------------------------------------------------------------------

function setScreenshotPreview( imageData, isPreviewImage )
{
    // check if we should clear the current image preview
    if ( ! imageData ) {
        // yup - make it so
        gScreenshotData = null ;
        $gScreenshotContainer.find( ".preview" ).hide() ;
        $gScreenshotContainer.find( ".remove" ).hide() ;
        $gScreenshotContainer.find( ".hint" ).show() ;
        return ;
    }

    // load the screenshot preview image
    $gScreenshotContainer.find( ".hint" ).hide() ;
    var $preview = $gScreenshotContainer.find( ".preview" ).hide() ;
    var $img = $preview.find( "img" ) ;
    $img.css( "border-width", isPreviewImage ? "1px" : 0 ) ;
    $img.attr( "src", imageData ).on( "load", function() {
        onResize() ;
        $preview.show() ;
    } ) ;

    // update the "remove" button
    var $btn = $gScreenshotContainer.find( ".remove" ) ;
    if ( isPreviewImage )
        $btn.show() ;
    else
        $btn.hide() ;
}

function onResize()
{
    // FUDGE! The screenshot container and image are set to have a height of 100%,
    // but at some point, a parent element needs to have an actual height set.
    $gScreenshotContainer.css( "height",
        $gDialog.innerHeight() - $gScreenshotContainer.position().top  - 15
    ) ;
}

// --------------------------------------------------------------------

} )() ; // end local namespace
