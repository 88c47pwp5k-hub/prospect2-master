#!/bin/bash
# Lance le dashboard Flask Prospect 2.0 sur localhost:7373
# et l'ouvre dans Chrome. Appelé par Pipeline Prospects.app.

FLASK_SCRIPT="$HOME/dashboard/dashboard_server.py"
PORT=7373
LOG="/tmp/pipeline_flask.log"

# Vérifier si quelque chose écoute déjà sur le port 7373
if ! lsof -i :"$PORT" -n -P 2>/dev/null | grep -q LISTEN; then
    # Démarrer le serveur Flask en arrière-plan
    nohup python3 "$FLASK_SCRIPT" >> "$LOG" 2>&1 &
    # Attendre que le serveur soit prêt (max 8 secondes)
    for i in $(seq 1 8); do
        sleep 1
        if curl -s -o /dev/null -w "%{http_code}" "http://localhost:$PORT/" 2>/dev/null | grep -q "200"; then
            break
        fi
    done
fi

# Ouvrir dans Chrome
open -a "Google Chrome" "http://localhost:$PORT/"
