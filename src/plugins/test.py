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
import database
import random
import string

class TestThread(threading.Thread):
    def __init__(self):
        super(TestThread, self).__init__()
        random.seed(123456)
        self.keylist = []
        for each in range(100):
            s = ""
            for i in range(5):
                s = s + random.choice(string.ascii_uppercase + string.digits)
            self.keylist.append(s)
        
    def run(self):
        starttime = time.time()
        print "T1 Starting Thread"
        for each in range(100000):
            key = random.choice(self.keylist)
            if random.choice((True, False)):
                x = random.random()
                database.write(key, x)
                print "T1 WRITE " + key + " " + str(x)
            else:
                x = database.read(key)
                print "T1 READ  " + key + " " + str(x)
        print "T1 Stopping Thread " + str(time.time() - starttime)
        

class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name,config)
    
    def run(self):
        super(Plugin, self).run()
        self.t = TestThread()
        self.t.start()
        
    def stop(self):
        super(Plugin, self).stop()
        self.t.join() # Wait for the thread to stop
