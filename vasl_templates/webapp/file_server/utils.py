""" Miscellaneous utilities. """

import os
import json

# ---------------------------------------------------------------------

def get_vo_gpids( data_dir, extns ): #pylint: disable=too-many-locals,too-many-branches
    """Get the GPID's for the vehicles/ordnance."""

    gpids = set()
    for vo_type in ("vehicles","ordnance"): #pylint: disable=too-many-nested-blocks

        # process each file
        dname = os.path.join( data_dir, vo_type )
        for root,_,fnames in os.walk(dname):
            for fname in fnames:
                if os.path.splitext(fname)[1] != ".json":
                    continue

                # load the GPID's from the next file
                # NOTE: We originally assumed that GPID's are integers, but the main VASL build file started
                # to have non-numeric values, as do, apparently, extensions :-/ For back-compat, we support both.
                entries = json.load( open( os.path.join(root,fname), "r" ) )
                for entry in entries:
                    entry_gpids = entry[ "gpid" ]
                    if not isinstance( entry_gpids, list ):
                        entry_gpids = [ entry_gpids ]
                    for gpid in entry_gpids:
                        if gpid:
                            gpids.add( get_effective_gpid( str(gpid) ) )

    # process any extensions
    if extns: #pylint: disable=too-many-nested-blocks
        for extn in extns:
            extn_info = extn[1]
            for nat in extn_info:
                if not isinstance( extn_info[nat], dict ):
                    continue
                for vo_type in ("vehicles","ordnance"):
                    for piece in extn_info[ nat ].get( vo_type, [] ):
                        if isinstance( piece["gpid"], list ):
                            gpids.update( piece["gpid"] )
                        else:
                            gpids.add( piece["gpid"] )

    return gpids

# ---------------------------------------------------------------------

# VASL 6.4.3 removed several PieceSlot's. There's no comment for the commmit (0a27c24)
# but I suspect it's because they're duplicates. Our data files have the following mappings:
#   SdKfz 10/5: 7140, 2775
#   SdKfz 10/4: 7146, 2772
# but we can't just remove the now-missing GPID's, since any scenarios that use them
# will break. This kind of thing is going to happen again, so we provide a generic mechanism
# for dealing with this kind of thing...
GPID_REMAPPINGS = {
    "7140": "2775", # SdKfz 10/5
    "7146": "2772", # SdKfz 10/4
}

def get_effective_gpid(  gpid ):
    """Return the effective GPID."""
    return GPID_REMAPPINGS.get( gpid, gpid )
