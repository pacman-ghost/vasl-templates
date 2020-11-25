#!/usr/bin/env python3
""" Stress-test the shared WebDriver. """

import os
import threading
import signal
import http.client
import time
import datetime
import base64
import random
import json
import logging
from collections import defaultdict

import click
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

from vasl_templates.webapp.webdriver import WebDriver
from vasl_templates.webapp.tests.test_scenario_persistence import load_scenario
from vasl_templates.webapp.tests.utils import wait_for, find_child, find_snippet_buttons, \
    select_tab, select_menu_option, click_dialog_button, set_stored_msg, get_stored_msg

shutdown_event = threading.Event()
thread_count = None

stats_lock = threading.Lock()
stats = defaultdict( lambda: [0,0] ) # nb: [ #runs, total elapsed time ]

# ---------------------------------------------------------------------

@click.command()
@click.option( "--webapp-url", default="http://localhost:5010", help="Webapp server URL." )
@click.option( "--snippet-images", default=1, help="Number of 'snippet image' threads to run." )
@click.option( "--update-vsav", default=1, help="Number of 'update VSAV' threads to run." )
@click.option( "--vsav","vsav_fname", help="VASL scenario file (.vsav) to be updated." )
def main( webapp_url, snippet_images, update_vsav, vsav_fname ):
    """Stress-test the shared WebDriver."""

    # initialize
    logging.disable( logging.CRITICAL )

    # read the VASL scenario file
    vsav_data = None
    if update_vsav > 0:
        vsav_data = open( vsav_fname, "rb" ).read()

    # prepare the test threads
    threads = []
    for i in range(0,snippet_images):
        threads.append( threading.Thread(
            target = snippet_images_thread,
            name = "snippet-images/{:02d}".format( 1+i ),
            args = ( webapp_url, )
        ) )
    for i in range(0,update_vsav):
        threads.append( threading.Thread(
            target = update_vsav_thread,
            name = "update-vsav/{:02d}".format( 1+i ),
            args = ( webapp_url, vsav_fname, vsav_data )
        ) )

    # launch the test threads
    start_time = time.time()
    global thread_count
    thread_count = len(threads)
    for thread in threads:
        thread.start()

    # wait for Ctrl-C
    def on_sigint( signum, stack ): #pylint: disable=missing-docstring,unused-argument
        print( "\n*** SIGINT received ***\n" )
        shutdown_event.set()
    signal.signal( signal.SIGINT, on_sigint )
    while not shutdown_event.is_set():
        time.sleep( 1 )

    # wait for the test threads to shutdown
    for thread in threads:
        print( "Waiting for thread to finish:", thread )
        thread.join()
    elapsed_time = time.time() - start_time
    print()

    # output stats
    print( "=== STATS ===")
    print()
    print( "Total run time: {}".format( datetime.timedelta( seconds=int(elapsed_time) ) ) )
    for key,val in stats.items():
        print( "- {:<14} {}".format( key+":", val[0] ), end="" )
        if val[0] > 0:
            print( " (avg={:.3f}s)".format( float(val[1])/val[0] ) )
        else:
            print()

# ---------------------------------------------------------------------

def snippet_images_thread( webapp_url ):
    """Test generating snippet images."""

    with WebDriver() as webdriver:

        # initialize
        webdriver = webdriver.driver
        init_webapp( webdriver, webapp_url,
             [ "snippet_image_persistence", "scenario_persistence" ]
        )

        # load a scenario (so that we get some sortable's)
        scenario_data = {
            "SCENARIO_NOTES": [ { "caption": "Scenario note #1"  } ],
            "OB_SETUPS_1": [ { "caption": "OB setup note #1" } ],
            "OB_NOTES_1": [ { "caption": "OB note #1" } ],
            "OB_SETUPS_2": [ { "caption": "OB setup note #2" } ],
            "OB_NOTES_2": [ { "caption": "OB note #2" } ],
        }
        load_scenario( scenario_data, webdriver )

        # locate all the "generate snippet" buttons
        snippet_btns = find_snippet_buttons( webdriver )
        tab_ids = list( snippet_btns.keys() )

        while not shutdown_event.is_set():

            try:
                # clear the return buffer
                ret_buffer = find_child( "#_snippet-image-persistence_", webdriver )
                assert ret_buffer.tag_name == "textarea"
                webdriver.execute_script( "arguments[0].value = arguments[1]", ret_buffer, "" )

                # generate a snippet
                tab_id = random.choice( tab_ids )
                btn = random.choice( snippet_btns[ tab_id ] )
                log( "Getting snippet image: {}", btn.get_attribute("data-id") )
                select_tab( tab_id, webdriver )
                start_time = time.time()
                ActionChains( webdriver ) \
                    .key_down( Keys.SHIFT ) \
                    .click( btn ) \
                    .key_up( Keys.SHIFT ) \
                    .perform()

                # wait for the snippet image to be generated
                wait_for( 10*thread_count, lambda: ret_buffer.get_attribute( "value" ) )
                _, img_data = ret_buffer.get_attribute( "value" ).split( "|", 1 )
                elapsed_time = time.time() - start_time

                # update the stats
                with stats_lock:
                    stats["snippet image"][0] += 1
                    stats["snippet image"][1] += elapsed_time

                # FUDGE! Generating the snippet image for a sortable entry is sometimes interpreted as
                # a request to edit the entry (Selenium problem?) - we dismiss the dialog here and continue.
                dlg = find_child( ".ui-dialog", webdriver )
                if dlg and dlg.is_displayed():
                    click_dialog_button( "Cancel", webdriver )

            except ( ConnectionRefusedError, ConnectionResetError, http.client.RemoteDisconnected ):
                if shutdown_event.is_set():
                    break
                raise

            # check the generated snippet
            img_data = base64.b64decode( img_data )
            log( "Received snippet image: #bytes={}", len(img_data) )
            assert img_data[:6] == b"\x89PNG\r\n"

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

def update_vsav_thread( webapp_url, vsav_fname, vsav_data ):
    """Test updating VASL scenario files."""

    # initialize
    vsav_data_b64 = base64.b64encode( vsav_data ).decode( "utf-8" )

    with WebDriver() as webdriver:

        # initialize
        webdriver = webdriver.driver
        init_webapp( webdriver, webapp_url,
             [ "vsav_persistence", "scenario_persistence" ]
        )

        # load a test scenario
        fname = os.path.join( os.path.split(__file__)[0], "../webapp/tests/fixtures/update-vsav/full.json" )
        saved_scenario = json.load( open( fname, "r" ) )
        load_scenario( saved_scenario, webdriver )

        while not shutdown_event.is_set():

            try:

                # send the VSAV data to the front-end to be updated
                log( "Updating VSAV: {}", vsav_fname )
                set_stored_msg( "_vsav-persistence_", vsav_data_b64, webdriver )
                select_menu_option( "update_vsav", webdriver )
                start_time = time.time()

                # wait for the front-end to receive the data
                wait_for( 2*thread_count,
                    lambda: get_stored_msg( "_vsav-persistence_", webdriver ) == ""
                )

                # wait for the updated data to arrive
                wait_for( 60*thread_count,
                    lambda: get_stored_msg( "_vsav-persistence_", webdriver ) != ""
                )
                elapsed_time = time.time() - start_time

                # get the updated VSAV data
                updated_vsav_data = get_stored_msg( "_vsav-persistence_", webdriver )
                if updated_vsav_data.startswith( "ERROR: " ):
                    raise RuntimeError( updated_vsav_data )
                updated_vsav_data = base64.b64decode( updated_vsav_data )

                # check the updated VSAV
                log( "Received updated VSAV data: #bytes={}", len(updated_vsav_data) )
                assert updated_vsav_data[:2] == b"PK"

                # update the stats
                with stats_lock:
                    stats["update vsav"][0] += 1
                    stats["update vsav"][1] += elapsed_time

            except (ConnectionRefusedError, ConnectionResetError, http.client.RemoteDisconnected):
                if shutdown_event.is_set():
                    break
                raise

# ---------------------------------------------------------------------

def log( fmt, *args, **kwargs ):
    """Log a message."""
    now = time.time()
    msec = now - int(now)
    now = "{}.{:03d}".format( time.strftime("%H:%M:%S",time.localtime(now)), int(msec*1000) )
    msg = fmt.format( *args, **kwargs )
    msg = "{} | {:17} | {}".format( now, threading.current_thread().name, msg )
    print( msg )

# ---------------------------------------------------------------------

def init_webapp( webdriver, webapp_url, options ):
    """Initialize the webapp."""
    log( "Initializing the webapp." )
    url = webapp_url + "?" + "&".join( "{}=1".format(opt) for opt in options )
    url += "&store_msgs=1" # nb: stop notification balloons from building up
    webdriver.get( url )
    wait_for( 5, lambda: find_child("#_page-loaded_",webdriver) is not None )

# ---------------------------------------------------------------------

if __name__ == "__main__":
    main() #pylint: disable=no-value-for-parameter
