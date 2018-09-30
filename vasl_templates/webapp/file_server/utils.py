""" Miscellaneous utilities. """

import os
import json

# ---------------------------------------------------------------------

def get_vo_gpids( data_dir ):
    """Get the GPID's for the vehicles/ordnance."""

    gpids = set()
    for vo_type in ("vehicles","ordnance"):
        dname = os.path.join( data_dir, vo_type )
        for root,_,fnames in os.walk(dname):
            for fname in fnames:
                if os.path.splitext(fname)[1] != ".json":
                    continue
                entries = json.load( open( os.path.join(root,fname), "r" ) )
                for entry in entries:
                    if isinstance( entry["gpid"], list):
                        gpids.update( entry["gpid"] )
                    else:
                        gpids.add( entry["gpid"] )
    gpids.remove( None )

    return gpids
