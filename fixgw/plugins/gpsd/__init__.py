#!/usr/bin/env python

#  Copyright (c) 2024 Janne Mäntyharju
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

#  This plugin pulls the location information from GPSD

import threading
from collections import OrderedDict

import gpsd2
import time
import fixgw.plugin as plugin


class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging

    def run(self):
        try:
            gpsd2.connect()
        except:
            self.parent.log.error("Can't connect to gpsd")
            return
        
        while not self.getout:
            p = None
            try:
                p = gpsd2.get_current()
            except UserWarning as e:
                self.parent.log.warning(f"gpsd warning: {e}")
                time.sleep(5)
                continue

            self.parent.db_write("GPS_SATS_VISIBLE", p.sats)
            self.parent.db_write("GPS_FIX_TYPE", p.mode)

            if p.mode >=2:
                self.parent.db_write("LAT", p.lat)
                self.parent.db_write("LONG", p.lon)
                self.parent.db_write("TRACK", p.track)
                self.parent.db_write("GS", p.hspeed * 1.94384) # m/s to knots
                self.parent.db_write("GPS_ACCURACY_HORIZ", p.error["x"] * 3.28084)
            if p.mode >=3:
                self.parent.db_write("GPS_ELLIPSOID_ALT", p.alt * 3.28084) # m to ft
                self.parent.db_write("GPS_ACCURACY_VERTICAL", p.error["v"] * 3.28084)
                self.parent.db_write("GPS_ACCURACY_SPEED", p.error["s"] * 1.94384)
        time.sleep(0.2)
                            
    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self)
        self.status = OrderedDict()

    def run(self):
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(1.0)
        if self.thread.is_alive():
            raise plugin.PluginFail

    def get_status(self):
        return self.status
