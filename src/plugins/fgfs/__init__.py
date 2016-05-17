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
import os
import xml.etree.ElementTree as ET
import socket
import queue


class UDP_Process(threading.Thread):
    def __init__(self, conn, host, port):
        threading.Thread.__init__(self)
        self.queue = conn
        UDP_IP = host
        UDP_PORT = int(port)

        self.sock = socket.socket(socket.AF_INET,  # Internet
                             socket.SOCK_DGRAM)  # UDP
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind((UDP_IP, UDP_PORT))
        self.running = 1

    def run(self):
        while self.running:
            #Reads the UDP packet splits then sends it to the Queue
            data, addr = self.sock.recvfrom(1024)  # buffer size is 1024 bytes
            data_test = data
            if (data_test):
                self.queue.put(data_test)
            else:
                pass

    def stop(self):
        self.running = 0


def parseProtocolFile(fg_root, xml_file):
    # First we build a list with the possible locations of the file
    # We look in the FG_ROOT/Protocols directory as well as the
    # directory where our module is located.  May add others if they
    # make sense.
    Name_List = []

    filelist = [os.path.join(fg_root, xml_file)]  # "Protocols", xml_file)]
                #os.path.join(os.path.dirname(__file__), xml_file)]
    # Now loop through the files and use the first one we find
    found = False
    for each in filelist:
        if os.path.isfile(each):
            tree = ET.parse(each)
            found = True
            break
    if not found:
        raise RuntimeError("XML file not found")
    root = tree.getroot()
    if root.tag != "PropertyList":
        raise ValueError("Root Tag is not PropertyList")

    for node in tree.findall('.//key'):
        Name_List.append(node.text)

    return Name_List

    #generic = root.find("generic")
    #output = generic.find("output")
    #if child.text != "CANFIX":
    #    raise ValueError("Not a CANFIX Protocol File")

    #child = root.find("version")
    #version = child.text


class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False
        self.parent = parent
        self.log = parent.log
        self.config = parent.config

    def run(self):
        q = queue.Queue()
        t = UDP_Process(q, self.config['host'], self.config['port'])
        t.setDaemon(True)
        t.start()
        while True:
            if self.getout:
                break
            try:
                data_test = q.get(0)
                data_test = data_test.decode().rstrip()
                data_test = data_test.split(',')
                if data_test != ['']:
                    for data in data_test:
                        for l, d in zip(self.parent.xml_list, data_test):
                            try:
                                try:
                                    self.parent.db_write(l.upper(), float(d))
                                except ValueError:
                                    self.parent.db_write(l, d)
                            except KeyError:
                                self.log.warning(l.upper() + " not in index")
            except queue.Empty:
                pass
            self.log.debug("Yep")
        t.stop()

    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self)

    def run(self):
        super(Plugin, self).run()
        try:
            self.xml_list = parseProtocolFile(self.config['fg_root'],
                                         self.config['xml_file'])
        except Exception as e:
            self.log.critical(e)
            return
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join()
        super(Plugin, self).stop()
