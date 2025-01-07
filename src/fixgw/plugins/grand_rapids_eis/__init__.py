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


class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False  # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        serial_port = self.parent.config["port"]
        self.model = self.parent.config["model"]
        if self.model != 2004 and self.model != 4000 and self.model != 6000:
            print("Unsupported EIS model")
        else:
            print("EIS model: " + str(self.model))
        self.ser = serial.Serial(serial_port, 9600, timeout=1)

    def run(self):
        while not self.getout:
            if self.model == 2004:
                s = self.ser.read_until(bytes.fromhex("fefffe"), size=100)
                if len(s) != 48:
                    print("bad frame")
                    continue
                tach1 = int.from_bytes(s[0:2], "big")
                cht1 = int((int.from_bytes(s[2:4], "big") - 32) * 5.0 / 9)
                cht2 = int((int.from_bytes(s[4:6], "big") - 32) * 5.0 / 9)
                egt1 = int((int.from_bytes(s[6:8], "big") - 32) * 5.0 / 9)
                egt2 = int((int.from_bytes(s[8:10], "big") - 32) * 5.0 / 9)
                airspeed = int.from_bytes(s[10:12], "big")  # guess
                altitude = int.from_bytes(s[12:14], "big")
                volts = int.from_bytes(s[14:16], "big") / 10.0
                fuel_flow = int.from_bytes(s[16:18], "big")
                internal_temp = (s[18] - 32) * 5.0 / 9
                vsi = s[19]  # guess
                oat = s[20]
                if oat > 127:
                    oat -= 256
                oat = int((oat - 32) * 5.0 / 9)
                coolant = int((int.from_bytes(s[21:23], "big") - 32) * 5.0 / 9)
                oilt = int((int.from_bytes(s[23:25], "big") - 32) * 5.0 / 9)
                oilp = s[25]
                aux1 = int.from_bytes(s[26:28], "big")
                aux2 = int.from_bytes(s[28:30], "big")
                engine_time = int.from_bytes(s[30:32], "big") / 10.0
                fuel_qty = int.from_bytes(s[32:34], "big")  # guess
                hours = s[34]
                minutes = s[35]
                seconds = s[36]
                endurance = int.from_bytes(s[37:39], "big")  # guess
                baro = int.from_bytes(s[39:41], "big")
                tach2 = int.from_bytes(s[41:44], "big")  # guess
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
                self.parent.db_write("H2OT1", coolant)

            elif self.model == 4000 or self.model == 6000:
                s = self.ser.read_until(bytes.fromhex("fefffe"), size=150)
                if len(s) != 73:
                    print("bad frame")
                    continue

                tach1 = int.from_bytes(s[0:2], "big")
                cht1 = int((int.from_bytes(s[2:4], "big") - 32) * 5.0 / 9)
                cht2 = int((int.from_bytes(s[4:6], "big") - 32) * 5.0 / 9)
                cht3 = int((int.from_bytes(s[6:8], "big") - 32) * 5.0 / 9)
                cht4 = int((int.from_bytes(s[8:10], "big") - 32) * 5.0 / 9)
                cht5 = int((int.from_bytes(s[10:12], "big") - 32) * 5.0 / 9)
                cht6 = int((int.from_bytes(s[12:14], "big") - 32) * 5.0 / 9)
                egt1 = int((int.from_bytes(s[14:16], "big") - 32) * 5.0 / 9)
                egt2 = int((int.from_bytes(s[16:18], "big") - 32) * 5.0 / 9)
                egt3 = int((int.from_bytes(s[18:20], "big") - 32) * 5.0 / 9)
                egt4 = int((int.from_bytes(s[20:22], "big") - 32) * 5.0 / 9)
                egt5 = int((int.from_bytes(s[22:24], "big") - 32) * 5.0 / 9)
                egt6 = int((int.from_bytes(s[24:26], "big") - 32) * 5.0 / 9)
                aux5 = int.from_bytes(s[26:28], "big")
                aux6 = int.from_bytes(s[28:30], "big")
                airspeed = int.from_bytes(s[30:32], "big")
                altitude = int.from_bytes(s[32:34], "big")
                volts = int.from_bytes(s[34:36], "big") / 10.0
                fuel_flow = int.from_bytes(s[36:38], "big")
                internal_temp = (s[38] - 32) * 5.0 / 9
                carb_temp = s[39]
                vsi = s[40]
                oat = s[41]
                if oat > 127:
                    oat -= 256
                oat = int((oat - 32) * 5.0 / 9)
                oilt = int((int.from_bytes(s[42:44], "big") - 32) * 5.0 / 9)
                oilp = s[44]
                aux1 = int.from_bytes(s[45:47], "big")
                aux2 = int.from_bytes(s[47:49], "big")
                aux3 = int.from_bytes(s[49:51], "big")
                aux4 = int.from_bytes(s[51:53], "big")
                coolant = int((int.from_bytes(s[53:55], "big") - 32) * 5.0 / 9)
                engine_time = int.from_bytes(s[55:57], "big") / 10.0
                fuel_qty = int.from_bytes(s[57:59], "big")
                hours = s[59]
                minutes = s[60]
                seconds = s[61]
                endurance = int.from_bytes(s[62:64], "big")
                baro = int.from_bytes(s[64:66], "big")
                tach2 = int.from_bytes(s[66:68], "big")
                # 68 spare
                checksum = s[69]

                self.parent.db_write("TACH1", tach1)
                self.parent.db_write("CHT11", cht1)
                self.parent.db_write("CHT12", cht2)
                self.parent.db_write("CHT13", cht3)
                self.parent.db_write("CHT14", cht4)
                self.parent.db_write("CHT15", cht5)
                self.parent.db_write("CHT16", cht6)
                self.parent.db_write("EGT11", egt1)
                self.parent.db_write("EGT12", egt2)
                self.parent.db_write("EGT13", egt3)
                self.parent.db_write("EGT14", egt4)
                self.parent.db_write("EGT15", egt5)
                self.parent.db_write("EGT16", egt6)
                self.parent.db_write("VOLT", volts)
                self.parent.db_write("HOBBS1", engine_time)
                self.parent.db_write("OILP1", oilp)
                self.parent.db_write("OILT1", oilt)
                self.parent.db_write("FUELQ1", fuel_qty)
                self.parent.db_write("BARO", baro)
                self.parent.db_write("OAT", oat)
                self.parent.db_write("ALT", altitude)
                self.parent.db_write("H2OT1", coolant)

        self.running = False

    def stop(self):
        self.getout = True
        self.ser.close()


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
