#!/usr/bin/env python

#  Copyright (c) 2019 Makerplane
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

#  Reads data from GRT EIS serial output stream

import threading
import time
from collections import OrderedDict
import fixgw.plugin as plugin
import serial
import struct

class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self.ser = serial.Serial('/dev/ttyUSB0', 9200, timeout=1)

    def run(self):
        while not self.getout:
            s = self.ser.read_until(bytes.fromhex('fefffe'), size=100)
            if(len(s)==48):
                tach1 = int.from_bytes(s[0:2], "big")
                cht1 = int((int.from_bytes(s[2:4], "big") - 32) * 5.0/9)
                cht2 = int((int.from_bytes(s[4:6], "big") - 32) * 5.0/9)
                egt1 = int((int.from_bytes(s[6:8], "big") - 32) * 5.0/9)
                egt2 = int((int.from_bytes(s[8:10], "big") - 32) * 5.0/9)
                airspeed = int.from_bytes(s[10:12], "big") #guess
                altitude = int.from_bytes(s[12:14], "big")
                volts = int.from_bytes(s[14:16], "big")/10.0
                fuel_flow = int.from_bytes(s[16:18], "big")
                internal_temp = (s[18] - 32) * 5.0/9
                vsi = s[19] #guess
                oat = s[20]
                if (oat > 127):
                    oat -= 256
                oat = int((oat - 32) * 5.0/9)
                coolant = int((int.from_bytes(s[21:23], "big") - 32) * 5.0/9)
                oilt = int((int.from_bytes(s[23:25], "big") - 32) * 5.0/9)
                oilp = s[25]
                aux1 = int.from_bytes(s[26:28], "big")
                aux2 = int.from_bytes(s[28:30], "big")
                engine_time = int.from_bytes(s[30:32], "big")/10.0
                fuel_qty = int.from_bytes(s[32:34], "big") #guess
                hours = s[34]
                minutes = s[35]
                seconds = s[36]
                endurance = int.from_bytes(s[37:39], "big") #guess
                baro = int.from_bytes(s[39:41], "big")
                tach2 = int.from_bytes(s[41:44], "big") #guess
                checksum = s[44]

                self.parent.db_write("TACH1", tach1)
                self.parent.db_write("CHT11", cht1)
                self.parent.db_write("CHT12", cht2)
                self.parent.db_write("EGT11", egt1)
                self.parent.db_write("EGT12", egt2)
                self.parent.db_write("VOLT", volts)
                self.parent.db_write("HOBBS1", engine_time)
                self.parent.db_write("OILP1", oilp)
                self.parent.db_write("OILT1", oilt)
                self.parent.db_write("FUELQ1", fuel_qty)
                self.parent.db_write("BARO", baro)
                self.parent.db_write("OAT", oat)
                self.parent.db_write("ALT", altitude)

        self.running = False

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
