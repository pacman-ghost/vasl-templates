""" Utilities to help load the vehicle/ordnance listings. """

import os
import json
import re
import copy
import logging

from vasl_templates.webapp import app, globvars
from vasl_templates.webapp.config.constants import DATA_DIR

_vo_comments = None

# ---------------------------------------------------------------------

_NOTE_ID_PREFIXES = {
    "US": "american",
    "Br": "british",
    "Ge": "german",
    "Ru": "russian",
    "Fr": "french",
    "Ch": "chinese",
    "AllM": "allied-minor",
}

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

_COMMENT_HANDLERS = {
    "russian": {
        "vehicles": {
            "N": lambda vo_entry, note_id: _check_name( vo_entry, note_id, {
                "(a)": "American ESB",
                "(b)": "British ESB"
            } ),
            "LL": lambda vo_entry, note_id: _check_name( vo_entry, note_id, {
                "(a)": "{? 01/1944- | Black TH# | Red TH# | Black TH#<sup>44+</sup> ?}"
            }, "Black TH#" ),
        }
    },
    "british": {
        "vehicles": {
            "A": lambda vo_entry, note_id: _check_name( vo_entry, note_id, {
                "(a)": "American ESB+"
            } )
        }
    },
    "french": {
        "vehicles": {
            "F": lambda vo_entry, note_id: _check_name( vo_entry, note_id, {
                "(a)": _french_veh_f,
                "(b)": _french_veh_f,
                "(f)": _french_veh_f,
            } ),
        }
    },
    "finnish": {
        "vehicles": {
            "D": lambda vo_entry, note_id: _check_name( vo_entry, note_id, {
                "(b)": "British ESB",
                "(g)": [ "German ESB", "Black TH#" ],
                "(r)": "Russian ESB",
                "(s)": [ "Swedish ESB", "Black TH#" ]
            } )
        },
        "ordnance": {
            "B": lambda vo_entry, note_id: _check_name( vo_entry, note_id, {
                "(b)": "Black TH#",
                "(f)": "Black TH#",
                "(g)": [ "Black TH#", "No Captured Use penalty for Germans" ],
                "(r)": "No Captured Use penalty for Russians",
                "(s)": "Black TH#",
                "(t)": "Black TH#",
            } )
        }
    },
    "chinese": {
        "vehicles": {
            "A": lambda vo_entry, note_id: _check_name( vo_entry, note_id, {
                "(a)": [ "American ESB, +1 DRM" ],
                "(b)": [ "British ESB, +1 DRM" ],
                "(g)": [ "German ESB, +1 DRM" ],
                "(i)": [ "Italian ESB, +1 DRM" ],
                "(r)": [ "Russian ESB, +1 DRM" ],
            } ),
            "D": "2 TK DR"
        }
    },
    "allied-minor": {
        "vehicles": {
            "A": lambda vo_entry, note_id: _check_name( vo_entry, note_id, {
                "(a)": "American ESB+",
                "(b)": "British ESB+",
                "(f)": "French ESB+",
                "(i)": "Italian ESB+",
            } )
        }
    },
    "axis-minor": {
        "vehicles": {
            "E": lambda vo_entry, note_id: _check_name( vo_entry, note_id, {
                "(f)": "French ESB",
                "(g)": _axis_minor_veh_e,
                "(i)": "Italian ESB",
                "(r)": "Russian ESB",
                "(t)": _axis_minor_veh_e,
            } ),
        },
        "ordnance": {
            "E": lambda vo_entry, note_id: _check_name( vo_entry, note_id, {
                "(g)": _axis_minor_ord_e,
                "(t)": _axis_minor_ord_e,
            } ),
        }
    },
    "kfw-un": {
        "vehicles": {
            "UU": lambda vo_entry, note_id: _check_name( vo_entry, note_id, {
                "(a)": "American ESB+",
            } ),
        }
    }
}

def _check_comment_handlers( vo_entry, nat, vo_type, note_id, comments, orig_nat ):
    """Add any multi-applicable note-specific comments to the vehicle/ordnance."""
    val = _COMMENT_HANDLERS.get( nat, {} ).get( vo_type, {} ).get( note_id )
    if not val:
        return
    if isinstance( val, str ):
        comments.append( val )
    elif isinstance( val, list ):
        comments.extend( val )
    else:
        assert callable( val )
        val = val( vo_entry, orig_nat )
        if val:
            assert isinstance( val, list )
            comments.extend( val )

def _french_veh_f( vo_entry, orig_nat ): #pylint: disable=unused-argument
    """Handle French Vehicle Note F."""
    # NOTE: French Vehicle Note F says things like:
    #   "(a)" also indicates that this vehicle is treated as captured if crewed by other than Free French or U.S.
    # so we would like to be smart here and check the owning player's nationality and add a "Captured Use" comment
    # only if it applies. Unfortunately, while this technique works for the Allied/Axis Minor common vehicles/ordnance,
    # it won't here :-(
    # Consider a scenario where the British have an Ac de 40 CA(a). This piece won't appear in the list of
    # British vehicles, so the user has to set up a 2nd scenario, with a Free French player, to get access to
    # this piece. The code will detect the owning player is the Free French, and so conclude that it doesn't need
    # to add a "Captured Use" comment. There's no way of fixing this (other than adding the Free French
    # vehicles/ordnance to every nationality that could possibly use them), so we add the comment verbatim
    # and let the user figure it out.
    if "(a)" in vo_entry["name"]:
        comments = [ "Black TH#", "American ESB+" ]
        if vo_entry["id"] == "fr/v:020": # nb: AM Dodge(a)
            comments.append( "Captured Use (unless Vichy French)" )
        else:
            comments.append( "Captured Use (unless Free French or US)" )
    elif "(b)" in vo_entry["name"]:
        comments = [ "Black TH#", "British ESB+" ]
        comments.append( "Captured Use (unless Vichy French or British)" )
    elif "(f)" in vo_entry["name"]:
        comments = [ "Red TH#", "French ESB+" ]
        comments.append( "Captured Use (unless Free/Vichy French)" )
    else:
        comments = []
    return comments

def _axis_minor_veh_e( vo_entry, orig_nat ):
    """Handle Axis Minor Vehicle Note E (cases (g) and (t) only)."""
    assert "(g)" in vo_entry["name"] or "(t)" in vo_entry["name"]
    comments = [ "German ESB" if "(g)" in vo_entry["name"] else "Czech ESB" ]
    if orig_nat in ( "romanian", "hungarian", "slovakian" ):
        comments.append( "Black TH#" )
    return comments

def _axis_minor_ord_e( vo_entry, orig_nat ):
    """Handle Axis Minor Ordnance Note E."""
    assert "(g)" in vo_entry["name"] or "(t)" in vo_entry["name"]
    if orig_nat in ( "romanian", "hungarian", "slovakian" ):
        return [ "Black TH#" ]
    return None

def _check_name( vo_entry, nat, cases, defaultVal=None ):
    """Check the vehicle/ordnance's name."""
    for key,val in cases.items():
        if key in vo_entry.get("name",""):
            if isinstance( val, str ):
                return [val]
            elif isinstance( val, list ):
                return val
            else:
                assert callable( val )
                return val( vo_entry, nat )
    if defaultVal:
        return [defaultVal]
    return None

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def add_vo_comments( listings, vo_type, msg_store ):
    """Add comments to the vehicle/ordnance entries."""
    # Melbourne, Australia (JUN/20)

    # initialize
    global _vo_comments
    if not _vo_comments:
        fname = os.path.join( app.config.get("DATA_DIR",DATA_DIR), "vo-comments.json" )
        _vo_comments = json.load( open( fname, "r" ) )

    # process each vehicle/ordnance
    for nat,vo_entries in listings.items():
        for vo_entry in vo_entries:
            if "copy_from" in vo_entry:
                continue # nb: we do these later, when the entry is actually copied
            _do_add_vo_comments( vo_entry, nat, vo_type, msg_store )

def _do_add_vo_comments( vo_entry, nat, vo_type, msg_store ): #pylint: disable=too-many-locals,too-many-branches
    """Add comments to a vehicle/ordnance entry."""

    # figure out which comments have been disabled
    disable_comments_for_note_ids = set() # disable all omments associated with these note ID's
    disabled_comments = set() # disable these specific comments
    prefixes = "|".join( _NOTE_ID_PREFIXES.keys() )
    regex = re.compile( "^(({}) )?[A-Za-z]{{,2}}$".format( prefixes ) )
    vals = vo_entry.get( "disabled_comments", [] )
    for val in vals if isinstance(vals,list) else [vals]:
        if regex.search( val ):
            disable_comments_for_note_ids.add( val )
        else:
            disabled_comments.add( val )

    # get the vehicle/ordnance's manually-defined comments
    comments = vo_entry.get( "comments", [] )
    if isinstance( comments, str ):
        comments = [ comments ]

    # add any generated comments
    comments.extend(
        _make_comments( vo_entry, nat, vo_type, disable_comments_for_note_ids )
    )

    # dedupe the comments
    # NOTE: This needs to be done in the front-end as well, since some comments will be generated
    # based on the scenario date, and we have no way of knowing what that is here.
    comments2, comment_index = [], set()
    for cmt in comments:
        if cmt in comment_index:
            continue
        comments2.append( cmt )
        comment_index.add( cmt )

    # remove comments that have been disabled
    # NOTE: This needs to be done in the front-end as well, since some comments will be generated
    # based on the scenario date, and we have no way of knowing what that is here.
    comments3 = []
    def parse_cmd( cmt ):
        """Parse a disabled comment command."""
        if cmt.startswith( "?:" ):
            return cmt[2:].strip(), False # nb: this is an optional comment (i.e. don't warn if it's not there)
        else:
            return cmt, True
    disabled_comments = dict( parse_cmd(c) for c in disabled_comments )
    for cmt in comments2:
        if cmt in disabled_comments:
            del disabled_comments[ cmt ]
        else:
            comments3.append( cmt )
    disabled_comments = { k: v for k,v in disabled_comments.items() if v }
    if disabled_comments:
        if msg_store:
            msg_store.warning(
                "Can't find disabled comments for {}: <ul> {} </ul>".format(
                    vo_entry["id"],
                    " ".join( "<li> {}".format(c) for c in disabled_comments )
                )
            )

    # install the comments into the vehicle/ordnance entry
    if comments3:
        vo_entry["comments"] = comments3
    else:
        vo_entry.pop( "comments", None )

def _make_comments( vo_entry, nat, vo_type, disabled_note_ids ): #pylint: disable=too-many-branches
    """Automatically generate comments for a vehicle/ordnance."""

    # initialize
    all_comments = []

    # process each multi-applicable note
    vo_notes = vo_entry.get( "notes", [] )
    for note_id in vo_notes:

        # clean up the next note ID
        pos = note_id.find( "\u2020" )
        if pos >= 0:
            note_id = note_id[:pos]
        note_id = re.sub( r"\<sup\>.*?\</sup\>", "", note_id )
        note_id = re.sub( r"\<s\>.*?\</s\>", "", note_id )
        if not note_id:
            continue
        assert re.search( "^[A-Za-z0-9 ]+$", note_id )

        # translate nationality-specific note ID's
        orig_note_id = note_id
        force_auto_comment = False
        nat2 = nat
        nat_type = globvars.template_pack[ "nationalities" ].get( nat, {} ).get( "type" ) \
            if globvars.template_pack else None
        if nat in ( "kfw-uro", "kfw-bcfk", "kfw-un-common" ):
            nat2 = "kfw-un"
        elif nat in ( "kfw-kpa", "kfw-cpva" ):
            nat2 = "kfw-comm"
        elif nat_type == "allied-minor" or nat == "allied-minor-common":
            nat2 = "allied-minor"
        elif nat_type == "axis-minor" or nat == "axis-minor-common":
            nat2 = "axis-minor"
        words = note_id.split()
        if len(words) > 1:
            nat2 = _NOTE_ID_PREFIXES.get( words[0] )
            if nat2:
                note_id = " ".join( words[1:] )
            force_auto_comment = True

        # check if all comments for this note have been disabled
        if orig_note_id in disabled_note_ids:
            continue

        # generate any comments associated with this multi-applicable note
        comments = []
        if not vo_entry.get( "extn_id" ):
            # NOTE: We don't do this for extensions because if a vehicle/ordnance has Note X,
            # that references the extension's Note X, not the nationality's normal Note X.
            # However, vehicles/ordnance can reference things like "Ru M" or "AllM F", but these will
            # set force_auto_comment and cause those comments to be added below.
            if nat2 != nat:
                _check_comment_handlers( vo_entry, nat2, vo_type, note_id, comments, nat )
            else:
                _check_comment_handlers( vo_entry, nat, vo_type, note_id, comments, None )
        if not vo_entry.get( "extn_id" ) or force_auto_comment:
            auto_comments = _vo_comments.get( nat2, {} ).get( vo_type, {} ).get( note_id )
            if auto_comments:
                _append_to( comments, auto_comments )

        # update the vehicle/ordnance entry
        _append_to( all_comments, comments )

    return all_comments

def _append_to( dest, val ):
    """Append value(s) to a list."""
    assert isinstance( dest, list )
    if isinstance( val, str ):
        dest.append( val )
    elif isinstance( val, list ):
        dest.extend( val )
    else:
        assert False

# ---------------------------------------------------------------------

def copy_vo_entry( placeholder_vo_entry, src_vo_entry, nat, vo_type, msg_store ): #pylint: disable=too-many-branches
    """Create a new vehicle/ordnance entry by copying an existing one."""
    # Anjuna, India (FEB/19)

    # create the new vehicle/ordnance entry
    new_vo_entry = copy.deepcopy( src_vo_entry )
    new_vo_entry["id"] = placeholder_vo_entry["id"]
    if "name" in placeholder_vo_entry:
        new_vo_entry["name"] = placeholder_vo_entry["name"]
    if "gpid" in placeholder_vo_entry:
        new_vo_entry["gpid"] = placeholder_vo_entry["gpid"]
    elif "extra_gpids" in placeholder_vo_entry:
        if not isinstance( new_vo_entry["gpid"], list ):
            new_vo_entry["gpid"] = [ new_vo_entry["gpid"] ]
        new_vo_entry["gpid"].extend( placeholder_vo_entry["extra_gpids"] )

    def add_prefix( notes, prefix ):
        """Add a prefix to a list of note ID's."""
        for i,note in enumerate(notes):
            notes[i] = "{} {}".format( prefix, note )

    # fixup any note numbers and multi-applicable notes
    vo_id = placeholder_vo_entry[ "copy_from" ]
    if vo_id.startswith( "br/" ):
        prefix = "Br"
    elif vo_id.startswith( "am/" ):
        prefix = "US"
    elif vo_id.startswith( "fr/" ):
        prefix = "Fr"
    else:
        logging.warning( "Unexpected vehicle/ordnance reference nationality: %s", vo_id )
        prefix = ""
    if "note_number" in placeholder_vo_entry:
        # replace the note# with the explicitly-defined one
        new_vo_entry["note_number"] = placeholder_vo_entry["note_number"]
    else:
        # fixup the note# from the original vehicle/ordnance
        new_vo_entry["note_number"] = "{} {}".format(  prefix, new_vo_entry["note_number"] )
    if "notes" in placeholder_vo_entry:
        # replace the multi-applicable notes with the explicitly-defined ones
        new_vo_entry["notes"] = placeholder_vo_entry["notes"]
    elif "notes" in new_vo_entry:
        # fixup the multi-applicable notes from the original vehicle/ordnance
        add_prefix( new_vo_entry["notes"], prefix )
        if "extra_notes" in placeholder_vo_entry:
            new_vo_entry["notes"].extend( placeholder_vo_entry["extra_notes"] )

    # fixup the comments
    if "comments" in placeholder_vo_entry:
        if "comments" in new_vo_entry:
            new_vo_entry["comments"].extend( placeholder_vo_entry["comments"] )
        else:
            new_vo_entry["comments"] = placeholder_vo_entry["comments"]
    if "disabled_comments" in new_vo_entry:
        add_prefix( new_vo_entry["disabled_comments"], prefix )
    if "disabled_comments" in placeholder_vo_entry:
        if "disabled_comments" in new_vo_entry:
            new_vo_entry["disabled_comments"].extend( placeholder_vo_entry["disabled_comments"] )
        else:
            new_vo_entry["disabled_comments"] = placeholder_vo_entry["disabled_comments"]
    # NOTE: Dynamically adding comments complicates things a lot, since they sometimes depend on
    # the vehicle/ordnance's name (e.g. if it contains "(a)"), or the owning nationality.
    # We re-generate the comments here, which means that comments from the source entry will be
    # re-added, but they will get deduped.
    _do_add_vo_comments( new_vo_entry, nat, vo_type, msg_store )

    return new_vo_entry

# ---------------------------------------------------------------------

def apply_extn_info( listings, extn_fname, extn_info, vo_index, vo_type ):
    """Update the vehicle/ordnance listings for the specified VASL extension."""

    # initialize
    logger = logging.getLogger( "vasl_mod" )
    logger.info( "Updating %s for VASL extension '%s': %s",
        vo_type, extn_info["extensionId"], os.path.split(extn_fname)[1]
    )

    # process each entry
    for nat in extn_info:
        if not isinstance( extn_info[nat], dict ):
            continue
        for entry in extn_info[nat].get( vo_type, [] ):
            vo_entry = vo_index.get( entry["id"] )
            if vo_entry:
                # update an existing vehicle/ordnance
                logger.debug( "- Updating GPID's for %s: %s", entry["id"], entry["gpid"] )
                if vo_entry["gpid"]:
                    prev_gpids = vo_entry["gpid"]
                    if not isinstance( vo_entry["gpid"], list ):
                        vo_entry["gpid"] = [ vo_entry["gpid"] ]
                    vo_entry["gpid"].extend( entry["gpid"] )
                else:
                    prev_gpids = "(none)"
                    vo_entry["gpid"] = entry["gpid"]
                # NOTE: We can't really set the extension ID here because the counter is also in the core VASL module.
                logger.debug( "  - %s => %s", prev_gpids, vo_entry["gpid"] )
            else:
                # add a new vehicle/ordnance
                if nat not in listings:
                    listings[ nat ] = []
                entry[ "extn_id" ] = extn_info[ "extensionId" ]
                listings[ nat ].append( entry )

# ---------------------------------------------------------------------

def make_vo_index( vo_entries ):
    """Generate an index of each vehicle/ordnance entry."""
    vo_index = {}
    for nat in vo_entries:
        for vo_entry in vo_entries[nat]:
            vo_index[ vo_entry["id"] ] = vo_entry
    return vo_index
