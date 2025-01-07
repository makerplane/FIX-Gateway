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

import threading
import time
import Adafruit_GPIO.SPI as SPI
import Adafruit_MCP3008
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
        SPI_PORT = 0
        SPI_DEVICE = 0
        self.CLK = (
            int(parent.config["clk"])
            if ("clk" in parent.config) and parent.config["clk"]
            else 18
        )
        self.MISO = (
            int(parent.config["miso"])
            if ("miso" in parent.config) and parent.config["miso"]
            else 23
        )
        self.MOSI = (
            int(parent.config["mosi"])
            if ("mosi" in parent.config) and parent.config["mosi"]
            else 24
        )
        self.CS = (
            int(parent.config["cs"])
            if ("cs" in parent.config) and parent.config["cs"]
            else 25
        )
        self.VKEY1 = (
            parent.config["vkey1"]
            if ("vkey1" in parent.config) and parent.config["vkey1"]
            else "ANLG1"
        )
        self.VKEY2 = (
            parent.config["vkey2"]
            if ("vkey2" in parent.config) and parent.config["vkey2"]
            else "ANLG2"
        )
        self.VKEY3 = (
            parent.config["vkey3"]
            if ("vkey3" in parent.config) and parent.config["vkey3"]
            else "ANLG3"
        )
        self.VKEY4 = (
            parent.config["vkey4"]
            if ("vkey4" in parent.config) and parent.config["vkey4"]
            else "ANLG4"
        )
        self.VKEY5 = (
            parent.config["vkey5"]
            if ("vkey5" in parent.config) and parent.config["vkey5"]
            else "ANLG5"
        )
        self.VKEY6 = (
            parent.config["vkey6"]
            if ("vkey6" in parent.config) and parent.config["vkey6"]
            else "ANLG6"
        )
        self.VKEY7 = (
            parent.config["vkey7"]
            if ("vkey7" in parent.config) and parent.config["vkey7"]
            else "ANLG7"
        )
        self.VKEY8 = (
            parent.config["vkey8"]
            if ("vkey8" in parent.config) and parent.config["vkey8"]
            else "ANLG8"
        )
        self.HARDW = (
            parent.config["hardw"]
            if ("hardw" in parent.config) and parent.config["hardw"]
            else "False"
        )
        if self.HARDW == True:
            self.mcp = Adafruit_MCP3008.MCP3008(spi=SPI.SpiDev(SPI_PORT, SPI_DEVICE))
        else:
            self.mcp = Adafruit_MCP3008.MCP3008(
                clk=self.CLK, cs=self.CS, miso=self.MISO, mosi=self.MOSI
            )

    def run(self):
        while True:
            if self.getout:
                break
            time.sleep(1)
            self.count += 1
            value1 = self.mcp.read_adc(0)
            value2 = self.mcp.read_adc(1)
            value3 = self.mcp.read_adc(2)
            value4 = self.mcp.read_adc(3)
            value5 = self.mcp.read_adc(4)
            value6 = self.mcp.read_adc(5)
            value7 = self.mcp.read_adc(6)
            value8 = self.mcp.read_adc(7)
            self.parent.db_write(self.VKEY1, value1)
            self.parent.db_write(self.VKEY2, value2)
            self.parent.db_write(self.VKEY3, value3)
            self.parent.db_write(self.VKEY4, value4)
            self.parent.db_write(self.VKEY5, value5)
            self.parent.db_write(self.VKEY6, value6)
            self.parent.db_write(self.VKEY7, value7)
            self.parent.db_write(self.VKEY8, value8)
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
