#!/bin/bash
pkill -f generer_pipeline.py 2>/dev/null
sleep 1
/usr/bin/python3 "$HOME/Documents/prospect2/generer_pipeline.py" > "$HOME/Documents/prospect2/pipeline_log.txt" 2>&1 &
