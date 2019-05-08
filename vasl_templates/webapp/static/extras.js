
// --------------------------------------------------------------------

function init_extras()
{
    // initialize the layout
    $( "#tabs-extras .left-panel" ).resizable( {
        resizeHeight: false,
        handles: "e",
        create: function( event, ui ) {
            $( ".ui-resizable-e" ).css( "cursor", "ew-resize" ) ;
        },
    } ) ;

    // identify the extras templates
    var extra_templates = [] ;
    for ( var template_id in gTemplatePack.templates ) {
        if ( template_id.substr( 0, 7 ) === "extras/" ) {
            extra_templates.push(
                _parse_extra_template( template_id, gTemplatePack.templates[template_id] )
            ) ;
        }
    }

    // sort the extras templates by name
    extra_templates.sort( function( lhs, rhs ) {
        return lhs.name.localeCompare( rhs.name, "en", { sensitivity: "base" } ) ;
    } ) ;

    // build the side-panel showing the available templates
    var $index = $( "<ul></ul>" ) ;
    for ( var i=0 ; i < extra_templates.length ; ++i ) {
        var buf = [] ;
        buf.push( "<li class='ui-widget-content'>",
            "<div class='name'>", extra_templates[i].name, "</div>"
        ) ;
        if ( extra_templates[i].caption )
            buf.push( "<div class='caption'>", extra_templates[i].caption, "</div>" ) ;
        buf.push( "</div>", "</li>" ) ;
        var $entry = $( buf.join("") ) ;
        if ( i === 0 )
            $entry.addClass( "ui-selecting" ) ;
        $entry.data( "template_id", extra_templates[i].template_id ) ;
        $index.append( $entry ) ;
    }
    $index.selectable( {
        selected: function( evt, ui ) {
            _show_extra_template( $(ui.selected).data( "template_id" ) ) ;
        },
        selecting: function( evt, ui ) { // nb: prevent multiple selections
            if ( $index.find( ".ui-selected, .ui-selecting" ).length > 1 )
              $(ui.selecting).removeClass( "ui-selecting" ) ;
        },
    } ) ;
    $index.data( "ui-selectable" )._mouseStop( null ) ; // nb: trigger the selection
    $( "#tabs-extras .left-panel .content" ).empty().append( $index ) ;
}

// - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

function _show_extra_template( template_id )
{
    // parse the template (nb: we do this every time since the user may have changed it in the UI)
    var template_info = _parse_extra_template( template_id, gTemplatePack.templates[template_id] ) ;

    // generate the form for entering the template parameters
    var buf = [ "<div>" ] ;
    buf.push( "<div class='name'>", template_info.name, "</div>" ) ;
    if ( template_info.caption )
        buf.push( "<div class='caption'>", template_info.caption, "</div>" ) ;
    if ( template_info.description )
        buf.push( "<div class='description'>", template_info.description, "</div>" ) ;
    if ( template_info.params.length > 0 ) {
        buf.push( "<table>" ) ;
        for ( var i=0 ; i < template_info.params.length ; ++i ) {
            buf.push( "<tr>" ) ;
            var display_name = template_info.params[i].caption || template_info.params[i].name ;
            buf.push( "<td class='caption'>", escapeHTML(display_name)+":" ) ;
            buf.push( "<td class='value'>" ) ;
            var j ;
            if ( template_info.params[i].type === "input" ) {
                buf.push( "<input class='param' name='" + escapeHTML(template_info.params[i].name) + "' type='text'" ) ;
                if ( template_info.params[i].width )
                    buf.push( " size='" + escapeHTML(template_info.params[i].width) + "'" ) ;
                if ( template_info.params[i].default )
                    buf.push( " value='" + escapeHTML(template_info.params[i].default) + "'" ) ;
                if ( template_info.params[i].description )
                    buf.push( " title='" + escapeHTML(template_info.params[i].description) + "'" ) ;
                buf.push( ">" ) ;
            } else if ( template_info.params[i].type === "select" ) {
                buf.push( "<select class='param' name='" + escapeHTML(template_info.params[i].name) + "'>" ) ;
                for ( j=0 ; j < template_info.params[i].options.length ; ++j )
                    buf.push( "<option>", template_info.params[i].options[j], "</option>" ) ;
                buf.push( "</select>" ) ;
            } else if ( template_info.params[i].type.substr(0,22) === "player-color2-droplist" ) {
                buf.push( "<select class='param' name='PLAYER_COLOR2_DROPLIST' style='width:9em;'>" ) ;
                if ( template_info.params[i].type === "player-color2-droplist-ex" )
                    buf.push( "<option value='black'>black</option>", "<option value='#c0c0c0'>gray</option>" ) ;
                var nats = get_sorted_nats() ;
                for ( j=0 ; j < nats.length ; ++j ) {
                    var nat_info = gTemplatePack.nationalities[ nats[j] ] ;
                    buf.push( "<option value='", nat_info.ob_colors[2], "'>", nat_info.display_name, "</option>" ) ;
                }
                buf.push( "</select>" ) ;
            }
        }
        buf.push( "</table>" ) ;
    }
    buf.push( "<button class='generate' data-id='" + template_info.template_id + "'>Snippet</button>" ) ;
    buf.push( "</div>" ) ;
    var $form = $( buf.join("") ) ;
    $form.find( "select" ).select2( {
        minimumResultsForSearch: -1
    } ).on( "select2:open", function() {
        restrict_droplist_height( $(this) ) ;
    } ) ;
    fixup_external_links( $form ) ;

    // initialize the "generate" button
    init_snippet_button( $form.find( "button.generate" ) ) ;

    // install the form
    $( "#tabs-extras .right-panel" ).empty().append( $form ) ;
}

// --------------------------------------------------------------------

function _parse_extra_template( template_id, template )
{
    // extract the main details
    var result = { template_id: template_id, name: template_id } ;
    function extract_val( key ) {
        var match = template.match( new RegExp( "<!-- vasl-templates:" + key + " (.*?) -->" ) ) ;
        if ( match )
            result[key] = match[1] ;
    }
    extract_val( "name" ) ;
    extract_val( "caption" ) ;
    extract_val( "description" ) ;

    // extract the template parameters
    result.params = [] ;
    var params_regex = new RegExp( /\{\{(.*?)\}\}/g ) ;
    while( (match = params_regex.exec( template )) !== null ) {
        // extract the parameter name and default value
        var words = match[1].split( "|" ) ;
        var param = { name: words[0] } ;
        var pos = param.name.indexOf( ":" ) ;
        if ( pos === -1 )
            continue ;
        var val = param.name.substr( pos+1 ) ;
        param.name = param.name.substr( 0, pos ) ;
        if ( param.name === "CSS" )
            continue ;
        // figure out what type of parameter we have
        if ( val.indexOf( "::" ) !== -1 ) {
            // we have a <select>
            param.type = "select" ;
            param.options = val.split( "::" ) ;
        } else if ( param.name === "PLAYER_COLOR2_DROPLIST" )
            param.type = "player-color2-droplist" ;
        else if ( param.name === "PLAYER_COLOR2_DROPLIST_EX" )
            param.type = "player-color2-droplist-ex" ;
        else {
            // we have an <input>
            param.type = "input" ;
            // extract the default value and field width
            pos = val.indexOf( "/" ) ;
            if ( pos === -1 )
                param.default = val ;
            else {
                param.default = val.substr( 0, pos ) ;
                param.width = val.substr( pos+1 ) ;
            }
        }
        // extract the caption and description
        if ( words.length >= 2 )
            param.caption = words[1] ;
        if ( words.length >= 3 )
            param.description = words[2] ;
        result.params.push( param ) ;
    }

    return result ;
}

// --------------------------------------------------------------------

function fixup_template_parameters( template )
{
    // identify any non-standard template parameters
    var regex = /\{\{([A-Z0-9_]+?):.*?\}\}/g ;
    var matches = [] ;
    var match ;
    while( (match = regex.exec( template )) !== null )
        matches.push( [ regex.lastIndex-match[0].length, match[0].length, match[1] ] ) ;

    // fix them up
    var i ;
    if ( matches.length > 0 ) {
        for ( i=matches.length-1 ; i >= 0 ; --i )
            template = template.substr(0,matches[i][0]) + "{{"+matches[i][2]+"}}" + template.substr(matches[i][0]+matches[i][1]) ;
    }

    // remove all our special comments, except for the snippet ID
    regex = /<!-- vasl-templates:(.*?) .*? -->\n*/g ;
    matches = [] ;
    while( (match = regex.exec( template )) !== null ) {
        if ( match[1] !== "id" )
            matches.push( [ regex.lastIndex-match[0].length, match[0].length ] ) ;
    }
    if ( matches.length > 0 ) {
        for ( i=matches.length-1 ; i >= 0 ; --i )
            template = template.substr(0,matches[i][0]) + template.substr(matches[i][0]+matches[i][1]) ;
    }

    return template ;
}
