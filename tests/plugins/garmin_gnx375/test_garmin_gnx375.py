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
from fixgw.plugins.garmin_gnx375 import MainThread

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


if __name__ == "__main__":
    unittest.main()
