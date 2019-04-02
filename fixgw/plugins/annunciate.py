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

import operator
from collections import OrderedDict
import fixgw.plugin as plugin


class AnnunciateItem(object):
    operators = {"<":operator.lt,
                 "<=":operator.le,
                 "=":operator.eq,
                 "!=":operator.ne,
                 ">":operator.gt,
                 ">=":operator.ge}

    def __init__(self, plugin, defaults, itemdef):
        self.plugin = plugin
        self.key = itemdef["key"]
        self.item = plugin.db_get_item(self.key)
        if self.item is None:
            raise ValueError("Key {} not found".format(self.key))
        low_point = defaults["low_aux_point"] if "low_aux_point" in defaults else None
        self.low_aux_point = itemdef["low_aux_point"] if "low_aux_point" in itemdef else low_point
        high_point = defaults["high_aux_point"] if "high_aux_point" in defaults else None
        self.high_aux_point = itemdef["high_aux_point"] if "high_aux_point" in itemdef else high_point
        low_bypass = defaults["low_bypass"] if "low_bypass" in defaults else None
        self.low_bypass = itemdef["low_bypass"] if "low_bypass" in itemdef else low_bypass

        deadband = defaults["deadband"] if "deadband" in defaults else None
        deadband = itemdef["deadband"] if "deadband" in itemdef else deadband
        if type(deadband) == str and '%' in deadband:
            db = float(deadband.replace("%", "").strip()) / 100
            self.deadband = abs(db * (self.item.max - self.item.min))
        else:
            self.deadband = float(deadband)

        cond_bypass = defaults["cond_bypass"] if "cond_bypass" in defaults else None
        self.cond_bypass = itemdef["cond_bypass"] if "cond_bypass" in itemdef else cond_bypass
        if self.cond_bypass == "None": self.cond_bypass = None
        if self.cond_bypass is not None:
            tokens = self.cond_bypass.split()
            if len(tokens) != 3:
                #self.plugin.log.error("Wrong number of tokens given for conditional bypass: {}".format(self.key))
                raise ValueError("Wrong number of tokens given for conditional bypass: {}".format(self.key))
            self.cond_item = plugin.db_get_item(tokens[0])
            if self.cond_item is None:
                raise ValueError("Unknown Key {} for conditional bypass: {}".format(tokens[0], self.key))
            try:
                self.cond_oper = self.operators[tokens[1]]
            except KeyError:
                raise ValueError("Unknown operator {} for conditional bypass: {}".format(tokens[1], self.key))
            self.cond_value = self.cond_item.dtype(tokens[2])

        plugin.db_callback_add(self.key, self.evaluate)

    def evaluate(self,k, x, udata):
        print("{} = {}".format(self.key, x[0]))


    def __str__(self):
        s = []
        s.append(self.key)
        s.append("  Low Aux Point Name: {}".format(self.low_aux_point))
        s.append("  High Aux Point Name: {}".format(self.high_aux_point))
        s.append("  Deadband: {}".format(self.deadband))
        s.append("  Low Bypass Enabled: {}".format("Yes" if self.low_bypass else "No"))
        s.append("  Conditional Bypass: {}".format(self.cond_bypass))
        return "\n".join(s)

class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.items = []

    def run(self):
        # This directory of functions are functions that aggregate a list
        # of inputs and produce a single output.
        for item in self.config["items"]:
            i = AnnunciateItem(self, self.config["defaults"], item)
            self.items.append(i)

    def stop(self):
        pass

    def get_status(self):
        """ The get_status method should return a dict or OrderedDict that
        is basically a key/value pair of statistics"""
        return OrderedDict({"Item Count":len(self.items)})

# TODO: Add a check for Warns and alarms and annunciate appropriatly
# TODO: Add tests for this plugin
# TODO: write stop function to remove all the callbacks
