# FIX-Gateway

**Status:** Open Source — Experimental Amateur-Built Category  
**License:** GPL v2  
**Language:** Python 3  
**Snap:** `fixgateway` on snapcraft.io

[![Coverage](https://raw.githubusercontent.com/makerplane/FIX-Gateway/python-coverage-comment-action-data/badge.svg)](https://htmlpreview.github.io/?https://github.com/makerplane/FIX-Gateway/blob/python-coverage-comment-action-data/htmlcov/index.html)
[![snapcraft.io](https://snapcraft.io/fixgateway/badge.svg)](https://snapcraft.io/fixgateway)
[![Snapcraft Version](https://img.shields.io/snapcraft/v/fixgateway/latest/candidate?label=candidate&color=d5d90d)](https://snapcraft.io/fixgateway)
[![Snapcraft Version](https://img.shields.io/snapcraft/v/fixgateway/latest/beta?label=beta&color=d9870d)](https://snapcraft.io/fixgateway)
[![Snapcraft Version](https://img.shields.io/snapcraft/v/fixgateway/latest/edge?label=edge&color=d90d0d)](https://snapcraft.io/fixgateway)


---

## What This Is

FIX-Gateway is the **central avionics data broker** for the MakerPlane and MAOS avionics ecosystem. It is a Python daemon that maintains a real-time database of named flight parameters and routes data between heterogeneous sources and consumers via a plugin architecture.

Think of it as an avionics middleware bus: any sensor, protocol, or simulator can publish data to one standard parameter namespace, and any display or system can subscribe without knowing where the data came from.

## Architecture

```
[CAN-FIX bus] ─────────────────────────────────┐
[GPS / gpsd] ───────────────────────────────────┤
[Stratux ADS-B] ────────────────────────────────┤
[MAVLink autopilot / MAOS-FCS] ─────────────────┤
[X-Plane / FlightGear simulator] ───────────────┤→ [FIX-Gateway database] ─→ [pyEfis EFIS display]
[RPi IMU (BNO055)] ─────────────────────────────┤                          ─→ [pyAvMap moving map]
[RPi barometer (BMP085)] ───────────────────────┤                          ─→ [NetFIX network clients]
[MGL / Dynon / GrandRapids EGS serial] ─────────┤                          ─→ [CAN-FIX output nodes]
[Compute plugin (derived values)] ──────────────┘
```

## Parameter Database

The central database maps named keys to typed, bounded, toleranced values. Key domains include:

| Domain | Example Keys |
|---|---|
| Navigation | `LAT`, `LONG`, `ALT`, `IAS`, `TAS`, `GS`, `HEAD`, `TRACK`, `XTE` |
| AHRS | `PITCH`, `ROLL`, `YAW`, `ALAT`, `ALONG`, `ANORM` |
| Engine | `RPM1`, `MAP1`, `EGT11`–`EGT16`, `CHT11`–`CHT16`, `OILP1`, `OILT1`, `FFLOW1` |
| Control surfaces | `CTLPTCH`, `CTLROLL`, `CTLYAW`, `CTLFLAP`, `CTLATP`, `CTLCOLL` |
| Electrical | `VOLT1`, `CURR1`, `ALT1` |
| COM/NAV radios | `COM1ACT`, `COM1SBY`, `NAV1ACT`, `NAV1SBY` |
| Trims | `PITCHTRIM`, `ROLLTRIM`, `YAWTRIM` |
| Autopilot | `APENG`, `APALT`, `APHDG`, `APSPD` |

Each key has defined type, min/max bounds, units, and a **tolerance (stale data) timer** — if a key is not updated within its tol window it is marked stale, which pyEfis can display as a failure flag.

## Plugin Ecosystem

Input/output plugins currently available:

| Plugin | Description |
|---|---|
| `canfix` | CAN-FIX bus via SocketCAN or MCP2515 |
| `gpsd` | GPS position and ground track from gpsd |
| `stratux` | ADS-B traffic and GPS from Stratux receiver |
| `mavlink` | MAVLink autopilot/FCS data (compatible with MAOS-FCS) |
| `netfix` | TCP/IP network interface for distributed avionics |
| `xplane` | X-Plane 11/12 flight simulator |
| `fgfs` | FlightGear flight simulator |
| `dynon` | Dynon serial protocol |
| `mgl` / `mgl_serial` | MGL Avionics serial protocol |
| `grand_rapids_eis` | Grand Rapids Technologies EIS serial |
| `megasquirt` | MegaSquirt ECU data |
| `rpi_bno055` | Raspberry Pi IMU (attitude) |
| `rpi_bmp085` | Raspberry Pi barometric sensor |
| `rpi_mcp3008` | Raspberry Pi 8-channel SPI ADC |
| `rpi_rotary_encoder` | Rotary encoder inputs (altimeter, heading bugs) |
| `rpi_button` | GPIO button inputs |
| `compute` | Derived value computation (e.g., density altitude, TAS from IAS/OAT/ALT) |
| `data_recorder` | Log all parameters to file |
| `data_playback` | Replay recorded flight data |
| `quorum` | Multi-source data arbitration / voting |
| `annunciate` | Generate warning/caution/advisory annunciations from parameter limits |
| `demo` | Simulated flight data for display testing |

## Installation

```bash
git clone https://github.com/makerplane/FIX-Gateway.git fixgw
cd fixgw
make venv
source venv/bin/activate
make init
```

Run the server:
```bash
./fixGw.py
```

Run the debug client:
```bash
./fixGwClient.py        # console
./fixGwClient.py --gui  # GUI client
```
Run tests:
```bash
make test
```

Cleanup to remove the virtual environment and test output:
```bash
make clean
```


## Configuration

Configuration files live in `src/fixgw/config/`:

- `default.yaml` — main server config; selects which plugins load
- `database.yaml` — parameter namespace definition
- `database/custom.yaml` — add or override parameters without touching upstream files
- `init_data/custom.ini` — set initial parameter values for your specific aircraft

## Important Disclaimer

> FIX-Gateway is developed for Experimental Amateur-Built aircraft use only.  
> It is not FAA-approved avionics software. Aircraft builders are responsible for all integration and safety decisions.
