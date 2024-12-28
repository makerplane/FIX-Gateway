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

#  Reads data from Dynon D10/D100 serial output stream

import threading
from collections import OrderedDict

import serial
import fixgw.plugin as plugin


class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self._buffer = bytearray()
        self._c = None
        self._vario_values = []

    def run(self):
        self._c = serial.Serial(self.parent.config['port'],
                                baudrate=115200,
                                timeout=0.5,)
        while not self.getout:
            try:
                s = self._c.read(self._c.in_waiting)
            except serial.SerialException:
                self.parent.log.error("Serial port error")

            for c in s:
                if c == 0x0A:  # message end
                    message = self._buffer
                    self._buffer = bytearray()
                    self._parse(message)
                else:
                    self._buffer.extend(c.to_bytes())

    def stop(self):
        self.getout = True

    def _parse(self, message):
        if len(message) != 52:
            self.parent.log.warning("Incorrect data length")
            return

        status = int(message[41:47], 16) & 1
        
        pitch = int(message[8:12]) / 10.0     
        self.parent.db_write("PITCH", pitch)
        
        roll = int(message[12:17]) / 10.0     
        self.parent.db_write("ROLL", roll)
        
        yaw = int(message[17:20]) 
        self.parent.db_write("YAW", yaw)

        # 1/10 m/s to knots
        speed = round(int(message[20:24]) * 0.194384)          
        self.parent.db_write("TAS", speed)
        
        alt = round(int(message[24:29]) * 3.28084)  # meters to feet

        if status == 0:
            self.parent.db_write("ALT", alt)
            self.parent.db_write("TALT", alt)
            
            turn_rate = int(message[29:33]) / 10
            self.parent.db_write("ROT", turn_rate)
        else:
            self.parent.db_write("PALT", alt)

            vs = int(message[29:33]) / 10 * 60
            
            self._vario_values.append(vs)
            if len(self._vario_values) > 128:
                self._vario_values.pop(0)
            if len(self._vario_values):
                vs = round(sum(self._vario_values) / len(self._vario_values))
                
            self.parent.db_write("VS", vs)

        alat = int(message[33:36]) / 100
        self.parent.db_write("ALAT", alat)


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
