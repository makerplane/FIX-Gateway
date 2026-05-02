#  Copyright (c) 2026 Bill Mallard
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.

"""Unit tests for the garmin_gnx375 FIX-Gateway plugin.

Tests exercise the NMEA sentence parsers (_handle_rmc, _handle_gga,
_handle_rmb, _handle_apb) by bypassing the serial port entirely and
driving MainThread._dispatch() directly with parsed pynmea2 objects.
"""

import io
import unittest
from unittest.mock import MagicMock

import pynmea2

import fixgw.database as database
import fixgw.plugins.garmin_gnx375 as garmin_gnx375
from fixgw.plugins.garmin_gnx375 import MainThread, Plugin

DB_CONFIG = """
variables:
  e: 1
  c: 1
  a: 1
  b: 1
  r: 1
  t: 1

entries:
- key: LAT
  description: Latitude
  type: float
  min: -90.0
  max: 90.0
  units: deg
  initial: 0.0
  tol: 2000

- key: LONG
  description: Longitude
  type: float
  min: -180.0
  max: 180.0
  units: deg
  initial: 0.0
  tol: 2000

- key: GS
  description: Ground Speed
  type: float
  min: 0.0
  max: 9999.0
  units: knots
  initial: 0.0
  tol: 2000

- key: TRACK
  description: Track
  type: float
  min: 0.0
  max: 360.0
  units: deg
  initial: 0.0
  tol: 2000

- key: GPS_ELLIPSOID_ALT
  description: GPS Ellipsoid Altitude
  type: float
  min: -1500.0
  max: 60000.0
  units: ft
  initial: 0.0
  tol: 2000

- key: GPS_FIX_TYPE
  description: GPS Fix Type
  type: int
  min: 0
  max: 9
  initial: 0
  tol: 2000

- key: XTRACK
  description: Cross-Track Error
  type: float
  min: -100.0
  max: 100.0
  units: nM
  initial: 0.0
  tol: 2000

- key: CDI
  description: Course Deviation Indicator
  type: float
  min: -1.0
  max: 1.0
  initial: 0.0
  tol: 2000

- key: COURSE
  description: Course to Destination
  type: float
  min: 0.0
  max: 360.0
  units: deg
  initial: 0.0
  tol: 2000
"""

_CDI_FULL_SCALE = 5.0  # nm, default for these tests


def _make_thread():
    """Return a MainThread with a mock parent that writes to the real FIX DB."""
    parent = MagicMock()
    parent.config = {
        "port": "/dev/null",
        "baud": "9600",
        "cdi_full_scale_nm": str(_CDI_FULL_SCALE),
    }
    parent.log = MagicMock()

    thread = MainThread(parent)

    # Route db_write calls to the real database
    def _db_write(key, value):
        database.write(key, value)

    thread.parent.db_write.side_effect = _db_write
    return thread


def _db_value(key):
    """Return the raw scalar value for a database key."""
    result = database.read(key)
    return result[0]


class TestRmcParsing(unittest.TestCase):
    def setUp(self):
        database.init(io.StringIO(DB_CONFIG))
        self.thread = _make_thread()

    def test_active_rmc_writes_lat_lon_gs_track(self):
        sentence = "$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A"
        msg = pynmea2.parse(sentence)
        self.thread._handle_rmc(msg)
        self.assertAlmostEqual(_db_value("LAT"), 48.1173, places=3)
        self.assertAlmostEqual(_db_value("LONG"), 11.5167, places=3)
        self.assertAlmostEqual(_db_value("GS"), 22.4, places=1)
        self.assertAlmostEqual(_db_value("TRACK"), 84.4, places=1)

    def test_void_rmc_does_not_write(self):
        msg = MagicMock()
        msg.status = "V"
        initial_lat = _db_value("LAT")
        self.thread._handle_rmc(msg)
        self.assertEqual(_db_value("LAT"), initial_lat)

    def test_rmc_skips_missing_speed_and_track(self):
        msg = MagicMock()
        msg.status = "A"
        msg.latitude = 12.5
        msg.longitude = -45.25
        msg.spd_over_grnd = None
        msg.true_course = None

        self.thread._handle_rmc(msg)

        self.assertAlmostEqual(_db_value("LAT"), 12.5)
        self.assertAlmostEqual(_db_value("LONG"), -45.25)
        self.assertEqual(_db_value("GS"), 0.0)
        self.assertEqual(_db_value("TRACK"), 0.0)


class TestGgaParsing(unittest.TestCase):
    def setUp(self):
        database.init(io.StringIO(DB_CONFIG))
        self.thread = _make_thread()

    def test_gga_fix_writes_position_and_altitude(self):
        # Altitude 545.4 m → 1789.1 ft
        sentence = "$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47"
        msg = pynmea2.parse(sentence)
        self.thread._handle_gga(msg)
        self.assertAlmostEqual(_db_value("LAT"), 48.1173, places=3)
        self.assertAlmostEqual(_db_value("LONG"), 11.5167, places=3)
        self.assertAlmostEqual(_db_value("GPS_ELLIPSOID_ALT"), 545.4 * 3.28084, places=0)
        self.assertEqual(_db_value("GPS_FIX_TYPE"), 1)

    def test_gga_no_fix_skips_position(self):
        msg = MagicMock()
        msg.gps_qual = "0"
        msg.altitude = None
        initial_lat = _db_value("LAT")
        self.thread._handle_gga(msg)
        self.assertEqual(_db_value("GPS_FIX_TYPE"), 0)
        self.assertEqual(_db_value("LAT"), initial_lat)

    def test_dgps_fix_type_2(self):
        sentence = "$GPGGA,123519,4807.038,N,01131.000,E,2,08,0.9,545.4,M,46.9,M,,*44"
        msg = pynmea2.parse(sentence)
        self.thread._handle_gga(msg)
        self.assertEqual(_db_value("GPS_FIX_TYPE"), 2)

    def test_gga_fix_without_altitude_skips_altitude(self):
        msg = MagicMock()
        msg.gps_qual = "1"
        msg.latitude = 10.0
        msg.longitude = 20.0
        msg.altitude = None

        self.thread._handle_gga(msg)

        self.assertEqual(_db_value("GPS_FIX_TYPE"), 1)
        self.assertEqual(_db_value("GPS_ELLIPSOID_ALT"), 0.0)


class TestRmbParsing(unittest.TestCase):
    def setUp(self):
        database.init(io.StringIO(DB_CONFIG))
        self.thread = _make_thread()

    def _dispatch_rmb(self, sentence):
        msg = pynmea2.parse(sentence)
        self.thread._handle_rmb(msg, _CDI_FULL_SCALE)

    def test_steer_left_gives_positive_xtrack(self):
        # dir_steer='L' → aircraft is RIGHT of track → positive XTRACK
        sentence = "$GPRMB,A,3.000,L,ORIG,DEST,4000.000,N,08800.000,W,5.0,090.0,5.0,V*XX"
        try:
            self._dispatch_rmb(sentence)
        except pynmea2.ParseError:
            # Build msg manually if checksum fails in test
            msg = MagicMock()
            msg.status = "A"
            msg.cross_track_err = 3.0
            msg.dir_steer = "L"
            self.thread._handle_rmb(msg, _CDI_FULL_SCALE)
        self.assertAlmostEqual(_db_value("XTRACK"), 3.0, places=3)
        self.assertAlmostEqual(_db_value("CDI"), -3.0 / _CDI_FULL_SCALE, places=4)

    def test_steer_right_gives_negative_xtrack(self):
        # dir_steer='R' → aircraft is LEFT of track → negative XTRACK
        msg = MagicMock()
        msg.status = "A"
        msg.cross_track_err = 3.0
        msg.dir_steer = "R"
        self.thread._handle_rmb(msg, _CDI_FULL_SCALE)
        self.assertAlmostEqual(_db_value("XTRACK"), -3.0, places=3)
        self.assertAlmostEqual(_db_value("CDI"), 3.0 / _CDI_FULL_SCALE, places=4)

    def test_zero_xte_gives_zero_xtrack_and_cdi(self):
        msg = MagicMock()
        msg.status = "A"
        msg.cross_track_err = 0.0
        msg.dir_steer = "L"
        self.thread._handle_rmb(msg, _CDI_FULL_SCALE)
        self.assertAlmostEqual(_db_value("XTRACK"), 0.0, places=4)
        self.assertAlmostEqual(_db_value("CDI"), 0.0, places=4)

    def test_large_xte_clips_cdi_to_one(self):
        msg = MagicMock()
        msg.status = "A"
        msg.cross_track_err = 20.0  # >> 5 nm full scale
        msg.dir_steer = "L"
        self.thread._handle_rmb(msg, _CDI_FULL_SCALE)
        self.assertAlmostEqual(_db_value("XTRACK"), 20.0, places=3)
        self.assertAlmostEqual(_db_value("CDI"), -1.0, places=4)

    def test_void_status_does_not_update(self):
        msg = MagicMock()
        msg.status = "V"
        msg.cross_track_err = 5.0
        msg.dir_steer = "L"
        self.thread._handle_rmb(msg, _CDI_FULL_SCALE)
        self.assertEqual(_db_value("XTRACK"), 0.0)

    def test_missing_or_bad_rmb_cross_track_inputs_do_not_update(self):
        for cross_track_err, dir_steer in [(None, "L"), (1.0, "X")]:
            database.init(io.StringIO(DB_CONFIG))
            self.thread = _make_thread()
            msg = MagicMock()
            msg.status = "A"
            msg.cross_track_err = cross_track_err
            msg.dir_steer = dir_steer

            self.thread._handle_rmb(msg, _CDI_FULL_SCALE)

            self.assertEqual(_db_value("XTRACK"), 0.0)

    def test_nmea_sign_convention_north_of_eastbound_is_negative(self):
        """Consistency check: aircraft north of east-bound course should → negative XTRACK.

        North of eastbound = pilot's left = needs to steer right to return → 'R' in NMEA.
        """
        msg = MagicMock()
        msg.status = "A"
        msg.cross_track_err = 3.0
        msg.dir_steer = "R"  # steer right to return
        self.thread._handle_rmb(msg, _CDI_FULL_SCALE)
        self.assertLess(_db_value("XTRACK"), 0.0)  # must be negative

    def test_nmea_sign_convention_south_of_eastbound_is_positive(self):
        """Consistency check: aircraft south of east-bound course should → positive XTRACK."""
        msg = MagicMock()
        msg.status = "A"
        msg.cross_track_err = 3.0
        msg.dir_steer = "L"  # steer left to return
        self.thread._handle_rmb(msg, _CDI_FULL_SCALE)
        self.assertGreater(_db_value("XTRACK"), 0.0)  # must be positive


class TestApbParsing(unittest.TestCase):
    def setUp(self):
        database.init(io.StringIO(DB_CONFIG))
        self.thread = _make_thread()

    def test_apb_writes_course(self):
        msg = MagicMock()
        msg.bearing_present_dest = 270.0
        self.thread._handle_apb(msg)
        self.assertAlmostEqual(_db_value("COURSE"), 270.0, places=1)

    def test_apb_none_bearing_does_not_write(self):
        msg = MagicMock()
        msg.bearing_present_dest = None
        initial = _db_value("COURSE")
        self.thread._handle_apb(msg)
        self.assertEqual(_db_value("COURSE"), initial)


class TestDispatch(unittest.TestCase):
    def setUp(self):
        database.init(io.StringIO(DB_CONFIG))
        self.thread = _make_thread()

    def test_dispatch_routes_known_sentence_types_and_ignores_unknown(self):
        handlers = {
            "_handle_rmc": MagicMock(),
            "_handle_gga": MagicMock(),
            "_handle_rmb": MagicMock(),
            "_handle_apb": MagicMock(),
        }
        for name, handler in handlers.items():
            setattr(self.thread, name, handler)

        for sentence_type in ["RMC", "GGA", "RMB", "APB", "TXT"]:
            msg = MagicMock()
            msg.sentence_type = sentence_type
            self.thread._dispatch(msg, _CDI_FULL_SCALE)

        handlers["_handle_rmc"].assert_called_once()
        handlers["_handle_gga"].assert_called_once()
        handlers["_handle_rmb"].assert_called_once()
        handlers["_handle_apb"].assert_called_once()


class TestSerialRunLoop(unittest.TestCase):
    def setUp(self):
        self.parent = MagicMock()
        self.parent.config = {"port": "/dev/null"}
        self.parent.log = MagicMock()
        self.thread = MainThread(self.parent)

    def _patch_serial(self, factory):
        original = garmin_gnx375.serial.Serial
        garmin_gnx375.serial.Serial = factory
        return original

    def test_run_logs_open_failure(self):
        def serial_factory(*args, **kwargs):
            raise garmin_gnx375.serial.SerialException("no port")

        original = self._patch_serial(serial_factory)
        try:
            self.thread.run()
        finally:
            garmin_gnx375.serial.Serial = original

        self.parent.log.error.assert_called_once()
        self.assertIn("cannot open /dev/null", self.parent.log.error.call_args.args[0])

    def test_run_reads_parses_dispatches_and_closes_serial(self):
        class FakeSerial:
            def __init__(self):
                self.is_open = True
                self.closed = False
                self.calls = 0

            def readline(self):
                self.calls += 1
                if self.calls == 1:
                    return b""
                self.thread.getout = True
                return b"$GPRMC,ignored*00\r\n"

            def close(self):
                self.closed = True
                self.is_open = False

        fake_serial = FakeSerial()
        fake_serial.thread = self.thread
        parsed = MagicMock()
        parsed.sentence_type = "RMC"
        self.thread._dispatch = MagicMock()
        parse_mock = MagicMock(return_value=parsed)
        original_serial = self._patch_serial(
            lambda port, baud, timeout: fake_serial
        )
        original_parse = garmin_gnx375.pynmea2.parse
        garmin_gnx375.pynmea2.parse = parse_mock
        try:
            self.thread.run()
        finally:
            garmin_gnx375.serial.Serial = original_serial
            garmin_gnx375.pynmea2.parse = original_parse

        parse_mock.assert_called_once_with("$GPRMC,ignored*00")
        self.thread._dispatch.assert_called_once_with(parsed, 5.0)
        self.assertTrue(fake_serial.closed)

    def test_run_uses_configured_baud_and_cdi_scale(self):
        self.parent.config = {
            "port": "/dev/ttyS1",
            "baud": "4800",
            "cdi_full_scale_nm": "0.3",
        }
        self.thread = MainThread(self.parent)

        class FakeSerial:
            is_open = False

            def readline(self):
                self.thread.getout = True
                return b"$GPRMC,ignored*00\n"

        fake_serial = FakeSerial()
        fake_serial.thread = self.thread
        parsed = MagicMock()
        self.thread._dispatch = MagicMock()
        original_serial = self._patch_serial(
            lambda port, baud, timeout: fake_serial
        )
        original_parse = garmin_gnx375.pynmea2.parse
        garmin_gnx375.pynmea2.parse = MagicMock(return_value=parsed)
        try:
            self.thread.run()
        finally:
            garmin_gnx375.serial.Serial = original_serial
            garmin_gnx375.pynmea2.parse = original_parse

        self.thread._dispatch.assert_called_once_with(parsed, 0.3)

    def test_run_skips_decode_and_parse_errors_and_logs_dispatch_errors(self):
        class BadDecode:
            def decode(self, *args, **kwargs):
                raise UnicodeError("bad bytes")

        class FakeSerial:
            is_open = False

            def __init__(self, thread):
                self.thread = thread
                self.items = [
                    BadDecode(),
                    b"$BAD\n",
                    b"$GOOD\n",
                ]

            def readline(self):
                item = self.items.pop(0)
                if not self.items:
                    self.thread.getout = True
                return item

        def parse(line):
            if line == "$BAD":
                raise pynmea2.ParseError("bad nmea", line)
            return MagicMock()

        fake_serial = FakeSerial(self.thread)
        self.thread._dispatch = MagicMock(side_effect=RuntimeError("boom"))
        original_serial = self._patch_serial(lambda *args, **kwargs: fake_serial)
        original_parse = garmin_gnx375.pynmea2.parse
        garmin_gnx375.pynmea2.parse = parse
        try:
            self.thread.run()
        finally:
            garmin_gnx375.serial.Serial = original_serial
            garmin_gnx375.pynmea2.parse = original_parse

        self.thread._dispatch.assert_called_once()
        self.parent.log.debug.assert_called_once()
        self.assertIn("dispatch error", self.parent.log.debug.call_args.args[0])

    def test_run_logs_read_error_and_closes_serial(self):
        class FakeSerial:
            is_open = True

            def __init__(self):
                self.closed = False

            def readline(self):
                raise garmin_gnx375.serial.SerialException("read failed")

            def close(self):
                self.closed = True
                self.is_open = False

        fake_serial = FakeSerial()
        original = self._patch_serial(lambda *args, **kwargs: fake_serial)
        try:
            self.thread.run()
        finally:
            garmin_gnx375.serial.Serial = original

        self.parent.log.error.assert_called_once()
        self.assertIn("serial read error", self.parent.log.error.call_args.args[0])
        self.assertTrue(fake_serial.closed)

    def test_stop_sets_getout(self):
        self.assertFalse(self.thread.getout)

        self.thread.stop()

        self.assertTrue(self.thread.getout)


class TestPluginLifecycle(unittest.TestCase):
    def test_plugin_run_stop_and_status(self):
        pl = Plugin("garmin-test", {"port": "/dev/null"}, {})
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
        pl = Plugin("garmin-test", {"port": "/dev/null"}, {})
        thread = MagicMock()
        thread.is_alive.side_effect = [True, False]
        pl.thread = thread

        pl.stop()

        thread.join.assert_called_once_with(2.0)

    def test_plugin_stop_raises_when_thread_survives_join(self):
        pl = Plugin("garmin-test", {"port": "/dev/null"}, {})
        thread = MagicMock()
        thread.is_alive.return_value = True
        pl.thread = thread

        with self.assertRaises(garmin_gnx375.plugin.PluginFail):
            pl.stop()

        thread.join.assert_called_once_with(2.0)


if __name__ == "__main__":
    unittest.main()
