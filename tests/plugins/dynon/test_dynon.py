"""
Unit tests for the Dynon D10/D100 FIX-Gateway plugin.

Exercises MainThread._parse() directly by passing crafted 52-byte messages,
bypassing the serial port entirely.

Message format (52 ASCII bytes, terminated with 0x0A — not included here):
  [0:8]   header/type (ignored by parser)
  [8:12]  pitch  × 10 (e.g. b"+120" = 12.0°)
  [12:17] roll   × 10 (e.g. b"+0300" = 30.0°)
  [17:20] yaw/heading (e.g. b"090" = 90°)
  [20:24] airspeed × 10 in m/s (e.g. b"0515" → 51.5 m/s × 0.194384 ≈ 100 kt)
  [24:29] altitude in meters (e.g. b"00304" → 304 m × 3.28084 ≈ 997 ft)
  [29:33] ROT × 10 (status=0) or VS × 10 (status=1)
  [33:36] lateral accel × 100
  [36:41] (ignored)
  [41:47] status hex string — bit 0: 0=ALT/ROT, 1=PALT/VS
  [47:52] (ignored)
"""
import io
import unittest
from unittest.mock import MagicMock

import fixgw.database as database
import fixgw.plugins.dynon as dynon
from fixgw.plugins.dynon import MainThread, Plugin

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
- key: YAW
  description: Yaw
  type: int
  min: 0
  max: 360
  units: deg
  initial: 0
  tol: 2000
- key: TAS
  description: True Airspeed
  type: int
  min: 0
  max: 9999
  units: knots
  initial: 0
  tol: 2000
- key: ALT
  description: Altitude
  type: int
  min: -1500
  max: 60000
  units: ft
  initial: 0
  tol: 2000
- key: TALT
  description: True Altitude
  type: int
  min: -1500
  max: 60000
  units: ft
  initial: 0
  tol: 2000
- key: PALT
  description: Pressure Altitude
  type: int
  min: -1500
  max: 60000
  units: ft
  initial: 0
  tol: 2000
- key: ROT
  description: Rate of Turn
  type: float
  min: -30.0
  max: 30.0
  units: deg/s
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
- key: ALAT
  description: Lateral Acceleration
  type: float
  min: -5.0
  max: 5.0
  units: g
  initial: 0.0
  tol: 2000
- key: ZZLOADER
  description: DB load sentinel
  type: str
  initial: "Loaded"
"""


def _make_thread():
    parent = MagicMock()
    parent.config = {"port": "/dev/null"}
    parent.log = MagicMock()
    thread = MainThread(parent)
    # Route db_write to the real database
    thread.parent.db_write = lambda key, val: database.write(key, val)
    return thread


def _db(key):
    return database.read(key)[0]


def _build_msg(pitch_10=0, roll_10=0, yaw=0, speed_10ms=0, alt_m=0,
               rot_vs_10=0, alat_100=0, status_hex="000000"):
    """Build a 52-byte Dynon message. All numeric args are raw integer values."""
    header = b"12345678"          # [0:8]  — not parsed
    pitch  = f"{pitch_10:+04d}".encode()   # [8:12]
    roll   = f"{roll_10:+05d}".encode()   # [12:17]
    heading = f"{yaw:03d}".encode()        # [17:20]
    speed  = f"{speed_10ms:04d}".encode()  # [20:24]
    alt    = f"{alt_m:05d}".encode()       # [24:29]
    rot_vs = f"{rot_vs_10:+04d}".encode()  # [29:33]
    alat   = f"{alat_100:+03d}".encode()   # [33:36]
    pad    = b"00000"                       # [36:41]
    status = status_hex.encode()[:6]       # [41:47]
    tail   = b"12345"                       # [47:52]
    msg = header + pitch + roll + heading + speed + alt + rot_vs + alat + pad + status + tail
    assert len(msg) == 52, f"Bad message length: {len(msg)}"
    return bytearray(msg)


class TestDynonParser(unittest.TestCase):

    def setUp(self):
        database.init(io.StringIO(DB_CONFIG))
        self.thread = _make_thread()

    def test_pitch_positive(self):
        # pitch_10 = 120 → pitch = 12.0°
        self.thread._parse(_build_msg(pitch_10=120))
        self.assertAlmostEqual(_db("PITCH"), 12.0, places=5)

    def test_pitch_negative(self):
        self.thread._parse(_build_msg(pitch_10=-55))
        self.assertAlmostEqual(_db("PITCH"), -5.5, places=5)

    def test_roll_positive(self):
        self.thread._parse(_build_msg(roll_10=300))
        self.assertAlmostEqual(_db("ROLL"), 30.0, places=5)

    def test_roll_negative(self):
        self.thread._parse(_build_msg(roll_10=-150))
        self.assertAlmostEqual(_db("ROLL"), -15.0, places=5)

    def test_yaw(self):
        self.thread._parse(_build_msg(yaw=90))
        self.assertEqual(_db("YAW"), 90)

    def test_airspeed_conversion(self):
        # speed_10ms = 515 → 51.5 m/s → round(51.5 * 0.194384) = 100 kt
        self.thread._parse(_build_msg(speed_10ms=515))
        self.assertEqual(_db("TAS"), 100)

    def test_airspeed_zero(self):
        self.thread._parse(_build_msg(speed_10ms=0))
        self.assertEqual(_db("TAS"), 0)

    def test_altitude_status0_goes_to_alt_and_talt(self):
        # alt_m = 304 → round(304 * 3.28084) = 997 ft; status bit0=0
        self.thread._parse(_build_msg(alt_m=304, status_hex="000000"))
        expected_ft = round(304 * 3.28084)
        self.assertEqual(_db("ALT"), expected_ft)
        self.assertEqual(_db("TALT"), expected_ft)

    def test_altitude_status1_goes_to_palt(self):
        # status bit0=1 → pressure altitude path
        self.thread._parse(_build_msg(alt_m=1000, status_hex="000001"))
        expected_ft = round(1000 * 3.28084)
        self.assertEqual(_db("PALT"), expected_ft)

    def test_rot_written_when_status0(self):
        # rot_vs_10 = 20 → ROT = 2.0 deg/s
        self.thread._parse(_build_msg(rot_vs_10=20, status_hex="000000"))
        self.assertAlmostEqual(_db("ROT"), 2.0, places=5)

    def test_vs_written_when_status1(self):
        # rot_vs_10 = 100 → vs = 100/10 * 60 = 600 fpm; single-sample average = 600
        self.thread._parse(_build_msg(rot_vs_10=100, status_hex="000001"))
        self.assertEqual(_db("VS"), 600)

    def test_lateral_accel(self):
        # alat_100 = 50 → ALAT = 0.50
        self.thread._parse(_build_msg(alat_100=50))
        self.assertAlmostEqual(_db("ALAT"), 0.50, places=5)

    def test_wrong_length_ignored(self):
        # A 10-byte message should produce a warning, not an exception
        self.thread._parse(bytearray(b"tooshort"))
        # Value remains at DB default (0)
        self.assertAlmostEqual(_db("PITCH"), 0.0, places=5)

    def test_vario_averaging(self):
        # Send 3 status=1 messages with different VS values; average should be the mean
        for rot_vs in [100, 200, 300]:  # 600, 1200, 1800 fpm
            self.thread._parse(_build_msg(rot_vs_10=rot_vs, status_hex="000001"))
        expected = round((600 + 1200 + 1800) / 3)
        self.assertEqual(_db("VS"), expected)

    def test_vario_history_is_limited_to_128_samples(self):
        for i in range(130):
            self.thread._parse(_build_msg(rot_vs_10=i, status_hex="000001"))

        self.assertEqual(len(self.thread._vario_values), 128)

    def test_thread_stop_sets_getout(self):
        self.assertFalse(self.thread.getout)

        self.thread.stop()

        self.assertTrue(self.thread.getout)

    def test_run_reads_serial_data_until_newline(self):
        class FakeSerial:
            def __init__(self, owner):
                self.owner = owner
                self.in_waiting = 53

            def read(self, count):
                self.owner.getout = True
                return bytes(_build_msg(pitch_10=75)) + b"\n"

        fake_serial = FakeSerial(self.thread)

        def serial_factory(port, baudrate, timeout):
            self.assertEqual(port, "/dev/null")
            self.assertEqual(baudrate, 115200)
            self.assertEqual(timeout, 0.5)
            return fake_serial

        original_serial = dynon.serial.Serial
        try:
            dynon.serial.Serial = serial_factory
            self.thread.run()
        finally:
            dynon.serial.Serial = original_serial

        self.assertIs(self.thread._c, fake_serial)
        self.assertAlmostEqual(_db("PITCH"), 7.5, places=5)

    def test_run_logs_serial_errors(self):
        class FakeSerial:
            def __init__(self, owner):
                self.owner = owner
                self.in_waiting = 0
                self.calls = 0

            def read(self, count):
                self.calls += 1
                if self.calls == 1:
                    return b""
                self.owner.getout = True
                raise dynon.serial.SerialException()

        fake_serial = FakeSerial(self.thread)
        original_serial = dynon.serial.Serial
        try:
            dynon.serial.Serial = lambda *args, **kwargs: fake_serial
            self.thread.run()
        finally:
            dynon.serial.Serial = original_serial

        self.thread.parent.log.error.assert_called_once_with("Serial port error")


class TestDynonPlugin(unittest.TestCase):
    def test_plugin_lifecycle_and_status(self):
        pl = Plugin("dynon-test", {"port": "/dev/null"}, {})

        thread = MagicMock()
        thread.is_alive.return_value = False
        pl.thread = thread

        pl.run()
        thread.start.assert_called_once_with()

        pl.stop()
        thread.stop.assert_called_once_with()
        thread.join.assert_not_called()
        self.assertIs(pl.get_status(), pl.status)

    def test_plugin_stop_joins_live_thread(self):
        pl = Plugin("dynon-test", {"port": "/dev/null"}, {})
        thread = MagicMock()
        thread.is_alive.side_effect = [True, False]
        pl.thread = thread

        pl.stop()

        thread.stop.assert_called_once_with()
        thread.join.assert_called_once_with(1.0)

    def test_plugin_stop_raises_when_thread_survives_join(self):
        pl = Plugin("dynon-test", {"port": "/dev/null"}, {})
        thread = MagicMock()
        thread.is_alive.return_value = True
        pl.thread = thread

        with self.assertRaises(dynon.plugin.PluginFail):
            pl.stop()

        thread.join.assert_called_once_with(1.0)


if __name__ == "__main__":
    unittest.main()
