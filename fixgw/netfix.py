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

# This is the FIX-Net client library for FIX-Gateway

import threading
import socket
import logging
import time
try:
    import queue
except:
    import Queue as queue
from collections import OrderedDict

log = logging.getLogger(__name__)

# This is the main communication thread of the FIX Gateway client.
class ClientThread(threading.Thread):
    def __init__(self, host, port):
        super(ClientThread, self).__init__()
        self.host = host
        self.port = port
        self.getout = False
        self.timeout = 1.0
        self.s = None
        # This Queue will hold normal data parameter responses
        self.dataqueue = queue.Queue()
        # This Queue will hold command responses
        self.cmdqueue = queue.Queue()
        self.connectedEvent = threading.Event()
        self.dataCallback = None

    def handle_request(self, d):
        log.debug("Response - {}".format(d))
        if d[0] == '@':
            self.cmdqueue.put([d[1], d[2:]])
        else:
            x = d.split(";")
            if len(x) != 3 and len(x) != 2:
                log.error("Bad Data Sentence Received")
            if len(x) == 3:
                s = ""
                if x[2][0] == "1": s += "a";
                if x[2][1] == "1": s += "o";
                if x[2][2] == "1": s += "b";
                if x[2][3] == "1": s += "f";
                x[2] = s
            self.dataqueue.put(x)
            if self.dataCallback:
                self.dataCallback(x)

    def run(self):
        log.debug("ClientThread - Starting")
        while True:
            self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.s.settimeout(self.timeout)

            try:
                self.s.connect((self.host, self.port))
            except Exception as e:
                log.debug("Failed to connect {0}".format(e))
            else:
                self.connectedEvent.set()
                log.debug("Connected to {0}:{1}".format(self.host, self.port))

                buff = ""
                while True:
                    try:
                        data = self.s.recv(1024)
                    except socket.timeout:
                        if self.getout:
                            self.s.close()
                            self.connectedEvent.clear()
                            break;
                    except Exception as e:
                        log.debug("Receive Failure {0}".format(e))
                        break
                    else:
                        if not data:
                            log.debug("No Data, Bailing Out")
                            self.connectedEvent.clear()
                            break
                        else:
                            try:
                                dstring = data.decode("utf-8")
                            except UnicodeDecodeError:
                                self.log.debug("Bad Message from {0}".format(self.addr[0]))
                            for d in dstring:
                                if d=='\n':
                                    try:
                                        self.handle_request(buff)
                                    except Exception as e:
                                        log.debug("Error handling request {0}".format(buff))
                                    buff = ""
                                else:
                                    buff += d
            if self.getout:
                self.connectedEvent.clear()
                self.s.close()
                log.debug("ClientThread - Exiting")
                break
            else:
                # TODO: Replace with configuration time
                time.sleep(2)
                log.debug("Attempting to Reconnect to {0}:{1}".format(self.host, self.port))

    def stop(self):
        self.getout = True

    def connectWait(self, timeout = 1.0):
        return self.connectedEvent.wait(timeout)

    def send(self, s):
        # TODO: Deal with errors gracefully
        try:
            self.s.send(s)
        except Exception as e:
            log.error(e)


def decodeDataString(d):
    x = d.split(';')
    id = x[0]
    v = x[1]
    f = "" # Quality Flags
    if x[2][0] == '1': f += "a"
    if x[2][1] == '1': f += "o"
    if x[2][2] == '1': f += "b"
    if x[2][3] == '1': f += "f"
    return (id,v,f)


class Client:
    def __init__(self, host, port, timeout=1.0):
        self.cthread = ClientThread(host, port)
        self.cthread.timeout = timeout
        self.cthread.daemon = True

    def connect(self):
        self.cthread.start()
        return self.cthread.connectWait()

    def disconnect(self):
        self.cthread.stop()
        # TODO: Block unit disconnected.

    def isConnected(self):
        return self.cthread.connectedEvent.is_set()

    def setDataCallback(self, func):
        self.cthread.dataCallback = func

    def clearDataCallback(self):
        self.cthread.dataCallback = None

    def read(self, id):
        self.cthread.send("@r{}\n".format(id).encode())
        try:
            res = self.cthread.cmdqueue.get(timeout = 1.0)
        except queue.Empty:
            return None
        return decodeDataString(res[1])

    def write(self, id, value):
        s = "{};{};00000\n".format(id, value)
        self.cthread.send(s.encode())

    def subscribe(self, id):
        self.cthread.send("@s{}\n".format(id).encode())
        try:
            res = self.cthread.cmdqueue.get(timeout = 1.0)
        except queue.Empty:
            return None

    def unsubscribe(self, id):
        self.cthread.send("@u{}\n".format(id).encode())
        try:
            res = self.cthread.cmdqueue.get(timeout = 1.0)
        except queue.Empty:
            return None

    def getStatus(self):
        self.cthread.send("@xstatus\n".encode())
        try:
            res = self.cthread.cmdqueue.get(timeout = 1.0)
        except queue.Empty:
            return None
        return res[1][7:]


if __name__ == "__main__":
    logging.basicConfig()
    log.level = logging.DEBUG
    c = Client("localhost", 3490)
    c.connect()
    print(c.write("IAS", 127.3))
    c.disconnect()
