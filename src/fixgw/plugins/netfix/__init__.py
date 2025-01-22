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

import threading
import socket

try:
    import queue
except:
    import Queue as queue
from collections import OrderedDict
from collections import defaultdict
from collections import deque
import json
import fixgw.plugin as plugin
import fixgw.status as status
import fixgw.netfix as netfix
import time

# Track where data came from to prevent loops
client_block = defaultdict(set)


# This holds the data and functions that are needed by both connection threads.
class Connection(object):
    global client_block

    def __init__(self, parent, conn, addr):
        self.parent = parent  # This should point to the plugin object
        self.conn = conn
        self.addr = addr
        self.log = parent.log
        self.queue = queue.Queue()
        self.buffer_size = (
            int(parent.config["buffer_size"])
            if ("buffer_size" in parent.config) and parent.config["buffer_size"]
            else 1024
        )
        self.subscriptions = set()
        self.output_inhibit = False

    # This sends a standard Net-FIX value update message to the queue.
    def __send_value(self, id, value):
        if type(value) is tuple:
            a = "1" if value[1] else "0"
            o = "1" if value[2] else "0"
            b = "1" if value[3] else "0"
            f = "1" if value[4] else "0"
            s = "1" if value[5] else "0"
            st = "{0};{1};{2}{3}{4}{5}{6}\n".format(id, value[0], a, o, b, f, s)
        else:
            st = "{0};{1}\n".format(id, value)
        self.queue.put(st.encode())

    def __send_report(self, id):
        try:
            x = self.parent.db_get_item(id)
            if not x:
                raise KeyError
            a = ""
            for each in x.aux:
                if len(a) > 0:
                    a = a + ","
                a = a + each
            s = "@q{0};{1};{2};{3};{4};{5};{6};{7}\n".format(
                id, x.description, x.typestring, x.min, x.max, x.units, x.tol, a
            )
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
            if len(s) + len(each) > self.buffer_size - 20:
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
            current += len(message.split(","))

    def __server_specific(self, d):
        if d == "status":
            s = json.dumps(self.parent.get_status())
            self.queue.put("@xstatus;{}\n".format(s).encode())
        elif d == "kill":
            self.queue.put("@xkill\n".encode())
            self.parent.quit()
        else:
            self.queue.put("@x{}!001".format(d).encode())

    def __flag(self, d):
        a = d.split(";")
        try:
            item = self.parent.db_get_item(a[0])
        except KeyError:
            self.queue.put("@f{0}!001\n".format(d[0]).encode())
            return
        if a[1] not in ["a", "f", "b", "s", "o"]:
            self.queue.put("@f{0}!002\n".format(d[0]).encode())
            return
        if a[2] not in ["1", "0"]:
            self.queue.put("@f{0}!003\n".format(d[0]).encode())
            return
        bit = a[2] == "1"
        if a[1] == "a":
            item.annunciate = bit
        elif a[1] == "o":
            item.old = bit
        elif a[1] == "b":
            item.bad = bit
        elif a[1] == "f":
            item.fail = bit
        elif a[1] == "s":
            item.secfail = bit
        self.queue.put("@f{0}\n".format(d).encode())

    # This is a command that simply writes the value.  It does not change the
    # flags like the normal data write sentence would.  It also has a return
    # value.
    def __writeValue(self, d):
        a = d.split(";")
        if len(a) < 2:
            self.queue.put("@w{0}!003\n".format(a[0]).encode())
            return
        try:
            self.output_inhibit = True
            # Track inputs so we do not send back to same client
            client_block[self.addr[0]].add(a[0])
            self.parent.db_write(a[0], a[1])
        except KeyError:
            self.queue.put("@w{0}!001\n".format(a[0]).encode())
            return
        except ValueError:
            self.queue.put("@w{0}!003\n".format(a[0]).encode())
            return

        val = self.parent.db_read(a[0])
        if "." in a[0]:  # This is an aux write
            self.queue.put("@w{};{}\n".format(a[0], val).encode())
        else:
            flags = ""
            flags += "1" if val[1] else "0"
            flags += "1" if val[2] else "0"
            flags += "1" if val[3] else "0"
            flags += "1" if val[4] else "0"
            flags += "1" if val[5] else "0"
            self.queue.put("@w{};{};{}\n".format(a[0], val[0], flags).encode())

    def handle_request(self, d):
        if d[0] == "@":  # It's a command frame
            if d[1] == "l":
                self.__send_list()
                return
            else:
                id = d[2:].strip()
            if d[1] == "r":
                try:
                    val = self.parent.db_read(id)
                    if type(val) is tuple:
                        a = "1" if val[1] else "0"
                        o = "1" if val[2] else "0"
                        b = "1" if val[3] else "0"
                        f = "1" if val[4] else "0"
                        s = "1" if val[5] else "0"
                        st = "@r{0};{1};{2}{3}{4}{5}{6}\n".format(
                            id, val[0], a, o, b, f, s
                        )
                    else:
                        st = "@r{0};{1}\n".format(id, val)
                    self.queue.put(st.encode())
                except KeyError:
                    self.queue.put("@r{0}!001\n".format(id).encode())
            elif d[1] == "s":
                if id not in self.subscriptions:
                    try:
                        self.parent.db_callback_add(id, self.subscription_handler)
                        self.queue.put("@s{0}\n".format(id).encode())
                        self.subscriptions.add(id)
                    except KeyError:
                        self.queue.put("@s{0}!001\n".format(id).encode())
                else:  # Duplicate subscription
                    self.queue.put("@s{0}!002\n".format(id).encode())

            elif d[1] == "u":
                try:
                    self.parent.db_callback_del(id, self.subscription_handler)
                    self.queue.put("@u{0}\n".format(id).encode())
                    self.subscriptions.remove(id)
                except KeyError:
                    self.queue.put("@u{0}!001\n".format(id).encode())
            elif d[1] == "q":
                self.__send_report(id)
            elif d[1] == "x":
                self.__server_specific(d[2:])
            elif d[1] == "f":
                self.__flag(d[2:])
            elif d[1] == "w":
                self.__writeValue(d[2:])
            else:  # Unknown command given
                self.queue.put("{}!004\n".format(d).encode())

        else:  # If no '@' then it must be a value update
            try:
                x = d.strip().split(";")
                if len(x) != 3:
                    self.log.debug(
                        "Bad Frame {0} from {1}".format(d.strip(), self.addr[0])
                    )
                if x[2] != "0000" or x[2] != "000":
                    item = self.parent.db_get_item(x[0])
                    a = x[2][0]
                    b = x[2][1]
                    f = x[2][2]
                    if len(x[2]) == 4:
                        s = x[2][3]
                    else:
                        s = "0"
                    if a and a == "1":
                        # self.output_inhibit = True
                        item.annunciate = True
                    elif a and a == "0":
                        # self.output_inhibit = True
                        item.annunciate = False
                    if b and b == "1":
                        # self.output_inhibit = True
                        item.bad = True
                    elif b and b == "0":
                        # self.output_inhibit = True
                        item.bad = False
                    if f and f == "1":
                        # self.output_inhibit = True
                        item.fail = True
                    elif f and f == "0":
                        # self.output_inhibit = True
                        item.fail = False
                    if s and s == "1":
                        # self.output_inhibit = True
                        item.secfail = True
                    elif s and s == "0":
                        # self.output_inhibit = True
                        item.secfail = False
                self.output_inhibit = True
                # Track inputs so we do not send back to same client
                client_block[self.addr[0]].add(x[0])
                self.parent.db_write(x[0], x[1])
            except Exception as e:
                # We pretty much ignore this stuff for now
                self.log.debug("Problem with input {0}: {1}".format(d.strip(), e))

    # Callback function used for subscriptions
    def subscription_handler(self, id, value, udata):
        if self.output_inhibit:
            self.output_inhibit = False
        else:
            self.__send_value(id, value)


# Two threads are started for each connection.  This one is for receiving the data
class ReceiveThread(threading.Thread):
    def __init__(self, co):
        super(ReceiveThread, self).__init__()
        self.co = co
        self.conn = co.conn
        self.addr = co.addr
        self.parent = co.parent  # This should point up to the Plugin Object
        self.running = True
        self.log = self.parent.log
        self.getout = False
        self.bsize = self.parent.thread.buffer_size
        self.msg_recv = 0

    def run(self):
        data = b""
        try:
            self.log.info(
                "Client connection from {0} port {1}".format(
                    str(self.addr[0]), str(self.addr[1])
                )
            )
            buff = ""
            while True:
                try:
                    data = self.conn.recv(self.bsize)
                except:
                    break  # Major error we'll just bail
                if not data:
                    break
                try:
                    dstring = data.decode("utf-8")
                except UnicodeDecodeError:
                    self.log.debug("Bad Message from {0}".format(self.addr[0]))
                for d in dstring:
                    if d == "\n":
                        self.co.handle_request(buff)
                        self.msg_recv += 1
                        buff = ""
                    else:
                        buff += d

            self.co.queue.put("exit")  # Signals the send thread to exit.
            self.parent.db_callback_del("*", self.co.subscription_handler, None)
            self.log.info(
                "Disconnected by {0} port {1}".format(
                    str(self.addr[0]), str(self.addr[1])
                )
            )
            self.running = False
        finally:
            self.conn.close()

    def stop(self):
        self.getout = True
        try:
            self.conn.shutdown(socket.SHUT_RDWR)
        except Exception as e:
            self.log.debug("Problem shutting down connection - {0}".format(e))


class SendThread(threading.Thread):
    def __init__(self, co):
        super(SendThread, self).__init__()
        self.co = co
        self.conn = co.conn
        self.addr = co.addr
        self.parent = co.parent  # This should point up to the Plugin Object
        self.running = True
        self.log = self.parent.log
        self.msg_sent = 0

    # All this does is watch the queue in the connection object and
    # send anything that it finds there to the socket connection
    def run(self):
        try:
            while True:
                data = self.co.queue.get()
                if data == "exit":
                    break
                self.conn.sendall(data)
                self.msg_sent += 1
            self.running = False
        finally:
            self.conn.close()

    def stop(self):
        self.co.queue.put("exit")


# This thread is responsible for starting and stopping the thread pairs that
#  represent connections.
class ServerThread(threading.Thread):
    def __init__(self, parent):
        super(ServerThread, self).__init__()
        self.getout = False  # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self.host = (
            parent.config["host"]
            if ("host" in parent.config) and parent.config["host"]
            else ""
        )
        self.port = (
            int(parent.config["port"])
            if ("port" in parent.config) and parent.config["host"]
            else 3490
        )
        self.timeout = (
            float(parent.config["timeout"])
            if ("timeout" in parent.config) and parent.config["timeout"]
            else 1.0
        )
        self.buffer_size = (
            int(parent.config["buffer_size"])
            if ("buffer_size" in parent.config) and parent.config["buffer_size"]
            else 1024
        )

        self.threads = []
        self.getout = False

    def run(self):
        while True:
            if self.getout:
                break
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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

                    self.threads.append((receivethread, sendthread))
                    receivethread.start()
                    sendthread.start()
            finally:
                s.close()

    def stop(self):
        self.getout = True

    def get_status(self):
        d = OrderedDict({"Current Connections": len(self.threads)})
        for i, t in enumerate(self.threads):
            c = OrderedDict()
            c["Client"] = t[0].addr
            c["Messages Received"] = t[0].msg_recv
            c["Messages Sent"] = t[1].msg_sent
            # "Subscriptions":','.join(t[0].co.subscriptions)}
            c["Subscriptions"] = len(t[0].co.subscriptions)
            d["Connection {0}".format(i)] = c
        return d


class ClientThread(threading.Thread):
    global client_block

    def __init__(self, parent):
        super(ClientThread, self).__init__()
        self.getout = False  # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self.config = parent.config
        self.queue = deque()

        # Connect to each client here
        self.clients = []

        for c in self.config["clients"]:
            self.clients.append(netfix.Client(c["host"], c.get("port", 3490)))
            self.clients[-1].connect()

        for o in self.config["outputs"]:
            self.parent.db_callback_add(o.upper(), self.getOutputFunction(o.upper()))

    def run(self):
        while True:
            if self.getout:
                break
            # Do stuff here
            while len(self.queue) > 0:
                # Maybe a pause when exception?
                key = self.queue.popleft()
                for c in self.clients:
                    try:
                        # Block sending back to self
                        if key not in client_block[c.cthread.host]:
                            c.writeValue(key, self.parent.db_read(key)[0])
                        else:
                            # Remove the block since we just blocked it
                            client_block[c.cthread.host].discard(key)
                    except Exception as e:
                        if key not in self.queue:
                            self.queue.append(key)
                time.sleep(0.0001)
            # Limit how often we send data to other nodes
            time.sleep(0.2)

    def getOutputFunction(self, key):
        def outputCallback(fixkey, value, udata):
            if True in value[1:]:
                # This callback is likely only for old/fail etc we only care about the value itself
                # Maybe this could be improved in the future
                # But currently the goal is just sending the value and
                # preventing loops
                return
            if key not in self.queue:
                self.queue.append(key)

        return outputCallback

    def stop(self):
        self.getout = True
        for c in self.clients:
            c.disconnect()

    def get_status(self):
        connected = 0
        disconnected = 0
        for c in self.clients:
            if c.isConnected:
                connected += 1
            else:
                disconnected += 1
        d = OrderedDict({"Current Clients": connected + disconnected})
        d["Connected"] = connected
        d["Disonnected"] = disconnected

        return d


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        if config["type"] in ["server", "both"]:
            self.thread = ServerThread(self)
        if config["type"] in ["client", "both"]:
            self.client = ClientThread(self)
        if config["type"] not in ["server", "client", "both"]:
            raise ValueError("Must specify server. client or both")

    def run(self):
        if self.config["type"] in ["server", "both"]:
            self.thread.start()
        if self.config["type"] in ["client", "both"]:
            self.client.start()

    def stop(self):
        if self.config["type"] in ["server", "both"]:
            self.thread.stop()
            if self.thread.is_alive():
                self.thread.join(2.0)
        if self.config["type"] in ["client", "both"]:
            self.client.stop()
            if self.client.is_alive():
                self.client.join(2.0)
        if self.config["type"] == "both":
            if self.thread.is_alive() or self.client.is_alive():
                raise plugin.PluginFail
        elif self.config["type"] == "server":
            if self.thread.is_alive():
                raise plugin.PluginFail
        elif self.config["type"] == "client":
            if self.client.is_alive():
                self.client.join(2.0)

            # if self.thread.is_alive():
            #    raise plugin.PluginFail

    def get_status(self):
        return self.thread.get_status()
