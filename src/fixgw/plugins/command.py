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

import cmd
import threading
import fixgw.plugin as plugin
import fixgw.status as status


class Command(cmd.Cmd):
    def __init__(self):
        super(Command, self).__init__()
        self.subs = set()

    def setplugin(self, p):
        self.plugin = p

    def do_read(self, line):
        """read\nRead the value from the database given the key"""
        args = line.split(" ")
        try:
            x = self.plugin.db_read(args[0])
            print(x)
        except KeyError:
            print(("Unknown Key " + args[0]))

    def do_write(self, line):
        """writevalue\nWrite Value into Database with given key"""
        args = line.split(" ")
        if len(args) < 2:
            print("Missing Argument")
        else:
            try:
                # TODO: Should do more error checking here
                self.plugin.db_write(args[0], args[1])
            except KeyError:
                print(("Unknown Key " + args[0]))

    def do_list(self, line):
        """list\nList Database Keys"""
        x = self.plugin.db_list()
        if x:
            x.sort()
            for each in x:
                print(each)

    def do_report(self, line):
        """Report\nDetailed ID Report"""
        args = line.split(" ")
        try:
            x = self.plugin.db_get_item(args[0])
            print(x.description)
            print("Type:  {0}".format(x.typestring))
            print("Value: {0}".format(str(x.value[0])))
            print("Q:     {0}".format(str(x.value[1:])))
            print("Min:   {0}".format(str(x.min)))
            print("Max:   {0}".format(str(x.max)))
            print("Units: {0}".format(x.units))
            print("TOL:   {0}".format(str(x.tol)))
            print("Auxillary Data:")
            for each in x.aux:
                if each:
                    print("  {0} = {1}".format(each, str(x.aux[each])))
            for each in x.callbacks:
                print("Callback function defined: {0}".format(each[0]))
        except KeyError:
            print(("Unknown Key " + args[0]))

    def do_sub(self, line):
        """Subscribe\nSubscribe to updates"""
        args = line.split(" ")
        if args[0] not in self.subs:
            try:
                self.plugin.db_callback_add(args[0], self.callback_function)
                self.subs.add(args[0])
            except KeyError:
                print(("Unknown Key " + args[0]))
        else:
            print("Already subscribed to {}".format(args[0]))

    def do_unsub(self, line):
        """Unsubscribe\nRemove subscription to updates"""
        args = line.split(" ")
        try:
            self.plugin.db_callback_del(args[0], self.callback_function)
            self.subs.remove(args[0])
        except KeyError:
            print(("Unknown Key " + args[0]))

    def do_flag(self, line):
        """flag\nSet or clear quality flags"""
        args = line.split(" ")
        if len(args) < 3:
            print("Not Enough Arguments")  # TODO print usage??
            return
        try:
            x = self.plugin.db_get_item(args[0])
        except KeyError:
            print("Unknown Key " + args[0])
        bit = True if args[2].lower() in ["true", "high", "1", "yes"] else False
        if args[1].lower()[0] == "b":
            x.bad = bit
        elif args[1].lower()[0] == "f":
            x.fail = bit
        elif args[1].lower()[0] == "a":
            x.annunciate = bit
        elif args[1].lower()[0] == "s":
            x.secfail = bit

    def do_status(self, line):
        """status\nRead status information"""
        print(status.get_string())

    def do_quit(self, line):
        """quit\nExit Plugin"""
        return True

    def do_exit(self, line):
        """exit\nExit Plugin"""
        return self.do_quit(line)

    def do_EOF(self, line):
        return True

    def callback_function(self, key, value, udata):
        print("{0} = {1}".format(key, value))


class MainThread(threading.Thread):
    def __init__(self, parent):
        """The calling object should pass itself as the parent.
        This gives the thread all the plugin goodies that the
        parent has."""
        super(MainThread, self).__init__()
        self.getout = False  # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self.cmd = Command()
        self.cmd.setplugin(self.parent)
        self.cmd.prompt = self.parent.config.get("prompt", "FIX>")

    def run(self):
        self.cmd.cmdloop()
        quit_ = self.parent.config.get("quit", True)
        if quit_:
            self.parent.quit()

    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    def __init__(self, name, config, config_meta):
        super(Plugin, self).__init__(name, config, config_meta)
        self.thread = MainThread(self)

    def run(self):
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(1.0)
        if self.thread.is_alive():
            raise plugin.PluginFail

    def is_running(self):
        return self.thread.is_alive()
