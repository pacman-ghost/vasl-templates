#!/usr/bin/env python3
""" Check how scenarios at the ASL Scenario Archive are connected to those at ROAR. """

import sys
import json

from vasl_templates.webapp.scenarios import _match_roar_scenario, \
    _asa_scenarios, _build_asa_scenario_index, _roar_scenarios, _build_roar_scenario_index

# ---------------------------------------------------------------------

def asa_string( s ):
    """Return an ASL Scenario Archive scenario as a string."""
    return "[{}] {} ({})".format(
        s["scenario_id"], s.get("title"), s.get("sc_id")
    )

def roar_string( s ):
    """Return ROAR scenario as a string."""
    return "[{}] {} ({})".format(
        s["roar_id"], s.get("name"), s.get("scenario_id")
    )

# ---------------------------------------------------------------------

# load the ASL Scenario Archive scenarios
fname = sys.argv[1]
with open( fname, "r", encoding="utf-8" ) as fp:
    asa_data = json.load( fp )
_build_asa_scenario_index( _asa_scenarios, asa_data, None )

# load the ROAR scenarios
fname = sys.argv[2]
with open( fname, "r", encoding="utf-8" ) as fp:
    roar_data = json.load( fp )
_build_roar_scenario_index( _roar_scenarios, roar_data, None )

# try to connect each ASA scenario to ROAR
exact_matches, multiple_matches, unmatched = [], [], []
for scenario in asa_data["scenarios"]:
    matches = _match_roar_scenario( scenario )
    if not matches:
        unmatched.append( scenario )
    elif len(matches) == 1:
        exact_matches.append( scenario )
    else:
        multiple_matches.append( [ scenario, matches ] )

# output the results
print( "ASL Scenario Archive scenarios: {}".format( len(asa_data["scenarios"]) ) )
print()
print( "Exact matches: {}".format( len(exact_matches) ) )
print()
print( "Multiple matches: {}".format( len(multiple_matches) ) )
if multiple_matches:
    for scenario,matches in multiple_matches:
        print( "  {}:".format( asa_string(scenario) ) )
        for match in matches:
            print( "  - {}".format( roar_string( match ) ) )
print()
print( "Unmatched: {}".format( len(unmatched) ) )
if unmatched:
    for scenario in unmatched:
        print( "  {}".format( asa_string(scenario) ) )
