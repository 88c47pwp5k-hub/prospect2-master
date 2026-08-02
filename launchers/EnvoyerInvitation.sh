#!/bin/bash
pkill -f send_invitation_app.py 2>/dev/null
sleep 1
/usr/bin/python3 "$HOME/Documents/prospect2/send_invitation_app.py" > "$HOME/Documents/prospect2/invitation_log.txt" 2>&1 &
