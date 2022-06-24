""" Test the turn track functionality. """

import os
import re

from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.tests.utils import \
    init_webapp, get_turn_track_nturns, set_turn_track_nturns, select_droplist_val, get_droplist_vals, \
    SwitchFrame, unload_table, wait_for, wait_for_elem, wait_for_clipboard, find_child
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario, save_scenario

# extract the turn track shading colors
_TURN_TRACK_SHADING_COLORS = {}
with open( os.path.join( os.path.dirname(__file__), "../main.py" ), "r", encoding="ascii" ) as fp:
    mo = re.search( r'"TURN_TRACK_SHADING_COLORS": \[ (.+) \]', fp.read(), flags=re.MULTILINE )
    for mo2 in re.finditer( '"#[0-9a-f]{6}"', mo.group(1) ):
        _TURN_TRACK_SHADING_COLORS[ mo2.group()[1:-1] ] = len(_TURN_TRACK_SHADING_COLORS) + 1

# ---------------------------------------------------------------------

def test_turn_track_basic( webapp, webdriver ):
    """Test basic turn track functionality."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver )

    # check the initial state of the UI
    assert get_turn_track_nturns() == ""
    assert not find_child( "button#turn-track-settings" ).is_displayed()
    assert not find_child( ".snippet-control[data-id='turn_track']" ).is_displayed()

    # configure a number of turns
    set_turn_track_nturns( 6 )
    assert find_child( "button#turn-track-settings" ).is_displayed()
    assert find_child( ".snippet-control[data-id='turn_track']" ).is_displayed()

    # generate a snippet
    assert _generate_turn_track_snippet( None ) == [
        [ (1,None,None), (2,None,None), (3,None,None), (4,None,None), (5,None,None), (6,None,None) ]
    ]

# ---------------------------------------------------------------------

def test_turn_track_controls( webapp, webdriver ):
    """Test the basic controls for configuring the turn track."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver )

    # show the turn track dialog
    dlg = _show_turn_track_dialog( 6 )
    with SwitchFrame( webdriver, "#turn-track-preview" ):
        _toggle_reinf( 1, 1 )
        _toggle_reinf( 2, 1 )
        _toggle_reinf( 2, 2 )
        _toggle_reinf( 3, 2 )

    # change the width
    _change_turn_track_width( dlg, 3 )
    def check_for_width():
        return _generate_turn_track_snippet( dlg ) == [
            [ (1,"player1",None), (2,"player1","player2"), (3,None,"player2") ],
            [ (4,None,None), (5,None,None), (6,None,None) ]
        ]
    wait_for( 2, check_for_width )

    # swap the players
    _swap_turn_track_players( dlg )
    def check_for_swap_players():
        return _generate_turn_track_snippet( dlg ) == [
            [ (1,None,"player2"), (2,"player1","player2"), (3,"player1",None) ],
            [ (4,None,None), (5,None,None), (6,None,None) ]
        ]
    wait_for( 2, check_for_swap_players )

    # make the turn track vertical
    _change_turn_track_direction( dlg )
    def check_for_vertical():
        return _generate_turn_track_snippet( dlg ) == [
            [ (1,None,"player2"), (3,"player1",None), (5,None,None) ],
            [ (2,"player1","player2"), (4,None,None), (6,None,None) ]
        ]
    wait_for( 2, check_for_vertical )

    # reset the controls
    find_child( "button.reset2" ).click()
    ask = wait_for_elem( 2, ".ui-dialog.ask" )
    find_child( "button.ok", ask ).click()
    def check_for_reset():
        return _generate_turn_track_snippet( dlg ) == [
            [ (1,None,None), (2,None,None), (3,None,None), (4,None,None), (5,None,None), (6,None,None) ]
        ]
    wait_for( 2, check_for_reset )

# ---------------------------------------------------------------------

def test_turn_track_reinforcements( webapp, webdriver ):
    """Test configuring reinforcements on the turn track."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver )

    # show the turn track dialog
    dlg = _show_turn_track_dialog( 6.5 )

    # turn on some reinforcements, then check the snippet
    with SwitchFrame( webdriver, "#turn-track-preview" ):
        _toggle_reinf( 2, 1 )
        _toggle_reinf( 3, 1 )
        _toggle_reinf( 3, 2 )
        _toggle_reinf( 7, 1 )
    assert _generate_turn_track_snippet( dlg ) == [
        [ (1,None,None), (2,"player1",None), (3,"player1","player2"),
          (4,None,None), (5,None,None) , (6,None,None), (7,"player1",None)
        ]
    ]

    # turn off some reinforcements, turn some on, then check the snippet
    with SwitchFrame( webdriver, "#turn-track-preview" ):
        _toggle_reinf( 2, 2 )
        _toggle_reinf( 3, 1 )
        _toggle_reinf( 3, 2 )
        _toggle_reinf( 5, 2 )
        _toggle_reinf( 7, 1 )
    assert _generate_turn_track_snippet( dlg ) == [
        [ (1,None,None), (2,"player1","player2"), (3,None,None),
          (4,None,None), (5,None,"player2") , (6,None,None), (7,None,None)
        ]
    ]

# ---------------------------------------------------------------------

def test_turn_track_shading( webapp, webdriver ):
    """Test shading squares on the turn track."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver )

    # show the turn track dialog
    dlg = _show_turn_track_dialog( 6.5 )

    # shade some turn track squares, then check the snippet
    with SwitchFrame( webdriver, "#turn-track-preview" ):
        _toggle_shading( 1 )
        _toggle_shading( 2 )
        _toggle_shading( 7 )
    assert _generate_turn_track_snippet( dlg ) == [
        [ (1,None,None,"shading1"), (2,None,None,"shading1"), (3,None,None),
          (4,None,None), (5,None,None) , (6,None,None), (7,None,None,"shading1")
        ]
    ]

    # change the shading for some turn track squares, then check the snippet
    with SwitchFrame( webdriver, "#turn-track-preview" ):
        _toggle_shading( 1 )
        _toggle_shading( 3 )
        _toggle_shading( 7 )
    assert _generate_turn_track_snippet( dlg ) == [
        [ (1,None,None,"shading2"), (2,None,None,"shading1"), (3,None,None,"shading1"),
          (4,None,None), (5,None,None) , (6,None,None), (7,None,None,"shading2")
        ]
    ]

    # change the shading for some turn track squares, then check the snippet
    with SwitchFrame( webdriver, "#turn-track-preview" ):
        _toggle_shading( 1 )
        _toggle_shading( 3 )
        _toggle_shading( 2 )
        _toggle_shading( 2 )
    assert _generate_turn_track_snippet( dlg ) == [
        [ (1,None,None), (2,None,None), (3,None,None,"shading2"),
          (4,None,None), (5,None,None) , (6,None,None), (7,None,None,"shading2")
        ]
    ]

# ---------------------------------------------------------------------

def test_turn_track_persistence( webapp, webdriver ):
    """Test saving and loading turn track settings."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # show the turn track dialog
    load_scenario( {
        "PLAYER_1": "japanese", "PLAYER_2": "american",
        "TURN_TRACK": { "NTURNS": 6.5 },
    } )
    dlg = _show_turn_track_dialog( None )

    # configure the turn track
    with SwitchFrame( webdriver, "#turn-track-preview" ):
        _toggle_reinf( 1, 1 )
        _toggle_reinf( 2, 2 )
        _toggle_reinf( 3, 1 )
        _toggle_reinf( 3, 2 )
        _toggle_shading( 2 )
        _toggle_shading( 4 )
        _toggle_shading( 4 )
    _change_turn_track_width( dlg, 4 )
    _swap_turn_track_players( dlg )
    _change_turn_track_direction( dlg )

    # check the snippet
    expected = [
        [ (1,None,"player2"), (3,"player1","player2"), (5,None,None), (7,None,None) ],
        [ (2,"player1",None,"shading1") , (4,None,None,"shading2"), (6,None,None) ]
    ]
    wait_for( 2,
        lambda: _generate_turn_track_snippet( dlg ) == expected
    )

    # save the scenario
    dlg.send_keys( Keys.ESCAPE )
    saved_scenario = save_scenario()
    assert saved_scenario["TURN_TRACK"] == {
        "NTURNS": "6.5",
        "WIDTH": "4", "VERTICAL": True, "SWAP_PLAYERS": True,
        "SHADING": "2,4+",
        "REINFORCEMENTS_1": "2,3", "REINFORCEMENTS_2": "1,3",
    }
    assert _generate_turn_track_snippet( None ) == expected

    # reset the scenario
    webdriver.refresh()
    assert not find_child( "button.generate[data-id='turn_track']" ).is_displayed()

    # load the scenario and generate the snippet
    load_scenario( saved_scenario )
    assert _generate_turn_track_snippet( None ) == expected

    # open the turn track dialog and check that the controls were loaded correctly
    dlg = _show_turn_track_dialog( None )
    assert get_turn_track_nturns() == "6.5"
    sel = Select( find_child( "select[name='width']", dlg ) )
    assert sel.first_selected_option.get_attribute( "value" ) == "4"
    assert find_child( "input[name='vertical']" ).is_selected()
    assert find_child( "input[name='swap-players']" ).is_selected()
    assert _generate_turn_track_snippet( dlg ) == expected

# ---------------------------------------------------------------------

def test_turn_track_droplist( webapp, webdriver ):
    """Test updating entries in the turn track droplist (#turns)."""

    # initialize
    webapp.control_tests.set_data_dir( "{REAL}" )
    init_webapp( webapp, webdriver, scenario_persistence=1 )

    # check the initial state of the droplist
    assert _unload_turn_track_droplist() == [
        "", "6", "6.5", "7", "7.5", "8", "8.5", "9", "9.5", "10", "(show-dialog)"
    ]

    # configure a number of turns that is not in the default list (small)
    sel = Select( find_child( "select[name='TURN_TRACK_NTURNS']" ) )
    select_droplist_val( sel, "(show-dialog)" )
    sel2 = Select( find_child( "#turn-track select[name='nturns']" ) )
    select_droplist_val( sel2, "2" )
    assert _unload_turn_track_droplist() == [
        "", "2", "6", "6.5", "7", "7.5", "8", "8.5", "9", "9.5", "10"
    ]

    # configure a number of turns that is not in the default list (large)
    select_droplist_val( sel2, "14.5" )
    expected = [ "", "6", "6.5", "7", "7.5", "8", "8.5", "9", "9.5", "10", "14.5" ]
    assert _unload_turn_track_droplist() == expected

    # save and reload the scenario
    find_child( ".ui-dialog.turn-track" ).send_keys( Keys.ESCAPE )
    saved_scenario = save_scenario()
    webdriver.refresh()
    load_scenario( saved_scenario )
    assert _unload_turn_track_droplist() == expected

    # configure a number of turns that is in the default list
    sel = Select( find_child( "select[name='TURN_TRACK_NTURNS']" ) )
    select_droplist_val( sel, "8" )
    assert _unload_turn_track_droplist() == [
        "", "6", "6.5", "7", "7.5", "8", "8.5", "9", "9.5", "10"
    ]

    # disable the turn track
    select_droplist_val( sel, "" )
    assert _unload_turn_track_droplist() == [
        "", "6", "6.5", "7", "7.5", "8", "8.5", "9", "9.5", "10", "(show-dialog)"
    ]

# ---------------------------------------------------------------------

def _show_turn_track_dialog( nturns ):
    """Show the TURN TRACK dialog."""
    if nturns:
        set_turn_track_nturns( nturns )
    btn = wait_for_elem( 2, "button#turn-track-settings" )
    btn.click()
    dlg = wait_for_elem( 2, ".ui-dialog.turn-track" )
    return dlg

def _generate_turn_track_snippet( dlg ):
    """Generate a turn track snippet."""

    # generate the snippet
    btn = find_child( "button.snippet", dlg ) if dlg else find_child( "button.generate[data-id='turn_track']" )
    assert btn.is_displayed()
    btn.click()
    clipboard = wait_for_clipboard( 2, "<!-- vasl-templates:id", contains=True )

    def get_reinforce_class( cell ):
        cell_class = str( cell.xpath( ".//@class" )[0] )
        if cell_class == "reinforce1":
            return "player1"
        elif cell_class == "reinforce2":
            return "player2"
        else:
            assert cell_class == "no-reinforce"
            return None

    def unload_square( square ):
        # unload the reinforcement flags
        cells = square.xpath( ".//td" )
        assert len(cells) == 3
        vals = (
            int( cells[1].text ),
            get_reinforce_class( cells[0] ),
            get_reinforce_class( cells[2] ),
        )
        # check if the square is shaded
        cols = [ s for s in square.xpath( ".//@style" ) if s.startswith( "background-color:" ) ]
        if cols:
            assert len(cols) == 1
            col = cols[0][17:]
            assert col.endswith( ";" )
            col = col[:-1]
            shading = _TURN_TRACK_SHADING_COLORS.get( col )
            assert shading, "Can't find turn track shading color: {}".format( shading )
            vals = ( *vals, "shading{}".format( shading ) )
        return vals

    # unload the snippet contents
    squares = unload_table( "//table[@class='turn-track']", html=clipboard, unload=False )
    for row_no, row in enumerate(squares):
        for col_no, square in enumerate(row):
            squares[row_no][col_no] = unload_square( square )

    return squares

def _unload_turn_track_droplist():
    """Get the available options in the turn track droplist."""
    keys = []
    prev_key = None
    options = get_droplist_vals( Select(
        find_child( "select[name='TURN_TRACK_NTURNS']" )
    ) )
    for key, caption in options:
        if key == "":
            assert caption == "-"
        elif key == "(show-dialog)":
            assert caption == "(more)"
        else:
            assert key == caption
            key2 = float( key )
            if prev_key:
                assert key2 > prev_key
            assert int( 10 * key2 ) % 10 in (0,5)
            prev_key = key2
        keys.append( key )
    return keys

def _toggle_reinf( turn_no, player_no ):
    """Toggle a player's reinforcements for the specified turn."""
    find_child(
        "#flag-{}_{} .flag-click".format( turn_no, player_no )
    ).click()

def _toggle_shading( turn_no ):
    """Toggle the shading for a turn track square."""
    find_child(
        "#turn-square-{} .shading-click".format( turn_no )
    ).click()

# ---------------------------------------------------------------------

def _change_turn_track_width( dlg, width ):
    """Change the turn track width."""
    sel = Select( find_child( "select[name='width']", dlg ) )
    _wait_for_preview( dlg,
        lambda: select_droplist_val( sel, width )
    )

def _change_turn_track_direction( dlg ):
    """Toggle the direction of the turn track."""
    _wait_for_preview( dlg,
        lambda: find_child( "input[name='vertical']", dlg ).click()
    )

def _swap_turn_track_players( dlg ):
    """Swap the turn track players."""
    _wait_for_preview( dlg,
        lambda: find_child( "input[name='swap-players']", dlg ).click()
    )

def _wait_for_preview( dlg, func ):
    """Make a change to the preview, and wait for the UI to update."""
    # NOTE: The preview <iframe> is replaced with a new one, so we need to be ready for the old one to disappear.
    iframe = find_child( "iframe", dlg )
    seqno = iframe.get_attribute( "data-seqno" )
    func()
    def check_seqno():
        iframe = find_child( "iframe", dlg )
        if not iframe:
            return False
        return iframe.get_attribute( "data-seqno" ) != seqno
    wait_for( 20, check_seqno )
