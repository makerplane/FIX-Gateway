#  Copyright (c) 2013 Phil Birkelbach
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

# This is the CAN-FIX plugin. CAN-FIX is a CANBus based protocol for
# aircraft data.

import threading
import plugin

import can
import canfix

class Parameter(object):
    def __init__(self, name = None, value = None):
        self.name = name
        self.value = value
        self.failed = False
        self.quaility = False
        self.annunciate = False

class MainThread(threading.Thread):
    def __init__(self, parent, config):
        super(MainThread, self).__init__()
        self.interface = config['interface']
        self.channel = config['channel']
        self.device = int(config['device'])

        self.getout = False
        self.parent = parent
        self.log = parent.log
        self.bus = can.interface.Bus(self.channel, bustype = self.interface)
        self._parameterCallback = None

    def setParameterCallback(self, function):
        if callable(function):
            self._parameterCallback = function
        else:
            raise ValueError("Argument is supposed to be callable")

    def run(self):
        while(True):
            try:
                msg = self.bus.recv(1.0)
                if msg:
                    print(msg)
                    # Once we get a frame we parse it through canfix then
                    # if the frame represents a CAN-FIX parameter then we make
                    # a generic FIX parameter and send that to the callback
                    try:
                        cfobj = canfix.parseMessage(msg)
                    except ValueError as e:
                        self.log.warning(e)
                    else:
                        self.log.debug("Fix Thread parseFrame() returned, {0}".format(cfobj))
                        if isinstance(cfobj, canfix.Parameter):
                            p = Parameter(cfobj.name, cfobj.value)
                            if self._parameterCallback:
                                self._parameterCallback(cfobj)
                        else:
                            print(cfobj)
                #     # TODO increment frame counter
                #     # TODO increment error counter
            finally:
                if(self.getout):
                    break
        self.log.debug("End of the CAN-FIX Thread")
        #self.can.disconnect()

    def stop(self):
        self.getout = True
        self.join()


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self, config)

    def run(self):
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(1.0)
        if self.thread.is_alive():
            raise plugin.PluginFail

    def get_status(self):
        return OrderedDict({"Count":self.thread.count})
