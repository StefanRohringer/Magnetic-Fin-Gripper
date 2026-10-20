#!/usr/bin/env bash
# Magnetic-Fin-Gripper  Copyright (C) 2026  Stefan Rohringer
# SPDX-License-Identifier: GPL-3.0-or-later
# This program comes with ABSOLUTELY NO WARRANTY. It is free software, and you are welcome
# to redistribute it under the terms of the GNU GPL, version 3 or later (see LICENSE).

# Startet den Greifer-Monitor (Live-Diagramm, Aufnahme, Pol-Anzeige) in der venv.
#   pc/monitor.sh                      live vom Pico
#   pc/monitor.sh greifer_....csv      eine Aufnahme auswerten
set -e
source "$(dirname "$0")/_venv.sh"
exec "$VENV/bin/python" "$PROJEKT/pc/greifer_monitor.py" "$@"
