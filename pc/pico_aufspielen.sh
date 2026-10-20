#!/usr/bin/env bash
# Kopiert pico/main.py und pico/kontakt.py auf den Pico (statt Thonny) und startet ihn neu.
# Voraussetzung: MicroPython ist schon auf dem Pico (siehe README.de.md, Abschnitt 3.4).
# Thonny, pc/start.sh und pc/monitor.sh vorher schliessen, sonst ist der Anschluss belegt.
set -e
source "$(dirname "$0")/_venv.sh"
"$VENV/bin/mpremote" connect auto cp "$PROJEKT/pico/kontakt.py" :kontakt.py \
    + cp "$PROJEKT/pico/main.py" :main.py + reset
echo "main.py und kontakt.py sind auf dem Pico. Jetzt mit pc/start.sh oder pc/monitor.sh die Werte ansehen."
