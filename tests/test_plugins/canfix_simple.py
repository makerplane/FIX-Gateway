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

# This is a list of the parameters that we are testing.  It is a list of tuples
# that contain (FIXID, CANID, DataString, Value, Test tolerance)
ptests = [("PITCH", 0x180, "FF0000D8DC", -90.0, 0.0),
          ("PITCH", 0x180, "FF00002823", 90.0, 0.0),
          ("PITCH", 0x180, "FF00000000", 0.0, 0.0),
          ("ROLL", 0x181, "FF0000B0B9", -180.0, 0.0),
          ("ROLL", 0x181, "FF00005046", 180.0, 0.0),
          ("ROLL", 0x181, "FF00000000", 0.0, 0.0),
          ("IAS", 0x183, "FF00000000", 0.0, 0.0),
          ("IAS", 0x183, "FF0000E803", 100.0, 0.0),
          ("IAS", 0x183, "FF0000E803", 100.0, 0.0),
          ("IAS", 0x183, "FF00000F27", 999.9, 0.01),
          ("IAS.Min", 0x183, "FF00100000", 0.0, 0.01),
          ("IAS.Max", 0x183, "FF0020D007", 200.0, 0.01),
          ("IAS.V1", 0x183, "FF00309001", 40.0, 0.01),
          ("IAS.V2", 0x183, "FF00406202", 61.0, 0.01),
          ("IAS.Vne", 0x183, "FF0050DC02", 73.2, 0.01),
          ("IAS.Vfe", 0x183, "FF0060EE02", 75.0, 0.01),
          ("IAS.Vmc", 0x183, "FF00702003", 80.0, 0.01),
          ("IAS.Va", 0x183, "FF00802B03", 81.1, 0.01),
          ("IAS.Vno", 0x183, "FF00908603", 90.2, 0.01),
          ("IAS.Vs", 0x183, "FF00A0A501", 42.1, 0.01),
          ("IAS.Vs0", 0x183, "FF00B0C401", 45.2, 0.01),
          ("IAS.Vx", 0x183, "FF00E06203", 86.6, 0.01),
          ("IAS.Vy", 0x183, "FF00F06D03", 87.7, 0.01),
          ("ALT", 0x184, "FF000018FCFFFF", -1000.0, 0.01),
          ("ALT", 0x184, "FF000000000000", 0.0, 0.01),
          ("ALT", 0x184, "FF0000E8030000", 1000.0, 0.01),
          ("ALT", 0x184, "FF0000D0070000", 2000.0, 0.01),
          ("ALT", 0x184, "FF000010270000", 10000.0, 0.01),
          ("ALT", 0x184, "FF000060EA0000", 60000.0, 0.01),
          ("HEAD", 0x185, "FF00000000", 0.0, 0.01),
          ("HEAD", 0x185, "FF00000807", 180.0, 0.01),
          ("HEAD", 0x185, "FF00000F0E", 359.9, 0.01),
          ("HEAD", 0x185, "FF0000100E", 359.9, 0.01), # Write 360.0 get back 359.9
          ("VS", 0x186, "FF0000D08A", -30000, 0.01),
          ("VS", 0x186, "FF00000000", 0, 0.01),
          ("VS", 0x186, "FF00003075", 30000, 0.01),
          ("VS.Min", 0x186, "FF0010F0D8", -10000, 0.01),
          ("VS.Max", 0x186, "FF00201027", 10000, 0.01),
          ("TACH1", 0x200, "FF00000000", 0, 0.01),
          ("TACH1", 0x200, "FF0000E803", 1000, 0.01),
          ("TACH1", 0x200, "FF00005A0A", 2650, 0.01),
          ("PROP1", 0x202, "FF00000000", 0, 0.01),
          ("PROP1", 0x202, "FF0000E803", 1000, 0.01),
          ("PROP1", 0x202, "FF00005A0A", 2650, 0.01),
          ("MAP1", 0x21E, "FF00000000", 0.0, 0.001),
          ("MAP1", 0x21E, "FF0000C409", 25.0, 0.001),
          ("MAP1.Min", 0x21E, "FF00100000", 0.0, 0.001),
          ("MAP1.Max", 0x21E, "FF0020B80B", 30.0, 0.001),
          ("OILP1", 0x220, "FF00000000", 0.0, 0.001),
          ("OILP1", 0x220, "FF0000A911", 45.21, 0.001),
          ("OILP1", 0x220, "FF00005125", 95.53, 0.001),
          ("OILP1.Min", 0x220, "FF00100000", 0.0, 0.001),
          ("OILP1.Max", 0x220, "FF00201027", 100.0, 0.001),
          ("OILP1.lowWarn", 0x220, "FF0040A00F", 40.0, 0.001),
          ("OILP1.lowAlarm", 0x220, "FF0050AC0D", 35.0, 0.001),
          ("OILP1.highWarn", 0x220, "FF0060401F", 80.0, 0.001),
          ("OILP1.highAlarm", 0x220, "FF00701C25", 95.0, 0.001),
#          ("OILT1", 0x220, "FF0000", 0.0, 0.001),
]

def string2data(s):
    b = bytearray()
    for x in range(0, len(s), 2):
        b.append(int(s[x:x+2], 16))
    return b


# A simple thread that listens on the queue and writes whatever it finds there
# to the fifo.
class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()

        self.getout = False
        self.parent = parent


    def run(self):
        try:
            for each in ptests:
                print("Testing {} = {}".format(each[0], each[3]), end='')
                msg = can.Message(extended_id = False, arbitration_id = each[1])
                msg.data = string2data(each[2])
                self.parent.bus.send(msg)
                time.sleep(0.03)
                x = self.parent.db_read(each[0])
                if '.' in each[0]:
                    val = x
                else:
                    val = x[0]
                if(abs(val-each[3]) > each[4]):
                    print(" - FAIL!!")
                    raise Exception("{} != {}".format(val, each[3]))
                else:
                    print(" - PASS")


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
