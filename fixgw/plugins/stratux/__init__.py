#!/usr/bin/env python

#  Copyright (c) 2019 Garrett Herschleb
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

import urllib.request as request
import json
import threading
import os
import time
from collections import OrderedDict

import fixgw.plugin as plugin

MIN_GPS_FIX_QUALITY = 3
MAGIC_NUMBER_INVALID=3276.7
stratux_map = {
        'AHRSPitch' : 'PITCH'
       ,'AHRSRoll' : 'ROLL'
       ,'AHRSMagHeading' : 'HEAD'
       ,'AHRSSlipSkid' : 'ALAT'
       ,'AHRSTurnRate' : 'ROT'
       ,'AHRSGLoad' : 'ANORM'
       ,'GPSLatitude' : 'LAT'
       ,'GPSLongitude' : 'LONG'
       ,'GPSTrueCourse' : 'TRACK'
       ,'GPSGroundSpeed' : 'GS'
       ,'BaroVerticalSpeed' : 'VS'
       ,'GPSAltitude' : 'ALT'
}

class StratuxClient(threading.Thread):
    def __init__(self, parent, host, rate):
        super(StratuxClient, self).__init__()
        self.host = host
        self.update_period = 1.0 / rate
        self.parent = parent
        self.db_items = dict()
        for k,v in self.parent.config['situation_report'].items():
            self.db_items[k] = self.parent.db_get_item(v)
        self.requests = 0
        self.received = 0
        self.conn_failures = 0
        self.bad_msgs = 0
        self.ahrs_status = False
        self.gps_status = False

    def run(self):
        next_update = time.time()
        while not self.parent.getout:
            try:
                r = request.urlopen('http://%s/getSituation'%self.host
                    ,timeout=0.1)
                self.requests += 1;
            except Exception as e:
                self.parent.log.error ("Failed to Connect Stratux: %s"%str(e))
                self.conn_failures += 1
                r = None

            if r is not None:
                response_str = ''
                try:
                    while not r.isclosed():
                        response_str += r.read(1024).decode('utf-8')
                except Exception as e:
                    self.parent.log.error ("Read Failure: %s"%str(e))
                    break
                try:
                    data = json.loads(response_str)
                    self.received += 1
                except Exception as e:
                    self.parent.log.error("Bad Message Received")
                    self.bad_msgs += 1
                self.ahrs_status = True if (data['AHRSStatus'] & 0x01) else False
                # AHRSStatus bitmask values:
                #  dcba
                #   a = IMU is providing data. 1=yes,0=no.
                #   b = Pressure sensor is providing data. 1=yes,0=no.
                #   c = IMU is calibrating. 1=yes,0=no.
                #   d = data is being logged to CSV. 1=yes,0=no.
                self.gps_status = data['GPSFixQuality'] > MIN_GPS_FIX_QUALITY
                for k,v in self.db_items.items():
                    if k.startswith('GPS'):
                        if self.gps_status:
                            v.value = data[k]
                            v.fail = False
                        else:
                            v.value = 0
                            v.fail = True
                    else:
                        if self.ahrs_status:
                            if data[k] == MAGIC_NUMBER_INVALID:
                                v.value = 0
                                v.fail = True
                            else:
                                v.fail = False
                                if 'Heading' in k:
                                    v.value = data[k] % 360
                                else:
                                    v.value = data[k]
            next_update += self.update_period
            sleep_time = next_update - time.time()
            if sleep_time <= 0:
                next_update = time.time()
            else:
                time.sleep(sleep_time)

class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.getout = False
        self.config = config
        self.host = self.config['host']
        self.rate = float(self.config['rate'])
        self.clientThread = None

    def run(self):
        # This loop checks to see if we have each item in the database
        # if not then we'll just let it get set to None and ignore it when
        # we parse the string from FlightGear
        self.clientThread = StratuxClient(self
                     ,self.host
                     ,self.rate)
        self.clientThread.start()

    def stop(self):
        if self.clientThread is not None:
            self.getout = True
            try:
                self.clientThread.stop()
            except AttributeError:
                pass
            if self.clientThread.is_alive():
                self.clientThread.join(2.0)
            if self.clientThread.is_alive():
                raise plugin.PluginFail

    def get_status(self):
        d = OrderedDict()
        # For stuff that might fail we just ignore the errors and get what we get
        try:
            d["Stratux Host"] = "{}".format(self.clientThread.host)
            d["Connection Failures"] = self.clientThread.conn_failures
            d["Messages"] = OrderedDict([
                                        ("Requests Sent",self.clientThread.requests),
                                        ("Valid Responses",self.clientThread.received),
                                        ("Bad Responses", self.clientThread.bad_msgs)
                                        ])
            d["GPS Status"] = "Good" if self.clientThread.gps_status else "Failed"
            d["AHRS Status"] = "Good" if self.clientThread.ahrs_status else "Failed"
        except:
            pass

        return d
