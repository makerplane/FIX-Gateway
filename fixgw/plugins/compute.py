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

#  This is a compute plugin.  It calculates derivative points like averages,
#  minimums or maximums and the like.  Specific calculations for things like
#  True Airspeed could be done also.

from collections import OrderedDict
import fixgw.plugin as plugin

# Determines the average of the inputs and writes that to output
def averageFunction(inputs, output):
    vals = {}
    for each in inputs:
        vals[each] = None

    def func(key, value, parent):
        nonlocal vals
        o = parent.db_get_item(output)
        # This is to set the aux data in the output to one of the inputs
        if type(value) != tuple:
            x = key.split('.')
            # we use the first input in the list to set the aux values
            if x[0] == inputs[0]:
                if o.get_aux_value(x[1]) != value:
                    o.set_aux_value(x[1], value)
            return

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
        o.value = arrsum / len(vals)
        o.fail = flag_fail
        if o.fail: o.value = 0.0
        o.bad = flag_bad
        o.old = flag_old
    return func


def sumFunction(inputs, output):
    """Determines the sum of the inputs and writes that to output"""
    vals = {}
    for each in inputs:
        vals[each] = None
    def func(key, value, parent):
        if type(value) != tuple: return # This might be a meta data update
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
            try:
                arrsum += vals[each][0]
                if vals[each][2]: flag_old = True
                if vals[each][3]: flag_bad = True
                if vals[each][4]: flag_fail = True
            except TypeError:
                print("WTF {} {}".format(key, value))
                raise
        o = parent.db_get_item(output)
        o.value = arrsum
        o.fail = flag_fail
        if o.fail: o.value = 0.0
        o.bad = flag_bad
        o.old = flag_old
    return func


# Determines the max of the inputs and writes that to output
def maxFunction(inputs, output):
    vals = {}
    for each in inputs:
        vals[each] = None
    def func(key, value, parent):
        nonlocal vals
        # This is to set the aux data in the output to one of the inputs
        o = parent.db_get_item(output)
        if type(value) != tuple:
            x = key.split('.')
            # we use the first input in the list to set the aux values
            if x[0] == inputs[0]:
                if o.get_aux_value(x[1]) != value:
                    o.set_aux_value(x[1], value)
            return
        vals[key] = value
        flag_old = False
        flag_bad = False
        flag_fail = False
        vmax = None
        for each in vals:
            if vals[each] is None:
                return  # We don't have one of each yet
            if vmax:
                if vals[each][0] > vmax: vmax = vals[each][0]
            else:  # The first time through we just set vmax to the value
                vmax = vals[each][0]
            if vals[each][2]: flag_old = True
            if vals[each][3]: flag_bad = True
            if vals[each][4]: flag_fail = True
        o.value = vmax
        o.fail= flag_fail
        if o.fail: o.value = 0.0
        o.bad = flag_bad
        o.old = flag_old
    return func


# Determines the min of the inputs and writes that to output
def minFunction(inputs, output):
    vals = {}
    for each in inputs:
        vals[each] = None
    def func(key, value, parent):
        nonlocal vals
        # This is to set the aux data in the output to one of the inputs
        o = parent.db_get_item(output)
        if type(value) != tuple:
            x = key.split('.')
            # we use the first input in the list to set the aux values
            if x[0] == inputs[0]:
                if o.get_aux_value(x[1]) != value:
                    o.set_aux_value(x[1], value)
            return
        vals[key] = value
        flag_old = False
        flag_bad = False
        flag_fail = False
        vmin = None
        for each in vals:
            if vals[each] is None:
                return  # We don't have one of each yet
            if vmin:
                if vals[each][0] < vmin: vmin = vals[each][0]
            else:  # The first time through we just set vmax to the value
                vmin = vals[each][0]
            if vals[each][2]: flag_old = True
            if vals[each][3]: flag_bad = True
            if vals[each][4]: flag_fail = True
        o.value = vmin
        o.fail= flag_fail
        if o.fail: o.value = 0.0
        o.bad = flag_bad
        o.old = flag_old
    return func

# Determines the span between the highest and lowest of the inputs
# and writes that to output
def spanFunction(inputs, output):
    vals = {}
    for each in inputs:
        vals[each] = None
    def func(key, value, parent):
        nonlocal vals
        if type(value) != tuple: return # This might be a meta data update
        vals[key] = value
        flag_old = False
        flag_bad = False
        flag_fail = False
        vmin = None
        for each in vals:
            if vals[each] is None:
                return  # We don't have one of each yet
            if vmin:
                if vals[each][0] < vmin: vmin = vals[each][0]
                if vals[each][0] > vmax: vmax = vals[each][0]
            else:  # The first time through we just set vmax to the value
                vmin = vals[each][0]
                vmax = vals[each][0]

            if vals[each][2]: flag_old = True
            if vals[each][3]: flag_bad = True
            if vals[each][4]: flag_fail = True
        o = parent.db_get_item(output)
        o.value = vmax - vmin
        o.fail= flag_fail
        if o.fail: o.value = 0.0
        o.bad = flag_bad
        o.old = flag_old
    return func


class Plugin(plugin.PluginBase):
    # def __init__(self, name, config):
    #     super(Plugin, self).__init__(name, config)

    def run(self):
        # This directory of functions are functions that aggregate a list
        # of inputs and produce a single output.
        aggregate_functions = {"average":averageFunction,
                               "sum":sumFunction,
                               "max":maxFunction,
                               "min":minFunction,
                               "span":spanFunction
                               }

        for function in self.config["functions"]:
            fname = function["function"].lower()
            if fname in aggregate_functions:
                f = aggregate_functions[fname](function["inputs"], function["output"])
                for each in function["inputs"]:
                    self.db_callback_add(each, f, self)

            else:
                self.log.warning("Unknown function - {}".format(function["function"]))

    def stop(self):
        pass


    # def get_status(self):
    #     """ The get_status method should return a dict or OrderedDict that
    #     is basically a key/value pair of statistics"""
    #     return OrderedDict({"Count":self.thread.count})

# TODO: Add a check for Warns and alarms and annunciate appropriatly
# TODO: Add tests for this plugin
# TODO: write stop function to remove all the callbacks
