#!/usr/bin/env python

#  Copyright (c) 2014 Phil Birkelbach, Neil Domalik
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
import os
import xml.etree.ElementTree as ET
from collections import OrderedDict
import socket
import time
import fixgw.plugin as plugin

# out and in are actually backwards here.  These are with respect to the
# flight simulator.  The recv_items are associated with chunks in the
# <output> section of the XML file and the generic protocol 'out' argument
# they are inputs to FIXGateway.  The opposite is true of send_items
recv_items = []
send_items = []
var_sep = ','

class UDPClient(threading.Thread):
    def __init__(self, host, port):
        super(UDPClient, self).__init__()

        self.host = host
        self.port = int(port)

        self.sock = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.settimeout(2.0)
        self.sock.bind((self.host, self.port))
        self.getout = False
        self.msg_recv = 0

    def save_data(self, data):
        l = data.split(var_sep)
        for i, each in enumerate(l):
            recv_items[i].value = each

    def run(self):
        buff = ""
        while not self.getout:
            #Reads the UDP packet splits then sends it to the Queue
            try:
                data = self.sock.recv(1024)  # buffer size is 1024 bytes
                if data:
                    for d in data.decode('utf-8'):
                        if d != '\n':
                            buff += d
                        else:
                            self.save_data(buff)
                            self.msg_recv += 1
                            buff = ""
            except socket.timeout:
                pass
        self.running = False

    def stop(self):
        self.getout = True


class Item(object):
    def __init__(self, key):
        self.key = key
        self.item = None
        self.format = ""
        self.conversion = None
        #self.__value = 0.0

    def setValue(self, value):
        #self.__value = value
        if self.item != None:
            self.item.value = value

    def getValue(self):
        if self.item != None:
            return self.item.value[0]
        else:
            return 0.0

    value = property(getValue, setValue)

    def __str__(self):
        return self.key

def parseProtocolFile(fg_root, xml_file):
    # Open the XML Protocol file
    filepath = os.path.join(fg_root, "Protocol/" + xml_file)
    # Needed to work OK in a snap
    if not os.path.isfile(filepath):
        filepath = os.path.join(fg_root, xml_file)
 
    tree = ET.parse(os.path.expanduser(filepath))
    root = tree.getroot()
    if root.tag != "PropertyList":
        raise ValueError("Root Tag is not PropertyList")

    # TODO Read var_separator tag and adjust accordingly
    # TODO Add <input> tags if any
    generic = root.find("generic")
    outputs = generic.find("output")
    for chunk in outputs:
        name = chunk.find("name")
        if name != None:
            info = name.text.split(":")
            recv_items.append(Item(info[0].strip()))
    inputs = generic.find("input")
    for chunk in inputs:
        name = chunk.find("name")
        if name != None:
            info = name.text.split(":")
            i = Item(info[0].strip())
            send_items.append(i)
            format = chunk.find("format")
            if format != None:
                i.format = format.text
            else:
                i.format = "%.2f"



class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False
        self.parent = parent
        self.log = parent.log
        self.config = parent.config
        self.msg_sent = 0
        self.host = self.config['send_host']
        self.port = int(self.config['send_port'])
        self.delay_time = 1.0 / float(self.config['rate'])

    def run(self):
        self.clientThread = UDPClient(self.config['recv_host'], self.config['recv_port'])
        self.clientThread.start()
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        while not self.getout:
            time.sleep(self.delay_time)
            ss = []
            for x in send_items:
                ss.append("%.2f" % x.value)
            msg = var_sep.join(ss)
            msg += "\n"
            sock.sendto(bytearray(msg, 'UTF-8'), (self.host, self.port))
            self.msg_sent += 1

    def stop(self):
        self.getout = True
        self.clientThread.stop()


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self)

    def run(self):
        try:
            self.xml_list = parseProtocolFile(self.config['fg_root'],
                                              self.config['xml_file'])
        except Exception as e:
            self.log.critical(e)
            self.stop()
            return

        # This loop checks to see if we have each item in the database
        # if not then we'll just let it get set to None and ignore it when
        # we parse the string from FlightGear
        for each in recv_items:
            each.item = self.db_get_item(each.key)
            if each.item == None:
                self.log.warning("{0} found in protocol file but not in the database".format(each.key))
        for each in send_items:
            each.item = self.db_get_item(each.key)
            if each.item == None:
                self.log.warning("{0} found in protocol file but not in the database".format(each.key))

        self.thread.start()

    def stop(self):
        try:
            self.thread.stop()
        except AttributeError:
            pass
        if self.thread.is_alive():
            self.thread.join(2.0)
        if self.thread.is_alive():
            raise plugin.PluginFail

    def get_status(self):
        d = OrderedDict()
        # For stuff that might fail we just ignore the errors and get what we get
        try:
            d["Listening on"] = "{}:{}".format(self.thread.clientThread.host, self.thread.clientThread.port)
            d["Sending to"] = "{}:{}".format(self.thread.host, self.thread.port)
            d["Properties"] = OrderedDict([("Receiving",len(recv_items)),
                                           ("Sending",len(send_items))])
            d["Messages"] = OrderedDict([("Received", self.thread.clientThread.msg_recv),
                                         ("Sent", self.thread.msg_sent)])
        except:
            pass

        return d
