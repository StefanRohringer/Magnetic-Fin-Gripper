#!/usr/bin/env python3
# Magnetic-Fin-Gripper  Copyright (C) 2026  Stefan Rohringer
# SPDX-License-Identifier: GPL-3.0-or-later
# This program comes with ABSOLUTELY NO WARRANTY. It is free software, and you are welcome
# to redistribute it under the terms of the GNU GPL, version 3 or later (see LICENSE).

"""Kontakterkennung alt gegen neu an Aufnahmen vergleichen, Druckrichtung messen.

Aufruf (in der venv, z. B. .venv/bin/python pc/kontakt_vergleich.py ...):
  pc/kontakt_vergleich.py messungen/*.csv                 alt (git main) gegen pico/kontakt.py
  pc/kontakt_vergleich.py --alt <rev> datei.csv           anderer Vergleichsstand (git-Revision)
  pc/kontakt_vergleich.py --rampe datei.csv               zusaetzlich kuenstlicher langsamer Druck
  pc/kontakt_vergleich.py --richtung datei.csv            Druckrichtung je Sensor messen (nach
                                                          Neukleben/Umdrehen eines Magneten)

Je Sensor: Zahl der Kontakte, Kontaktzeit, ob am Ende noch Kontakt ist (haengt), Verzug des EIN
(neu minus alt, nur fuer Kontakte, die beide finden), Kontakte nur alt oder nur neu mit Uhrzeit.
CSV-Format wie von pc/start.sh und pc/monitor.sh (README 3.6).
"""
import argparse
import csv
import datetime
import os
import subprocess
import sys
import types

import numpy as np

PROJEKT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(PROJEKT, "pico"))
import kontakt as NEU  # noqa: E402


def alt_laden(rev):
    quelle = subprocess.run(["git", "-C", PROJEKT, "show", rev + ":pico/kontakt.py"],
                            check=True, capture_output=True, text=True).stdout
    m = types.ModuleType("kontakt_alt")
    exec(compile(quelle, "kontakt_alt.py", "exec"), m.__dict__)
    return m


def erkenner(modul, name):
    if hasattr(modul, "DRUCKRICHTUNG"):
        return modul.Kontakt(name)
    return modul.Kontakt()         # alte Fassung ohne Druckrichtung und Sensorname


def lade(pfad):
    with open(pfad, newline="") as f:
        zeilen = list(csv.reader(f))
    kopf = zeilen[0]
    rumpf = [z for z in zeilen[1:] if len(z) == len(kopf)]
    i = kopf.index("ms")
    namen = [k[:-1] for k in kopf[i + 1:-1:4]]

    def zahl(s):
        try:
            return float(s)
        except ValueError:
            return float("nan")
    w = np.array([[zahl(v) for v in z[:-1]] for z in rumpf])
    t = (w[:, i] - w[0, i]) / 1000.0
    pc = w[:, 0] if kopf[0] == "pc_zeit" else None
    xyz = {n: w[:, i + 1 + 4 * k: i + 4 + 4 * k] for k, n in enumerate(namen)}
    return t, pc, namen, xyz


def lauf(k, t, xyz):
    an = np.zeros(len(t), bool)
    for j in range(len(t)):
        x, y, z = xyz[j]
        if x == x and y == y and z == z:
            an[j] = k.neu(x, y, z, t[j] - t[j - 1] if j else 0.02)
        else:
            an[j] = an[j - 1] if j else False
    return an


def stuecke(an):
    i = np.flatnonzero(np.diff(np.r_[0, an.astype(int), 0]))
    return list(zip(i[::2], i[1::2]))


def uhr(pc, t, j):
    if pc is None:
        return "%.1f s" % t[j]
    return datetime.datetime.fromtimestamp(pc[j]).strftime("%H:%M:%S")


def vergleichen(pfad, alt):
    t, pc, namen, xyz = lade(pfad)
    dt = float(np.median(np.diff(t))) if len(t) > 1 else 0.02
    print("== %s (%.0f s)" % (os.path.basename(pfad), t[-1] if len(t) else 0))
    print("     %-28s | %-28s | EIN-Verzug neu-alt" % ("alt: Kontakte, Zeit", "neu: Kontakte, Zeit"))
    for n in namen:
        a = lauf(erkenner(alt, n), t, xyz[n])
        b = lauf(erkenner(NEU, n), t, xyz[n])
        sa, sb = stuecke(a), stuecke(b)
        nah = int(0.5 / dt)
        verzug = []
        nur_alt = []
        for i0, i1 in sa:
            treffer = [j0 for j0, j1 in sb if j0 < i1 + nah and j1 > i0]
            if treffer:
                verzug.append(t[treffer[0]] - t[i0])
            else:
                nur_alt.append("%s (%.1f s)" % (uhr(pc, t, i0), t[i1 - 1] - t[i0]))
        nur_neu = ["%s (%.1f s)" % (uhr(pc, t, j0), t[j1 - 1] - t[j0])
                   for j0, j1 in sb if not any(i0 < j1 + nah and i1 > j0 for i0, i1 in sa)]
        print("  %s  %3d  %7.1f s %-9s | %3d  %7.1f s %-9s | %s" % (
            n, len(sa), a.sum() * dt, "HAENGT" if a[-1] else "", len(sb), b.sum() * dt,
            "HAENGT" if b[-1] else "",
            "max %+.2f s, Median %+.2f s" % (max(verzug), np.median(verzug)) if verzug else "-"))
        if nur_alt:
            print("        nur alt: " + ", ".join(nur_alt))
        if nur_neu:
            print("        nur neu: " + ", ".join(nur_neu))
    return t, namen, xyz


def rampe(t, namen, xyz, alt):
    """Kuenstlicher Druck in Druckrichtung auf die ersten 200 s der Aufnahme (sollte ruhig sein):
    Rampe bis 600 uT, 5 s halten, Loslassen auf 35 % mit Zurueckkriechen (20 s)."""
    print("-- kuenstlicher Druck: Rampe auf 600 uT ab 20 s, 5 s halten, loslassen")
    print("     uT/s | alt: EIN nach / danach   | neu: EIN nach / danach")
    m = t < t[0] + 200
    for n in namen:
        r = np.array(NEU.DRUCKRICHTUNG[n])
        for rate in (5, 10, 20, 50, 100, 300, 3000):
            tt = t[m] - t[0]
            s0, s1 = 20.0, 20.0 + 600.0 / rate
            s2 = s1 + 5
            if s2 + 10 > tt[-1]:
                continue
            h = np.where(tt < s0, 0, np.where(tt < s1, rate * (tt - s0), 600.0))
            h = np.where(tt >= s2, 210.0 * np.exp(-(tt - s2) / 20.0), h)
            v = xyz[n][m] + h[:, None] * r[None, :]
            zeile = "  %s %5d |" % (n, rate)
            for modul in (alt, NEU):
                an = lauf(erkenner(modul, n), tt, v)
                ein = tt[np.argmax(an)] - s0 if an.any() else None
                txt = ("%5.1f s bei %3.0f uT" % (ein, h[np.argmax(an)]) if ein is not None else "nie")
                txt += " / " + ("HAENGT" if an[tt > s2 + 0.5].any() else "aus")
                zeile += " %-24s |" % txt
            print(zeile)


def richtung(pfad):
    """Mittlere Druckrichtung je Sensor aus den Kontakten (Spitze ueber 300 uT) der alten,
    richtungsfreien Erkennung (git main), weil die neue die Richtung schon voraussetzt."""
    alt = alt_laden("737eb0a")    # letzte Fassung ohne Druckrichtung (16.10.)
    t, pc, namen, xyz = lade(pfad)
    for n in namen:
        k = alt.Kontakt()
        vek = []
        for j in range(len(t)):
            x, y, z = xyz[n][j]
            if x != x:
                continue
            vor = k.an
            an = k.neu(x, y, z, t[j] - t[j - 1] if j else 0.02)
            if vor and not an and k.spitze > 300:
                vek.append(k.richtung)
        if not vek:
            print("  %s: kein Kontakt" % n)
            continue
        u = np.array(vek)
        mitte = u.mean(axis=0)
        mitte /= np.linalg.norm(mitte)
        winkel = np.degrees(np.arccos(np.clip(u @ mitte, -1, 1)))
        print('  "%s": (%.3f, %.3f, %.3f),   # %d Kontakte, hoechstens %.0f Grad daneben' % (
            n, mitte[0], mitte[1], mitte[2], len(u), winkel.max()))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("dateien", nargs="+")
    ap.add_argument("--alt", default="main", help="git-Revision der alten kontakt.py (Standard main)")
    ap.add_argument("--rampe", action="store_true", help="kuenstlichen langsamen Druck pruefen")
    ap.add_argument("--richtung", action="store_true", help="Druckrichtung je Sensor messen")
    a = ap.parse_args()
    if a.richtung:
        for p in a.dateien:
            print("== " + p)
            richtung(p)
        return
    alt = alt_laden(a.alt)
    for p in a.dateien:
        t, namen, xyz = vergleichen(p, alt)
        if a.rampe:
            rampe(t, namen, xyz, alt)


if __name__ == "__main__":
    main()
