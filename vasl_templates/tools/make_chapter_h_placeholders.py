#!/usr/bin/env python3
""" Create placeholder files for the Chapter H notes. """

import os
import zipfile
import json
import re
import glob

import click

nationalities = None

# ---------------------------------------------------------------------

@click.command()
@click.option( "--output","-o", "output_fname", help="Output ZIP file to generate." )
def main( output_fname ): # pylint: disable=too-many-locals,too-many-branches
    """Create a ZIP file with placeholder files for each Chapter H note and multi-applicable note."""

    def log( fmt, *args ): #pylint: disable=missing-docstring
        print( fmt.format( *args ) )
    return make_chapter_h_placeholders( output_fname, log=log )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def make_chapter_h_placeholders( output_fname, log=None \
    ): #pylint: disable=too-many-locals,too-many-statements,too-many-branches
    """Create a ZIP file with placeholder files for each Chapter H note and multi-applicable note."""

    # initialize
    if not output_fname:
        raise RuntimeError( "Output ZIP file not specified." )
    if not log:
        def log_nothing( fmt, *args ): #pylint: disable=missing-docstring,unused-argument
            pass
        log = log_nothing
    results = {}

    # load the nationalities
    fname = os.path.join( os.path.split(__file__)[0], "../webapp/data/default-template-pack/nationalities.json" )
    global nationalities
    nationalities = json.load( open( fname, "r" ) )

    # load the vehicle/ordnance data files
    base_dir = os.path.join( os.path.split(__file__)[0], "../webapp/data/" )
    for vo_type in ("vehicles","ordnance"):
        dname = os.path.join( base_dir, vo_type )
        for root,_,fnames in os.walk( dname ):
            for fname in fnames:
                fname = os.path.join( root, fname )
                if os.path.splitext( fname )[1] != ".json":
                    continue
                if os.path.splitext( fname )[0].endswith( ".lend-lease" ):
                    # NOTE: Doing this means we will miss any pieces explicitly defined in a lend-lease file
                    # (instead of being copied from an existing piece), but we can live with that... :-/
                    continue
                dname2, fname2 = os.path.split( fname )
                nat = os.path.splitext( fname2 )[0]
                if nat == "common":
                    nat = os.path.split( dname2 )[1]
                if nat in ("british-commonwealth-forces-korea","cvpa","kpa","us-rok-ounc","un-forces"):
                    continue
                notes, ma_notes = load_vo_data( fname, nat )
                if nat not in results:
                    results[ nat ] = {}
                if nat == "landing-craft":
                    results[ nat ][ vo_type ] = { "notes": notes, "ma_notes": ma_notes }
                else:
                    results[ nat ][ vo_type ] = { "notes": notes, "ma_notes": ma_notes }

    # load the extensions
    base_dir = os.path.join( os.path.split(__file__)[0], "../webapp/data/extensions" )
    for fname in glob.glob( os.path.join( base_dir, "*.json" ) ):
        extn_data = load_vo_data_from_extension( fname )
        for nat in extn_data:
            for vo_type in extn_data[nat]:
                for key in extn_data[nat][vo_type]:
                    if nat not in results:
                        results[nat] = {}
                    if vo_type not in results[nat]:
                        results[nat][vo_type] = {}
                    if key not in results[nat][vo_type]:
                        results[nat][vo_type][key] = []
                    results[nat][vo_type][key].extend( extn_data[nat][vo_type].get( key, [] ) )

    # generate the placeholder files
    with zipfile.ZipFile( output_fname, "w" ) as zip_file:
        nats = sorted( results.keys() )
        for nat in nats: #pylint: disable=too-many-nested-blocks
            for vo_type in ("vehicles","ordnance"):
                log( "Generating {} {}...", nat, vo_type )
                for note_type in ("notes","ma_notes"):

                    # get the next set of note ID's
                    vals = results[nat].get( vo_type, {} ).get( note_type )
                    if not vals:
                        continue
                    log( "- {}: {}", note_type, ", ".join( str(v) for v in vals ) )

                    for val in vals:

                        # generate the filename for the next note placeholder
                        if isinstance(val, str):
                            # NOTE: Filenames are always lower-case, unless the note ID itself is lower-case,
                            # in which case we indicate this with a trailing underscore
                            if re.search( r"^([-a-z]+:)?[A-Z][A-Za-z]?$", val ):
                                val = val.lower()
                            elif re.search( r"^[a-z]{1,2}?$", val ):
                                val += "_"
                        if nat == "landing-craft":
                            fname = "{}/{}.{}".format( nat, val, "png" if note_type == "notes" else "html" )
                        else:
                            fname = "{}/{}/{}.{}".format( nat, vo_type, val, "png" if note_type == "notes" else "html" )

                        # add the placeholder file to the ZIP
                        fname = fname.replace( ":", "/" )
                        zip_file.writestr( fname, b"" )
        log( "" )

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def load_vo_data( fname, nat ):
    """Load a vehicle/ordnance data file."""

    # initialize
    notes, ma_notes = set(), set()

    # load the file
    vo_data = json.load( open( fname, "r" ) )
    for vo_entry in vo_data:
        if "note_number" in vo_entry:
            notes.add(
                _extract_note_number( vo_entry["note_number"] )
            )
        if "notes" in vo_entry and not _ignore_ma_notes(nat):
            ma_notes.update(
                _extract_ma_note_ids( vo_entry["notes"] )
            )

    return sorted(notes), sorted(ma_notes)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def load_vo_data_from_extension( fname ):
    """Load a vehicle/ordnance extension data file."""

    # initialize
    results = {}

    # get the extension ID
    data = json.load( open( fname, "r" ) )
    extn_id = data["extensionId"]

    # load the file
    for nat in data:

        if not isinstance( data[nat], dict ):
            continue

        results[nat] = {}
        for vo_type in ("vehicles","ordnance"):
            notes, ma_notes = set(), set()
            for vo_entry in data[nat].get(vo_type,[]):
                # load the vehicle/ordnance's note number
                if "note_number" in vo_entry:
                    notes.add(
                        _extract_note_number( vo_entry["note_number"] )
                    )
                if "notes" in vo_entry and not _ignore_ma_notes(nat,extn_id):
                    ma_notes.update(
                        _extract_ma_note_ids( vo_entry["notes"] )
                    )
            results[ nat ][ vo_type ] = {
                "notes": [ "{}:{}".format( extn_id, n ) for n in sorted(notes) ],
                "ma_notes": [ "{}:{}".format( extn_id, n ) for n in sorted(ma_notes) ]
            }

    return results

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

MA_NOTE_REGEXES = [
    re.compile( r"^([A-Z]{1,2})$" ),
    re.compile( r"^([A-Z]{1,2})\u2020" ),
    re.compile( r"^([a-z])$" ),
    re.compile( r"^([a-z])\u2020" ),
    re.compile( r"^([A-Z][a-z])$" ),
    re.compile( r"^([A-Za-z])<sup>" ),
    re.compile( r"^<s>([A-Za-z])</s>$" ),
]

REDIRECTED_MA_NOTE_REGEX = re.compile(
    r"^((Ge|Ru|US|Br|Fr|Jp|Ch|Gr|AllM|AxM) ([A-Z]{1,2}|[0-9]{1,2}|Note \d+|<s>P</s>))\u2020?(<sup>\d</sup>)?$"
)

def _extract_note_number( val ):
    """Extract a vehicle/ordnance's note number."""
    mo = re.search( r"^\d+", val )
    return int( mo.group() )

def _extract_ma_note_ids( val ):
    """Extract a vehicle/ordnance's multi-applicable note ID's."""
    ma_note_ids = []
    for ma_note in val:
        if REDIRECTED_MA_NOTE_REGEX.search( ma_note ):
            continue
        matches = [ regex.search(ma_note) for regex in MA_NOTE_REGEXES ]
        matches = [ mo.group(1) for mo in matches if mo ]
        assert len(matches) == 1
        ma_note_ids.append( matches[0] )
    return ma_note_ids

def _ignore_ma_notes( nat, extn_id=None ):
    if extn_id == "adf-bj" and nat == "american":
        return True
    if extn_id is None and nationalities.get( nat, {} ).get( "type" ) in ("allied-minor","axis-minor"):
        return True
    return False

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
