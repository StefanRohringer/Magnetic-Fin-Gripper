#!/usr/bin/env bash
# Startet greifer_lesen.py (Werte als Text, Aufnahme als CSV) in der eigenen virtuellen
# Umgebung .venv im Projektordner. Beim ersten Aufruf wird sie angelegt.
# Weitere Argumente gehen durch, z. B.:  pc/start.sh --port /dev/ttyACM1
set -e
source "$(dirname "$0")/_venv.sh"
exec "$VENV/bin/python" "$PROJEKT/pc/greifer_lesen.py" "$@"
