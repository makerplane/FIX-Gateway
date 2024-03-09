#!/usr/bin/env python

#  Copyright (c) 2019 Phil Birkelbach
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

#  This is a simple data simulation plugin.  It's mainly for demo purposese
#  It really has no function other than simple testing of displays

# TODO Make the keylist configurable
# TODO add some functions to change the values (noise, cyclic, reduction, etc)

import threading
import time
from collections import OrderedDict
import fixgw.plugin as plugin

class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self.keylist = {"ROLL":0.0, "PITCH":0.0, "IAS":113.0, "ALT":1153.0,
                        "TACH1":2450.0, "MAP1":24.2, "FUELP1":28.5, "OILP1":56.4,
                        "OILT1":95.0, "FUELQ1":11.2, "FUELQ2":19.8, "OAT": 32.0,
                        "CHT11":201.0,"CHT12":202.0,"CHT13":199.0,"CHT14":200.0,
                        "EGT11":710.0,"EGT12":700.0,"EGT13":704.0,"EGT14":702.0,
                        "FUELF1":8.7,"VOLT":13.7,"CURRNT":45.6,
                        "TAS":113,"ALAT":0.0,"HEAD":281.8,"LONG":-82.8550,"LAT":40.000200,
                        "CDI":0.0,"GSI":0.0,"COURSE":281.8
                        }
        self.script = [
            {"APMSG": "Roll/Pitch 0",     "ROLL": 0,   "PITCH": 0 },
            {"APMSG": "Roll/Pitch 10",    "ROLL": 10,  "PITCH": 10 },
            {"APMSG": "Roll/Pitch 20",    "ROLL": 20,  "PITCH": 20 },
            {"APMSG": "Roll/Pitch 10",    "ROLL": 10,  "PITCH": 10 },
            {"APMSG": "Roll/Pitch 0",     "ROLL": 0,   "PITCH": 0 },
            {"APMSG": "Roll/Pitch 10",    "ROLL": -10, "PITCH": -10 },
            {"APMSG": "Roll/Pitch 20",    "ROLL": -20, "PITCH": -20 },
            {"APMSG": "Roll/Pitch 10",    "ROLL": -10, "PITCH": -10 },
            {"APMSG": "Roll/Pitch 0",     "ROLL": 0,   "PITCH": 0 },
            {"APMSG": "PAPI 2 Red",       "ALT": 1153 },
            {"APMSG": "PAPI 1 Red",       "ALT": 1200 },
            {"APMSG": "PAPI 0 Red",       "ALT": 1250 },
            {"APMSG": "PAPI 1 Red",       "ALT": 1200 },
            {"APMSG": "PAPI 2 Red",       "ALT": 1153 },
            {"APMSG": "PAPI 3 Red",       "ALT": 1100 },
            {"APMSG": "PAPI 4 Red",       "ALT": 1050 },
            {"APMSG": "PAPI 3 Red",       "ALT": 1100 },
            {"APMSG": "PAPI 2 Red",       "ALT": 1153 },
            {"APMSG": "HEAD 281",         "HEAD": 281.8 },
            {"APMSG": "HEAD 254",         "HEAD": 254 },
            {"APMSG": "HEAD 234",         "HEAD": 234 },
            {"APMSG": "HEAD 214",         "HEAD": 214 },
            {"APMSG": "HEAD 194",         "HEAD": 194 },
            {"APMSG": "HEAD 174",         "HEAD": 174 },
            {"APMSG": "HEAD 154",         "HEAD": 154 },
            {"APMSG": "HEAD 134",         "HEAD": 134 },
            {"APMSG": "HEAD 114",         "HEAD": 114 },
            {"APMSG": "HEAD 94",          "HEAD": 94 },
            {"APMSG": "HEAD 74",          "HEAD": 74 },
            {"APMSG": "HEAD 54",          "HEAD": 54 },
            {"APMSG": "HEAD 34",          "HEAD": 34 },
            {"APMSG": "HEAD 14",          "HEAD": 14 },
            {"APMSG": "HEAD 0",           "HEAD": 0 },
            {"APMSG": "HEAD 14",          "HEAD": 14 },
            {"APMSG": "HEAD 34",          "HEAD": 34 },
            {"APMSG": "HEAD 54",          "HEAD": 54 },
            {"APMSG": "HEAD 74",          "HEAD": 74 },
            {"APMSG": "HEAD 94",          "HEAD": 94 },
            {"APMSG": "HEAD 114",         "HEAD": 114 },
            {"APMSG": "HEAD 134",         "HEAD": 134 },
            {"APMSG": "HEAD 154",         "HEAD": 154 },
            {"APMSG": "HEAD 174",         "HEAD": 174 },
            {"APMSG": "HEAD 194",         "HEAD": 194 },
            {"APMSG": "HEAD 214",         "HEAD": 214 },
            {"APMSG": "HEAD 234",         "HEAD": 234 },
            {"APMSG": "HEAD 254",         "HEAD": 254 },
            {"APMSG": "HEAD 281",         "HEAD": 281.8 },
            {"APMSG": "Landing",           "HEAD":281.8, "LONG": -82.8550, "LAT":40.000200, "ALT": 1153},
            {"APMSG": "Landing",           "HEAD":281.8, "LONG": -82.8650, "LAT":40.000750, "ALT": 1020},
            {"APMSG": "Landing",           "HEAD":281.8, "LONG": -82.8750, "LAT":40.001350, "ALT": 880},
            {"APMSG": "Landing",           "HEAD":281.8, "LONG": -82.8780, "LAT":40.001530, "ALT": 860},
            {"APMSG": "Landing",           "HEAD":281.8, "LONG": -82.8789, "LAT":40.00160, "ALT": 830},
            {"APMSG": "Reverse Landing",   "HEAD":281.8, "LONG": -82.8780, "LAT":40.001530, "ALT": 860},
            {"APMSG": "Reverse Landing",   "HEAD":281.8, "LONG": -82.8750, "LAT":40.001350, "ALT": 880},
            {"APMSG": "Reverse Landing",   "HEAD":281.8, "LONG": -82.8650, "LAT":40.000750, "ALT": 1020},
            {"APMSG": "Reverse Landing",   "HEAD":281.8, "LONG": -82.8550, "LAT":40.000200, "ALT": 1153},
            {"APMSG": "IAS/TAS 113",       "IAS": 113, "TAS": 113 },
            {"APMSG": "IAS/TAS 123",       "IAS": 123, "TAS": 123 },
            {"APMSG": "IAS/TAS 133",       "IAS": 133, "TAS": 133 },
            {"APMSG": "IAS/TAS 143",       "IAS": 143, "TAS": 143 },
            {"APMSG": "IAS/TAS 133",       "IAS": 133, "TAS": 133 },
            {"APMSG": "IAS/TAS 123",       "IAS": 123, "TAS": 123 },
            {"APMSG": "IAS/TAS 113",       "IAS": 113, "TAS": 113 },
            {"APMSG": "COURSE 281",         "COURSE": 281.8 },
            {"APMSG": "COURSE 254",         "COURSE": 254 },
            {"APMSG": "COURSE 234",         "COURSE": 234 },
            {"APMSG": "COURSE 214",         "COURSE": 214 },
            {"APMSG": "COURSE 194",         "COURSE": 194 },
            {"APMSG": "COURSE 214",         "COURSE": 214 },
            {"APMSG": "COURSE 234",         "COURSE": 234 },
            {"APMSG": "COURSE 254",         "COURSE": 254 },
            {"APMSG": "COURSE 281",         "COURSE": 281.8 },











        ]
        # Initialize the points
        for each in self.keylist:
            self.parent.db_write(each, self.keylist[each])

    def run(self):
        count = 0
        script_count = -1
        script_when = -1
        while not self.getout:
            count += 1
            script_when += 1
            time.sleep(0.1)
            # We just read the point and write it back in to reset the TOL timer
            for each in self.keylist:
                x = self.parent.db_read(each)
                self.parent.db_write(each, x)
            #continue
            #print(f"script_when:{script_when}, script_count:{script_count}")
            if script_when == 0:
                script_count += 1
                for k,v in self.script[script_count].items():
                    self.parent.db_write(k,v)
                    #print(f"{k}={v}")
                if script_count +1 == len(self.script):
                    script_count = -1
            else:
                if script_count  < len(self.script):
                    for k,v in self.script[script_count].items():
                        if not isinstance(v, str):
                            if self.script[script_count + 1].get(k,None) != None:
                                val = ( ( ( self.script[script_count + 1][k] - v ) / 20 ) * script_when ) + v
                                #print(f"{script_when}: next: {self.script[script_count + 1][k]}, cur:{v}, val:{val}")
                                self.parent.db_write(k,val)
                if script_when == 19:
                    script_when = -1
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
