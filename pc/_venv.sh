# Wird von start.sh, monitor.sh und pico_aufspielen.sh eingebunden (nicht direkt starten).
# Legt die virtuelle Umgebung .venv im Projektordner an und installiert pc/requirements.txt,
# beim ersten Mal und immer dann, wenn sich requirements.txt geaendert hat.
# PYTHONPATH (z. B. vom ROS-Workspace im Profil) gilt nur fuer dieses Skript nicht,
# damit keine fremden Pakete in die venv hineinragen. Das Terminal behaelt ihn.
unset PYTHONPATH PYTHONHOME
PROJEKT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$PROJEKT/.venv"
REQ="$PROJEKT/pc/requirements.txt"

if [ ! -x "$VENV/bin/python" ]; then
    echo "Lege virtuelle Umgebung an: $VENV"
    python3 -m venv "$VENV"
fi
if [ ! -f "$VENV/.installiert" ] || [ "$REQ" -nt "$VENV/.installiert" ]; then
    echo "Installiere Pakete aus pc/requirements.txt ..."
    "$VENV/bin/pip" install -q --disable-pip-version-check -r "$REQ"
    touch "$VENV/.installiert"
fi
