# kontakt.py  -  Kontakterkennung der Fin-Ray-Lamellen (MicroPython und Python am PC)
#
# Grundlage (README 3.7): Jeder echte Druck auf eine Lamelle schiebt sie an den Parallelfedern
# als Ganzes zurueck; das Feld aendert sich deshalb immer in fast dieselbe Richtung, die
# DRUCKRICHTUNG des Sensors (Aufnahmen 16.10. und 17.10.: hoechstens 24 Grad Abweichung bei
# festem Druck, 51 bis 59 Grad bei leichter Beruehrung). Gezaehlt wird nur der Anteil in dieser
# Richtung. Das TPU kriecht nach dem Loslassen ueber viele Sekunden zurueck (Gegenrichtung).
#
#   basis      schnelle Basislinie ohne Kontakt (Zeitkonstante TAU_S). Nach dem AUS folgt sie
#              MERKEN_S lang Bewegungen gegen die Druckrichtung schnell (TAU_ZURUECK_S), damit sie
#              nach dem Zurueckkriechen gleich wieder richtig sitzt.
#   basis_l    langsame Basislinie (TAU_L_S), Bezug fuer den langsamen Druck und die Gegenprobe.
#              Kriechen nach dem Loslassen folgt sie ebenso schnell; nach dem AUS springen beide
#              Basislinien auf den aktuellen Wert.
#   EIN schnell:  Abstand zur basis ueber EIN_UT, Winkel zur Druckrichtung unter WINKEL_EIN und
#                 Anteil in Druckrichtung gegen basis_l ueber GEGENPROBE_UT. Die Gegenprobe
#                 verhindert, dass die Rueckkehr aus einer Auslenkung in Gegenrichtung als Druck gilt.
#   EIN langsam:  Anteil in Druckrichtung gegen basis_l ueber LANGSAM_UT, Winkel unter WINKEL_EIN.
#                 Erkennt Druck, der sich langsam aufbaut (Arm setzt langsam auf, Mensch drueckt
#                 langsam): 50 uT/s nach etwa 4 s, 20 uT/s nach 11 s, 10 uT/s nach 24 s.
#   im Kontakt:   Basis steht, die Spitze (Anteil in Druckrichtung) wird gemerkt. Halten bleibt Kontakt.
#   Kontakt AUS:  Anteil in Druckrichtung unter AUS_UT oder unter AUS_ANTEIL * Spitze. Loslassen
#                 unter die Basis (Kriechen) ist damit immer AUS.
#
# Nie Kontakt: Aenderungen quer oder entgegen der Druckrichtung, also Zurueckkriechen, die
# Magnetwirkung beim Oeffnen auf 87 mm (R1: 339 uT bei 81 Grad) und Armbewegungen (bis 65 uT).
# Preis: Druck aus der Gegenrichtung (Lamelle von aussen/hinten ausgelenkt) meldet keinen Kontakt.
#
# Dieselbe Datei laeuft auf dem Pico (pico/main.py) und in der PC-Auswertung
# (pc/greifer_monitor.py, pc/kontakt_vergleich.py), damit beide genau gleich entscheiden.
import math

EIN_UT = 200.0         # schneller Druck: Abstand zur schnellen Basis (uT)
LANGSAM_UT = 200.0     # langsamer Druck: Anteil in Druckrichtung gegen die langsame Basis (uT)
GEGENPROBE_UT = 100.0  # schneller Druck braucht auch gegen die langsame Basis so viel (uT)
WINKEL_EIN = 70.0      # hoechstens so weit (Grad) darf die Aenderung von der Druckrichtung abweichen
AUS_UT = 100.0         # spaetestens unter diesem Anteil in Druckrichtung ist der Kontakt vorbei (uT)
AUS_ANTEIL = 0.4       # Kontakt vorbei, wenn der Anteil unter 40 % der Spitze faellt
TAU_S = 2.0            # so schnell laeuft die schnelle Basis ohne Kontakt mit (Sekunden)
TAU_L_S = 60.0         # so schnell laeuft die langsame Basis mit (Sekunden)
MERKEN_S = 5.0         # so lange nach dem Loslassen folgen beide Basen dem Kriechen schnell
TAU_ZURUECK_S = 0.3    # so schnell folgen sie dabei (Sekunden)

# Druckrichtung je Sensor (Einheitsvektor im Sensor-Koordinatensystem x, y, z), gemittelt aus
# den Kontakten der Aufnahmen vom 16.10. (messungen/greifer_2026-10-16_*.csv), am 17.10. am Arm
# bestaetigt. NACH NEUKLEBEN ODER UMDREHEN EINES MAGNETEN NEU MESSEN: Lamelle einige Male
# zuegig druecken, aufnehmen, dann pc/kontakt_vergleich.py <datei>.csv --richtung.
DRUCKRICHTUNG = {
    "L1": (-0.592, 0.051, 0.804),
    "L2": (0.863, -0.085, 0.498),
    "R1": (0.951, -0.163, 0.262),
    "R2": (-0.668, -0.056, 0.742),
}


def _nach(b, x, y, z, a):
    return [b[0] + a * (x - b[0]), b[1] + a * (y - b[1]), b[2] + a * (z - b[2])]


class Kontakt:
    def __init__(self, name, ein_ut=EIN_UT, langsam_ut=LANGSAM_UT, gegenprobe_ut=GEGENPROBE_UT,
                 winkel_ein=WINKEL_EIN, aus_ut=AUS_UT, aus_anteil=AUS_ANTEIL, tau_s=TAU_S,
                 tau_l_s=TAU_L_S, merken_s=MERKEN_S, tau_zurueck_s=TAU_ZURUECK_S):
        if name not in DRUCKRICHTUNG:
            raise ValueError("keine Druckrichtung fuer Sensor %s (kontakt.DRUCKRICHTUNG)" % name)
        self.r = DRUCKRICHTUNG[name]
        self.ein_ut = ein_ut
        self.langsam_ut = langsam_ut
        self.gegenprobe_ut = gegenprobe_ut
        self.cos_ein = math.cos(winkel_ein * math.pi / 180.0)   # ohne math.radians (MicroPython)
        self.aus_ut = aus_ut
        self.aus_anteil = aus_anteil
        self.tau_s = tau_s
        self.tau_l_s = tau_l_s
        self.merken_s = merken_s
        self.tau_zurueck_s = tau_zurueck_s
        self.zuruecksetzen()

    def zuruecksetzen(self):
        self.basis = None
        self.basis_l = None
        self.an = False
        self.spitze = 0.0
        self.seit_aus = None      # Sekunden seit dem letzten AUS, None nach MERKEN_S
        self.abstand = 0.0        # Abstand zur schnellen Basis (uT)
        self.anteil = 0.0         # Anteil in Druckrichtung (uT)
        self.ursache = ""         # "schnell" oder "langsam" beim letzten EIN

    def neu(self, x, y, z, dt_s):
        """Neue Messung (uT) nach dt_s Sekunden. Gibt True zurueck, solange Kontakt ist."""
        if self.basis is None:
            self.basis = [x, y, z]
            self.basis_l = [x, y, z]
            return False
        rx, ry, rz = self.r
        dx, dy, dz = x - self.basis[0], y - self.basis[1], z - self.basis[2]
        d = (dx * dx + dy * dy + dz * dz) ** 0.5
        p = dx * rx + dy * ry + dz * rz
        self.abstand = d
        self.anteil = p

        if self.an:
            if p > self.spitze:
                self.spitze = p
            if p < self.aus_ut or p < self.aus_anteil * self.spitze:
                self.an = False
                self.basis = [x, y, z]
                self.basis_l = [x, y, z]
                self.seit_aus = 0.0
            return self.an

        lx, ly, lz = x - self.basis_l[0], y - self.basis_l[1], z - self.basis_l[2]
        dl = (lx * lx + ly * ly + lz * lz) ** 0.5
        pl = lx * rx + ly * ry + lz * rz
        if self.seit_aus is not None:
            self.seit_aus += dt_s
            if self.seit_aus > self.merken_s:
                self.seit_aus = None

        if d > self.ein_ut and p > self.cos_ein * d and pl > self.gegenprobe_ut:
            self.an = True
            self.spitze = p
            self.ursache = "schnell"
        elif pl > self.langsam_ut and pl > self.cos_ein * dl:
            self.basis = list(self.basis_l)      # AUS zaehlt gegen das Feld vor dem Druck
            self.an = True
            self.spitze = pl
            self.anteil = pl
            self.ursache = "langsam"
        else:
            kriechen = self.seit_aus is not None
            a = self.tau_zurueck_s if (kriechen and p < 0) else self.tau_s
            self.basis = _nach(self.basis, x, y, z, min(dt_s / a, 1.0))
            a = self.tau_zurueck_s if (kriechen and pl < 0) else self.tau_l_s
            self.basis_l = _nach(self.basis_l, x, y, z, min(dt_s / a, 1.0))
        return self.an
