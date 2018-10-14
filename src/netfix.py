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
#import queue

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

    def handle_request(self, d):
        print(d)

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

                buff = ""
                while True:
                    try:
                        data = self.s.recv(1024)
                    except socket.timeout:
                        if self.getout:
                            break;
                    except Exception as e:
                        log.debug("Receive Failure {0}".format(e))
                        break
                    else:
                        if not data:
                            log.debug("No Data, Bailing Out")
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
                log.debug("ClientThread - Exiting")
                break
            else:
                # TODO: Replace with configuration time
                time.sleep(2)
                log.debug("Attempting to Reconnect to {0}:{1}".format(self.host, self.port))

    def stop(self):
        self.getout = True

    def send(self, s):
        # TODO: Deal with errors gracefully
        try:
            self.s.send(s)
        except Exception as e:
            log.error(e)


class Client:
    def __init__(self, host, port, timeout=1.0):
        self.cthread = ClientThread(host, port)
        self.cthread.timeout = timeout

    def connect(self):
        self.cthread.start()
        # TODO: Block until connected???

    def disconnect(self):
        self.cthread.stop()

    def read(self, id):
        self.cthread.send("@r{}\n".format(id).encode())

if __name__ == "__main__":
    logging.basicConfig()
    log.level = logging.DEBUG
    c = Client("localhost", 3490)
    c.connect()
    time.sleep(10.0)
    c.read("IAS")
    c.disconnect()
