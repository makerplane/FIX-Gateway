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

import fixgw.database as database
from collections import OrderedDict


def initialize(p):
    global plugins
    plugins = p

def get_dict():
    result = OrderedDict({"Version":"0.2"})
    # Database information
    db = {"Item Count":len(database.listkeys())}

    result["Database Statistics"] = db
    # Add plugin status
    for name in plugins:
        d = OrderedDict({"Running":plugins[name].is_running()})

        x = plugins[name].get_status()
        if x: d.update(x)
        result["Plugin-" + name] = d
    return result

def dict2string(d, indent = 0):
    s = "  " * indent
    result = ""
    for each in d:
        if type(d[each]) in [dict, OrderedDict]:
            result += s + each + "\n"
            result += dict2string( d[each], indent+1 )
        else:
            result += "{0}{1}: {2}\n".format(s, each, d[each])
    return result

def get_string():
    d = get_dict()
    s = dict2string(d)
    return s
