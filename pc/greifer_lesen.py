#!/usr/bin/env python3
"""Liest die Greifer-Sensorik vom Pico ueber USB, zeigt sie live und speichert sie als CSV.

Aufruf:   pc/start.sh                     (eigene venv, findet den Pico selbst)
          pc/start.sh --port /dev/ttyACM1
Ende:     Strg+C

Der Pico wird nur ueber seine USB-Kennung (Raspberry Pi, 2E8A) gesucht, damit nie
versehentlich der Anschluss des Arms geoeffnet wird.
Braucht:  pyserial (pc/requirements.txt, start.sh installiert es in die venv)
"""
import argparse
import datetime
import os
import sys
import time

import serial
from serial.tools import list_ports

PICO_VID = 0x2E8A
# Aufnahmen landen immer in <Projekt>/messungen, egal aus welchem Ordner gestartet wird
MESS_ORDNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "messungen")


def aufnahme_pfad():
    os.makedirs(MESS_ORDNER, exist_ok=True)
    name = "greifer_%s.csv" % datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")
    return os.path.normpath(os.path.join(MESS_ORDNER, name))


def pico_finden():
    treffer = [p.device for p in list_ports.comports() if p.vid == PICO_VID]
    if not treffer:
        sys.exit("Kein Pico gefunden. USB-Kabel pruefen (Datenkabel, kein reines Ladekabel).")
    if len(treffer) > 1:
        sys.exit("Mehrere Picos gefunden: %s. Bitte mit --port waehlen." % ", ".join(treffer))
    return treffer[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", help="z. B. /dev/ttyACM1 (Standard: automatisch)")
    ap.add_argument("--ohne-null", action="store_true",
                    help="beim Start keinen neuen Nullpunkt nehmen")
    a = ap.parse_args()

    port = a.port or pico_finden()
    datei = aufnahme_pfad()
    print("Pico an %s, speichere nach %s" % (port, datei))

    with serial.Serial(port, 115200, timeout=1) as s, open(datei, "w") as f:
        time.sleep(0.5)
        s.reset_input_buffer()
        s.write(b"a")              # Abweichung statt Rohwerte, falls jemand "r" gedrueckt hat
        if not a.ohne_null:
            print("Nullpunkt: Finger jetzt nicht beruehren ...")
            s.write(b"n")          # danach schickt der Pico auch die Kopfzeile
        else:
            s.write(b"k")          # nur die Kopfzeile anfordern
        s.write(b"f")              # schnelle Ausgabe fuer die Datei (Firmware 2)
        kopf = None
        zuletzt = 0.0
        while True:
            zeile = s.readline().decode(errors="replace").strip()
            if not zeile:
                continue
            if zeile.startswith("#"):
                print(zeile)
                if "Ausgabe: langsam" in zeile:   # jemand hat langsam geschaltet: wieder schnell
                    s.write(b"f")
                continue
            if zeile.startswith("K,"):
                kopf = zeile.split(",")
                f.write("pc_zeit," + zeile[2:] + "\n")
                continue
            if not zeile.startswith("D,") or kopf is None:
                continue
            f.write("%.3f,%s\n" % (time.time(), zeile[2:]))
            if time.time() - zuletzt >= 0.2:
                zuletzt = time.time()
                werte = zeile.split(",")
                teile = []
                for i in range(2, len(kopf) - 1, 4):
                    name = kopf[i][:-1]
                    teile.append("%s %6s" % (name, werte[i + 3] if i + 3 < len(werte) else "?"))
                print("  ".join(teile) + "   uT   Kontakt: " + werte[-1])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBeendet.")
