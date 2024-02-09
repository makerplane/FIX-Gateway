import threading
import time
import logging
import fixgw.plugin as plugin
import fixgw.database as database
from collections import OrderedDict
import json
import datetime
import os

class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self.config = parent.config

        self.starttime = time.monotonic()

    def run(self):
        while not self.getout:
            freq = 500
            for file in self.config['files']:
                path = file.format(CONFIG=self.config['CONFIGPATH'])
                with open(path) as f:
                    for line in f:
                        j = json.loads(line)
                        if j.get('frequency',False):
                            freq = int(j['frequency'])
                            continue
                        for key in j:
                            #print(f"Set '{key}' to '{j[key]}'")
                            database.get_raw_item(key).value = tuple(j[key])
                        # Wait for remainder of frequency interval
                        time.sleep((freq/1000) - ((time.monotonic() - self.starttime) % (freq/1000)))

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

