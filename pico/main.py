# Magnetic-Fin-Gripper  Copyright (C) 2026  Stefan Rohringer
# SPDX-License-Identifier: GPL-3.0-or-later
# This program comes with ABSOLUTELY NO WARRANTY. It is free software, and you are welcome
# to redistribute it under the terms of the GNU GPL, version 3 or later (see LICENSE).

# main.py  -  Zwillings-Fin-Ray, Sensorauslesung (MicroPython, Raspberry Pi Pico / RP2040)
#
# Liest bis zu vier Adafruit MLX90393 (#4022) am I2C-Bus GP4 (SDA) / GP5 (SCL)
# und schickt die Werte ueber USB als Textzeilen.
# Braucht kontakt.py auf dem Pico. Aufspielen (beide Dateien): pc/pico_aufspielen.sh
#
# Ausgabe (eine Zeile pro Messung):
#   D,<ms>,<s1_dx>,<s1_dy>,<s1_dz>,<s1_betrag>, ... ,<kontakte>
#   Werte in Mikrotesla (uT), als Abweichung vom Nullpunkt (Finger unbelastet).
#   <kontakte> = Namen der Sensoren mit Kontakt, z. B. "L1 R1", sonst "-".
#   Kontakt wird an der schnellen Aenderung erkannt (kontakt.py), nicht am Abstand zum
#   Nullpunkt; Kriechen des TPU nach dem Loslassen zaehlt deshalb nicht als Kontakt.
# Zeilen mit "#" sind Hinweise, "K," ist die Kopfzeile.
#
# Tasten (in Thonny unten in die Kommandozeile tippen, dann Enter):
#   n  Nullpunkt neu nehmen (Finger dabei NICHT beruehren)
#   r  umschalten: Abweichung <-> Rohwerte (absolutes Feld; Kontakterkennung laeuft weiter)
#   a  immer auf Abweichung schalten (schicken die PC-Programme beim Start)
#   s  umschalten: langsame Ausgabe (5/s, zum Mitlesen) <-> schnell (~50/s mit vier Sensoren)
#   f  immer schnell, l  immer langsam (fuer Programme, die den Zustand nicht kennen)
#   k  Kopfzeile noch einmal senden (kommt auch nach jedem "n")
#   v  Firmware-Version melden: "# firmware <FIRMWARE>"
#
# Schnittstelle fuer andere Programme (z. B. pc/greifer_lesen.py): Zeilen "K,", "D,",
# "#" wie oben, Befehle als einzelne Zeichen. FIRMWARE steigt, wenn sich daran etwas aendert.
FIRMWARE = 2

from machine import I2C, Pin
import time, sys, select
import kontakt

# ---------- Einstellungen ----------
SDA_PIN = 4            # GP4 = Pin 6
SCL_PIN = 5            # GP5 = Pin 7
I2C_TAKT = 100_000     # 100 kHz, robust bei 20-50 cm Kabel ueber den Hub

# Name je Loetbruecken-Stellung (Index = A1 A0: 0 keine, 1 A0, 2 A1, 3 beide).
# L = linker Finger, R = rechter Finger, 1/2 = Lamelle
NAMEN = ("L1", "L2", "R1", "R2")
# Grundadresse haengt von der Chipvariante ab (MLX90393-011: 0x0C ... -014: 0x18).
# Adafruit 4022 kommt mit 0x0C oder 0x18; die Loetbruecken zaehlen 0 bis 3 dazu.
BASIS = (0x0C, 0x10, 0x14, 0x18)
SENSOREN = {}          # Adresse -> Name, wird beim Start aus dem I2C-Scan gefuellt

GAIN_SEL = 7           # kleinste Verstaerkung (Magnet liefert ca. 17 mT am Chip, V1.7)
RES = 2                # Aufloesung 2: XY 0,601 uT/Bit, Z 0,968 uT/Bit, Bereich ca. +-19 mT (XY)
DIG_FILT = 5           # Digitalfilter
OSR = 0                # Ueberabtastung
# Kontaktschwellen und Zeitkonstanten stehen in kontakt.py
NULL_PROBEN = 50       # Messungen fuer den Nullpunkt

# Empfindlichkeit in uT pro Bit bei GAIN_SEL 7 und HALLCONF 0xC (Datenblatt MLX90393)
LSB_XY = (0.150, 0.300, 0.601, 1.202)[RES]
LSB_Z = (0.242, 0.484, 0.968, 1.936)[RES]
# Rohwert-Grenze, ab der der Sensor in die Saettigung laeuft
GRENZE = 31000 if RES >= 2 else 32000

# Wandlungszeit fuer X, Y, Z (Datenblatt: 67 + 64 * 2^OSR * (2 + 2^DIG_FILT) us pro Achse)
WARTE_MS = int(3 * (67 + 64 * (1 << OSR) * (2 + (1 << DIG_FILT))) / 1000) + 2

# ---------- MLX90393-Befehle ----------
CMD_SM = 0x3E   # Einzelmessung X, Y, Z
CMD_RM = 0x4E   # Messwerte X, Y, Z lesen
CMD_RR = 0x50   # Register lesen
CMD_WR = 0x60   # Register schreiben
CMD_EX = 0x80   # Modus verlassen
CMD_RT = 0xF0   # Reset
STATUS_FEHLER = 0x10

i2c = I2C(0, sda=Pin(SDA_PIN), scl=Pin(SCL_PIN), freq=I2C_TAKT)


def befehl(adr, daten, n_antwort=1):
    i2c.writeto(adr, bytes(daten))
    return i2c.readfrom(adr, n_antwort)


def reg_lesen(adr, reg):
    r = befehl(adr, [CMD_RR, reg << 2], 3)
    return (r[1] << 8) | r[2]


def reg_schreiben(adr, reg, wert):
    r = befehl(adr, [CMD_WR, (wert >> 8) & 0xFF, wert & 0xFF, reg << 2])
    if r[0] & STATUS_FEHLER:
        raise OSError("Register %d nicht geschrieben" % reg)


def einrichten(adr):
    befehl(adr, [CMD_EX])
    time.sleep_ms(2)
    try:
        befehl(adr, [CMD_RT])
    except OSError:
        pass                      # direkt nach dem Reset antwortet der Chip manchmal nicht
    time.sleep_ms(10)
    r0 = reg_lesen(adr, 0)
    r0 = (r0 & ~0x0070) | (GAIN_SEL << 4)
    reg_schreiben(adr, 0, r0)
    r2 = reg_lesen(adr, 2)
    r2 &= ~0x07FF                 # RES_Z, RES_Y, RES_X, DIG_FILT, OSR
    r2 |= (RES << 9) | (RES << 7) | (RES << 5) | (DIG_FILT << 2) | OSR
    reg_schreiben(adr, 2, r2)
    if reg_lesen(adr, 2) & 0x07FF != r2 & 0x07FF:
        raise OSError("Einstellung nicht uebernommen")


def roh_umrechnen(hi, lo):
    v = (hi << 8) | lo
    if RES == 2:
        return v - 32768
    if RES == 3:
        return v - 16384
    return v - 65536 if v >= 32768 else v


def starten(adr):
    r = befehl(adr, [CMD_SM])
    if r[0] & STATUS_FEHLER:
        raise OSError("Start abgelehnt")


def lesen(adr):
    r = befehl(adr, [CMD_RM], 7)
    if r[0] & STATUS_FEHLER:
        raise OSError("Statusfehler")
    x = roh_umrechnen(r[1], r[2])
    y = roh_umrechnen(r[3], r[4])
    z = roh_umrechnen(r[5], r[6])
    satt = abs(x) > GRENZE or abs(y) > GRENZE or abs(z) > GRENZE
    return x * LSB_XY, y * LSB_XY, z * LSB_Z, satt


def runde(aktive):
    """Startet alle Sensoren gleichzeitig und liest sie danach. Gibt {adr: werte|None}."""
    for adr in aktive:
        try:
            starten(adr)
        except OSError:
            pass
    time.sleep_ms(WARTE_MS)
    erg = {}
    for adr in aktive:
        try:
            erg[adr] = lesen(adr)
        except OSError:
            erg[adr] = None
    return erg


def nullpunkt(aktive):
    print("# Nullpunkt: Finger nicht beruehren ...")
    summe = {a: [0.0, 0.0, 0.0] for a in aktive}
    anzahl = {a: 0 for a in aktive}
    for _ in range(NULL_PROBEN):
        for adr, w in runde(aktive).items():
            if w:
                for i in range(3):
                    summe[adr][i] += w[i]
                anzahl[adr] += 1
    null = {}
    for adr in aktive:
        n = max(anzahl[adr], 1)
        null[adr] = [s / n for s in summe[adr]]
        x, y, z = null[adr]
        print("# %s Ruhefeld: x %.0f  y %.0f  z %.0f uT  (Betrag %.1f mT)"
              % (SENSOREN[adr], x, y, z, (x * x + y * y + z * z) ** 0.5 / 1000))
    return null


def main():
    print("# rebot Greifer-Sensorik")
    print("# firmware %d" % FIRMWARE)
    gefunden = i2c.scan()
    print("# I2C gefunden:", " ".join("0x%02X" % a for a in gefunden) or "nichts")
    for adr in gefunden:
        if adr & ~0x03 not in BASIS:
            continue
        name = NAMEN[adr & 0x03]
        if name in SENSOREN.values():
            print("# DOPPELT: %s auf 0x%02X und 0x%02X - Loetbruecken pruefen"
                  % (name, [a for a, n in SENSOREN.items() if n == name][0], adr))
            continue
        SENSOREN[adr] = name
    for i, name in enumerate(NAMEN):
        if name not in SENSOREN.values():
            print("# FEHLT: %s (Loetbruecke %s) - Kabel und Loetbruecke pruefen"
                  % (name, ("keine", "A0", "A1", "A0+A1")[i]))
    aktive = []
    for adr, name in sorted(SENSOREN.items(), key=lambda e: NAMEN.index(e[1])):
        try:
            einrichten(adr)
            aktive.append(adr)
            print("# OK: %s (0x%02X)" % (name, adr))
        except OSError as e:
            print("# FEHLER beim Einrichten %s: %s" % (name, e))
    if not aktive:
        print("# Kein Sensor bereit. Ende.")
        return

    null = nullpunkt(aktive)
    roh = False
    langsam = True
    letzte_ausgabe = 0
    kopf = ["K", "ms"]
    for adr in aktive:
        n = SENSOREN[adr]
        kopf += [n + "x", n + "y", n + "z", n + "b"]
    kopf.append("kontakt")
    print(",".join(kopf))

    p = select.poll()
    p.register(sys.stdin, select.POLLIN)
    fehler = {a: 0 for a in aktive}
    erkenner = {a: kontakt.Kontakt(SENSOREN[a]) for a in aktive}
    vorher = time.ticks_ms()

    while True:
        if p.poll(0):
            c = sys.stdin.read(1)
            if c == "n":
                null = nullpunkt(aktive)
                for e in erkenner.values():
                    e.zuruecksetzen()
                print(",".join(kopf))     # fuer pc/greifer_lesen.py, das spaeter dazukommt
            elif c == "a":
                roh = False
                print("# Ausgabe: Abweichung")
            elif c == "k":
                print(",".join(kopf))
            elif c == "r":
                roh = not roh
                print("# Ausgabe:", "Rohwerte" if roh else "Abweichung")
            elif c in "sfl":
                langsam = (not langsam) if c == "s" else (c == "l")
                print("# Ausgabe:", "langsam" if langsam else "schnell")
            elif c == "v":
                print("# firmware %d" % FIRMWARE)

        werte = runde(aktive)
        jetzt = time.ticks_ms()
        dt_s = time.ticks_diff(jetzt, vorher) / 1000
        vorher = jetzt
        teile = ["D", str(jetzt)]
        kontakte = []
        for adr in aktive:
            w = werte[adr]
            if w is None:
                fehler[adr] += 1
                teile += ["", "", "", ""]
                if fehler[adr] in (10, 100, 1000):
                    print("# %s liefert nicht (%d Fehler)" % (SENSOREN[adr], fehler[adr]))
                    try:
                        einrichten(adr)
                    except OSError:
                        pass
                continue
            x, y, z, satt = w
            if erkenner[adr].neu(x, y, z, dt_s):     # absolutes Feld, unabhaengig vom Nullpunkt
                kontakte.append(SENSOREN[adr])
            if not roh:
                x -= null[adr][0]
                y -= null[adr][1]
                z -= null[adr][2]
            b = (x * x + y * y + z * z) ** 0.5
            if satt:
                kontakte.append(SENSOREN[adr] + "!SAETTIGUNG")
            teile += ["%.0f" % x, "%.0f" % y, "%.0f" % z, "%.0f" % b]
        teile.append(" ".join(kontakte) or "-")
        if not langsam or time.ticks_diff(jetzt, letzte_ausgabe) >= 200:
            print(",".join(teile))
            letzte_ausgabe = jetzt


main()
