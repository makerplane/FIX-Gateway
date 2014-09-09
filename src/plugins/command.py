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

import plugin
import cmd
import threading
import time

class Command(cmd.Cmd):
    def setplugin(self, p):
        self.plugin = p
        
    def do_read(self, line):
        """read key\nRead the value from the database given the key"""
        args = line.split(" ")
        try:
            x = self.plugin.db_read(args[0].upper())
            print(x)
        except KeyError:
            print("Unknown Key " + args[0])

    def do_write(self, line):
        """write key value\nWrite Value into Database with given key"""
        args = line.split(" ")
        if len(args) < 2:
            print("Missing Argument")
        else:
            try:
                #TODO: Should do more error checking here
                self.plugin.db_write(args[0].upper(), args[1])
            except KeyError:
                print("Unknown Key " + args[0])

    def do_list(self, line):
        """list\nList Database Keys"""
        x = self.plugin.db_list()
        if x:
            x.sort()
            for each in x:
                print(each)

    def do_quit(self, line):
        """quit\nExit Plugin"""
        return True
    
    def do_exit(self, line):
        """exit\nExit Plugin"""
        return self.do_quit(line)
    
#    def do_help(self, line):
#        print("Helping...")

    def do_EOF(self, line):
        return True
    

class MainThread(threading.Thread):
    def __init__(self, parent):
        """The calling object should pass itself as the parent.
           This gives the thread all the plugin goodies that the
           parent has."""
        super(MainThread, self).__init__()
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log # simplifies logging
        self.cmd = Command()
        self.cmd.setplugin(self.parent)
        self.cmd.prompt = self.parent.config.get("prompt", "FIX>")
        
    def run(self):
        self.cmd.cmdloop()
        quit = self.parent.config.get("quit", "yes")
        if quit.lower() in ["yes", "true", "1"]:
            self.parent.quit()
        
    def stop(self):
        self.getout = True
    

class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name,config)
        self.thread = MainThread(self)

    def run(self):
        super(Plugin, self).run()
        self.thread.start()
    
    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join()
        super(Plugin, self).stop()
    
    def is_running(self):
        return self.thread.is_alive()