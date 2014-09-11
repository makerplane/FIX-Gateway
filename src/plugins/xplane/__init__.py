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

import plugin
import threading
import time
import socket
import select
import struct

#TODO Replace with configuration
UDP_IP = "127.0.0.1"
UDP_PORT = 49203


class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log # simplifies logging
 
        self.sock = socket.socket(socket.AF_INET, # Internet
                                  socket.SOCK_DGRAM) # UDP
        self.sock.bind((UDP_IP, UDP_PORT))
        self.sock.setblocking(0)
    
    def writedata(self, index, data):
        if index == 3:
            self.parent.db_write("IAS",data[0])
            self.parent.db_write("TAS",data[2])
        elif index == 20:
            self.parent.db_write("ALT",data[2])
            self.parent.db_write("LAT",data[0])
            self.parent.db_write("LONG",data[1])
        else:
            self.parent.log.debug("Dunno Index:" + str(index))
        #self.parent.db_write("",data[0])
    
    def senddata(self):
        """Function that sends data to X-Plane"""
        values = [float(self.parent.db_read("THR1")), float(self.parent.db_read("THR2")), 0.0,0.0,0.0,0.0,0.0,0.0]
        data = "DATA" + chr(0)
        data += struct.pack("i", 25)
        for x in range(8):
            data += struct.pack("f", values[x])
        #for each in data:
        #    print hex(ord(each)),
        self.sock.sendto(data, (UDP_IP, 49200))
        
    def run(self):
        while True:
            if self.getout:
                break
            ready = select.select([self.sock], [], [], 0.1)
            if ready[0]:
                data, addr = self.sock.recvfrom(4096)
                #print data
                header = data[:4]
                if header != "DATA": 
                    self.parent.log.error("Bad data packet")
                    continue
                if (len(data)-5) % 36 != 0:
                    self.parent.log.error("Bad packet length")
                    continue
                for x in range( (len(data)-5)/36 ):
                    start = x*36 + 5
                    #index = struct.unpack("i",data[start:start+4])[0]
                    index =  ord(data[start])
                    udata = []
                    for i in range(8):
                        y = start + i*4 +4
                        udata.append(struct.unpack("f", data[y:y+4])[0])
                    self.writedata(index, udata)
                    #print "index:", index, "Data: ", udata
            self.senddata()
    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name,config)
        self.thread = MainThread(self)

    def run(self):
        super(Plugin, self).run()
        self.thread.start()
    
    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join()
        super(Plugin, self).stop()
