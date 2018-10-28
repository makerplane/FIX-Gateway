#!/usr/bin/env python3

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
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
#  USA.import plugin

#  This file serves as a starting point for a plugin.  This is a Thread based
#  plugin where the main Plugin class creates a thread and starts the thread
#  when the plugin's run() function is called.

import time
from collections import OrderedDict
import fixgw.plugin as plugin


def averageFunction(inputs, output):
    vals = {}
    for each in inputs:
        vals[each] = None
    def func(key, value, parent):
        print("Callback Called")
        nonlocal vals
        nonlocal output
        vals[key] = value
        arrsum = 0
        flags = ""
        for each in vals:
            if vals[each] is None:
                return  # We don't have one of each yet
            arrsum += vals[each][0]
            if vals[each][2]: flags += 'O'
            if vals[each][3]: flags += 'B'
            if vals[each][4]: flags += 'F'

        i = parent.db_get_item(output)
        i.value = arrsum / len(vals)
        if "F" in flags:
            i.fail = True
            i.value = 0.0
        else:
            i.fail = False
        if "B" in flags:
            i.bad = True
        else:
            i.bad = False
        if "O" in flags:
            i.old = True
        else:
            i.old = False

    return func

class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)

    def run(self):
        for function in self.config["functions"]:
            if function["function"].lower() == 'average':
                f = averageFunction(function["inputs"], function["output"])
                for each in function["inputs"]:
                    self.db_callback_add(each, f, self)


    def stop(self):
        pass


    # def get_status(self):
    #     """ The get_status method should return a dict or OrderedDict that
    #     is basically a key/value pair of statistics"""
    #     return OrderedDict({"Count":self.thread.count})

# TODO: Add a check for Warns and alarms and annunciate appropriatly
# TODO:
