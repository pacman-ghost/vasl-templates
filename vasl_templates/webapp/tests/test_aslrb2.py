""" Test integration with asl-rulebook2. """

import os

from vasl_templates.webapp.tests.utils import init_webapp, find_child, find_children
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario

# ---------------------------------------------------------------------

def test_chapter_h( webapp, webdriver ):
    """Test links to Chapter H vehicle/ordnance notes."""

    # initialize
    webapp.control_tests.set_app_config_val( "ASL_RULEBOOK2_BASE_URL",
        os.path.join( os.path.dirname(__file__), "fixtures/asl-rulebook2/vo-note-targets.json" )
    )
    init_webapp( webapp, webdriver, scenario_persistence=1 )
    base_url = "{}/asl-rulebook2/".format( webapp.base_url )

    # test normal vehicles/ordnance
    load_scenario( {
        "PLAYER_1": "german",
        "OB_VEHICLES_1": [ { "name": "a german vehicle" }, { "name": "another german vehicle" } ],
        "PLAYER_2": "russian",
        "OB_ORDNANCE_2": [ { "name": "a russian ordnance" }, { "name": "another russian ordnance" } ],
    } )
    urls = _unload_aslrb2_urls( base_url )
    assert urls == [
        [ [ "gv:1", None ], [] ],
        [ [], [ None, "ro:2" ] ]
    ]

    # test Allied/Axis Minor vehicles/ordnance
    load_scenario( {
        "PLAYER_1": "dutch",
        "OB_VEHICLES_1": [ { "name": "dutch vehicle" }, { "name": "common allied minor vehicle" } ],
        "PLAYER_2": "romanian",
        "OB_ORDNANCE_2": [ { "name": "romanian ordnance" }, { "name": "common axis minor ordnance" } ],
    } )
    urls = _unload_aslrb2_urls( base_url )
    assert urls == [
        [ [ "dv:1", "almv:101" ], [] ],
        [ [], [ "ro:4", "axmo:104", ] ]
    ]

    # test Landing Craft
    load_scenario( {
        "PLAYER_1": "american",
        "OB_VEHICLES_1": [ { "name": "landing craft" } ],
        "PLAYER_2": "japanese",
        "OB_VEHICLES_2": [ { "name": "Daihatsu" } ],
    } )
    urls = _unload_aslrb2_urls( base_url )
    assert urls == [
        [ [ "lc:1" ], [] ],
        [ [ "lc:2" ], [] ]
    ]

    # test derived nationalities
    load_scenario( {
        "PLAYER_1": "chinese~gmd",
        "OB_VEHICLES_1": [ { "name": "a chinese vehicle" } ],
    } )
    urls = _unload_aslrb2_urls( base_url )
    assert urls == [
        [ ["chv:1"], [] ],
        [ [], [] ]
    ]

    # test K:FW (UN Forces)
    load_scenario( {
        "PLAYER_1": "american",
        "OB_VEHICLES_1": [ { "name": "kfw us vehicle" }, { "name": "kfw common vehicle" } ],
        "PLAYER_2": "british",
        "OB_ORDNANCE_2": [ { "name": "kfw british ordnance" }, { "name": "kfw common ordnance" } ],
    } )
    urls = _unload_aslrb2_urls( base_url )
    assert urls == [
        [ ["kfw-un:5","kfw-un:6"], [] ],
        [ [], ["kfw-un:7","kfw-un:8"] ]
    ]

    # test K:FW (Communist Forces)
    load_scenario( {
        "PLAYER_1": "kfw-kpa",
        "OB_VEHICLES_1": [ { "name": "kpa vehicle" } ],
        "PLAYER_2": "kfw-cpva",
        "OB_ORDNANCE_2": [ { "name": "cpva ordnance" } ],
    } )
    urls = _unload_aslrb2_urls( base_url )
    assert urls == [
        [ ["kfw-comm:15"], [] ],
        [ [], ["kfw-comm:16"] ]
    ]

# ---------------------------------------------------------------------

def _unload_aslrb2_urls( base_url ):
    """Unload the URL's to the asl-rulebook2 vehicle/ordnance notes."""
    urls = [
        [ [], [] ],
        [ [], [] ]
    ]
    for player_no in (1,2):
        for vo_type_index, vo_type in enumerate(["vehicles","ordnance"]):
            sortable = find_child( "#ob_{}-sortable_{}".format( vo_type, player_no ) )
            urls2 = urls[ player_no-1 ][ vo_type_index ]
            for vo_entry in find_children( ".vo-entry", sortable ):
                link = find_child( "a.aslrb2", vo_entry )
                if link:
                    url = link.get_attribute( "href" )
                    if url.startswith( base_url ):
                        url = url[ len(base_url): ]
                else:
                    url = None
                urls2.append( url )
    return urls
