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

# Right now we aren't using this.  It proved too difficult to deal with..
# for now we are just using a plugin that runs all the tests internally

import threading
import os
import queue
import can

import fixgw.plugin as plugin

def msg2string(canmsg, bus):
    ds = ""
    for b in canmsg.data:
        ds = ds + "{0:02X}".format(b)
    return "{}:{:x}:{}\n".format(bus,canmsg.arbitration_id, ds)


def string2msg(s):
    msg = can.Message()
    msg.extended_id = False

    x = s.strip().split(':')
    msg.arbitration_id = int(x[1], 16)
    msg.dlc = int(len(x[2]) / 2)
    for n in range(0, len(x[2]), 2):
        msg.data.append(int(x[2][n:n+2], 16))
    return (int(x[0]), msg)

# The two fifo's that we use for communicating to the test system.
input_fifo = '/tmp/fixgw_canin.pipe'
output_fifo = '/tmp/fixgw_canout.pipe'

# This thread is responsible for waiting for input on the CAN bus passed
# as 'bus'.  A received message is converted to a string and then put on
# the queue for the QueueThread to send to the fifo.  i is the CAN bus
# index '0', '1' or '2'
class RecvThread(threading.Thread):
    def __init__(self, parent, bus, i, q):
        super(RecvThread, self).__init__()

        self.getout = False
        self.parent = parent
        self.bus = bus
        self.busindex = i
        self.queue = q

    def run(self):

        while(True):
            try:
                msg = self.bus.recv(0.5)
                if msg:
                    self.queue.put(msg2string(msg, self.busindex))

            finally:
                if(self.getout):
                    break


    def stop(self):
        self.getout = True
        self.join()

# This is a thread that listens to the fifo and when a line is received it
# converts the text to a CAN message and sends it on the appropriate bus
class SendThread(threading.Thread):
    def __init__(self, parent, buses):
        super(SendThread, self).__init__()

        self.getout = False
        self.parent = parent
        self.buses = buses


    def run(self):
        self.fifo = open(input_fifo, 'r')

        for line in self.fifo:
            b, msg = string2msg(line)
            self.buses[b].send(msg)
        self.fifo.close()

    def stop(self):
        self.getout = True
        self.join()

# A simple thread that listens on the queue and writes whatever it finds there
# to the fifo.
class QueueThread(threading.Thread):
    def __init__(self, parent, q):
        super(QueueThread, self).__init__()

        self.getout = False
        self.parent = parent
        self.queue = q


    def run(self):
        self.fifo = open(output_fifo, 'w')

        while True:
            try:
                x = self.queue.get(timeout = 0.5)
                self.fifo.write(x)
            except queue.Empty:
                if self.getout: break
        self.fifo.close()


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
        self.buses = []
        self.buses.append(can.ThreadSafeBus(self.channel+'0', bustype = self.interface))
        self.buses.append(can.ThreadSafeBus(self.channel+'1', bustype = self.interface))
        self.buses.append(can.ThreadSafeBus(self.channel+'2', bustype = self.interface))
        self.queue = queue.Queue()

    def run(self):
        self.threads = []
        self.threads.append( QueueThread(self, self.queue) )
        self.threads.append( RecvThread(self, self.buses[0], '0', self.queue) )
        self.threads.append( RecvThread(self, self.buses[1], '1', self.queue) )
        self.threads.append( RecvThread(self, self.buses[2], '2', self.queue) )
        self.threads.append( SendThread(self, self.buses) )

        for thread in self.threads:
            thread.start()


    def stop(self):
        for thread in self.threads:
            thread.stop()
            if thread.is_alive():
                thread.join(1.0)
            if thread.is_alive():
                raise plugin.PluginFail


    def get_status(self):
        return OrderedDict({"Frame Count":self.thread.framecount,
                            "Error Count":self.thread.errorcount})
