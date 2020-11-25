#!/bin/sh

# set up the display (so we can run VASSAL and a webdriver)
export ENV=10
export DISPLAY=:10.0
Xvfb :10 -ac 1>/tmp/xvfb.log 2>/tmp/xvfb.err &

# run the webapp server
python3 /app/vasl_templates/webapp/run_server.py \
    --addr 0.0.0.0 \
    --force-init-delay 30
