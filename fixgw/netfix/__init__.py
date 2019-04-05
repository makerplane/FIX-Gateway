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

class ResponseError(Exception):
    pass

class SendError(Exception):
    pass

class NotConnectedError(Exception):
    pass

# A convenience class for working with the get_report() response.
class Report:
    def __init__(self, res):
        self.desc = res[1]
        self.dtype = res[2]
        self.min = res[3]
        self.max = res[4]
        self.units = res[5]
        self.tol = res[6]
        self.aux = []
        if res[7]:
            x = res[7].split(',')
            for aux in x:
                self.aux.append(aux)

    def __str__(self):
        return "{}:{}".format(self.desc, self.units)


# This is the main communication thread of the FIX Gateway client.
class ClientThread(threading.Thread):
    def __init__(self, host, port):
        super(ClientThread, self).__init__()
        self.daemon = True
        self.host = host
        self.port = port
        self.getout = False
        self.timeout = 1.0
        self.s = None
        # This Queue will hold normal data parameter responses
        #self.dataqueue = queue.Queue()
        # This Queue will hold command responses
        self.cmdqueue = queue.Queue()
        self.connectedEvent = threading.Event()
        # Callbeack function for connection events.  Passes True for connected
        # and False for disconnected
        self.connectCallback = None
        self.dataCallback = None

    def connectedState(self, connected):
        if connected:
            self.connectedEvent.set()
        else:
            self.connectedEvent.clear()
        if self.connectCallback != None:
            self.connectCallback(connected)

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
                if x[2][4] == "1": s += "s";
                x[2] = s
            #self.dataqueue.put(x)
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
                log.debug("Connected to {0}:{1}".format(self.host, self.port))
                self.connectedState(True)

                buff = ""
                while True:
                    try:
                        data = self.s.recv(1024)
                    except socket.timeout:
                        if self.getout:
                            self.connectedState(False)
                            self.s.close()
                            break;
                    except Exception as e:
                        log.error("Receive Failure {0}".format(e))
                        break
                    else:
                        if not data:
                            log.error("No Data, Bailing Out")
                            self.connectedState(False)
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
                                        # TODO: Print file and line number here.  Use traceback module
                                        log.error("Error handling request {} - {}".format(buff, e))
                                    buff = ""
                                else:
                                    buff += d
            if self.getout:
                self.connectedState(False)
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

    def isConnected(self):
        return self.connectedEvent.isSet()

    def getResponse(self, c, timeout = 1.0):
        # TODO Check for errors and report those as well
        if not self.isConnected():
            raise ResponseError("Not Connected to Server")
        try:
            x = self.cmdqueue.get(timeout = 1.0)
            while x[0] != c:
                x = self.cmdqueue.get(timeout = 1.0)
            return x
        except queue.Empty:
            raise ResponseError("Timeout waiting on data")

    def send(self, s):
        if not self.isConnected():
            raise NotConnectedError("Not Connected to Server")
        self.s.send(s)


def decodeDataString(d):
    x = d.split(';')
    id = x[0]
    v = x[1]
    if len(x) == 3:
        f = "" # Quality Flags
        if x[2][0] == '1': f += "a"
        if x[2][1] == '1': f += "o"
        if x[2][2] == '1': f += "b"
        if x[2][3] == '1': f += "f"
        if x[2][4] == '1': f += "s"
        return (id,v,f)
    else:
        return (id, v)


class Client:
    def __init__(self, host, port, timeout=1.0):
        self.cthread = ClientThread(host, port)
        self.cthread.timeout = timeout
        self.cthread.daemon = True
        self.lock = threading.Lock()

    def connect(self):
        self.cthread.start()
        return self.cthread.connectWait()

    def disconnect(self):
        self.cthread.stop()
        # TODO: Block unit disconnected.

    def isConnected(self):
        return self.cthread.isConnected()

    def setDataCallback(self, func):
        self.cthread.dataCallback = func

    def clearDataCallback(self):
        self.cthread.dataCallback = None

    def setConnectCallback(self, func):
        self.cthread.connectCallback = func

    def clearConnectCallback(self):
        self.cthread.connectCallback = None

    def getList(self):
        with self.lock:
            self.cthread.send("@l{}\n".format(id).encode())
            res = self.cthread.getResponse('l')
            # TODO: Deal with partial list responses
        a = res[1].split(';')
        return a[2].split(',')

    def getReport(self, id):
        with self.lock:
            self.cthread.send("@q{}\n".format(id).encode())
            res = self.cthread.getResponse('q')
            if '!' in res[1]:
                e = res[1].split('!')
                if e[1] == '001':
                    raise ResponseError("Key Not Found {}".format(e[0]))
                else:
                    raise ResponseError("Response Error {} for {}".format(e[1], e[0]))
            a = res[1].split(';')
            return a

    def read(self, id):
        with self.lock:
            self.cthread.send("@r{}\n".format(id).encode())
            res = self.cthread.getResponse('r')
            return decodeDataString(res[1])

    def write(self, id, value, flags=""):
        with self.lock:
            a = "1" if 'a' in flags else "0"
            b = "1" if 'b' in flags else "0"
            f = "1" if 'f' in flags else "0"
            s = "1" if 's' in flags else "0"
            sendStr = "{0};{1};{2}{3}{4}{5}\n".format(id, value, a, b, f, s)
            self.cthread.send(sendStr.encode())


    def subscribe(self, id):
        with self.lock:
            self.cthread.send("@s{}\n".format(id).encode())
            res = self.cthread.getResponse('s')

    def unsubscribe(self, id):
        with self.lock:
            self.cthread.send("@u{}\n".format(id).encode())
            res = self.cthread.getResponse('u')

    def flag(self, id, flag, setting):
        with self.lock:
            if setting: s = '1'
            else:       s = '0'
            self.cthread.send("@f{};{};{}\n".format(id, flag.lower(), s).encode())
            res = self.cthread.getResponse('f')
            if '!' in res[1]:
                e = res[1].split('!')
                if e[1] == '001':
                    raise ResponseError("Key Not Found {}".format(e[0]))
                elif e[1] == '002':
                    raise ResponseError("Unknown Flag {}".format(flag))
                else:
                    raise ResponseError("Response Error {} for {}".format(e[1], e[0]))

    def writeValue(self, id, value):
        with self.lock:
            self.cthread.send("@w{};{}\n".format(id, value).encode())
            res = self.cthread.getResponse('w')
            return res[1]

    def getStatus(self):
        with self.lock:
            self.cthread.send("@xstatus\n".encode())
            res = self.cthread.getResponse('x')
        return res[1][7:]

    def stop(self):
        with self.lock:
            self.cthread.send("@xkill\n".encode())
            res = self.cthread.getResponse('x')
