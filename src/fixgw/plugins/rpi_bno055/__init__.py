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
#  USA.import plugin

#  This file serves as a starting point for a plugin.  This is a Thread based
#  plugin where the main Plugin class creates a thread and starts the thread
#  when the plugin's run() function is called.

import threading
import time
from Adafruit_BNO055 import BNO055
from collections import OrderedDict
import fixgw.plugin as plugin


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
        self.sleep_time = 0.005  # 3 x .005 give +/-60Hz refresh rate
        self.bno = BNO055.BNO055(serial_port="/dev/ttyAMA0", rst=18)
        if not self.bno.begin():
            self.parent.db_write(
                "ORISYSW", 0
            )  # TODO put 0 to orientation system status but a fail flag are need here.
            raise RuntimeError("Failed to initialize BNO055! Is the sensor connected?")

    def run(self):
        while True:
            if self.getout:
                break
            time.sleep(self.sleep_time)
            self.count += 1
            heading, roll, pitch = self.bno.read_euler()
            if pitch >= 90:
                pdiff = pitch - 90
                pitch = 90 - pdiff
                if roll > 0:
                    roll = -(roll - 180)
                else:
                    roll = -(roll + 180)
            else:
                mpdiff = pitch + 90
                pitch = -(90 + mpdiff)
                if roll > 0:
                    roll = -(roll - 180)
                else:
                    roll = -(roll + 180)
            if heading >= 180:
                heading = heading - 180
            else:
                heading = heading + 180
            try:
                pitchset = self.parent.db_read("PITCHSET")
                pitch = pitch + int(pitchset[0])
            except:
                pass
            self.parent.db_write("HEAD", heading)
            self.parent.db_write("ROLL", roll)
            self.parent.db_write("PITCH", pitch)
            time.sleep(self.sleep_time)
            x, y, z = self.bno.read_accelerometer()
            x = -x / 60
            y = -y / 60
            z = -z / 60
            self.parent.db_write("ALAT", x)
            self.parent.db_write("ANORM", y)
            self.parent.db_write("ALONG", z)
            time.sleep(self.sleep_time)
            sys, gyro, accel, mag = (
                self.bno.get_calibration_status()
            )  # 0 to 3 calibration status, 3 is full calibrated
            self.parent.db_write("ORISYSW", sys)
            self.parent.db_write("GYROW", gyro)
            self.parent.db_write("ACCELW", accel)
            self.parent.db_write("MAGW", mag)
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
