#  Copyright (c) 2016 Phil Birkelbach
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

from collections import OrderedDict
import fixgw.database as database
import logging

try:
    import psutil
except:
    psutil = None

__status = None


class Status:
    def __init__(self, plugins, config_status):
        self.plugins = plugins
        self.version = "0.2"
        self.db_item_count = len(database.listkeys())
        self.config_status = config_status

    def get_dict(self):
        result = OrderedDict({"Version": self.version})
        result.update(self.config_status)
        result.update(get_system_status())
        # Database information
        db = {"Item Count": self.db_item_count}
        result["Database Statistics"] = db
        # Add plugin status
        for name in self.plugins:
            d = OrderedDict({"Running": self.plugins[name].is_running()})
            x = self.plugins[name].get_status()
            if x:
                d.update(x)
            result["Connection: " + name] = d
        return result


if psutil != None:

    def get_system_status():
        p = psutil.Process()
        d = OrderedDict()
        d["CPU Percent"] = "%.2f" % p.cpu_percent()
        d["Memory Percent"] = "%.2f" % p.memory_percent()
        return {"Performance": d}

else:

    def get_system_status():
        return {}


def get_object():
    return __status


def initialize(p, ss):
    global __status
    global log
    __status = Status(p, ss)
    log = logging.getLogger(__name__)
    if psutil == None:
        log.info("psutil package not found.  No system stats will be available.")


def get_dict():
    return __status.get_dict()


def dict2string(d, indent=0, spaces=3):
    s = " " * indent * spaces
    result = ""
    for each in d:
        if type(d[each]) in [dict, OrderedDict]:
            result += s + each + "\n"
            result += dict2string(d[each], indent + 1, spaces)
        else:
            result += "{0}{1}: {2}\n".format(s, each, d[each])
    return result


def get_string():
    d = __status.get_dict()
    s = dict2string(d)
    return s
