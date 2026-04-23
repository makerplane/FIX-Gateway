#!/usr/bin/env python

#  Copyright (c) 2026 Bill Mallard
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

"""FIX-Gateway plugin for the Garmin GNX 375 (and compatible Garmin GPS navigators).

Reads NMEA 0183 sentences from the GNX 375 RS-232 serial port (Aviation Output 1
format, 9600 8N1 by default) and writes navigation state into the FIX-Gateway
database.

GNX 375 serial port configuration (set via unit installer menu):
  RS-232/RS-422 Port 1 or Port 2 → "Aviation Output 1"
  Baud: 9600 (fixed for Aviation Output 1)

NMEA sentences consumed
-----------------------
  $GPRMC  position, ground speed, track
  $GPGGA  position, GPS altitude, fix quality
  $GPRMB  cross-track error (XTE), destination waypoint, range/bearing
  $GPAPB  XTE, heading-to-steer, bearing to destination

FIX-Gateway keys written
------------------------
  LAT                 latitude (deg, decimal)
  LONG                longitude (deg, decimal)
  GS                  ground speed (knots)
  TRACK               track over ground (deg true)
  GPS_ELLIPSOID_ALT   GPS ellipsoid altitude (feet)
  GPS_FIX_TYPE        GPS fix quality (0=none, 1=GPS, 2=DGPS/WAAS)
  XTRACK              signed cross-track error (nm); negative = left of track
  CDI                 scaled course deviation [-1.0, +1.0]
  COURSE              bearing to active destination waypoint (deg true)

Sign convention for XTRACK (matches FIX-Gateway compute.py xte function):
  Negative → aircraft is LEFT of desired course (need to steer right)
  Positive → aircraft is RIGHT of desired course (need to steer left)

In $GPRMB the steer-direction flag encodes this as:
  'L' (steer left to return) → aircraft is RIGHT of course → XTRACK positive
  'R' (steer right to return) → aircraft is LEFT of course  → XTRACK negative
"""

import threading
from collections import OrderedDict

import pynmea2
import serial
import fixgw.plugin as plugin


_DEFAULT_BAUD = 9600
_DEFAULT_CDI_FULL_SCALE_NM = 5.0  # enroute GPS full-scale; use 0.3 for approach


class MainThread(threading.Thread):
    def __init__(self, parent):
        super().__init__()
        self.daemon = True
        self.getout = False
        self.parent = parent
        self.log = parent.log
        self._serial = None

    def run(self):
        try:
            self._serial = serial.Serial(
                self.parent.config["port"],
                int(self.parent.config.get("baud", _DEFAULT_BAUD)),
                timeout=1.0,
            )
        except serial.SerialException as exc:
            self.log.error(f"garmin_gnx375: cannot open {self.parent.config['port']}: {exc}")
            return

        cdi_scale = float(self.parent.config.get("cdi_full_scale_nm", _DEFAULT_CDI_FULL_SCALE_NM))

        while not self.getout:
            try:
                raw = self._serial.readline()
            except serial.SerialException as exc:
                self.log.error(f"garmin_gnx375: serial read error: {exc}")
                break

            if not raw:
                continue

            try:
                line = raw.decode("ascii", errors="replace").strip()
            except Exception:
                continue

            try:
                msg = pynmea2.parse(line)
            except pynmea2.ParseError:
                continue

            try:
                self._dispatch(msg, cdi_scale)
            except Exception as exc:
                self.log.debug(f"garmin_gnx375: dispatch error on {line!r}: {exc}")

        if self._serial and self._serial.is_open:
            self._serial.close()

    def stop(self):
        self.getout = True

    # ------------------------------------------------------------------
    # Sentence handlers
    # ------------------------------------------------------------------

    def _dispatch(self, msg, cdi_scale):
        stype = msg.sentence_type
        if stype == "RMC":
            self._handle_rmc(msg)
        elif stype == "GGA":
            self._handle_gga(msg)
        elif stype == "RMB":
            self._handle_rmb(msg, cdi_scale)
        elif stype == "APB":
            self._handle_apb(msg)

    def _handle_rmc(self, msg):
        if msg.status != "A":
            return
        self.parent.db_write("LAT", msg.latitude)
        self.parent.db_write("LONG", msg.longitude)
        if msg.spd_over_grnd is not None:
            self.parent.db_write("GS", float(msg.spd_over_grnd))
        if msg.true_course is not None:
            self.parent.db_write("TRACK", float(msg.true_course))

    def _handle_gga(self, msg):
        qual = int(msg.gps_qual) if msg.gps_qual is not None else 0
        self.parent.db_write("GPS_FIX_TYPE", qual)
        if qual == 0:
            return
        self.parent.db_write("LAT", msg.latitude)
        self.parent.db_write("LONG", msg.longitude)
        if msg.altitude is not None:
            # GGA altitude is in meters above MSL; convert to feet
            alt_ft = float(msg.altitude) * 3.28084
            self.parent.db_write("GPS_ELLIPSOID_ALT", alt_ft)

    def _handle_rmb(self, msg, cdi_scale):
        if msg.status != "A":
            return
        if msg.cross_track_err is None or msg.dir_steer not in ("L", "R"):
            return
        xte_mag = float(msg.cross_track_err)
        # 'L' (steer left) = aircraft is RIGHT of track = positive XTRACK
        xtrack = xte_mag if msg.dir_steer == "L" else -xte_mag
        self.parent.db_write("XTRACK", xtrack)
        cdi = max(-1.0, min(1.0, -xtrack / cdi_scale))
        self.parent.db_write("CDI", cdi)

    def _handle_apb(self, msg):
        # Update COURSE from bearing-present-to-destination if available
        if msg.bearing_present_dest is not None:
            self.parent.db_write("COURSE", float(msg.bearing_present_dest))


class Plugin(plugin.PluginBase):
    def __init__(self, name, config, config_meta):
        super().__init__(name, config, config_meta)
        self.thread = MainThread(self)
        self.status = OrderedDict()

    def run(self):
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(2.0)
        if self.thread.is_alive():
            raise plugin.PluginFail

    def get_status(self):
        return self.status
