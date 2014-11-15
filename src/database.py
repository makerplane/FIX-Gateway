#!/usr/bin/env python

#  Copyright (c) 2014 Phil Birkelbach
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

import logging

__database = {}

log = logging.getLogger('database')
log.info("Initializing")


class db_item:
    def __init__(self, value=None):
        self.value = value
        self.quality = False
        self.max = None
        self.min = None
        self.callbacks = {}

__database["IAS"] = db_item(0.0)
__database["TAS"] = db_item(0.0)
__database["ALT"] = db_item(0.0)
__database["TALT"] = db_item(0.0)
__database["OAT"] = db_item(0.0)
__database["BARO"] = db_item(29.92)
__database["ROLL"] = db_item(0.0)
__database["PITCH"] = db_item(0.0)
__database["YAW"] = db_item(0.0)
__database["AOA"] = db_item(0.0)
__database["LAT"] = db_item(0.0)
__database["LONG"] = db_item(0.0)
__database["CTLPTCH"] = db_item(0.0)
__database["CTLROLL"] = db_item(0.0)
__database["CTLYAW"] = db_item(0.0)
__database["CTLFLAP"] = db_item(0.0)
__database["CTLLBRK"] = db_item(0.0)
__database["CTLRBRK"] = db_item(0.0)
__database["THR1"] = db_item(0.0)
__database["THR2"] = db_item(0.0)
__database["PROP1"] = db_item(0.0)
__database["PROP2"] = db_item(0.0)
__database["MIX1"] = db_item(0.0)
__database["MIX2"] = db_item(0.0)

def write(index, value):
    if index in __database:
        __database[index].value = value
    else:
        raise KeyError


def read(index):
    #try:
        return __database[index].value
    #except KeyError:
    #    return None


def listkeys():
    return list(__database.keys())


def callback_add(name, key, function, udata):
    log.debug("Adding callback function for %s on key %s" % (name, key))


def callback_del(name, key):
    log.debug("Deleting callback function for %s on key %s" % (name, key))
