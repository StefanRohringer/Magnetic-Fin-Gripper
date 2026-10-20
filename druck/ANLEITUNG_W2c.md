# W2c Fin-Ray mit PLA-Fingernagel: alles für Druck, Bau und Test

Stand 19.10.2026. Probe für sehr kleine Elektronikteile (0603, 0402). Der Finger bleibt die TPU-Lamelle V1.6-N (Basis V1.8.1): Sie kommt direkt in die Basis, mit den Querschrauben, dem Magneten, den Federn und dem Anschlag wie heute. Neu ist nur oben ein Zapfen, auf dem ein PLA-Fingernagel steckt. Basis, Platinen, Sensoren und Kabel bleiben.

## 1. Was im Paket ist

| Datei | Wofür |
|---|---|
| `W2c_Lamelle_TPU_2Stueck.stl` | 2 TPU-Lamellen je Druck, **2 × drucken** (4 Lamellen) |
| `W2c_Nagel_PLA_2Stueck.stl` | 2 PLA-Nägel (einer je Basis), 1 × drucken |
| `ANLEITUNG_W2c.md` | diese Anleitung |

## 2. Drucken

**TPU, Lamellen**: genau wie die Lamellen V1.6-N (README.de.md, 8.1)
- TPU 95A, externe Spule, vorher trocknen
- Profil „0.20mm Standard @BBL P2S“, Filament „Generic TPU“, 4 Wandlinien, 100 % Füllung, keine Stützen
- Teile liegen richtig; nicht drehen

**PLA, Nägel** (zusammen etwa 3 g)
- PLA+, Schichthöhe 0,12 mm, 4 Wandlinien, 100 % Füllung, keine Stützen, Brim 3 mm, glatte Druckplatte
- Die Nägel liegen mit der Greiffläche auf dem Bett; nicht drehen
- Brim vorsichtig entfernen, die Spitze nicht abbrechen, die Greiffläche nicht schleifen

## 3. Was du sonst brauchst

- 4 Magnete 4 × 2 mm N35 und Sekundenkleber (für die neuen Lamellen)
- 2 Stücke PLA-Filament 1,75 mm, je etwa 25 mm lang (der Stift)
- Fühlerlehre 0,1 bis 1 mm für den Test
- keine neuen Schrauben

## 4. Zusammenbau

1. **Magnete:** markieren und gleich herum einkleben wie bei V1.6-N (README.de.md, 5.2 und 8.2), markierte Seite nach außen.
2. **Lamellen einsetzen:** alte Lamellen raus (je Basis 2 Querschrauben), neue rein, Querschrauben wieder rein. Genau wie heute.
3. **Nagel aufstecken:** Der Nagel einer Basis wird von oben auf die Zapfen beider Lamellen geschoben, bis er auf der Schulter aufsitzt.
4. **Stift:** das Filamentstück quer durch Nagel und beide Zapfen stecken. Im TPU klemmt es, im PLA hat es Luft. Enden bündig abschneiden.
5. Andere Seite genauso.

Zurück auf die normalen Fin-Ray-Lamellen: Stift raus, Nagel ab, Lamellen tauschen.

## 5. Test am Tisch

1. Pico einstecken, `pc/monitor.sh` starten, Greifer beim Start nicht berühren (Nullpunkt).
2. **Tastsinn:** jeden Nagel leicht drücken. Beide Sensoren dieser Seite schlagen aus (L1 und L2 links, R1 und R2 rechts) und gehen beim Loslassen auf etwa 0 zurück. Keine Meldung `SAETTIGUNG`.
3. **Spalt ganz zu:** Greifer ganz zu. Mit der Fühlerlehre an den Spitzen messen. Soll: **0,3 mm**, die Spitzen dürfen sich nicht berühren.
4. **Greifen:** ein 0603 und ein 0402 von Hand greifen lassen, anheben, ablegen. Notieren: gegriffen? gerutscht? beim Öffnen hängen geblieben?
5. **Wackeln:** den Nagel mit dem Finger seitlich anstupsen. Wie weit gibt die Spitze nach (ungefähr)?
