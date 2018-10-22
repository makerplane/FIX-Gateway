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

import unittest
import subprocess
import os
import time

import canfix

# To test the canfix stuff we need a way to inject CAN messages and to read
# CAN messages that are sent by fixgw.  We are doing this with the cantest.py
# plugin that gets loaded.  We communicate with the cantest plugin through
# a pair of pipes.  A simple string will be used to send/receive CAN messages

#  b:iii:dddddddddddddddd

# b is the bus id because we'll be adding multiple CAN busses at some point
# to test redundancy 0,1,2 etc.  Can't imagine needing more than 3

# ii is the identifier
# dd is a databyte in hex

# This function creates the above string from a CAN Message and bus id character
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


# in and out are from the cantest plugin's perspective
# so we write to the input and read from the output
input_fifo = '/tmp/fixgw_canin.pipe'
output_fifo = '/tmp/fixgw_canout.pipe'


class TestCanfix(unittest.TestCase):

    def setUp(self):
        try:
            os.mkfifo(input_fifo)
            os.mkfifo(output_fifo)
        except FileExistsError:
            pass

        self.p = subprocess.Popen(["python3", "fixgw.py", "--debug", "--config-file", "tests/config/canfix.yaml"])
        self.ofifo = open(input_fifo, 'w')
        self.ififo = open(output_fifo, 'r')

    def test_Huh(self):
        p = canfix.Parameter()
        p.name = "Indicated Airspeed"
        p.value = 112.4
        m = p.getMessage()

        self.ofifo.write(msg2string(m,'0'))
        #self.ofifo.write("b:123:0123456789abcdef\n")


    def tearDown(self):
        self.ofifo.close()
        self.ififo.close()
        os.unlink(input_fifo)
        self.p.terminate()
        x = self.p.wait()
        os.unlink(output_fifo)


if __name__ == '__main__':
    unittest.main()
