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

#  X-Plane Plugin

import threading
import socket
import select
import struct
import fixgw.plugin as plugin

# TODO Replace with configuration
UDP_IP = "127.0.0.1"
UDP_PORT = 49203


class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False  # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        self.sock.bind((UDP_IP, UDP_PORT))
        self.sock.setblocking(0)

        # inputkeys is a dictionary that holds the data out indexes from X-Plane
        # and the keys to use for that data in FixGW to know what to send.  It's
        # read from the config file.  Only data that is found in this config
        # will be read from the database and sent to X-Plane
        self.inputkeys = {}
        for each in self.parent.config:
            if each[:3].lower() == "idx":
                index = int(each[3:])
                l = self.parent.config[each].replace(" ", "").split(",")
                self.inputkeys[index] = l

    def writedata(self, index, data):
        if index == 3:
            self.parent.db_write("IAS", data[0])
            self.parent.db_write("TAS", data[2])
        elif index == 20:
            self.parent.db_write("ALT", data[2])
            self.parent.db_write("LAT", data[0])
            self.parent.db_write("LONG", data[1])
        else:
            self.parent.log.debug("Dunno Index:" + str(index))
        # self.parent.db_write("",data[0])

    def senddata(self):
        """Function that sends data to X-Plane"""
        for each in self.inputkeys:
            data = "DATA" + chr(0)
            data += struct.pack("i", int(each))

            for i in range(8):
                if self.inputkeys[each][i].lower() == "x":
                    data += chr(0) + chr(192) + chr(121) + chr(196)
                    # data += struct.pack("f", 0.0)
                else:
                    data += struct.pack(
                        "f", float(self.parent.db_read(self.inputkeys[each][i].upper()))
                    )
            # for each in data:
            #    print hex(ord(each)),
            # print ""
            self.sock.sendto(data, (UDP_IP, 49200))

    def run(self):
        while True:
            if self.getout:
                break
            ready = select.select([self.sock], [], [], 0.1)
            if ready[0]:
                data, addr = self.sock.recvfrom(4096)
                # print data
                header = data[:4]
                if header != "DATA":
                    self.parent.log.error("Bad data packet")
                    continue
                if (len(data) - 5) % 36 != 0:
                    self.parent.log.error("Bad packet length")
                    continue
                for x in range((len(data) - 5) / 36):
                    start = x * 36 + 5
                    # index = struct.unpack("i",data[start:start+4])[0]
                    index = ord(data[start])
                    udata = []
                    for i in range(8):
                        y = start + i * 4 + 4
                        udata.append(struct.unpack("f", data[y : y + 4])[0])  # noqa: E203
                    self.writedata(index, udata)
                    # print "index:", index, "Data: ", udata
            self.senddata()

    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self)

    def run(self):
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(2.0)
        if self.thread.is_alive():
            raise plugin.PluginFail
