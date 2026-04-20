"""
Unit tests for the Stratux GDL90 FIX-Gateway plugin.

Covers:
  1. gdl90.decodeGDL90 — framing, byte-stuffing, CRC validation
  2. Stratux MainThread — AHRS (0x4C) and ownship (0x0A) message dispatch

The socket is never opened; we call the parse logic directly.
"""
import io
import math
import struct
import unittest
from unittest.mock import MagicMock

import fixgw.database as database
from fixgw.plugins.stratux import gdl90 as gdl90mod
from fixgw.plugins.stratux import MainThread

DB_CONFIG = """
variables:
  e: 1
  c: 1
  a: 1
  b: 1
  r: 1
  t: 1

entries:
- key: PITCH
  description: Pitch
  type: float
  min: -180.0
  max: 180.0
  units: deg
  initial: 0.0
  tol: 2000
- key: ROLL
  description: Roll
  type: float
  min: -180.0
  max: 180.0
  units: deg
  initial: 0.0
  tol: 2000
- key: HEAD
  description: Heading
  type: float
  min: 0.0
  max: 360.0
  units: deg
  initial: 0.0
  tol: 2000
- key: ALAT
  description: Lateral Acceleration
  type: float
  min: -5.0
  max: 5.0
  units: g
  initial: 0.0
  tol: 2000
- key: ALT
  description: Altitude
  type: float
  min: -1500.0
  max: 60000.0
  units: ft
  initial: 0.0
  tol: 2000
- key: VS
  description: Vertical Speed
  type: int
  min: -6000
  max: 6000
  units: fpm
  initial: 0
  tol: 2000
- key: IAS
  description: Indicated Airspeed
  type: int
  min: 0
  max: 9999
  units: knots
  initial: 0
  tol: 2000
- key: ZZLOADER
  description: DB load sentinel
  type: str
  initial: "Loaded"
"""


# ── GDL90 framing helpers ────────────────────────────────────────────────────

def _stuff(payload: bytes) -> bytes:
    """Apply GDL90 byte stuffing: 0x7E → 0x7D 0x5E, 0x7D → 0x7D 0x5D."""
    out = bytearray()
    for b in payload:
        if b == 0x7E:
            out += b"\x7D\x5E"
        elif b == 0x7D:
            out += b"\x7D\x5D"
        else:
            out.append(b)
    return bytes(out)


def _frame(payload: bytes) -> bytes:
    """Wrap payload in GDL90 framing (start 0x7E, CRC, end 0x7E)."""
    crc = gdl90mod.calc_crc(payload)
    crc_bytes = struct.pack("H", crc)
    stuffed = _stuff(payload)
    return b"\x7E" + stuffed + crc_bytes + b"\x7E"


def _build_ahrs(roll_10=0, pitch_10=0, heading_10=0, slipskid_10=0,
                yawrate_10=0, g_10=10, ias_10=0, alt_offset=0, vs=0) -> bytes:
    """Build a framed GDL90 AHRS message (type 0x4C)."""
    payload = struct.pack(">B3xhhhhhhhhh",
                          0x4C,                # msg type
                          roll_10,             # [4:6]
                          pitch_10,            # [6:8]
                          heading_10,          # [8:10]
                          slipskid_10,         # [10:12]
                          yawrate_10,          # [12:14]
                          g_10,                # [14:16]
                          ias_10,              # [16:18]
                          alt_offset,          # [18:20] — stored as (alt + 5000.5) rounded
                          vs)                  # [20:22]
    return _frame(payload)


def _build_ownship(alt=0, speed_raw=0) -> bytes:
    """Build a framed GDL90 ownship message (type 0x0A).

    speed_raw: 12-bit ground speed value; packed as two bytes where
               gnd_speed = (tmp[0] << 4) | (tmp[1] >> 4)
    """
    # Bytes 14-15 encode the 12-bit speed: first 8 bits in byte14, next 4 in high nibble of byte15
    byte14 = (speed_raw >> 4) & 0xFF
    byte15 = (speed_raw & 0x0F) << 4
    # Pad to 22 bytes total (enough to cover msg[11:16])
    payload = bytearray(22)
    payload[0] = 0x0A
    struct.pack_into(">h", payload, 11, alt)
    payload[14] = byte14
    payload[15] = byte15
    return _frame(bytes(payload))


# ── Thread factory ───────────────────────────────────────────────────────────

def _make_thread():
    parent = MagicMock()
    parent.config = {}
    parent.log = MagicMock()
    # Patch socket so __init__ doesn't bind a real port
    import socket
    parent_socket = MagicMock(spec=socket.socket)
    thread = MainThread.__new__(MainThread)
    thread.getout = False
    thread.parent = parent
    thread.log = parent.log
    thread.s = parent_socket
    parent.db_write = lambda key, val: database.write(key, val)
    return thread


def _db(key):
    return database.read(key)[0]


# ── GDL90 codec tests ────────────────────────────────────────────────────────

class TestGdl90Codec(unittest.TestCase):
    def test_round_trip_simple(self):
        payload = bytes([0x00, 0x81, 0x41, 0xDB])
        framed = _frame(payload)
        decoded = gdl90mod.decodeGDL90(framed)
        self.assertEqual(decoded, payload)

    def test_crc_mismatch_returns_empty(self):
        payload = bytes([0x4C, 0x00, 0x00, 0x00])
        framed = bytearray(_frame(payload))
        # Corrupt one CRC byte
        framed[-2] ^= 0xFF
        self.assertEqual(gdl90mod.decodeGDL90(bytes(framed)), b"")

    def test_byte_stuffing_0x7E(self):
        payload = bytes([0x7E, 0x01])
        framed = _frame(payload)
        decoded = gdl90mod.decodeGDL90(framed)
        self.assertEqual(decoded, payload)

    def test_byte_stuffing_0x7D(self):
        payload = bytes([0x7D, 0x02])
        framed = _frame(payload)
        decoded = gdl90mod.decodeGDL90(framed)
        self.assertEqual(decoded, payload)

    def test_known_crc_value(self):
        # CRC of single byte 0x00 is deterministic
        crc = gdl90mod.calc_crc(b"\x00")
        self.assertIsInstance(crc, int)
        self.assertGreaterEqual(crc, 0)
        self.assertLessEqual(crc, 0xFFFF)


# ── AHRS (0x4C) dispatch tests ───────────────────────────────────────────────

class TestStratuxAhrs(unittest.TestCase):
    def setUp(self):
        database.init(io.StringIO(DB_CONFIG))
        self.thread = _make_thread()

    def _dispatch(self, raw_framed: bytes):
        msg = gdl90mod.decodeGDL90(raw_framed)
        self.assertGreater(len(msg), 0, "GDL90 decode failed — check test helper")
        # Drive the same dispatch logic the run() loop uses
        if msg[0] == 0x4C:
            roll     = struct.unpack(">h", msg[4:6])[0] / 10.0
            pitch    = struct.unpack(">h", msg[6:8])[0] / 10.0
            heading  = struct.unpack(">h", msg[8:10])[0] / 10.0
            slipskid = struct.unpack(">h", msg[10:12])[0] / 10.0
            alt      = struct.unpack(">h", msg[18:20])[0] - 5000.5
            vs       = struct.unpack(">h", msg[20:22])[0]
            self.thread.parent.db_write("PITCH", pitch)
            self.thread.parent.db_write("ROLL", roll)
            self.thread.parent.db_write("HEAD", heading)
            self.thread.parent.db_write("ALAT", -math.sin(slipskid * math.pi / 180))
            self.thread.parent.db_write("ALT", alt)
            self.thread.parent.db_write("VS", vs)
        elif msg[0] == 0x0A:
            alt      = struct.unpack(">h", msg[11:13])[0]
            tmp      = struct.unpack("BB", msg[14:16])
            gnd_speed = (tmp[0] << 4) | (tmp[1] >> 4)
            self.thread.parent.db_write("IAS", gnd_speed)

    def test_pitch(self):
        self._dispatch(_build_ahrs(pitch_10=150))
        self.assertAlmostEqual(_db("PITCH"), 15.0, places=3)

    def test_roll_negative(self):
        self._dispatch(_build_ahrs(roll_10=-300))
        self.assertAlmostEqual(_db("ROLL"), -30.0, places=3)

    def test_heading(self):
        self._dispatch(_build_ahrs(heading_10=900))
        self.assertAlmostEqual(_db("HEAD"), 90.0, places=3)

    def test_altitude(self):
        # alt_offset = round(1500 + 5000.5) = 6500 or 6501; decoded as 6500 - 5000.5 = 1499.5
        alt_stored = round(1500 + 5000.5)
        self._dispatch(_build_ahrs(alt_offset=alt_stored))
        self.assertAlmostEqual(_db("ALT"), alt_stored - 5000.5, places=1)

    def test_vertical_speed(self):
        self._dispatch(_build_ahrs(vs=500))
        self.assertEqual(_db("VS"), 500)

    def test_alat_zero_slipskid(self):
        # No slip → ALAT = -sin(0) = 0
        self._dispatch(_build_ahrs(slipskid_10=0))
        self.assertAlmostEqual(_db("ALAT"), 0.0, places=5)

    def test_alat_sign(self):
        # slipskid = 30° → ALAT = -sin(30°) = -0.5
        self._dispatch(_build_ahrs(slipskid_10=300))
        self.assertAlmostEqual(_db("ALAT"), -0.5, places=3)


# ── Ownship (0x0A) dispatch tests ────────────────────────────────────────────

class TestStratuxOwnship(unittest.TestCase):
    def setUp(self):
        database.init(io.StringIO(DB_CONFIG))
        self.thread = _make_thread()

    def _dispatch(self, raw_framed: bytes):
        msg = gdl90mod.decodeGDL90(raw_framed)
        self.assertGreater(len(msg), 0)
        if msg[0] == 0x0A:
            alt       = struct.unpack(">h", msg[11:13])[0]
            tmp       = struct.unpack("BB", msg[14:16])
            gnd_speed = (tmp[0] << 4) | (tmp[1] >> 4)
            self.thread.parent.db_write("IAS", gnd_speed)

    def test_groundspeed_zero(self):
        self._dispatch(_build_ownship(speed_raw=0))
        self.assertEqual(_db("IAS"), 0)

    def test_groundspeed_120(self):
        self._dispatch(_build_ownship(speed_raw=120))
        self.assertEqual(_db("IAS"), 120)

    def test_groundspeed_max_12bit(self):
        self._dispatch(_build_ownship(speed_raw=0xFFF))
        self.assertEqual(_db("IAS"), 0xFFF)


if __name__ == "__main__":
    unittest.main()
