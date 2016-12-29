# coding: utf8
#!/usr/bin/env python

#  Copyright (c) 2017 Jean-Manuel Gagnon
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

import logging
import sys
import plugin
import threading
import time
import pigpio
from virtualwire import virtualwire
from collections import OrderedDict

class MainThread(threading.Thread):
    def __init__(self, parent):
		"""The calling object should pass itself as the parent.
		This gives the thread all the plugin goodies that the
		parent has."""
		super(MainThread, self).__init__()
		self.getout = False   # indicator for when to stop
		self.parent = parent  # parent plugin object
		self.log = parent.log  # simplifies logging
		self.count = 0
		self.ias = 0
		self.oat = 0
		self.ias_W_S = 0
		self.oat_W_S = 0
		self.smooted = 0.8
		pigpio.exceptions = False
		self.rxpin = int(parent.config['rxpin']) if ('rxpin' in parent.config) and parent.config['rxpin'] else 23
		self.bps = int(parent.config['bps']) if ('bps' in parent.config) and parent.config['rxpin'] else 2000
		self.pi = pigpio.pi() # Connect to local Pi
		self.rx = virtualwire.rx(self.pi, self.rxpin, self.bps) # Specify Pi, rx GPIO.

    def run(self):
		while True:
			if self.getout:
				break
			time.sleep(.25)
			self.count += 1
			try:
				while self.rx.ready():
					try:
						msg = str("".join(chr (c) for c in self.rx.get()))
					except:
						msg = [400, -50]
                    	#print msg
						pass
					msg = msg.split(',')
					if float(msg[0]) < 400 :
						init_ias = float(msg[0])
						self.ias = float((self.ias*self.smooted)+(1.0-self.smooted)*(init_ias))
						self.ias_W_S = 3
					if float(msg[1]) > -50 :                   
						self.oat = float(msg[1])
						self.oat_W_S = 3
					else: 
						self.ias_W_S = 2
						self.oat_W_S = 2
			except:
				self.ias_W_S = 2
				self.oat_W_S = 2
				pass
			self.parent.db_write("IAS", int(self.ias))
			self.parent.db_write("OAT", self.oat)
			self.parent.db_write("IASW", self.ias_W_S)
			self.parent.db_write("OATW", self.oat_W_S)
		self.running = False

    def stop(self):
    	self.rx.cancel()
        self.pi.stop()
        self.getout = True


class Plugin(plugin.PluginBase):
    """ All plugins for FIX Gateway should implement at least the class
    named 'Plugin.'  They should be derived from the base class in
    the plugin module.

    The run and stop methods of the plugin should be overridden but the
    base module functions should be called first."""
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self)

    def run(self):
        """ The run method should return immediately.  The main routine will
        block when calling this function.  If the plugin is simply a collection
        of callback functions, those can be setup here and no thread will be
        necessary"""
        super(Plugin, self).run()
        self.thread.start()

    def stop(self):
        """ The stop method should not return until the plugin has completely
        stopped.  This generally means a .join() on a thread.  It should
        also undo any callbacks that were set up in the run() method"""
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(1.0)
        if self.thread.is_alive():
            raise plugin.PluginFail
        super(Plugin, self).stop()

    def get_status(self):
        """ The get_status method should return a dict or OrderedDict that
        is basically a key/value pair of statistics"""
        return OrderedDict({"Count":self.thread.count})
