#!/usr/bin/env python

#  Copyright (c) 2016 Phil Birkelbach
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
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
#  USA.import plugin

# This plugin is the implementation of the Net-FIX protocol.  Right now
# The ASCII version of the protocol is the only one that is implemented

import plugin
import threading
import socket
import queue


# This holds the data and functions that are needed by both connection threads.
class Connection(object):
    def __init__(self, parent, conn, addr):
        self.parent = parent # This should point to the plugin object
        self.conn = conn
        self.addr = addr
        self.log = parent.log
        self.queue = queue.Queue()
        self.buffer_size = int(parent.config['buffer_size']) if ('buffer_size' in parent.config) and parent.config['buffer_size'] else 1024


    # This sends a standard Net-FIX value update message to the queue.
    def __send_value(self, id, value):
        if type(value) is tuple:
            a = "1" if value[1] else "0"
            o = "1" if value[2] else "0"
            b = "1" if value[3] else "0"
            f = "1" if value[4] else "0"
            s = "{0};{1};{2}{3}{4}{5}\n".format(id, value[0],a, o, b, f)
        else:
            s = "{0};{1}\n".format(id, value)
        self.queue.put(s.encode())

    def __send_report(self, id):
        try:
            x = self.parent.db_get_item(id)
            a = ""
            for each in x.aux:
                if len(a) > 0:
                    a = a + ","
                a = a + each
            s = "@q{0};{1};{2};{3};{4};{5};{6};{7}\n".format(id, x.description,
                                                             x.typestring, x.min,
                                                             x.max, x.units,
                                                             x.tol,a)
            self.queue.put(s.encode())
        except KeyError:
            self.queue.put("@q{0}!001\n".format(id).encode())


    def __send_list(self):
        keys = self.parent.db_list()
        msgs = []
        index = 0
        s = ""

        for each in keys:
            # TODO Use Buffer size
            if len(s) + len(each) > self.buffer_size-20:
                msgs.append(s)
                s = ""
            if len(s) > 0:
                s = s + ","
            s = s + each
        msgs.append(s)

        count = len(keys)
        current = 0
        for message in msgs:
            self.queue.put("@l{0};{1};{2}\n".format(count, current, message).encode())
            current += len(message.split(','))


    def handle_request(self, d):
        if d[0] == '@': # It's a command frame
            if d[1] == 'l':
                self.__send_list()
                #print("List ID's")
                return
            else:
                id = d[2:].strip()
            if d[1] == 'r':
                try:
                    val = self.parent.db_read(id)
                except KeyError:
                    self.queue.put("@r{0}!001\n".format(id).encode())
                else:
                    self.__send_value(id, val)
            elif d[1] == 's':
                try:
                    self.parent.db_callback_add(id, self.subscription_handler)
                    self.queue.put("@s{0}\n".format(id).encode())
                except KeyError:
                    self.queue.put("@s{0}!001\n".format(id).encode())
            elif d[1] == 'u':
                try:
                    self.parent.db_callback_del(id, self.subscription_handler)
                    self.queue.put("@u{0}\n".format(id).encode())
                except KeyError:
                    self.queue.put("@u{0}!001\n".format(id).encode())
            elif d[1] == 'q':
                self.__send_report(id)
        else:  # If no '@' then it must be a value update
            try:
                x = d.strip().split(';')
                if len(x) != 3:
                    self.log.debug("Bad Frame {0} from {1}".format(d.strip(), self.addr[0]))
                if x[2] != '0000' or x[2] != '000':
                    item = self.parent.db_get_item(x[0])
                    a = x[2][0]
                    b = x[2][1]
                    f = x[2][2]
                    if len(x[2]) == 4:
                        s = x[2][3]
                    if a and a == '1':
                        item.annunciate = True
                    elif a and a == '0':
                        item.annunciate = False
                    if b and b == '1':
                        item.bad = True
                    elif b and b == '0':
                        item.bad = False
                    if f and f == '1':
                        item.fail = True
                    elif f and f == '0':
                        item.fail = False
                    # TODO Finish dealing with secondary quality flag
                self.parent.db_write(x[0], x[1])
            except Exception as e:
                # We pretty much ignore this stuff for now
                self.log.debug("Problem with input {0}: {1}".format(d.strip, e))

    # Callback function used for subscriptions
    def subscription_handler(self, id, value, udata):
        self.__send_value(id, value)

# Two threads are started for each connection.  This one is for receiving the data
class ReceiveThread(threading.Thread):
    def __init__(self, co):
        super(ReceiveThread, self).__init__()
        self.co = co
        self.conn = co.conn
        self.addr = co.addr
        self.parent = co.parent # This should point up to the Plugin Object
        self.running = True
        self.log = self.parent.log
        self.getout = False
        self.bsize = self.parent.thread.buffer_size


    def run(self):
        data = b""
        with self.conn:
            self.log.info('Client connection from {0} port {1}'.format(str(self.addr[0]), str(self.addr[1]) ))
            buff = ""
            while True:
                data = self.conn.recv(self.bsize)
                if not data: break
                try:
                    dstring = data.decode("utf-8")
                except UnicodeDecodeError:
                    self.log.debug("Bad Message from {0}".format(self.addr[0]))
                for d in dstring:
                    if d=='\n':
                        self.co.handle_request(buff)
                        buff = ""
                    else:
                        buff += d

            # TODO Should remove all of the callbacks that we have set here
            self.co.queue.put('exit')  #Signals the send thread to exit.
            self.log.info('Disconnected by {0} port {1}'.format(str(self.addr[0]), str(self.addr[1]) ))
            self.running = False


    def stop(self):
        self.getout = True
        self.conn.shutdown(socket.SHUT_RDWR)


class SendThread(threading.Thread):
    def __init__(self, co):
        super(SendThread, self).__init__()
        self.co = co
        self.conn = co.conn
        self.addr = co.addr
        self.parent = co.parent # This should point up to the Plugin Object
        self.running = True
        self.log = self.parent.log
        #self.getout = False

    # All this does is watch the queue in the connection object and
    # send anything that it finds there to the socket connection
    def run(self):
        with self.conn:
            while True:
                data = self.co.queue.get()
                if data == 'exit': break
                self.conn.sendall(data)
            self.running = False


    def stop(self):
        self.co.queue.put('exit')
        #self.getout = True


# This thread is responsible for starting and stopping the thread pairs that
#  represent connections.
class ServerThread(threading.Thread):
    def __init__(self, parent):
        """The calling object should pass itself as the parent.
           This gives the thread all the plugin goodies that the
           parent has."""
        super(ServerThread, self).__init__()
        self.getout = False    # indicator for when to stop
        self.parent = parent   # parent plugin object
        self.log = parent.log  # simplifies logging
        self.host = parent.config['host'] if ('host' in parent.config) and parent.config['host'] else ''
        self.port = int(parent.config['port']) if ('port' in parent.config) and parent.config['host'] else 3490
        self.timeout = float(parent.config['timeout']) if ('timeout' in parent.config) and parent.config['timeout'] else 1.0
        self.buffer_size = int(parent.config['buffer_size']) if ('buffer_size' in parent.config) and parent.config['buffer_size'] else 1024

        self.threads = []
        self.getout = False


    def run(self):
        while True:
            if self.getout:
                break
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.settimeout(self.timeout)
                s.bind((self.host, self.port))
                s.listen(5)
                try:
                    conn, addr = s.accept()
                except socket.timeout:
                    # if the getout flag is set let's bail.
                    if self.getout:
                        try:
                            s.shutdown(socket.SHUT_RDWR)
                        except Exception as e:
                            # For now just log the exception
                            self.log.debug(e)
                        for each in self.threads:
                            each[0].stop()
                            each[0].join()
                            each[1].stop()
                            each[1].join()
                        break
                    # General thread maintainance
                    for each in self.threads:
                        # The receive thread will stop running when the client closes
                        # This shoudl stop the send thread and clean it all up.
                        if not each[0].running:
                            each[0].join()
                            each[1].stop()
                            each[1].join()
                            self.threads.remove(each)

                else:
                    co = Connection(self.parent, conn, addr)
                    receivethread = ReceiveThread(co)
                    sendthread = SendThread(co)

                    self.threads.append( (receivethread, sendthread) )
                    receivethread.start()
                    sendthread.start()


    def stop(self):
        self.getout = True




class Plugin(plugin.PluginBase):
    """ All plugins for FIX Gateway should implement at least the class
    named 'Plugin.'  They should be derived from the base class in
    the plugin module.

    The run and stop methods of the plugin should be overridden but the
    base module functions should be called first."""
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        if config['type'] == 'server':
            self.thread = ServerThread(self)
        else:
            raise ValueError("Only server type is implemented")


    def run(self):
        """ The run method should return immediately.  The main routine will
        block when calling this function.  If the plugin is simply a collection
        of callback functions, those can be setup here and no thread will be
        necessary"""
        super(Plugin, self).run()
        self.thread.start()

    def stop(self):
        """ The stop method should not return until the plugin has completely
        stopped.  This generally means a .join() on a thread.  It should
        also undo any callbacks that were set up in the run() method"""
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join()
        super(Plugin, self).stop()
