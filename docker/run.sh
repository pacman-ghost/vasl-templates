#!/bin/sh

# set up the display (so we can run a webdriver)
export ENV=10
Xvfb :10 -ac 1>/tmp/xvfb.log 2>/tmp/xvfb.err &

# run the webapp server
python /app/vasl_templates/webapp/run_server.py
