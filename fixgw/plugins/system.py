#!/usr/bin/env python

#  Copyright (c) 2019 Phil Birkelbach
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
from collections import OrderedDict
import fixgw.plugin as plugin

class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self.functions = [] # List of closures to call each time through the loop

    def run(self):
        while True:
            if self.getout:
                break
            time.sleep(1.0)
            for func in self.functions:
                func()
        self.running = False

    def stop(self):
        self.getout = True

class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self)
        self.status = OrderedDict()

    def run(self):
        if "time" in self.config:
            if self.config["time"]["enable"]:
                f = timeFunctionFactory(self)
                self.thread.functions.append(f)
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(1.0)
        if self.thread.is_alive():
            raise plugin.PluginFail

    def get_status(self):
        return self.status


def timeFunctionFactory(plugin):
    config = plugin.config["time"]
    keys = config["keys"]
    if "gmt_string" in keys and keys["gmt_string"] is not None:
        gmt_string = plugin.db_get_item(keys["gmt_string"])
    else:
        gmt_string = None
    if "gmt_format" in config and config["gmt_format"] is not None:
        gmt_format = config["gmt_format"]
    else:
        gmt_format = "%H:%M:%SZ"
    if "gmt_hours" in keys and keys["gmt_hours"] is not None:
        gmt_hours = plugin.db_get_item(keys["gmt_hours"])
    else:
        gmt_hours = None
    if "gmt_minutes" in keys and keys["gmt_minutes"] is not None:
        gmt_minutes = plugin.db_get_item(keys["gmt_minutes"])
    else:
        gmt_minutes = None
    if "gmt_seconds" in keys and keys["gmt_seconds"] is not None:
        gmt_seconds = plugin.db_get_item(keys["gmt_seconds"])
    else:
        gmt_seconds = None

    if "local_string" in keys and keys["local_string"] is not None:
        local_string = plugin.db_get_item(keys["local_string"])
    else:
        local_string = None
    if "local_format" in config and config["local_format"] is not None:
        local_format = config["local_format"]
    else:
        local_format = "%H:%M:%SZ"
    if "local_hours" in keys and keys["local_hours"] is not None:
        local_hours = plugin.db_get_item(keys["local_hours"])
    else:
        local_hours = None
    if "local_minutes" in keys and keys["local_minutes"] is not None:
        local_minutes = plugin.db_get_item(keys["local_minutes"])
    else:
        local_minutes = None
    if "local_seconds" in keys and keys["local_seconds"] is not None:
        local_seconds = plugin.db_get_item(keys["local_seconds"])
    else:
        local_seconds = None

    def func():
        gmt = time.gmtime()
        lt = time.localtime()
        if gmt_string:
            gmt_string.value = time.strftime(gmt_format, gmt)
        if gmt_hours:
            gmt_hours.value = gmt.tm_hour
        if gmt_minutes:
            gmt_minutes.value = gmt.tm_min
        if gmt_seconds:
            gmt_seconds.value = gmt.tm_sec
        if local_string:
            local_string.value = time.strftime(local_format, lt)
        if local_hours:
            local_hours.value = lt.tm_hour
        if local_minutes:
            local_minutes.value = lt.tm_min
        if local_seconds:
            local_seconds.value = lt.tm_sec

    return func
