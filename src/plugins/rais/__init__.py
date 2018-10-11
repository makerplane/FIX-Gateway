# -*- coding: utf-8 -*-
#!/usr/bin/env python3

#  Copyright (c) 2018 Garrett Herschleb
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

# This is a networked version of the command line plugin.  They probably
# need to be merged into the same plugin and configuration used to determine
# whether to use the network or prompt.

import sys
import time
import plugin
import importlib
import threading

class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False
        self.parent = parent
        self.log = parent.log
        self.config = parent.config
        rais_server_module = importlib.import_module(self.config['rais_server_module'])
        cfg = None
        if 'rais_config_path' in self.config:
            cfg = self.config['rais_config_path']
        self.rais = rais_server_module.RAIS(config_file=cfg)
        self.rais.setParameterCallback (self.callback)

    def run(self):
        while not self.getout:
            self.rais.listen (loop=False, timeout=0)
            time.sleep(.1)

    def callback(self, dbkey, value):
            self.parent.db_write(dbkey, value)

    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        if not config['rais_directory'] in sys.path:
            sys.path.append (config['rais_directory'])
        self.thread = MainThread(self)

    def run(self):
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join()
        
