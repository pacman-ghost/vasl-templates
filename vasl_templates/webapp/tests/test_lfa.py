""" Test log file analysis. """

import os
import base64
import csv

import pytest
from selenium.webdriver.support.ui import Select

from vasl_templates.webapp.tests.utils import init_webapp, select_menu_option, \
    wait_for, wait_for_elem, find_child, find_children, set_stored_msg, set_stored_msg_marker, get_stored_msg, \
    get_droplist_vals, select_droplist_val, unload_table
from vasl_templates.webapp.tests.test_vassal import _run_tests

# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest.config.option.vasl_mods, reason="--vasl-mods not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( not pytest.config.option.vassal, reason="--vassal not specified" ) #pylint: disable=no-member
def test_full( webapp, webdriver ):
    """Test a full log file analysis."""

    # initialize
    control_tests = init_webapp( webapp, webdriver, vlog_persistence=1, lfa_tables=1 )

    def do_test(): #pylint: disable=missing-docstring

        # analyze the log file
        #   === RPh ===     === PFPh ===   === MPh ===   === DFPh ===
        #   A1: Other 5 4   A6:  IFT 3 1                 B5:  IFT 4 2
        #   A2: Rally 4 1   B3:  MC  5 2                 b5:  sa  2
        #   A3: Rally 3 1   A7:  IFT 5 3                 A12: MC  1 2
        #   B1: Rally 6 2   b3:  sa  4
        #   A4: Rally 6 4   b4:  rs  6
        #   a1: dr    6     B4:  MC  1 6
        #   A5: Rally 3 4   A8:  TH  5 5
        #   B2: Rally 5 3   A9:  TK  2 3
        #   b1: dr    2     A10: IFT 3 3
        #   b2: dr    2     A11: IFT 4 4
        _analyze_vlogs( "full.vlog" )

        # check the results
        lfa = _get_chart_data( 1 )
        assert lfa["distrib"]["dr"] == [
            [ "Alice (6.0)", "Bob (3.2)" ],
            ["",""], ["","60"], ["",""], ["","20"], ["",""], ["100","20"]
        ]
        assert lfa["distrib"]["DR"] == [
            [ "Alice (6.6)", "Bob (7.2)" ],
            ["",""], ["8.3",""], ["16.7",""], ["16.7",""], ["8.3","20"],
            ["8.3","40"], ["16.7","40"], ["8.3",""], ["16.7",""], ["",""], ["",""]
        ]

        # check the results
        assert lfa["pie"]["dr"] == [ ["Bob","5"], ["Alice","1"] ]
        assert lfa["pie"]["DR"] == [ ["Bob","5"], ["Alice","12"] ]

        # check the results
        _check_time_plot_window_sizes( [ 1, 5 ] )
        assert lfa["timePlot"] == [
            [ "", "Alice (12)", "Bob (5)" ],
            ["","9",""], ["","5",""], ["","4",""], ["","","8"], ["","10",""],
            ["","7",""], ["","","8"],
            [ "Axis 1 PFPh", "4", "" ],
            ["","","7"], ["","8",""], ["","","7"], ["","10",""], ["","5",""],
            ["","6",""], ["","8",""],
            [ "Axis 1 DFPh", "","6" ],
            ["","3",""]
        ]
        _check_time_plot_values( [1,5], "5", [
            [ "", "Alice (12)", "Bob (5)" ],
            ["","7",""], ["Axis 1 PFPh","6",""], ["","6.6",""], ["","7.8",""], ["","6.8",""],
            ["","6.6",""], ["","7.4",""],
            [ "Axis 1 DFPh", "", "7.2" ],
            ["","6.4",""]
        ] )

        # check the results
        assert lfa["hotness"] == [ ["Alice","1.367"], ["Bob","-0.927"] ]

        # switch to showing the Morale Check DR's and check the results
        _select_roll_type( "MC" )
        lfa = _get_chart_data()
        assert lfa["distrib"]["dr"] == []
        assert lfa["distrib"]["DR"] == [
            [ "Alice (3.0)", "Bob (7.0)" ],
            ["",""], ["100",""], ["",""], ["",""], ["",""],
            ["","100"], ["",""], ["",""], ["",""], ["",""], ["",""]
        ]
        assert lfa["pie"]["dr"] == []
        assert lfa["pie"]["DR"] == [ ["Bob","2"], ["Alice","1"] ]
        _check_time_plot_values( [1], "1", [
            [ "", "Alice (1)", "Bob (2)" ],
            [ "Axis 1 PFPh", "", "7" ],
            ["","","7"],
            [ "Axis 1 DFPh", "3", "" ],
        ] )
        assert lfa["hotness"] == [ ["Alice","287.445"], ["Bob","0.000"] ]

        # switch to showing the Sniper Activation DR's and check the results
        _select_roll_type( "SA" )
        lfa = _get_chart_data()
        assert lfa["distrib"]["dr"] == [
            [ "Bob (3.0)" ],
            [""], ["50"], [""], ["50"], [""], [""]
        ]
        assert lfa["distrib"]["DR"] == []
        assert lfa["pie"]["dr"] == [ ["Bob","2"] ]
        assert lfa["pie"]["DR"] == []
        _check_time_plot_values( [1], 1, [
            [ "", "Bob (2)" ],
            [ "Axis 1 PFPh", "4" ],
            [ "Axis 1 DFPh", "2" ],
        ] )
        assert lfa["hotness"] == [ ["Alice",""], ["Bob",""] ]

        # switch to showing the Close Combat DR's and check the results
        _select_roll_type( "CC" )
        lfa = _get_chart_data()
        assert lfa["distrib"]["dr"] == []
        assert lfa["distrib"]["DR"] == []
        assert lfa["pie"]["dr"] == []
        assert lfa["pie"]["DR"] == []
        _check_time_plot_values( [1], 1, [] )
        assert lfa["hotness"] == [ ["Alice",""], ["Bob",""] ]

        # close the analysis window
        find_child( "#lfa button.ui-dialog-titlebar-close" ).click()

    # run the tests
    _run_tests( control_tests, do_test, not pytest.config.option.short_tests ) #pylint: disable=no-member


# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest.config.option.vasl_mods, reason="--vasl-mods not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( not pytest.config.option.vassal, reason="--vassal not specified" ) #pylint: disable=no-member
def test_4players( webapp, webdriver ):
    """Test a file log file analysis with 4 players."""

    # initialize
    control_tests = init_webapp( webapp, webdriver, vlog_persistence=1, lfa_tables=1 )

    def do_test(): #pylint: disable=missing-docstring

        # analyze the log file
        #   RPh     PFPh    MPh      DFPh
        #   ---     -----   ------   ------
        #   A1: 3   C1: 4   D3:  1   C6:  2
        #   B1: 3   C2: 4   D4:  3   D7:  3
        #   A2: 6   C3: 2   D5:  1   D8:  6
        #   A3: 1   B5: 5   A6:  4   A11: 2
        #   B2: 6   B6: 5   A7:  1   D9:  1
        #   A4: 5   D2: 1   A8:  4   D10: 2
        #   B3: 2   C4: 3   A9:  1
        #   B4: 4   C5: 4   A10: 1
        #   A5: 2           B7:  6
        #   D1: 4           B8:  5
        #                   D6:  6
        _analyze_vlogs( "4players.vlog" )

        # check the results
        lfa = _get_chart_data( 1 )
        assert lfa["distrib"]["dr"] == [
            [ "Alice (2.7)", "Bob (4.5)", "Dave (2.8)", "Chuck (3.2)" ],
            [ "36.4", "", "40", "" ],
            [ "18.2", "12.5", "10", "33.3" ],
            [ "9.1", "12.5", "20", "16.7" ],
            [ "18.2", "12.5", "10", "50" ],
            [ "9.1", "37.5", "", "" ],
            [ "9.1", "25", "20", "" ]
        ]
        assert lfa["distrib"]["DR"] == []

        # check the results
        assert lfa["pie"]["dr"] == [ ["Chuck","6"], ["Dave","10"], ["Bob","8"], ["Alice","11"] ]
        assert lfa["pie"]["DR"] == []

        # check the results
        assert lfa["timePlot"] == []

        # switch to showing the Random Selection dr's and check the results
        _select_roll_type( "RS" )
        lfa = _get_chart_data( 1 )
        _check_time_plot_window_sizes( [ 1, 5 ] )
        assert lfa["timePlot"] == [
            [ "", "Alice (11)", "Bob (8)", "Dave (10)", "Chuck (6)" ],
            ["","3","","",""], ["","","3","",""], ["","6","","",""], ["","1","","",""], ["","","6","",""],
            ["","5","","",""], ["","","2","",""], ["","","4","",""], ["","2","","",""], ["","","","4",""],
            [ "Allied 1 PFPh", "", "", "", "4" ],
            ["","","","","4"], ["","","","","2"], ["","","5","",""], ["","","5","",""], ["","","","1",""],
            ["","","","","3"], ["","","","","4"],
            [ "Allied 1 MPh", "", "", "1", "" ],
            ["","","","3",""], ["","","","1",""], ["","4","","",""], ["","1","","",""], ["","4","","",""],
            ["","1","","",""], ["","1","","",""], ["","","6","",""], ["","","5","",""], ["","","","6",""],
            [ "Allied 1 DFPh", "", "", "", "2" ],
            ["","","","3",""], ["","","","6",""], ["","2","","",""], ["","","","1",""], ["","","","2",""]
        ]
        lfa = _get_chart_data( 5 )
        assert lfa["timePlot"] == [
            [ "", "Alice (11)", "Bob (8)", "Dave (10)", "Chuck (6)" ],
            ["","3.4","","",""],
            ["Allied 1 PFPh","","4","",""],
            ["","","4.4","",""], ["","","","","3.4"],
            ["Allied 1 MPh","","","2",""],
            ["","3.6","","",""], ["","2.6","","",""], ["","3.2","","",""], ["","2.4","","",""], ["","2.2","","",""],
            ["","","4.4","",""], ["","","5","",""], ["","","","2.4",""],
            ["Allied 1 DFPh","","","","3"],
            ["","","","2.8",""], ["","","","3.8",""], ["","1.8","","",""], ["","","","3.4",""], ["","","","3.6",""]
        ]

        # close the analysis window
        find_child( "#lfa button.ui-dialog-titlebar-close" ).click()

    # run the tests
    _run_tests( control_tests, do_test, not pytest.config.option.short_tests ) #pylint: disable=no-member

# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest.config.option.vasl_mods, reason="--vasl-mods not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( not pytest.config.option.vassal, reason="--vassal not specified" ) #pylint: disable=no-member
def test_multiple_files( webapp, webdriver ):
    """Test analyzing multiple log files."""

    # initialize
    control_tests = init_webapp( webapp, webdriver, vlog_persistence=1, lfa_tables=1 )

    def check_color_pickers( expected ):
        """Check which color pickers are being presented to the user."""
        find_child( "#lfa .options button.player-colors" ).click()
        popup = wait_for_elem( 2, "#lfa .player-colors-popup" )
        player_names = [ e.text for e in find_children( ".row .caption", popup ) if e.text ]
        assert player_names.pop() == "expected results"
        assert player_names == expected

    def select_file( fname ):
        """Select one of the files being analyzed."""
        find_child( "#lfa .banner .select-file" ).click()
        popup = wait_for_elem( 2, "#lfa .select-file-popup" )
        for row in find_children( ".row", popup ):
            if find_child( "label", row ).text == fname:
                find_child( "input[type='radio']", row ).click()
                return
        assert False, "Couldn't find file: "+fname

    def do_test(): #pylint: disable=missing-docstring

        # NOTE: The "1a" and "1b" log files have the same players (Alice and Bob), but the "2" log file
        # has Bob and Chuck.
        #   multiple-1a   multiple-1b   multiple-2
        #   -----------   -----------   ----------
        #   A: IFT 5 2    A: IFT 3 6    B: IFT 5 5
        #   B: IFT 2 6    B: IFT 4 2    C: IFT 6 5
        #   A: rs  6      A: rs  2      B: sa  4
        #   A: IFT 4 1    Turn Track    Turn Track
        #   B: IFT 4 4    A: IFT 4 3    B: IFT 2 2
        #   B: rs  1      B: IFT 6 4    C: IFT 5 4
        #   Turn Track                  C: rs  5
        #   A: IFT 2 1
        #   B: IFT 4 4
        #   A: rs  2
        #   B: sa  5

        # load 2 log files that have the same players
        _analyze_vlogs( [ "multiple-1a.vlog", "multiple-1b.vlog" ] )

        # check the results
        lfa = _get_chart_data( 1 )
        assert lfa["timePlot"] == [
            [ "", "Alice (5)", "Bob (5)" ],
            ["","7",""], ["","","8"], ["","5",""], ["","","8"],
            [ "Allied 1 PFPh", "3", "" ],
            ["","","8"], ["","9",""], ["","","6"],
            [ "Allied 1 MPh", "7", "" ],
            ["","","10"],
        ]
        assert lfa["hotness"] == [ ["Alice","7.673"], ["Bob","-5.484"] ]
        _select_roll_type( "RS" )
        lfa = _get_chart_data( 1 )
        assert lfa["timePlot"] == [
            [ "", "Alice (3)", "Bob (1)" ],
            ["","6",""], ["","","1"],
            [ "Allied 1 PFPh", "2", "" ],
            ["","2",""],
        ]
        _select_roll_type( "SA" )
        lfa = _get_chart_data( 1 )
        assert lfa["timePlot"] == [
            [ "", "Bob (1)" ],
            [ "Allied 1 PFPh", "5" ],
        ]

        # close the analysis window
        find_child( "#lfa button.ui-dialog-titlebar-close" ).click()

        # load 2 log files that have different players
        _analyze_vlogs( [ "multiple-1a.vlog", "multiple-2.vlog" ] )
        def check_all_files():
            """Check the results for all files."""
            lfa = _get_chart_data( 1 )
            assert lfa["timePlot"] == [
                [ "", "Alice (3)", "Bob (5)", "Chuck (2)" ],
                ["","7","",""], ["","","8",""], ["","5","",""], ["","","8",""],
                [ "Allied 1 PFPh", "3", "", "" ],
                ["","","8",""], ["","","10",""], ["","","","11"],
                [ "UN 1 PFPh", "", "4", "" ],
                ["","","","9"],
            ]
            assert lfa["hotness"] == [ ["Alice","28.512"], ["Bob","-3.336"], ["Chuck","-71.744"] ]
            _select_roll_type( "RS" )
            lfa = _get_chart_data( 1 )
            assert lfa["timePlot"] == [
                [ "", "Alice (2)", "Bob (1)", "Chuck (1)" ],
                ["","6","",""], ["","","1",""],
                [ "Allied 1 PFPh", "2", "", "" ],
                ["UN 1 PFPh","","","5"],
            ]
            _select_roll_type( "SA" )
            lfa = _get_chart_data( 1 )
            assert lfa["timePlot"] == [
                [ "", "Bob (2)" ],
                [ "Allied 1 PFPh", "5" ],
                ["","4"],
            ]
        check_all_files()
        check_color_pickers( [ "Alice", "Bob", "Chuck" ] )

        # select a file and check the results
        select_file( "multiple-1a.vlog" )
        _select_roll_type( "" )
        lfa = _get_chart_data( 1 )
        assert lfa["timePlot"] == [
            [ "", "Alice (3)", "Bob (3)" ],
            ["","7",""], ["","","8"], ["","5",""], ["","","8"],
            [ "Allied 1 PFPh", "3", "" ],
            ["","","8"],
        ]
        assert lfa["hotness"] == [ ["Alice","28.512"], ["Bob","-10.944"] ]
        _select_roll_type( "RS" )
        lfa = _get_chart_data( 1 )
        assert lfa["timePlot"] == [
            [ "", "Alice (2)", "Bob (1)" ],
            ["","6",""], ["","","1"],
            [ "Allied 1 PFPh", "2", "" ],
        ]
        _select_roll_type( "SA" )
        lfa = _get_chart_data( 1 )
        assert lfa["timePlot"] == [
            [ "", "Bob (1)" ],
            [ "Allied 1 PFPh", "5" ],
        ]
        check_color_pickers( [ "Alice", "Bob" ] )

        # select another file and check the results
        select_file( "multiple-2.vlog" )
        _select_roll_type( "" )
        lfa = _get_chart_data( 1 )
        assert lfa["timePlot"] == [
            [ "", "Bob (2)", "Chuck (2)" ],
            ["","10",""], ["","","11"],
            [ "UN 1 PFPh", "4", "" ],
            ["","","9"],
        ]
        assert lfa["hotness"] == [ ["Bob","0.000"], ["Chuck","-71.744"] ]
        _select_roll_type( "RS" )
        lfa = _get_chart_data( 1 )
        assert lfa["timePlot"] == [
            [ "", "Chuck (1)" ],
            [ "UN 1 PFPh", "5" ],
        ]
        _select_roll_type( "SA" )
        lfa = _get_chart_data( 1 )
        assert lfa["timePlot"] == [
            [ "", "Bob (1)" ],
            ["","4"],
        ]
        check_color_pickers( [ "Bob", "Chuck" ] )

        # select all files and check the results
        select_file(  "All files" )
        _select_roll_type( "" )
        check_all_files()
        check_color_pickers( [ "Alice", "Bob", "Chuck" ] )

        # close the analysis window
        find_child( "#lfa button.ui-dialog-titlebar-close" ).click()

    # run the tests
    _run_tests( control_tests, do_test, not pytest.config.option.short_tests ) #pylint: disable=no-member

# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest.config.option.vasl_mods, reason="--vasl-mods not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( not pytest.config.option.vassal, reason="--vassal not specified" ) #pylint: disable=no-member
def test_3d6( webapp, webdriver ):
    """Test scenarios that use the 3d6 extension."""

    # initialize
    control_tests = init_webapp( webapp, webdriver, vlog_persistence=1, lfa_tables=1 )

    def do_test(): #pylint: disable=missing-docstring

        # analyze the log file
        _analyze_vlogs( "3d6.vlog" )

        # check the results
        #   IFT 6,6
        #   RS  2
        #   3d6 3,4,1
        #   IFT 6,5
        #   TH  6,2
        #   3d6 2,4,2
        lfa = _get_chart_data( 1 )
        assert lfa["timePlot"] == [
            [ "", "test (5)" ],
            ["","12"], ["","7"], ["","11"], ["","8"], ["","6"]
        ]
        _select_roll_type( "3d6 (DR)" )
        lfa = _get_chart_data()
        assert lfa["timePlot"] == [
            [ "", "test (2)" ],
            ["","7"], ["","6"]
        ]
        _select_roll_type( "3d6 (dr)" )
        lfa = _get_chart_data()
        assert lfa["timePlot"] == [
            [ "", "test (2)" ],
            ["","1"], ["","2"]
        ]

        # close the analysis window
        find_child( "#lfa button.ui-dialog-titlebar-close" ).click()

    # run the tests
    _run_tests( control_tests, do_test, not pytest.config.option.short_tests ) #pylint: disable=no-member

# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest.config.option.vasl_mods, reason="--vasl-mods not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( not pytest.config.option.vassal, reason="--vassal not specified" ) #pylint: disable=no-member
def test_banner_updates( webapp, webdriver ):
    """Test updating the banner."""

    # initialize
    control_tests = init_webapp( webapp, webdriver, vlog_persistence=1 )

    def check_banner( roll_type ):
        """Check the banner."""
        assert find_child( "#lfa .banner .title" ).text == "Log File Analysis test"
        assert find_child( "#lfa .banner .title2" ).text == "(LFA-1)"
        assert find_child( "#lfa .banner .roll-type" ).text == roll_type

    def do_test(): #pylint: disable=missing-docstring

        # analyze the log file
        _analyze_vlogs( "banner-updates.vlog" )

        # check the banner as the roll type is changed
        check_banner( "Showing all rolls." )
        _select_roll_type( "MC" )
        check_banner( "Showing Morale Check rolls." )
        _select_roll_type( "RS" )
        check_banner( "Showing Random Selection rolls." )

        # close the analysis window
        find_child( "#lfa button.ui-dialog-titlebar-close" ).click()

    # run the tests
    _run_tests( control_tests, do_test, not pytest.config.option.short_tests ) #pylint: disable=no-member

# ---------------------------------------------------------------------

@pytest.mark.skipif( not pytest.config.option.vasl_mods, reason="--vasl-mods not specified" ) #pylint: disable=no-member
@pytest.mark.skipif( not pytest.config.option.vassal, reason="--vassal not specified" ) #pylint: disable=no-member
def test_download_data( webapp, webdriver ):
    """Test downloading the data."""

    # initialize
    control_tests = init_webapp( webapp, webdriver, vlog_persistence=1, lfa_persistence=1 )

    def do_test(): #pylint: disable=missing-docstring

        # analyze the log file
        _analyze_vlogs( "download-test.vlog" )

        # download the data
        marker = set_stored_msg_marker( "_lfa-download_" )
        find_child( "#lfa button.download" ).click()
        wait_for( 2, lambda: get_stored_msg("_lfa-download_") != marker )
        data = get_stored_msg( "_lfa-download_" )

        # check the results
        data = data.split( "\n" )
        rows = list( csv.reader( data, quoting=csv.QUOTE_NONNUMERIC ) )
        assert rows == [
            [ "Log file", "Phase", "Player", "Type", "Die 1", "Die 2" ],
            [ "download-test.vlog", "", 'Joey "The Lips" Blow', "IFT", 4, 1 ],
            [ "", "", 'Joey "The Lips" Blow', "IFT", 2, 5 ],
            [ "", "", 'Joey "The Lips" Blow', "RS", 2, "" ],
            [ "", "UN 1 PFPh", "\u65e5\u672c Guy", "IFT", 4, 6 ],
            [ "", "", "\u65e5\u672c Guy", "IFT", 2, 6 ],
            [ "", "", "\u65e5\u672c Guy", "RS", 3, "" ],
            [ "", "UN 1 MPh", 'Joey "The Lips" Blow', "IFT", 2, 6 ],
            [ "", "", 'Joey "The Lips" Blow', "IFT", 2, 3 ],
            [ "", "", 'Joey "The Lips" Blow', "RS", 3, "" ]
        ]

    # run the test
    _run_tests( control_tests, do_test, False )

# ---------------------------------------------------------------------

def _analyze_vlogs( fnames ):
    """Analyze log file(s)."""

    # initialize
    if isinstance( fnames, str ):
        fnames = [ fnames ]
    select_menu_option( "analyze_vlog" )
    dlg = wait_for_elem( 2, ".ui-dialog.lfa-upload" )

    # add each log file
    for fname in fnames:
        fname = os.path.join( os.path.split(__file__)[0], "fixtures/analyze-vlog/"+fname )
        vlog_data = open( fname, "rb" ).read()
        set_stored_msg( "_vlog-persistence_", "{}|{}".format(
            os.path.split( fname )[1],
            base64.b64encode( vlog_data ).decode( "utf-8" )
        ) )
        find_child( "button.add", dlg ).click()
        wait_for( 2, lambda: get_stored_msg( "_vlog-persistence_" ) == "" )

    # start the analysis
    find_child( "button.ok", dlg ).click()
    wait_for_elem( 30, "#lfa" )

def _get_chart_data( window_size=None ):
    """Unload the chart data from the page."""
    # set the time-plot window size
    if window_size is not None:
        _set_time_plot_window_size( window_size )
    # unload the chart data
    remove_first_col = lambda data: [ row[1:] for row in data ]
    remove_last_col = lambda data: [ row[:-1] for row in data ]
    remove_first_row = lambda data: data[1:]
    return {
        "distrib": {
            "dr": remove_first_col( remove_last_col( _unload_table( "distrib d6x1" ) ) ),
            "DR": remove_first_col( remove_last_col( _unload_table( "distrib d6x2" ) ) ),
        },
        "pie": {
            "dr": remove_first_row( _unload_table( "pie d6x1" ) ),
            "DR": remove_first_row( _unload_table( "pie d6x2" ) ),
        },
        "timePlot": _unload_table( "time-plot" ),
        "hotness": remove_first_row( _unload_table( "hotness" ) ),
    }

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def _select_roll_type( roll_type ):
    """Select the roll type."""
    elem = find_child( "select[name='roll-type']" )
    select_droplist_val( Select(elem), roll_type, isSelectMenu=True )

def _check_time_plot_window_sizes( expected ):
    """Check the available time-plot window sizes."""
    elem = find_child( "select[name='moving-average']" )
    vals = get_droplist_vals( Select(elem) )
    assert [ int(v[0]) for v in vals ] == expected

def _set_time_plot_window_size( window_size ):
    """Select the specified time-plot moving average window size."""
    elem = find_child( "select[name='moving-average']" )
    select_droplist_val( Select(elem), window_size, isSelectMenu=True )

def _check_time_plot_values( expected_window_sizes, window_size, expected ):
    """Check the time-plot values."""
    # set the window size
    assert int(window_size) in expected_window_sizes
    _set_time_plot_window_size( window_size )
    # unload and check the time plot values
    vals = _unload_table( "time-plot" )
    assert vals == expected

def _unload_table( sel ):
    """Unload chart data from an HTML table."""
    return unload_table(
        "//*[@class='{}']//table[@class='chart-data']//tr".format( sel )
    )
