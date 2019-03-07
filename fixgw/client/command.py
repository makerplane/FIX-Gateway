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
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import cmd
import json
from collections import OrderedDict

import fixgw.netfix as netfix
import fixgw.status as status

def printData(x):
    flags = ""
    if len(x) == 3:
        if 'a' in x[2]: flags += " Annuc"
        if 'o' in x[2]: flags += " Old"
        if 'f' in x[2]: flags += " Fail"
        if 'b' in x[2]: flags += " Bad"
        if 's' in x[2]: flags += " SecFail"
    print("{} = {}{}".format(x[0],x[1],flags))


class Command(cmd.Cmd):
    def __init__(self, client):
        cmd.Cmd.__init__(self)
        self.client = client

    def do_read(self, line):
        """read [key] [value]\nRead the value from the database given the key"""
        args = line.split(" ")
        try:
            x = self.client.read(args[0])
        except netfix.SendError as e:
            print("Problem Sending Request -", e)
            return
        except netfix.ResponseError as e:
            print("Problem Receiving Response -", e)
            return
        flags = ""
        if x[2]: # Do we have any flags?
            if 'a' in x[2]: flags += " Annuc"
            if 'o' in x[2]: flags += " Old"
            if 'f' in x[2]: flags += " Fail"
            if 'b' in x[2]: flags += " Bad"
            if 's' in x[2]: flags += " SecFail"

        print(x[1]+flags)

    def do_write(self, line):
        """write [key] [value]\nWrite Value into Database with given key"""
        args = line.split(" ")
        if len(args) < 2:
            print("Missing Argument")
        else:
            try:
                self.client.writeValue(*args)
            except netfix.SendError as e:
                print("Problem Sending Request -", e)
                return
            except netfix.ResponseError as e:
                print("Problem Receiving Response -", e)
                return


    def do_list(self, line):
        """list\nList Database Keys"""
        try:
            list = self.client.getList()
        except netfix.SendError as e:
            print("Problem Sending Request -", e)
            return
        except netfix.ResponseError as e:
            print("Problem Receiving Response -", e)
            return

        list.sort()
        for each in list:
            print(each)

    def do_report(self, line):
        """Report [key]\nDetailed item information report"""
        args = line.split(" ")
        if len(args) < 1:
            print("Missing Argument")
        else:
            try:
                res = self.client.getReport(args[0])
                val = self.client.read(args[0])
                print(res[1])
                print("Type:  {0}".format(res[2]))
                print("Value: {0}".format(val[1]))
                print("Q:     {0}".format(val[2]))
                print("Min:   {0}".format(res[3]))
                print("Max:   {0}".format(res[4]))
                print("Units: {0}".format(res[5]))
                print("TOL:   {0}".format(res[6]))
                if res[7]:
                    print("Auxillary Data:")
                    x = res[7].split(',')
                    for aux in x:
                        val = self.client.read("{}.{}".format(args[0], aux))
                        if val[1] == 'None': s = ""
                        else: s = val[1]
                        print("  {0} = {1}".format(aux, s))

            except netfix.SendError as e:
                print("Problem Sending Request -", e)
                return
            except netfix.ResponseError as e:
                print("Problem Receiving Response -", e)
                return


    def do_poll(self, line):
        """Poll\nContinuously prints updates to the given key"""
        args = line.split(" ")
        self.client.setDataCallback(printData)
        for each in args:
            self.client.subscribe(each)
        input()
        for each in args:
            self.client.unsubscribe(each)
        self.client.clearDataCallback()


    def do_flag(self, line):
        """flag [key] [abfs] [true/false]\nSet or clear quality flags"""
        args = line.split(" ")
        if len(args) < 3:
            print("Missing Argument")
        else:
            bit = True if args[2].lower() in ["true", "high", "1", "yes", "set"] else False
            try:
                self.client.flag(args[0], args[1][0], bit)
            except netfix.SendError as e:
                print("Problem Sending Request -", e)
                return
            except netfix.ResponseError as e:
                print("Problem Receiving Response -", e)
                return

    def do_status(self, line):
        """status <json>\nRead status information.  If the 'json' argument is
added the output will be in JSON format."""
        try:
            res = self.client.getStatus()
        except netfix.SendError as e:
            print("Problem Sending Request -", e)
            return
        except netfix.ResponseError as e:
            print("Problem Receiving Response -", e)
            return

        if line == 'json':
            print(res)
        else:
            d = json.loads(res, object_pairs_hook=OrderedDict)
            print(status.dict2string(d))

    def do_stop(self, line):
        """Shutdown Server"""
        try:
            self.client.stop()
        except netfix.SendError as e:
            print("Problem Sending Request -", e)
            return
        except netfix.ResponseError as e:
            print("Problem Receiving Response -", e)
            return


    def do_quit(self, line):
        """quit\nExit Plugin"""
        return True

    def do_exit(self, line):
        """exit\nExit Plugin"""
        return self.do_quit(line)

    def do_EOF(self, line):
        return True
