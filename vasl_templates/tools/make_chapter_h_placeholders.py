#!/usr/bin/env python3
""" Create placeholder files for the Chapter H notes. """

import os
import zipfile
import json
import re

import click

# ---------------------------------------------------------------------

@click.command()
@click.option( "--output","-o", "output_fname", help="Output ZIP file to generate." )
def main( output_fname ): # pylint: disable=too-many-locals,too-many-branches
    """Create a ZIP file with placeholder files for each Chapter H note and multi-applicable note."""

    # initialize
    if not output_fname:
        raise RuntimeError( "Output ZIP file not specified." )
    if os.path.isfile( output_fname ):
        raise RuntimeError( "Output ZIP file exists." )
    results = {}

    # load the vehicle/ordnance data files
    base_dir = os.path.join( os.path.split(__file__)[0], "../webapp/data/" )
    for vo_type in ("vehicles","ordnance"):
        dname = os.path.join( base_dir, vo_type )
        for root,_,fnames in os.walk( dname ):
            for fname in fnames:
                fname = os.path.join( root, fname )
                if os.path.splitext( fname )[1] != ".json":
                    continue
                dname2, fname2 = os.path.split( fname )
                nat = os.path.splitext( fname2 )[0]
                if nat == "common":
                    nat = os.path.split( dname2 )[1]
                if nat in ("british-commonwealth-forces-korea","cvpa","kpa","us-rok-ounc","un-forces"):
                    continue
                notes, ma_notes = load_vo_data( fname )
                if nat not in results:
                    results[ nat ] = {}
                if nat == "landing-craft":
                    results[ nat ][ vo_type ] = { "notes": notes, "ma_notes": ma_notes }
                else:
                    results[ nat ][ vo_type ] = { "notes": notes, "ma_notes": ma_notes }

    # generate the placeholder files
    with zipfile.ZipFile( output_fname, "w" ) as zip_file:
        nats = sorted( results.keys() )
        for nat in nats: #pylint: disable=too-many-nested-blocks
            for vo_type in ("vehicles","ordnance"):
                print( "Generating {} {}...".format( nat, vo_type ) )
                for note_type in ("notes","ma_notes"):

                    # get the next set of note ID's
                    vals = results[nat].get( vo_type, {} ).get( note_type )
                    if not vals:
                        continue
                    print( "- {}: {}".format( note_type, ", ".join( str(v) for v in vals ) ) )

                    for val in vals:

                        # generate the filename for the next note placeholder
                        if isinstance(val, str):
                            # NOTE: Filenames are always lower-case, unless the note ID itself is lower-case,
                            # in which case we indicate this with a trailing underscore
                            if re.search( r"^[A-Z][A-Za-z]?$", val ):
                                val = val.lower()
                            elif re.search( r"^[a-z]{1,2}?$", val ):
                                val += "_"
                        if nat == "landing-craft":
                            fname = "{}/{}.{}".format( nat, val, "png" if note_type == "notes" else "html" )
                        else:
                            fname = "{}/{}/{}.{}".format( nat, vo_type, val, "png" if note_type == "notes" else "html" )

                        # add the placeholder file to the ZIP
                        zip_file.writestr( fname, b"" )

        print()

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

def load_vo_data( fname ):
    """Load a vehicle/ordnance data file."""

    # initialize
    notes, ma_notes = set(), set()

    # load the file
    vo_data = json.load( open( fname, "r" ) )
    for vo_entry in vo_data:

        # load the vehicle/ordnance's note number
        mo = re.search( r"^\d+", vo_entry["note_number"] )
        notes.add( int( mo.group() ) )

        # load the multi-applicable note ID's
        for ma_note in vo_entry.get("notes",[]):
            matches = [ regex.search(ma_note) for regex in MA_NOTE_REGEXES ]
            matches = [ mo.group(1) for mo in matches if mo ]
            assert len(matches) == 1
            ma_notes.add( matches[0] )

    return sorted(notes), sorted(ma_notes)

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
