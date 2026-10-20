#!/usr/bin/env bash
# Startet den Greifer-Monitor (Live-Diagramm, Aufnahme, Pol-Anzeige) in der venv.
#   pc/monitor.sh                      live vom Pico
#   pc/monitor.sh greifer_....csv      eine Aufnahme auswerten
set -e
source "$(dirname "$0")/_venv.sh"
exec "$VENV/bin/python" "$PROJEKT/pc/greifer_monitor.py" "$@"
