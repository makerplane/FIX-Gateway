# GNX 375 FIX-Gateway Plugin — Hardware Validation Guide

---

## Prerequisites

**Hardware needed**
- Garmin GNX 375 unit, powered and in normal operating mode
- USB-to-RS-232 adapter (FTDI-based recommended for aviation use)
- RS-232 cable: 3-wire (TX, RX, GND) — **not** a null-modem cable
- Laptop or Raspberry Pi running FIX-Gateway

**Software needed**
- FIX-Gateway installed with the `garmin_gnx375` plugin
- `python-serial` installed (`pip install pyserial`)
- A serial terminal for raw verification (e.g., `minicom`, PuTTY, or `screen`)

---

## Step 1 — Configure the GNX 375

On the GNX 375 unit, enter installer configuration mode:

1. Hold the **knob** while applying power to enter configuration mode
2. Navigate to **System Configuration → Interfaced Equipment → RS-232**
3. On the **RS-232/RS-422 Port 1** row, set:
   - **Format**: `Aviation Output 1`
   - (Port 1 is the most accessible — it's on J3752)
4. Exit and save configuration

> **If Port 1 is already used** (e.g., connected to a GTR 225 or G5), use Port 2 instead. Port 2 is also on J3752 and supports the same Aviation Output 1 format.

---

## Step 2 — Wire the Serial Connection

The GNX 375 uses high-density D-Sub connectors. **Only 3 wires are needed** for receive-only operation (you do not need to send data back to the unit for this plugin).

**J3752 connector pinout** (44-pin HD-DSub on rear of unit):

| Signal | J3752 Pin | Wire to USB adapter |
|--------|-----------|---------------------|
| RS-232 OUT 1 (TX from GNX) | **5** | RXD on adapter |
| RS-232 IN 1 (RX to GNX) | 20 | TXD on adapter (optional) |
| RS-232 GND 1 | **34** | GND on adapter |

> **Minimum wiring**: pins 5 and 34 only. The plugin reads only; it never writes to the unit.

For Port 2 (if Port 1 is occupied):

| Signal | J3752 Pin | Wire to USB adapter |
|--------|-----------|---------------------|
| RS-232 OUT 2 (TX from GNX) | **6** | RXD on adapter |
| RS-232 GND 2 | **35** | GND on adapter |

> **Voltage levels**: The GNX 375 outputs ±5V RS-232 (EIA RS-232C compliant). Most USB-serial adapters tolerate this. Do not connect directly to a 3.3V UART (Raspberry Pi GPIO) without a level shifter.

---

## Step 3 — Verify Raw Serial Output

Before running FIX-Gateway, confirm the GNX 375 is actually transmitting.

**On Linux/macOS:**
```bash
screen /dev/ttyUSB0 9600
```

**On Windows (PuTTY):** COM port, 9600, 8N1, no flow control

**Expected output** — you should see a stream of NMEA sentences like:
```
$GPRMC,152043.00,A,3000.0000,N,08800.0000,W,100.0,090.0,180426,,,A*6E
$GPGGA,152043.00,3000.0000,N,08800.0000,W,1,08,1.0,914.4,M,-30.0,M,,*57
$GPRMB,A,0.00,L,    ,    ,4000.0000,N,08800.0000,W,050.0,090.0,100.0,V,A*XX
$GPAPB,A,A,0.00,L,N,V,V,090.0,T,    ,090.0,T,090.0,T,A*XX
$GPVTG,090.0,T,,M,100.0,N,185.2,K,A*XX
```

If you see nothing: check wiring (pin 5 → RXD), verify Aviation Output 1 is configured, confirm the unit is in normal flight mode (not demo or test mode).

If you see garbage characters: baud rate is wrong. Try 4800 — some older Garmin firmware defaults to 4800.

---

## Step 4 — Configure and Start FIX-Gateway

In your FIX-Gateway connections config, include:

```yaml
garmin_gnx375:
  load: GARMIN_GNX375
  module: fixgw.plugins.garmin_gnx375
  port: /dev/ttyUSB0        # adjust to your port
  baud: 9600
  cdi_full_scale_nm: 5.0    # enroute; use 0.3 for approach
```

Start FIX-Gateway and watch the log for errors:
```
[garmin_gnx375] cannot open /dev/ttyUSB0 ...  → wrong port or permission denied
```

On Linux, fix permission with:
```bash
sudo usermod -a -G dialout $USER   # then log out and back in
```

---

## Step 5 — Validation Checks

Run these checks with the aircraft (or bench setup) in known states.

### Check A — GPS fix and position

With a GPS signal acquired and a known position:

```bash
python fixGwClient.py
```

Read `LAT` and `LONG` — they should match the GNX 375's position display within 0.001°.

| FIX key | Expected | Tolerance |
|---------|----------|-----------|
| `LAT` | Unit's displayed latitude | ±0.001° |
| `LONG` | Unit's displayed longitude | ±0.001° |
| `GPS_FIX_TYPE` | 1 (GPS) or 2 (WAAS) | exact |
| `GPS_ELLIPSOID_ALT` | Unit's GPS altitude in ft | ±50 ft |

### Check B — Ground speed and track

While taxiing or with a known ground speed input:

| FIX key | Expected | Tolerance |
|---------|----------|-----------|
| `GS` | GNX 375 groundspeed display | ±1 kt |
| `TRACK` | GNX 375 track display | ±2° |

### Check C — XTE sign convention (critical)

Program a direct-to waypoint **to the north of your current position**. Fly or taxi a track that puts you **south of the direct-to course** (i.e., right of the desired track when heading north).

| Condition | Expected `XTRACK` | Expected `CDI` |
|-----------|------------------|----------------|
| On course | ≈ 0.0 nm | ≈ 0.0 |
| Right of course (south, steer left) | **positive** | **negative** |
| Left of course (north, steer right) | **negative** | **positive** |

If the sign is backwards, the GNX 375 may be using a non-standard `$GPRMB` steer direction. Check the raw sentence `dir_steer` field: if `'L'` actually means left-of-track on your unit, flip the sign mapping in `_handle_rmb()`.

### Check D — CDI scaling

With a known XTE from the GNX 375 display (e.g., 2.5 nm):

```
CDI = -XTRACK / cdi_full_scale_nm
CDI = -2.5 / 5.0 = -0.50   (aircraft is right of course, needle left)
```

Verify the `CDI` key reads approximately −0.5.

### Check E — Destination course

With an active flight plan leg:

| FIX key | Expected | Tolerance |
|---------|----------|-----------|
| `COURSE` | GNX 375 DTK (desired track) display | ±2° |

---

## Step 6 — Regression: Run Unit Tests

After any hardware-driven adjustments, confirm the unit tests still pass:

```bash
cd /path/to/fix-gateway
.venv/bin/python -m pytest tests/plugins/garmin_gnx375/ -v
```

All 14 tests must pass before committing changes.

---

## Bench Testing Workflow (Workstation + VSCode)

A full Makerplane EFIS stack is **not required** for plugin validation. FIX-Gateway is a plain Python process and runs on Windows, macOS, or Linux — including directly in a VSCode terminal. The plugin has no dependency on pyEfis, a Raspberry Pi, or any EFIS hardware.

### What bench validation covers

The bench workflow validates everything the plugin is responsible for:

- Serial port opens and receives data from the GNX 375
- All four NMEA sentence types are parsed correctly
- Correct values land in the FIX-Gateway database
- XTE sign convention matches the compute.py XTE function

### What requires a live EFIS later

Two things are deferred to a full EFIS integration test:

| Item | Why deferred |
|------|-------------|
| CDI needle direction on pyEfis display | pyEfis concern, not a plugin concern |
| XTRACK driving MAOS-FCS lateral guidance | Requires FCS SIL or flight test |

### Bench setup (Windows + VSCode)

1. Connect the GNX 375 via USB-serial adapter
2. Identify the COM port in Device Manager (e.g., `COM4`)
3. In the FIX-Gateway connections config, set `port: COM4`
4. Open a VSCode terminal in the fix-gateway repo root
5. Activate the virtual environment:
   ```bat
   .venv\Scripts\activate
   ```
6. Start FIX-Gateway:
   ```bat
   python fixGw.py --config src/fixgw/config
   ```
7. In a second terminal, read live values:
   ```bat
   python fixGwClient.py
   ```

### Capturing a serial log for replay testing

Capturing a short live session from the bench permanently documents real GNX 375 output. The captured log can then be replayed in automated tests without hardware present.

**Capture** (run while the GNX 375 is active with a GPS fix and an active waypoint):

```bash
# Linux/macOS
timeout 30 cat /dev/ttyUSB0 > tests/plugins/garmin_gnx375/fixtures/gnx375_sample.nmea

# Windows (PowerShell)
$port = New-Object System.IO.Ports.SerialPort 'COM4', 9600
$port.Open()
$lines = 1..150 | ForEach-Object { $port.ReadLine() }
$port.Close()
$lines | Set-Content tests\plugins\garmin_gnx375\fixtures\gnx375_sample.nmea
```

Aim to capture at least 30 seconds with:
- A GPS fix active (WAAS preferred)
- An active direct-to waypoint with measurable XTE (fly/place the unit 2–3 nm off course)
- A course change mid-capture to exercise the `COURSE` key

**Replay test** — add this to `test_garmin_gnx375.py`:

```python
import os

FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "gnx375_sample.nmea")

@unittest.skipUnless(os.path.exists(FIXTURE), "no hardware fixture captured yet")
class TestFixtureReplay(unittest.TestCase):
    def setUp(self):
        database.init(io.StringIO(DB_CONFIG))
        self.thread = _make_thread()

    def test_replay_produces_valid_position(self):
        with open(FIXTURE, encoding="ascii", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = pynmea2.parse(line)
                    self.thread._dispatch(msg, _CDI_FULL_SCALE)
                except pynmea2.ParseError:
                    pass
        # After replaying a real session, position must be non-zero
        self.assertNotEqual(_db_value("LAT"), 0.0)
        self.assertNotEqual(_db_value("LONG"), 0.0)
        self.assertNotEqual(_db_value("GPS_FIX_TYPE"), 0)

    def test_replay_xtrack_within_range(self):
        with open(FIXTURE, encoding="ascii", errors="replace") as f:
            for line in f:
                line = line.strip()
                try:
                    msg = pynmea2.parse(line)
                    self.thread._dispatch(msg, _CDI_FULL_SCALE)
                except pynmea2.ParseError:
                    pass
        # XTRACK must be within database bounds
        xtrack = _db_value("XTRACK")
        self.assertGreaterEqual(xtrack, -100.0)
        self.assertLessEqual(xtrack, 100.0)
```

The `@skipUnless` decorator means the replay tests are silently skipped in CI (where no fixture exists) and run automatically once a fixture is committed.

---

## Known Issues and Edge Cases

**No active flight plan**: `$GPRMB` and `$GPAPB` are only transmitted when a waypoint is active. `XTRACK`, `CDI`, and `COURSE` will not update when flying without an active destination. `LAT`, `LONG`, `GS`, `TRACK`, and `GPS_ELLIPSOID_ALT` update continuously from `$GPRMC`/`$GPGGA` regardless.

**WAAS-acquired fix**: `GPS_FIX_TYPE` will read `2` when WAAS is active. This is correct.

**CDI full scale on approach**: Switch `cdi_full_scale_nm` to `0.3` when within the terminal area on a GPS approach. This matches the GNX 375's own CDI scaling in approach mode.

**Port 1 as RS-422**: If your installation uses Port 1 in RS-422 mode (balanced differential), you need an RS-422 receiver on the adapter side — a standard RS-232 USB adapter will not work. Use Port 2 (RS-232 only) instead.

**Universality**: This plugin parses standard NMEA 0183 sentences and will work with any Garmin navigator that supports Aviation Output 1 or any device outputting `$GPRMC`/`$GPGGA`/`$GPRMB`/`$GPAPB` sentences. This includes the GNS 430/530, GTN 650/750, GPS 175, and GNC 355.
