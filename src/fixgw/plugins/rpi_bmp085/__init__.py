#!/usr/bin/env python

#  Copyright (c) 2017 Jean-Manuel Gagnon
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
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
#  USA.import fixgw.plugin as plugin

#  This file serves as a starting point for a plugin.  This is a Thread based
#  plugin where the main Plugin class creates a thread and starts the thread
#  when the plugin's run() function is called.

import fixgw.plugin as plugin
import threading
import time
import Adafruit_BMP.BMP085 as BMP085
from collections import OrderedDict


class MainThread(threading.Thread):
    def __init__(self, parent):
        """The calling object should pass itself as the parent.
        This gives the thread all the plugin goodies that the
        parent has."""
        super(MainThread, self).__init__()
        self.getout = False  # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self.count = 0
        self.tkey = (
            parent.config["tkey"]
            if ("tkey" in parent.config) and parent.config["tkey"]
            else "CAT"
        )
        self.pkey = (
            parent.config["pkey"]
            if ("pkey" in parent.config) and parent.config["pkey"]
            else "AIRPRESS"
        )
        self.alt = 0
        self.sleep_time = 0.03  # 3 x .03 give +/-10Hz refresh rate
        self.smooted = 0.8  # smooth altitude 0 to 1 , 1 is very smooth.
        self.sensor = BMP085.BMP085(mode=BMP085.BMP085_ULTRAHIGHRES)

    def run(self):
        while True:
            if self.getout:
                break
            time.sleep(self.sleep_time)
            self.count += 1
            stdbaro = 29.92
            currentbaro = self.parent.db_read("BARO")
            init_alt = round((float(self.sensor.read_altitude()) * 3.28083989502))
            self.alt = float(
                (self.alt * self.smooted) + (1.0 - self.smooted) * (init_alt)
            )
            altitude = ((float(currentbaro[0]) - stdbaro) * 1000) + self.alt
            self.parent.db_write("ALT", altitude)
            time.sleep(self.sleep_time)
            cat = float(self.sensor.read_temperature())
            self.parent.db_write(self.tkey, cat)
            time.sleep(self.sleep_time)
            airpress = int(self.sensor.read_pressure())
            self.parent.db_write(self.pkey, airpress)
        self.running = False

    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    """All plugins for FIX Gateway should implement at least the class
    named 'Plugin.'  They should be derived from the base class in
    the plugin module.

    The run and stop methods of the plugin should be overridden but the
    base module functions should be called first."""

    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self)

    def run(self):
        """The run method should return immediately.  The main routine will
        block when calling this function.  If the plugin is simply a collection
        of callback functions, those can be setup here and no thread will be
        necessary"""
        super(Plugin, self).run()
        self.thread.start()

    def stop(self):
        """The stop method should not return until the plugin has completely
        stopped.  This generally means a .join() on a thread.  It should
        also undo any callbacks that were set up in the run() method"""
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(1.0)
        if self.thread.is_alive():
            raise plugin.PluginFail
        super(Plugin, self).stop()

    def get_status(self):
        """The get_status method should return a dict or OrderedDict that
        is basically a key/value pair of statistics"""
        return OrderedDict({"Count": self.thread.count})
