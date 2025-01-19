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

#  Checks current power source and battery state from Strom Pi 3 module

import threading
from collections import OrderedDict

import time
import struct
import fixgw.plugin as plugin
import smbus
import RPi.GPIO as GPIO

# GPIO26 is for x728 V2.1/V2.2/V2.3, GPIO13 is for X728 v1.2/v1.3/V2.0
GPIO_PORT     = 26
I2C_ADDR      = 0x36
PLD_PIN = 6

class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GPIO_PORT, GPIO.OUT)
        GPIO.setup(PLD_PIN, GPIO.IN)
        GPIO.setwarnings(False)
        self._bus = smbus.SMBus(1)

    def _readVoltage(self):
        address = I2C_ADDR
        read = self._bus.read_word_data(address, 2)
        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        voltage = swapped * 1.25 /1000/16
        return voltage

    def _readCapacity(self):
        address = I2C_ADDR
        read = self._bus.read_word_data(address, 4)
        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        capacity = swapped/256
        if capacity > 100:
            capacity = 100
        return capacity

    def run(self):
        power_fail_timer = None
        while not self.getout:
            if GPIO.input(PLD_PIN): # We are running on battery
                self.parent.db_write("POWER_FAIL", True)
                if not power_fail_timer:
                    power_fail_timer = time.time()
                    self.parent.log.warning("Power has failed")
                
                if power_fail_timer and "shutdown_after" in self.parent.config:
                    if time.time() > power_fail_timer + (self.parent.config['shutdown_after'] * 60):
                        GPIO.output(GPIO_PORT, GPIO.HIGH)
                        time.sleep(3)
                        GPIO.output(GPIO_PORT, GPIO.LOW)

            else:
                self.parent.db_write("POWER_FAIL", False)
                if power_fail_timer:
                    power_fail_timer = None
                    self.parent.log.warning("Power has been restored")

            self.parent.db_write("BAT_REMAINING", self._readCapacity())
            self.parent.db_write("BAT_VOLTAGE", self._readVoltage())

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