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

#  This class is the base class that should be used for all plugins in the
#  system


import fixgw.database as database
import logging
try:
    import queue
except:
    import Queue as queue

jobQueue = queue.Queue()

class PluginFail(Exception):
    pass

# This is the base class for all plugin objects.  Every plugin should
# inherit this class and override at least the run function.  See the
# skel.py file in the plugins directory for a basic example.
class PluginBase(object):
    def __init__(self, name, config):
        self.name = name
        self.log = logging.getLogger('plugin.' + name)
        self.log.info("Initializing")
        self.config = config
        self.log.debug("Config: " + str(self.config))

        self.running = False

    def start(self):
        self.log.info("Starting")
        self.run()
        self.running = True


    def shutdown(self):
        self.stop()
        self.log.info("Stopping")
        self.running = False

    def quit(self):
        """ Sends a job back to the main program to quit program """
        jobQueue.put("QUIT")

    def is_running(self):
        return self.running

    def db_read(self, key):
        return database.read(key)

    def db_write(self, key, value):
        database.write(key, value)

    def db_list(self):
        return database.listkeys()

    def db_get_item(self, key):
        return database.get_raw_item(key)

    def db_callback_add(self, key, function, udata=None):
        database.callback_add(self.name, key, function, udata)

    def db_callback_del(self, key, function, udata=None):
        database.callback_del(self.name, key, function, udata)

    # This method should be reimplemented in the child class
    # It should return a dictionary of status information
    def get_status(self):
        return None
