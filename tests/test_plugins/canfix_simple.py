#  Copyright (c) 2018 Phil Birkelbach
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

# This plugin is used by the testing system to inject CAN functionality
# using the python-can 'virtual' interface.  This way we don't need to have
# any 'real' CAN interfaces up and running

import threading
import os
import time
import traceback
import can
import canfix

import fixgw.plugin as plugin



# A simple thread that listens on the queue and writes whatever it finds there
# to the fifo.
class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()

        self.getout = False
        self.parent = parent


    def run(self):
        try:
            p = canfix.Parameter()
            p.name = "Indicated Airspeed"
            p.value = 112.4
            self.parent.bus.send(p.getMessage())
            time.sleep(0.01)
            x = self.parent.db_read("IAS")
            if(x[0] != 112.4):
                raise Exception("{} != {}".format(x[0], 112.4))

            # Check the min and max bounds checs
            p = canfix.Parameter()
            p.name = "Roll Angle"
            tests = [(0.0,     0.0),
                     (-180.0, -180.0),
                     (-180.1, -180.0),
                     (0.0,     0,0),
                     (180.0,   180.0),
                     (180.1,   180.0)]
            for test in tests:
                p.value = test[0]
                self.parent.bus.send(p.getMessage())
                time.sleep(0.01)
                x = self.parent.db_read("ROLL")
                if(x[0] != test[1]):
                    raise Exception("{} != {}".format(x[0], test[1]))

            
        except Exception as e:
            traceback.print_exc()
            os._exit(-1)

        self.parent.quit()


    def stop(self):
        self.getout = True
        self.join()

# This plugin consists of 5 threads.  One for dealing with the queue, three
# for dealing with incoming CAN messages and one for dealing with outgoing
# CAN messages.
class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.interface = config['interface']
        self.channel = config['channel']
        self.bus = can.Bus(self.channel, bustype = self.interface)

    def run(self):
        self.thread = MainThread(self)
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(1.0)
        if self.thread.is_alive():
            raise plugin.PluginFail


    def get_status(self):
        pass
