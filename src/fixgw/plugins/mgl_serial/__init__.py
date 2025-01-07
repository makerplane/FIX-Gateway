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

#  Plugin for MGL Serial protocol

import threading
import struct
from collections import OrderedDict

import serial
import fixgw.plugin as plugin


class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False  # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self._c = None
        self.engine = parent.config["engine_no"]

    def run(self):
        try:
            self._c = serial.Serial(
                self.parent.config["port"],
                self.parent.config["baud"],
                timeout=0.5,
            )
        except serial.serialutil.SerialException:
            self.parent.log.error(f"Could not open port: {self.parent.config['port']}")
            return

        while not self.getout:
            try:
                message = self._c.read_until(b"\x03")
                self._parse(message)
            except serial.SerialException:
                self.parent.log.error("Serial port error")

    def stop(self):
        self.getout = True

    def _parse(self, message):
        if len(message) != 16:
            return

        if not message.endswith(b"\x03"):
            self.parent.log.debug("Incomplete message received")
            return

        index = message.find(0x02)

        if index != -1:
            message = message[index:]
        else:
            self.parent.log.debug("Beginning of message was not found")

        data = struct.unpack(">BBBBBBhhhhBB", message)

        data[0]  # start of message
        data[1]  # address
        if data[2] != 8:  # message type (should be 8 for TP-3)
            self.parent.log.warning("Unsupported message")
            return

        data[3]  # message lenght
        channels = [{}, {}, {}, {}]
        channels[3]["type"] = (data[4] & 0b11110000) >> 4  # CH4 type
        channels[2]["type"] = data[4] & 0b00001111  # CH3 type
        channels[1]["type"] = (data[5] & 0b11110000) >> 4  # CH2 type
        channels[0]["type"] = data[5] & 0b00001111  # CH1 type
        channels[0]["value"] = data[6]  # ch1 val
        channels[1]["value"] = data[7]  # ch2 val
        channels[2]["value"] = data[8]  # ch3 val
        channels[3]["value"] = data[9]  # ch4 val
        data[10]  # checksum
        data[11]  # end

        for c in channels:
            db_key = ""
            if c["type"] == 0:  # not in use
                continue
            elif c["type"] == 1:  # pressure
                db_key = f"OILP{self.engine}"
                c["value"] /= 10
            elif c["type"] == 2:  # temperature
                db_key = f"OILT{self.engine}"
            elif c["type"] == 3:  # current
                db_key = f"CURRNT"
                c["value"] /= 10
            elif c["type"] == 4:  # fuel level
                db_key = f"FUELQT"
            elif c["type"] == 5:  # voltage
                db_key = f"VOLT"
                c["value"] /= 10

            print(db_key, c["value"])
            self.parent.db_write(db_key, c["value"])


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
