#!/usr/bin/python

import socket
import time

UDP_IP = "127.0.0.1"
UDP_PORT = 6789

sock = socket.socket(socket.AF_INET,  # Internet
                     socket.SOCK_DGRAM)  # UDP
sock.bind((UDP_IP, UDP_PORT))

starttime = time.time()
lasttime = starttime
throttle = 0

while True:
    data, addr = sock.recvfrom(1024)  # buffer size is 1024 bytes
    print(data)
    thistime = time.time()
    if thistime - lasttime > 5:
        throttle = throttle + 0.05
        if throttle > 1:
            throttle = 0.0
        ss = "%0.4f,\n" % (throttle,)
        print(ss)
        sock.sendto(ss, (UDP_IP, UDP_PORT + 1))
        lasttime = thistime