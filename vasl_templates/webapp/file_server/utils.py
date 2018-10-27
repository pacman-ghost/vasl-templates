""" Miscellaneous utilities. """

import os
import json

# ---------------------------------------------------------------------

def get_vo_gpids( data_dir ):
    """Get the GPID's for the vehicles/ordnance."""

    gpids = set()
    for vo_type in ("vehicles","ordnance"):
        dname = os.path.join( data_dir, vo_type )

        # process each file
        for root,_,fnames in os.walk(dname):
            for fname in fnames:
                if os.path.splitext(fname)[1] != ".json":
                    continue

                # load the GPID's from the next file
                entries = json.load( open( os.path.join(root,fname), "r" ) )
                for entry in entries:
                    if isinstance( entry["gpid"], list):
                        gpids.update( get_effective_gpid(gpid) for gpid in entry["gpid"] )
                    else:
                        gpids.add( entry["gpid"] )

    gpids.remove( None )

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
    7140: 2775, # SdKfz 10/5
    7146: 2772, # SdKfz 10/4
}

def get_effective_gpid(  gpid ):
    """Return the effective GPID."""
    return GPID_REMAPPINGS.get( gpid, gpid )
