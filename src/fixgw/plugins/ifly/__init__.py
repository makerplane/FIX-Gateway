#  Copyright (c) 2023 Eric Blevins
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

import threading
from collections import OrderedDict
import fixgw.plugin as plugin
import socket
import pynmea2
import re


# This plugin should be considered experimental
# Use at your own risk
# At this time it has seen no real-world use and testing
#
#
# This plugin listens for NMEA data sent to port 2000 from the iFly EFB app.
# When configuring ifly, the only NMEA data we need is RMB and APB
# At this time it does not seem possible to capture altitude data for waypoints
# This plugin only captures the next destination not the entire flight plan
# It is possible to get the data about the entire plan so this could be
# a future enhancement.
#
# The data is stored into three FIX database keys:
# WPNAME = the name of the waypoint
# WPLON = longitude of the waypoint
# WPLAT = latitude of the waypoint


# Potential issues:
#  Getting iFly to send to the FIX gateway might be a problem, it only seems to send to
#  the address 192.168.1.1
#  If you run iFly on waydroid and have waydroid running on the same computer
#  as the Fix gateway you can add that IP address to the waydroid0 interface
#  and this plugin will pickup the data from iFly
#
#  sudo ip addr add 192.168.1.1/24 dev waydroid0
#
#  Once when I inserted a new stop into the flight plan I observed the destination programmed into
#  the flight controller flipping back and forth between the old and new destination
#  I have since been unable to reproduce this error

from pynmea2 import nmea_utils


class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        print("running ifly plugin")
        self.getout = False  # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging

        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.bind(("192.168.1.1", 2000))

    def run(self):

        while not self.getout:
            msg, (adr, port) = self.s.recvfrom(8192)

            if len(msg) < 1 or not self.parent.quorum.leader:
                continue
            nmea_msg = re.findall(r"\$.*$", msg.decode(errors="ignore"), re.M)
            if len(nmea_msg) > 0:
                try:
                    data = pynmea2.parse(nmea_msg[0])
                except:
                    continue
                # print(repr(data))
                if not hasattr(data, "sentence_type"):
                    continue
                if data.sentence_type == "RMB":
                    # Info about destination, only sent when waypoint is active
                    lat = -1
                    lon = -1
                    if data.dest_lat_dir == "N":
                        lat = 1
                    if data.dest_lon_dir == "E":
                        lon = 1
                    self.parent.db_write(
                        "WPLAT", lat * nmea_utils.dm_to_sd(data.dest_lat)
                    )
                    self.parent.db_write(
                        "WPLON", lon * nmea_utils.dm_to_sd(data.dest_lon)
                    )

                    self.parent.db_write("WPNAME", data.dest_waypoint_id.ljust(5)[:5])

                elif data.sentence_type == "APB":
                    head_type = ""
                    if data.heading_to_dest_type == "T":
                        head_type = " True"
                    elif data.heading_to_dest_type == "M":
                        head_type = " Mag"
                    self.parent.db_write("WPHEAD", f"{data.heading_to_dest}{head_type}")

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
