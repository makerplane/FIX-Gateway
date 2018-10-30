#!/usr/bin/env python

#  Copyright (c) 2014 Phil Birkelbach
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

import threading
import time
import random
import string
import fixgw.plugin as plugin

random.seed(123456)


class TestThread(threading.Thread):
    def __init__(self, parent):
        super(TestThread, self).__init__()
        self.parent = parent
        self.getout = False

    def run(self):
        starttime = time.time()
        self.parent.log.debug("Starting Thread")
        while(True):
            if self.getout: break
            low = self.parent.config["low"]
            high = self.parent.config["high"]
            x = (random.random() * (high - low)) + low
            self.parent.db_write(self.parent.config["key"], x)


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.t = TestThread(self)

    def run(self):
        self.t.start()

    def stop(self):
        self.t.getout = True
        self.t.join()  # Wait for the thread to stop
