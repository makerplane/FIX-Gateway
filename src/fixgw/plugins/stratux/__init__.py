import threading
from collections import OrderedDict
import fixgw.plugin as plugin
from fixgw.plugins.stratux import gdl90
import socket
import struct
import math


class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        print("running stratux plugin")
        self.getout = False  # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging

        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(("", 4000))

    def run(self):

        while not self.getout:
            msg, adr = self.s.recvfrom(8192)
            msg = gdl90.decodeGDL90(msg)

            if len(msg) < 1:
                continue

            if msg[0] == 0x4C:
                roll = struct.unpack(">h", msg[4:6])[0] / 10.0
                pitch = struct.unpack(">h", msg[6:8])[0] / 10.0
                heading = struct.unpack(">h", msg[8:10])[0] / 10.0
                slipskid = struct.unpack(">h", msg[10:12])[0] / 10.0
                yawrate = struct.unpack(">h", msg[12:14])[0] / 10.0  # noqa: F841
                g = struct.unpack(">h", msg[14:16])[0] / 10.0  # noqa: F841
                ias = struct.unpack(">h", msg[16:18])[0] / 10.0  # noqa: F841
                alt = struct.unpack(">h", msg[18:20])[0] - 5000.5
                vs = struct.unpack(">h", msg[20:22])[0]

                self.parent.db_write("PITCH", pitch)
                self.parent.db_write("ROLL", roll)
                self.parent.db_write("HEAD", heading)

                self.parent.db_write("ALAT", -math.sin(slipskid * math.pi / 180))
                self.parent.db_write("ALT", alt)
                self.parent.db_write("VS", vs)
            elif msg[0] == 0x0A:
                # ownship report
                alt = struct.unpack(">h", msg[11:13])[0]
                tmp = struct.unpack("BB", msg[14:16])
                gnd_speed = (tmp[0] << 4) | (tmp[1] >> 4)
                self.parent.db_write("IAS", gnd_speed)

        self.running = False

    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self)
        self.status = OrderedDict()

    def run(self):

        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(1.0)
        if self.thread.is_alive():
            raise plugin.PluginFail

    def get_status(self):
        return self.status
