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
        nonlocal vals
        nonlocal output
        vals[key] = value
        arrsum = 0
        flag_old = False
        flag_bad = False
        flag_fail = False
        for each in vals:
            if vals[each] is None:
                return  # We don't have one of each yet
            arrsum += vals[each][0]
            if vals[each][2]: flag_old = True
            if vals[each][3]: flag_bad = True
            if vals[each][4]: flag_fail = True
        i = parent.db_get_item(output)
        i.value = arrsum / len(vals)
        i.fail= flag_fail
        if i.fail: i.value = 0.0
        i.bad = flag_bad
        i.old = flag_old

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
