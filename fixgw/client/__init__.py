#!/usr/bin/env python3

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

# This module is a FIX-Net client for FIX-Gateway

from __future__ import print_function

import argparse
import threading
import sys
import logging
logging.basicConfig()

import fixgw.netfix as netfix
from . import command

# Used to print to stderr
def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)

def printData(x):
    flags = ""
    if len(x) == 3:
        if 'a' in x[2]: flags += " Annuc"
        if 'o' in x[2]: flags += " Old"
        if 'f' in x[2]: flags += " Fail"
        if 'b' in x[2]: flags += " Bad"
        if 's' in x[2]: flags += " SecFail"
    print("{} = {}{}".format(x[0],x[1],flags))


def main():
    parser = argparse.ArgumentParser(description='FIX Gateway')
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode')
    parser.add_argument('--host', '-H', default='localhost',
                        help="IP address or hostname of the FIX-Gateway Server")
    parser.add_argument('--port', '-P', type=int, default=3490,
                        help="Port number to use for FIX-Gateway Server connection")
    parser.add_argument('--prompt', '-p', default='FIX: ',
                        help="Command line prompt")
    parser.add_argument('--file', '-f', nargs=1, metavar='FILENAME',
                        help="Execute commands within file")
    parser.add_argument('--execute','-x', nargs='+', help='Execute command')
    parser.add_argument('--interactive', '-i', action='store_true',
                        help='Keep running after commands are executed')
    parser.add_argument('--gui', '-g', action='store_true',
                        help='Run in graphical mode')

    args, unknown_args = parser.parse_known_args()
    log = logging.getLogger()
    if args.debug:
        log.level = logging.DEBUG

    c = netfix.Client(args.host, args.port)
    c.connect()

    cmd = command.Command(c)
    # If commands are beign redirected or piped we set the prompt to nothing
    if sys.stdin.isatty():
        cmd.prompt = args.prompt
    else:
        cmd.prompt = ""
    if args.execute:
        s = " ".join(args.execute)
        cmd.onecmd(s)
        if not args.interactive:
            exit(0)
    # Run in Graphical mode if set
    if args.gui:
        from . import gui
        gui = gui.GUI(c)
        sys.exit(gui.run())
    else:
        cmd.cmdloop()

    c.disconnect()


if __name__ == '__main__':
    main()
