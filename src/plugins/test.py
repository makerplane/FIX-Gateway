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

import plugin
import threading
import time
import random
import string

random.seed(123456)


class TestThread(threading.Thread):
    def __init__(self, parent):
        super(TestThread, self).__init__()
        self.parent = parent

    def run(self):
        starttime = time.time()
        self.parent.log.debug("Starting Thread")
        for each in range(100000):
            key = random.choice(self.parent.keylist)
            if random.choice((True, False)):
                x = random.random()
                self.parent.db_write(key, x)
                self.parent.log.debug("WRITE " + key + " " + str(x))
            else:
                x = self.parent.db_read(key)
                self.parent.log.debug("READ  " + key + " " + str(x))
        self.parent.log.debug("Stopping Thread " + str(time.time() - starttime))


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.t = TestThread(self)
        self.keylist = []
        for each in range(100):
            s = ""
            for i in range(5):
                s = s + random.choice(string.ascii_uppercase + string.digits)
            self.keylist.append(s)

    def run(self):
        super(Plugin, self).run()
        self.t.start()

    def stop(self):
        self.t.join()  # Wait for the thread to stop
        super(Plugin, self).stop()
