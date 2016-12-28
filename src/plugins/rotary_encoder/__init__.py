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
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
#  USA.import plugin

#  This file serves as a starting point for a plugin.  This is a Thread based
#  plugin where the main Plugin class creates a thread and starts the thread
#  when the plugin's run() function is called.

import plugin
import threading
import time
from RPi import GPIO
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
        self.key = parent.config['rkey'] if ('rkey' in parent.config) and parent.config['rkey'] else "ENC1"
        self.btn = parent.config['btn'] if ('btn' in parent.config) and parent.config['btn'] else "False"
        self.btnpin = int(parent.config['btnpin']) if ('btnpin' in parent.config) and parent.config['btnpin'] else 4
        self.btnkey = parent.config['btnkey'] if ('btnkey' in parent.config) and parent.config['btnkey'] else "BTN1"
        self.btnstcounter = int(parent.config['btnstcounter']) if ('btnstcounter' in parent.config) and parent.config['btnstcounter'] else 0
        self.btnincr = float(parent.config['btnincr']) if ('btnincr' in parent.config) and parent.config['btnincr'] else 1
        self.counter = float(parent.config['stcount']) if ('stcount' in parent.config) and parent.config['stcount'] else 0
        self.incr = float(parent.config['incr']) if ('incr' in parent.config) and parent.config['incr'] else 1
        self.clk = int(parent.config['pina']) if ('pina' in parent.config) and parent.config['pina'] else 19
        self.dt = int(parent.config['pinb']) if ('pinb' in parent.config) and parent.config['pinb'] else 26
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.btnpin,GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.clk, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(self.dt, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        self.count = 0
        self.clkLastState = GPIO.input(self.clk)

    def run(self):
        while True:
            if self.getout:
                break
            time.sleep(0.001)
            self.count += 1
            clkState = GPIO.input(self.clk)
            dtState = GPIO.input(self.dt)
            if self.btn == "True" and (GPIO.input(self.btnpin)):
                if clkState != self.clkLastState:
                    if dtState != clkState:
                        self.btnstcounter += self.btnincr
                    else:
                        self.btnstcounter -= self.btnincr
                    self.parent.db_write(self.btnkey, self.btnstcounter)
            else:
                if clkState != self.clkLastState:
                    if dtState != clkState:
                        self.counter += self.incr
                    else:
                        self.counter -= self.incr
                    self.parent.db_write(self.key, self.counter)
            self.clkLastState = clkState
    
        self.running = False

    def stop(self):
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
