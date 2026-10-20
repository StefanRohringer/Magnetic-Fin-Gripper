# Magnetic-Fin-Gripper: twin Fin-Ray fingers with magnetic touch sensing

![Gripper closing on a grape until all four lamellae report contact, then the W2c fingernail picking an 0603 SMD part](bilder/greifer.gif)

Gripper fingers for the Seeed reBot DevArm B601-DM. They mount on the stock gripper jaws (Seeed hole pattern). Each finger carries two soft TPU Fin-Ray lamellae. Every lamella holds a small magnet, and behind it sits a magnetometer (Adafruit MLX90393). When something presses on a lamella, the magnet moves, the sensor sees the field change, and the PC reports "contact".

```
PC ──USB── Pico (RP2040) ──I2C── hub ──┬── L1  left finger, lamella 1
                                       ├── L2  left finger, lamella 2
                                       ├── R1  right finger, lamella 1
                                       └── R2  right finger, lamella 2
```

The full guide is in German: **[README.de.md](README.de.md)** (wiring, soldering, magnets, software, testing, printing, assembly).

## What's in here

| Path | What |
|---|---|
| `druck/Basis_V1.8.1_PLA.stl` | Finger base V1.8.1, PLA, print 2× |
| `druck/Lamellen_V1.6N_TPU_2Stueck.stl` | Twin Fin-Ray lamellae V1.6-N, TPU 95A, 2 per plate, print 2× |
| `druck/W2c_*.stl`, `druck/ANLEITUNG_W2c.md` | Variant W2c: the same lamella with a PLA fingernail for very small parts (0603/0402 SMD) |
| `zeichnungen/Massblatt_V1.8.1.pdf` | Dimensioned drawing of the base V1.8.1 (also as PNG) |
| `zeichnungen/Massblatt_Lamelle_V1.6N.pdf` | Dimensioned drawing of the Fin-Ray lamella V1.6-N (also as PNG) |
| `zeichnungen/Massblatt_W2c_Fingernagel.pdf` | Drawing of the W2c fingernail and its fit on the lamellae (also as PNG) |
| `ansicht/greifer_3d.html` | Interactive 3D view (open in a browser, needs internet for three.js): demo button, live sensor readout per lamella, gripper width, gaps, Fin-Ray or W2c, grape or SMD part |
| `ANSCHLUSSPLAN.html`, `anschlussplan.svg` | Wiring diagram |
| `zeichnungen/Loetbruecken_A0_A1.png` | Where to solder the address jumpers A0/A1 |
| `pico/` | MicroPython firmware for the Raspberry Pi Pico: reads the four sensors and detects contact |
| `pc/` | PC tools: live monitor with plots, CSV recording, flashing the Pico |

## Quick start

1. Print 2 bases (PLA) and 2 lamella plates (TPU), glue a 4 × 2 mm N35 magnet into each lamella, all the same way round.
2. Set the I2C address jumpers on the four MLX90393 boards (none / A0 / A1 / A0+A1 → 0x18 to 0x1B).
3. Wire Pico → I2C hub → sensors (3V3 on pin 36, GND pin 38, SDA GP4 pin 6, SCL GP5 pin 7), then plug in USB.
4. On Linux you need `python3-venv` and `python3-tk` (`sudo apt install python3-venv python3-tk`) and your user in the `dialout` group.
5. Flash MicroPython onto the Pico, then run `pc/pico_aufspielen.sh`.
6. Run `pc/monitor.sh` for the live view. The scripts create their own Python venv on first start (Linux).

## Developer

Stefan Rohringer

## License

Copyright © 2026 Stefan Rohringer

- Hardware (STL files, drawings, build instructions): **CERN-OHL-S-2.0**, see [`LICENSE-HARDWARE`](LICENSE-HARDWARE).
- Software (`pc/`, `pico/`): **GPL-3.0**, see [`LICENSE`](LICENSE).

Each source file carries a short copyright and SPDX license header. Both licenses are strongly reciprocal: if you distribute a modified version, you must publish its source under the same license.
