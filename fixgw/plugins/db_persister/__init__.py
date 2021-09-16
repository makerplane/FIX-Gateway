#!/usr/bin/env python

#  Copyright (c) 2021 Quentin Bossard
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
#  USA

#  This is a simple data simulation plugin.  It's mainly for demo purposese

import threading
import time
from collections import OrderedDict
import fixgw.plugin as plugin
import tables
import yaml
import re


class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging

        f_path = f"{parent.config['CONFIGPATH']}/{parent.config['db_schema']}"
        db_desc = yaml.load(open(f_path, 'r'), Loader=yaml.FullLoader)
        self.log.info(f'loaded db schema from {f_path}')

        f_path = f"{parent.config['CONFIGPATH']}/{parent.config['h5f_file']}"
        self.h5f = tables.open_file(f_path, mode="a", title="Test file")
        self.log.info(f'opened h5f {f_path}')

        def persist(key, value, udata=None):
            # print(key, (value))
            # print(key, value, (value[0], time.time()))
            tbl = self.h5f.get_node('/', key)
            tbl.row['value'] = value[0]
            tbl.row['timestamp'] = time.time()
            # print(tbl.row)
            tbl.row.append()

        regex = re.compile(parent.config['entries_regex'])
        persisted_entries = (e for e in db_desc['entries'] if regex.match(e['key']))
        self.log.info(f'registering {persisted_entries} for persistence')

        for entry in persisted_entries:
            key = entry['key']
            self.parent.db_callback_add(key, persist)

            try:
                self.h5f.get_node('/', key)
            except:
                description = {
                    'value': 
                        tables.Float64Col() if entry['type']=='float' else 
                        tables.IntCol() if entry['type']=='int' else 
                        tables.BoolCol() if entry['type']=='bool' else 
                        tables.StringCol(),
                    'timestamp': tables.Time64Col(),
                }
                self.h5f.create_table('/', key, description)
                self.log.debug(f'create table {key}')


    def run(self):
        while not self.getout:
            time.sleep(0.5)
            self.h5f.flush()
            # self.log.debug(f'flushing h5f')

        self.running = False

    def stop(self):
        self.getout = True



class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self)
        self.status = OrderedDict()

    def run(self):

        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(1.0)
        if self.thread.is_alive():
            raise plugin.PluginFail

    def get_status(self):
        return self.status
