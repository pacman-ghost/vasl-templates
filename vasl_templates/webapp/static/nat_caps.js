// --------------------------------------------------------------------

function set_nat_caps_params( player_nat, params )
{
    // get the national capabilities
    var is_kfw = params.SCENARIO_THEATER == "Korea" ;
    var nat_caps = get_national_capabilities( player_nat, is_kfw ) ;
    if ( ! nat_caps )
        return ;

    // initialize
    params.NAT_CAPS = {} ;
    var val ;

    function add_nat_cap( key, val ) {
        if ( val !== undefined )
            params.NAT_CAPS[ key ] = val ;
    }
    function fixup_content( val ) {
        val = strReplaceAll( val, "1st", "1<sup>st</sup>" ) ;
        val = strReplaceAll( val, "2nd", "2<sup>nd</sup>" ) ;
        return wrapExcWithSpan( val ) ;
    }

    // set the TH# color
    if ( nat_caps.th_color ) {
        if ( $.isArray( nat_caps.th_color ) ) {
            var buf = [
                make_time_based_comment( nat_caps.th_color[0], params.SCENARIO_MONTH, params.SCENARIO_YEAR ) + " TH#",
                " <span class='comment'>"
            ] ;
            var comment = nat_caps.th_color[ 1 ] ;
            if ( comment.substring( 0, 5 ) === "[EXC:" && comment[comment.length-1] === "]" )
                buf.push( comment ) ;
            else
                buf.push( "(" + comment + ")" ) ;
            buf.push( "</span>" ) ;
            add_nat_cap( "TH_COLOR", buf.join("") ) ;
        } else {
            var th_color = make_time_based_comment( nat_caps.th_color, params.SCENARIO_MONTH, params.SCENARIO_YEAR ) ;
            var match = th_color.match( /\(.+\)$/ ) ;
            if ( match )
                th_color = th_color.substring(0,match.index) + "TH# " + match[0] ;
            else
                th_color += " TH#" ;
            add_nat_cap( "TH_COLOR", th_color ) ;
        }
    }

    // set the HoB DRM
    if ( nat_caps.hob_drm ) {
        if ( $.isArray( nat_caps.hob_drm ) ) {
            add_nat_cap( "HOB_DRM",
                nat_caps.hob_drm[0] +
                " <span class='comment'>(" + nat_caps.hob_drm[1] + ")</span>"
            ) ;
        } else {
            add_nat_cap( "HOB_DRM", nat_caps.hob_drm ) ;
        }
    }

    // set the type of grenades available
    if ( nat_caps.grenades !== undefined ) {
        val = (nat_caps.grenades === null) ? "No" : make_time_based_comment( nat_caps.grenades, params.SCENARIO_MONTH, params.SCENARIO_YEAR ) ;
        add_nat_cap( "GRENADES", val+" grenades" ) ;
    }

    // set the OBA red/black numbers
    if ( nat_caps.oba ) {
        params.NAT_CAPS.OBA_BLACK = make_time_based_comment( nat_caps.oba[0], params.SCENARIO_MONTH, params.SCENARIO_YEAR ) ;
        params.NAT_CAPS.OBA_RED = make_time_based_comment( nat_caps.oba[1], params.SCENARIO_MONTH, params.SCENARIO_YEAR ) ;
        if ( nat_caps.oba.length > 2 ) {
            var oba_comments = [] ;
            for ( i=2 ; i < nat_caps.oba.length ; ++i ) {
                val = make_time_based_comment( nat_caps.oba[i], params.SCENARIO_MONTH, params.SCENARIO_YEAR ) ;
                if ( val )
                    oba_comments.push( val ) ;
            }
            if ( oba_comments.length > 0 )
                params.NAT_CAPS.OBA_COMMENTS = oba_comments ;
        }
    }

    // set the OBA access number
    add_nat_cap( "OBA_ACCESS", nat_caps.oba_access ) ;

    // add any additional notes
    if ( nat_caps.notes ) {
        params.NAT_CAPS.NOTES = [] ;
        for ( i=0 ; i < nat_caps.notes.length ; ++i ) {
            val = make_time_based_comment( nat_caps.notes[i], params.SCENARIO_MONTH, params.SCENARIO_YEAR ) ;
            if ( val )
                params.NAT_CAPS.NOTES.push( fixup_content( val ) ) ;
        }
    }
}

// --------------------------------------------------------------------

function get_national_capabilities( nat, is_kfw )
{
    // get the capabilities for the specified nationality
    if ( ! nat )
        return null ;
    if ( is_kfw ) {
        if ( nat === "american" )
            nat = "kfw-american" ;
        else if ( ["british","british~canadian","british~newzealand"].indexOf( nat ) !== -1 )
            nat = "kfw-bcfk" ;
    }
    else if ( nat === "free-french" || nat.substring(0,8) === "british~" )
        nat = "british" ;
    var nat_caps = gTemplatePack["national-capabilities"][ nat ] ;
    if ( nat_caps )
        return nat_caps ;
    if ( gTemplatePack.nationalities[ nat ] ) {
        var nat_type = gTemplatePack.nationalities[ nat ].type ;
        if ( nat_type )
            return gTemplatePack["national-capabilities"][ nat_type ] ;
    }
    return null ;
}

