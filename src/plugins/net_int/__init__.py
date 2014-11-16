# -*- coding: utf-8 -*-
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
import socket
import select


class clientthread(threading.Thread):
    def __init__(self, parent, conn):
        super(clientthread, self).__init__()
        self.getout = False
        self.parent = parent
        self.log = parent.log
        self.conn = conn

    def run(self):
        #Sending initial connection message
        self.conn.send('Connected\n'.encode('utf-8'))
        #loop so that function do not terminate and thread do not end.
        while not self.getout:
            #Receiving from client
            incoming_data, rw, err = select.select([self.conn], [], [], 1)
            if incoming_data:
                self.choice(incoming_data)

        #Close out Socket
        self.conn.close()

    def choice(self, in_data):
        data = self.conn.recv(1024)
        data = data.decode('utf-8')
        data = data.strip('\r\n')
        args = data.split(" ")
        if args[0] == "list":
            self.do_list(data)
        elif args[0] == "read":
            self.do_read(data)
        elif args[0] == "write":
            self.do_write(data)
        elif args[0] == "poll":
            self.do_poll()
        elif args[0] == "stop":
            self.stop_poll()
        elif args[0] == "quit":
            self.do_quit()
        else:
            pass

    def stop(self):
        self.getout = True
        self.conn.close()

    def do_list(self, data):
        """list List Database Keys"""
        x = self.parent.db_list()
        for each in x:
                reply = each + "\n"
                self.conn.sendall(reply.encode('utf-8'))

    def do_read(self, data):
        """read key Read the value from the database given the key"""
        args = data.split(" ")
        try:
            reply = self.parent.db_read(args[1].upper())
            if reply:
                reply = str(reply) + "\n"
            else:
                reply = str("Unknown Key " + args[1] + "\n")
        except:
            reply = "Missing Values\n"
        self.conn.sendall(reply.encode('utf-8'))

    def do_write(self, data):
        """write key value\nWrite Value into Database with given key"""
        args = data.split(" ")
        if len(args) < 2:
            self.conn.sendall("Missing Argument\n".encode('utf-8'))
        else:
            #TODO: Should do more error checking here
            self.parent.db_write(args[1].upper(), args[2])

    def do_poll(self):
        self.poll = True
        while self.poll:
            listing = self.parent.db_list()
            for name in listing:
                packet = name + "=" + str(
                         self.parent.db_read(name.upper())) + ", "
                try:
                    self.conn.sendall(packet.encode('utf-8'))
                except:
                    pass
            incoming_data, rw, err = select.select([self.conn], [], [], 0.01)
            if incoming_data:
                self.choice(incoming_data)

    def stop_poll(self):
        self.poll = False

    def do_quit(self):
        self.poll = False
        self.getout = True


class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False
        self.parent = parent
        self.log = parent.log
        self.config = parent.config

        # Pulls host and port from the Config file
        HOST = self.config['host']
        PORT = int(self.config['port'])

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        #Bind socket to local host and port
        try:
            self.s.bind((HOST, PORT))
            self.log.info('Socket bind complete')
        except socket.error as msg:
            msg = str(msg)
            msg = msg.strip('[Errno ')
            msg = msg.split('] ')
            self.log.error('Bind failed. Message: ' + str(msg[1]))

        #Start listening on socket
        self.s.listen(10)
        self.s.setblocking(10)

    def run(self):
        while not self.getout:
            #Waiting for incomming clinet
            Incoming_client, rw, err = select.select([self.s], [], [], 1)
            if Incoming_client:
                #wait to accept a connection
                self.conn, addr = self.s.accept()
                self.log.info('Connected with ' + addr[0] + ':' + str(addr[1]))
                self.thread1 = clientthread(self.parent, self.conn)
                self.thread1.setDaemon(True)
                #start new thread
                self.thread1.start()
            else:
                pass
        #Close Socket
        self.s.close()

    def stop(self):
        try:
            self.thread1.stop()
        except:
            pass
        self.getout = True
        self.s.close()


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self)

    def run(self):
        super(Plugin, self).run()
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join()
        super(Plugin, self).stop()
