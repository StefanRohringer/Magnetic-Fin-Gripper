#!/usr/bin/env python3
# Magnetic-Fin-Gripper  Copyright (C) 2026  Stefan Rohringer
# SPDX-License-Identifier: GPL-3.0-or-later
# This program comes with ABSOLUTELY NO WARRANTY. It is free software, and you are welcome
# to redistribute it under the terms of the GNU GPL, version 3 or later (see LICENSE).

"""Greifer-Monitor: Sensorwerte live als Diagramm, Aufnahme, Magnet-Pol-Pruefung, CSV-Auswertung.

Aufruf:   pc/monitor.sh                         live vom Pico (findet ihn selbst)
          pc/monitor.sh --port /dev/ttyACM1
          pc/monitor.sh greifer_2026-10-16_194112.csv   eine Aufnahme auswerten
Thonny und pc/start.sh vorher schliessen, sonst ist der Anschluss belegt.

Live-Fenster:
  oben     Betrag der Abweichung vom Nullpunkt je Sensor (uT); ob Kontakt ist, entscheidet
           der Pico (pico/kontakt.py, Druck in Druckrichtung), angezeigt rechts
  unten    x, y, z des gewaehlten Sensors
  rechts   Wert und Kontakt je Sensor, Sensorwahl, Knoepfe Nullpunkt und Aufnahme,
           Pol-Anzeige: Magnet mit der flachen Seite vor den Chip halten (etwa 5 mm),
           angezeigt wird, in welche Richtung das Feld zeigt. Gleiche Anzeige = gleicher Pol.
"""
import argparse
import collections
import csv
import sys
import threading
import time

import os

import matplotlib
if not os.environ.get("MPLBACKEND"):
    matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button, RadioButtons

# Kontakterkennung: dieselbe Datei wie auf dem Pico, damit die Auswertung gleich entscheidet
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "pico"))
import kontakt  # noqa: E402

POL_AB_UT = 1000.0       # ab dieser Abweichung zeigt die Pol-Anzeige etwas an
FENSTER_S = 10.0         # so viele Sekunden zeigt das Live-Diagramm
FARBEN = {"L1": "tab:blue", "L2": "tab:orange", "R1": "tab:green", "R2": "tab:red"}


def zahl(s):
    try:
        return float(s)
    except ValueError:
        return float("nan")


def namen_aus_kopf(kopf):
    """Kopf: [.., ms, L1x, L1y, L1z, L1b, ..., kontakt] -> ["L1", ...]"""
    i = kopf.index("ms") + 1
    return [k[:-1] for k in kopf[i:-1:4]]


# ---------------------------------------------------------------- live

class Verbindung(threading.Thread):
    """Liest die Zeilen vom Pico im Hintergrund und haelt die letzten Sekunden bereit."""

    def __init__(self, port):
        import serial
        super().__init__(daemon=True)
        self.s = serial.Serial(port, 115200, timeout=0.2)
        self.lock = threading.Lock()
        self.namen = []
        self.kopf = None
        self.daten = {}                       # Name -> deque[(t, x, y, z, b)]
        self.kontakt = "-"
        self.meldungen = collections.deque(maxlen=5)
        self.aufnahme = None
        self.aufnahme_zeilen = 0
        self.laeuft = True

    def senden(self, zeichen):
        self.s.write(zeichen.encode())

    def run(self):
        time.sleep(0.5)
        self.s.reset_input_buffer()
        self.senden("a")                      # Abweichung statt Rohwerte, falls jemand "r" gedrueckt hat
        self.senden("n")                    # Nullpunkt, danach kommt die Kopfzeile
        self.senden("f")                      # schnelle Ausgabe (Firmware 2)
        while self.laeuft:
            zeile = self.s.readline().decode(errors="replace").strip()
            if not zeile:
                continue
            if zeile.startswith("#"):
                with self.lock:
                    self.meldungen.append(zeile[1:].strip())
                if "Ausgabe: langsam" in zeile:   # jemand hat langsam geschaltet: wieder schnell
                    self.senden("f")
                continue
            teile = zeile.split(",")
            if teile[0] == "K":
                with self.lock:
                    self.kopf = teile
                    self.namen = namen_aus_kopf(teile)
                    for n in self.namen:
                        self.daten.setdefault(n, collections.deque(maxlen=3000))
                    if self.aufnahme:
                        self.aufnahme.write("pc_zeit," + zeile[2:] + "\n")
                continue
            if teile[0] != "D" or self.kopf is None or len(teile) != len(self.kopf):
                continue
            t = int(teile[1]) / 1000.0
            with self.lock:
                for i, n in enumerate(self.namen):
                    x, y, z, b = (zahl(v) for v in teile[2 + 4 * i: 6 + 4 * i])
                    self.daten[n].append((t, x, y, z, b))
                self.kontakt = teile[-1]
                if self.aufnahme:
                    self.aufnahme.write("%.3f,%s\n" % (time.time(), zeile[2:]))
                    self.aufnahme_zeilen += 1

    def aufnahme_umschalten(self):
        with self.lock:
            if self.aufnahme:
                self.aufnahme.close()
                self.aufnahme = None
                return None
            from greifer_lesen import aufnahme_pfad
            datei = aufnahme_pfad()
            self.aufnahme = open(datei, "w")
            self.aufnahme_zeilen = 0
            if self.kopf:
                self.aufnahme.write("pc_zeit," + ",".join(self.kopf[1:]) + "\n")
            return datei

    def schliessen(self):
        self.laeuft = False
        with self.lock:
            if self.aufnahme:
                self.aufnahme.close()
                self.aufnahme = None
        self.s.close()


def pol_text(x, y, z, b):
    if not b == b or b < POL_AB_UT:
        return "Pol: Magnet naeher ran\n(flache Seite zum Chip)", "0.5"
    achse, wert = max((("x", x), ("y", y), ("z", z)), key=lambda e: abs(e[1]))
    return "Pol: %s %s\n(%.1f mT)" % (achse, "PLUS" if wert > 0 else "MINUS", wert / 1000), \
        ("tab:red" if wert > 0 else "tab:blue")


def live(port):
    v = Verbindung(port)
    v.start()
    print("Pico an %s. Fenster schliessen zum Beenden." % port)

    fig = plt.figure("Greifer-Monitor", figsize=(13, 7.5))
    ax_b = fig.add_axes([0.06, 0.42, 0.62, 0.52])
    ax_xyz = fig.add_axes([0.06, 0.07, 0.62, 0.27], sharex=ax_b)
    ax_b.set_ylabel("Abweichung |B| vom Nullpunkt (uT)")
    ax_xyz.set_ylabel("x / y / z (uT)")
    ax_xyz.set_xlabel("Zeit (s)")
    for ax in (ax_b, ax_xyz):
        ax.grid(alpha=0.3)

    status = fig.text(0.72, 0.94, "Warte auf Pico ...", va="top", family="monospace", fontsize=12)
    pol = fig.text(0.72, 0.44, "", va="top", fontsize=13, weight="bold")
    info = fig.text(0.72, 0.30, "", va="top", fontsize=8.5, color="0.35", wrap=True)

    linien_b, linien_xyz = {}, []
    for farbe, achse in (("tab:red", "x"), ("tab:green", "y"), ("tab:blue", "z")):
        linien_xyz.append(ax_xyz.plot([], [], color=farbe, lw=1, label=achse)[0])
    ax_xyz.legend(loc="upper left", ncol=3, fontsize=8)

    auswahl = {"name": None}
    ax_radio = fig.add_axes([0.72, 0.56, 0.1, 0.16])
    ax_radio.set_title("Sensor unten", fontsize=9)
    radio = {"w": None}

    def radio_bauen(namen):
        ax_radio.clear()
        ax_radio.set_title("Sensor unten", fontsize=9)
        radio["w"] = RadioButtons(ax_radio, namen)
        radio["w"].on_clicked(lambda n: auswahl.update(name=n))
        auswahl["name"] = namen[0]

    ax_null = fig.add_axes([0.84, 0.66, 0.13, 0.06])
    ax_auf = fig.add_axes([0.84, 0.57, 0.13, 0.06])
    knopf_null = Button(ax_null, "Nullpunkt (n)")
    knopf_auf = Button(ax_auf, "Aufnahme starten")
    knopf_null.on_clicked(lambda _e: v.senden("n"))

    def aufnahme(_e):
        datei = v.aufnahme_umschalten()
        knopf_auf.label.set_text("Aufnahme stoppen" if datei else "Aufnahme starten")
        ax_auf.set_facecolor("#f4c7c3" if datei else "0.85")
        print("Aufnahme nach %s" % datei if datei else "Aufnahme beendet.")
    knopf_auf.on_clicked(aufnahme)

    bekannte = []

    def zeichnen(_frame):
        with v.lock:
            namen = list(v.namen)
            kopien = {n: list(v.daten.get(n, ())) for n in namen}
            kontakt = v.kontakt
            meldungen = list(v.meldungen)
            auf, auf_n = v.aufnahme, v.aufnahme_zeilen
        if namen and namen != bekannte:
            bekannte[:] = namen
            for n in namen:
                if n not in linien_b:
                    linien_b[n] = ax_b.plot([], [], color=FARBEN.get(n), lw=1.4, label=n)[0]
            ax_b.legend(loc="upper left", ncol=4, fontsize=9)
            radio_bauen(namen)
        if not namen:
            info.set_text("\n".join(meldungen))
            return
        t_end = max((d[-1][0] for d in kopien.values() if d), default=0)
        zeilen, ymax = [], 300.0
        for n in namen:
            d = np.array(kopien[n]) if kopien[n] else np.empty((0, 5))
            d = d[d[:, 0] > t_end - FENSTER_S] if len(d) else d
            linien_b[n].set_data(d[:, 0] - t_end, d[:, 4]) if len(d) else linien_b[n].set_data([], [])
            if len(d):
                ymax = max(ymax, np.nanmax(d[:, 4]) * 1.1)
            letzter = d[-1, 4] if len(d) else float("nan")
            marke = "KONTAKT" if n in kontakt.split() else ""
            if n + "!SAETTIGUNG" in kontakt:
                marke = "SAETTIGUNG!"
            zeilen.append("%-3s %7.0f uT  %s" % (n, letzter, marke))
            if n == auswahl["name"] and len(d):
                for i, linie in enumerate(linien_xyz):
                    linie.set_data(d[:, 0] - t_end, d[:, 1 + i])
                lo, hi = np.nanmin(d[:, 1:4]), np.nanmax(d[:, 1:4])
                rand = max(50.0, (hi - lo) * 0.1)
                ax_xyz.set_ylim(lo - rand, hi + rand)
                text, farbe = pol_text(*d[-1, 1:5])
                pol.set_text("%s  %s" % (n, text))
                pol.set_color(farbe)
        ax_b.set_xlim(-FENSTER_S, 0)
        ax_b.set_ylim(0, ymax)
        if auf:
            zeilen.append("\n* Aufnahme: %d Zeilen" % auf_n)
        status.set_text("\n".join(zeilen))
        info.set_text("Letzte Meldungen vom Pico:\n" + "\n".join(meldungen[-4:]))

    _anim = FuncAnimation(fig, zeichnen, interval=100, cache_frame_data=False)
    fig.canvas.mpl_connect("close_event", lambda _e: v.schliessen())
    plt.show()


# ---------------------------------------------------------------- Datei auswerten

def kontakte_berechnen(t, werte, namen):
    """Kontakt je Sensor und Messung, mit derselben Erkennung wie auf dem Pico (kontakt.py)."""
    erg = []
    for i, name in enumerate(namen):
        k = kontakt.Kontakt(name)
        an = np.zeros(len(t), bool)
        for j in range(len(t)):
            x, y, z = werte[j, 1 + 4 * i: 4 + 4 * i]
            if x == x and y == y and z == z:
                an[j] = k.neu(x, y, z, t[j] - t[j - 1] if j else 0.02)
            else:
                an[j] = an[j - 1] if j else False
        erg.append(an)
    return erg


def auswerten(pfad):
    if not os.path.exists(pfad):                  # nur der Name: im Ordner messungen suchen
        from greifer_lesen import MESS_ORDNER
        im_ordner = os.path.join(MESS_ORDNER, os.path.basename(pfad))
        if os.path.exists(im_ordner):
            pfad = os.path.normpath(im_ordner)
    with open(pfad, newline="") as f:
        zeilen = list(csv.reader(f))
    if len(zeilen) < 2:
        sys.exit("%s enthaelt keine Messwerte." % pfad)
    kopf, rumpf = zeilen[0], [z for z in zeilen[1:] if len(z) == len(zeilen[0])]
    namen = namen_aus_kopf(kopf)
    i_ms = kopf.index("ms")
    werte = np.array([[zahl(v) for v in z[i_ms:-1]] for z in rumpf])
    t = (werte[:, 0] - werte[0, 0]) / 1000.0
    dauer = t[-1] if len(t) else 0

    print("%s: %d Messungen in %.1f s (%.0f pro Sekunde)" %
          (pfad, len(t), dauer, len(t) / dauer if dauer else 0))
    # Rohwert-Modus (Taste r am Pico): Betrag weit ueber dem Nullpunkt-Bereich und alte Firmware
    # hat dann nie einen Kontakt gemeldet
    betraege = werte[:, 4::4]
    roh = all(z[-1] == "-" for z in rumpf) and np.nanmedian(betraege) > 1000
    if roh:
        print("Hinweis: Diese Aufnahme ist in ROHWERTEN (absolutes Feld, Taste r am Pico). Die Kontakte")
        print("unten sind trotzdem richtig, sie werden aus den Messwerten neu berechnet.")
    an_alle = kontakte_berechnen(t, werte, namen)
    print("%-4s %10s %10s %8s %12s  %s" % ("", "Rauschen", "Maximum", "Kontakte", "Kontaktzeit", "staerkste Achse beim Maximum"))
    for i, n in enumerate(namen):
        x, y, z, b = (werte[:, 1 + 4 * i + k] for k in range(4))
        an = an_alle[i]
        # Rauschen aus den Spruengen von Messung zu Messung ausserhalb der Kontakte,
        # robust geschaetzt (MAD), damit langsames Heranfuehren des Magneten nicht mitzaehlt
        sprung = np.diff(b)[~an[1:] & ~an[:-1]]
        sprung = sprung[sprung == sprung]
        rauschen = (1.4826 * np.median(np.abs(sprung - np.median(sprung))) / np.sqrt(2)
                    if len(sprung) > 10 else float("nan"))
        kontakte = int(np.sum(an[1:] & ~an[:-1]) + (an[0] if len(an) else 0))
        kontaktzeit = float(np.sum(np.diff(t)[an[1:]])) if len(t) > 1 else 0.0
        j = int(np.nanargmax(b)) if np.any(b == b) else 0
        achse, wert = max((("x", x[j]), ("y", y[j]), ("z", z[j])), key=lambda e: abs(e[1]))
        print("%-4s %7.1f uT %7.0f uT %8d %10.1f s  %s %+.0f uT" %
              (n, rauschen, np.nanmax(b),
               kontakte, kontaktzeit, achse, wert))
    print("Rauschen = Zittern von |B| von Messung zu Messung ausserhalb der Kontakte.")
    print("Kontakte = mit pico/kontakt.py aus den Messwerten berechnet (wie der Pico).")

    fig, achsen = plt.subplots(1 + len(namen), 1, sharex=True, figsize=(12, 2.2 + 2 * len(namen)),
                               num="Auswertung " + pfad)
    ax_b = achsen[0]
    for i, n in enumerate(namen):
        ax_b.plot(t, werte[:, 4 + 4 * i], color=FARBEN.get(n), lw=1, label=n)
        ax = achsen[1 + i]
        for k, (farbe, achse) in enumerate((("tab:red", "x"), ("tab:green", "y"), ("tab:blue", "z"))):
            ax.plot(t, werte[:, 1 + 4 * i + k], color=farbe, lw=0.8, label=achse)
        ax.fill_between(t, 0, 1, where=an_alle[i], color="tab:green", alpha=0.18, lw=0,
                        transform=ax.get_xaxis_transform(), label="Kontakt")
        ax.set_ylabel("%s (uT)" % n)
        ax.legend(loc="upper right", ncol=4, fontsize=8)
        ax.grid(alpha=0.3)
    ax_b.set_ylabel("|B| absolut (uT)" if roh else "|B| (uT)")
    ax_b.legend(loc="upper right", ncol=4, fontsize=8)
    ax_b.grid(alpha=0.3)
    ax_b.set_title(pfad + ("   [ROHWERTE]" if roh else ""))
    achsen[-1].set_xlabel("Zeit (s)")
    fig.tight_layout()
    plt.show()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("datei", nargs="?", help="CSV-Aufnahme auswerten statt live messen")
    ap.add_argument("--port", help="z. B. /dev/ttyACM1 (Standard: automatisch)")
    a = ap.parse_args()
    if a.datei:
        auswerten(a.datei)
    else:
        from greifer_lesen import pico_finden
        live(a.port or pico_finden())


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nBeendet.")
