#!/usr/bin/env bash
# Magnetic-Fin-Gripper  Copyright (C) 2026  Stefan Rohringer
# SPDX-License-Identifier: GPL-3.0-or-later
# This program comes with ABSOLUTELY NO WARRANTY. It is free software, and you are welcome
# to redistribute it under the terms of the GNU GPL, version 3 or later (see LICENSE).

# Startet greifer_lesen.py (Werte als Text, Aufnahme als CSV) in der eigenen virtuellen
# Umgebung .venv im Projektordner. Beim ersten Aufruf wird sie angelegt.
# Weitere Argumente gehen durch, z. B.:  pc/start.sh --port /dev/ttyACM1
set -e
source "$(dirname "$0")/_venv.sh"
exec "$VENV/bin/python" "$PROJEKT/pc/greifer_lesen.py" "$@"
