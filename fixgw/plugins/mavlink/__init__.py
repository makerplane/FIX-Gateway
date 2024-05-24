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

# This plugin will connect to a hobby flight controler such as Ardupilot/pixhawk.
# It uses the mavlink protocol to communicate
# The primary use for this is a source of accurate GPS, AHRS and airspeed data
# Connected to servo controlled trim tabs some of the auto pilot features
# might be usable.
#
# This code has not seen any real-world testing
# Use at your own risk!!!
# If you do not understand what the code does and trust it then you should not use it!

import threading
import time
import logging
from collections import OrderedDict
import fixgw.plugin as plugin
from fixgw.plugins.mavlink.Mav import Mav

import math

class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        #print("running mavlink plugin")
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self.config = parent.config

        # Trims -1000 to 1000
        self.pitch = 0
        self.yaw = 0
        self.roll = 0

        # The modes we can request:
        self.req = {
          'TRIM': False,
          'CRUISE': False,
          'AUTOTUNE': False,
          'GUIDED': False,
        }

    # Callback to set the requested mode
    # Only once mode can be set at a time.
    def getRequestFunction(self,mode):
        def requestCallback(fixkey, value, udata):
            for f in self.req:
                if f"MAVREQ{f}" == fixkey:
                    self.req[f] = value[0]
                else:
                    # Only change others to false if
                    # key is getting set to True
                    if value[0]:
                        self.req[f] = False
        return requestCallback

    def run(self):
        self._type = self.config['type']
        self.baud = int(self.config['baud']) if ( 'baud' in self.config) else 57600
        self.port = self.config['port'] if ( 'port' in self.config) else '/dev/ttyACM0'
        self.options = self.config['options'] if ( "options" in self.config) else {}
        
        for f in self.req:
            self.parent.db_callback_add(f"MAVREQ{f}",self.getRequestFunction(f))

        while not self.getout:
            time.sleep(0.00001)
            try:
                print("Mav init")
                self.conn = Mav(self.parent, port=self.port, baud=self.baud, options=self.options)
            except Exception as e:
                try:
                    print(e) 
                    self.conn.close()
                except Exception:
                    self.log.debug(f"Mavlink failed to connect")
 
                self.log.debug(f"Mavlink failed to connect, trying again in 1 second type: {self._type} port: {self.port} baud: {self.baud}")
                self.log.debug(e)
                time.sleep(1)      
                continue
            self.log.debug("Wait for heartbeat")
            try: self.conn.wait_heartbeat()
            except Exception as e:
                self.conn.close()
                self.log.debug(f"Mavlink failed wait_heartbeat")
                self.log.debug(e)
                time.sleep(1)
                continue

            self.log.debug("processing messages")
            loopc = 1
            while not self.getout:
                time.sleep(0.001)
                try:
                    self.conn.process()
                    self.conn.sendTrims()
                    # Processing AHRS and Trim is more important than
                    # changing auto pilot modes
                    # So we only deal with the AP once every 10 cycles
                    if loopc > 10:
                        self.conn.checkMode(self.req)
                        loopc = 0
                    loopc += 1
                except Exception as e:
                    self.conn.close()
                    self.log.debug(f"Mavlink failed while processing messages")
                    self.log.debug(e)
                    time.sleep(1)
                    break
            self.running = False

    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        if config['type'] == 'serial':
          self.thread = MainThread(self)
          self.status = OrderedDict()   
        else:
            raise ValueError("Only serial type is implemented")

    def run(self):

        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            try:
                self.thread.join(1.0)
            except:
                pass
        if self.thread.is_alive():
            raise plugin.PluginFail

    def get_status(self):
        return self.status

