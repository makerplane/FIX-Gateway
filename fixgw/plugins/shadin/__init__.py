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

#  Plugin for Shadin protocol. Currently only fuel related items are supported
#  Fdatasystems FC-10 fuel computer was used for testing

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
        self._c = None

    def run(self):
        try:
            self._c = serial.Serial(self.parent.config['port'],
                                    self.parent.config['baud'],
                                    timeout=0.5,)
        except serial.serialutil.SerialException:
            self.parent.log.error(f"Could not open port: {self.parent.config['port']}")
            return
        
        while not self.getout:
            try:
                self._parse(self._c.read_until())
            except serial.SerialException:
                self.parent.log.error("Serial port error")

    def stop(self):
        self.getout = True

    def _parse(self, message):
        if not len(message):
            return
        
        message = message.decode('ASCII')
        
        if not message.endswith('\n'):
            self.parent.log.debug("Incomplete message received")
            return
        
        index = message.find('Z')

        if index != -1:
            message = message[index:]
        else:
            self.parent.log.debug("Beginning of message was not found")

        if message.startswith("ZM"):    # Fuel flow right
            if "FUELF2" not in self.parent.db_list():
                # Second engine not in config
                return
            
            try:
                fuel_flow = int(message[2:])
            except ValueError:
                self.parent.log.error(f"Bad data received: {message}")
                return
            self.parent.db_write("FUELF2", fuel_flow / 0.1)
        elif message.startswith("ZO"):    # Fuel flow left
            try:
                fuel_flow = int(message[2:])
            except ValueError:
                self.parent.log.error(f"Bad data received: {message}")
                return
            self.parent.db_write("FUELF1", fuel_flow / 0.1)
        elif message.startswith("ZR"):    # Fuel remaining
            try:
                fuel_remaining = float(message[2:])
            except ValueError:
                self.parent.log.error(f"Bad data received: {message}")
                return
            self.parent.db_write("FUELQT", fuel_remaining)


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