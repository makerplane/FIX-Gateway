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
    def __init__(self, value = None):
        self.value = value
        self.quality = False
        self.max = None
        self.min = None
        self.callbacks = {}

def write(index, value):
    if index in __database:
        __database[index].value = value
    else:
        __database[index] = db_item(value)

def read(index):
    try:
        return __database[index].value
    except KeyError:
        return None
        
def callback_add(name, key, function, udata):
    log.debug("Adding callback function for %s on key %s" % (name, key))

def callback_del(name, key):
    log.debug("Deleting callback function for %s on key %s" % (name, key))
