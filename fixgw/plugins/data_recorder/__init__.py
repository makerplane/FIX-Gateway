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

        self.data = dict()
        self.collect = True
        # callback
        def persist(key, value, udata=None):
            # Pause collection while writing and clearing
            while not self.collect:
                time.sleep(0.001)
            self.data[key] = [ value[0], int(value[1]), int(value[2]), int(value[3]), int(value[4]), int(value[5]) ] 

        # Create callbacks for defined keys
        for key in database.listkeys():
            for sw in self.config['key_prefixes']:
                if key.startswith(sw):
                    self.parent.db_callback_add(key, persist)
                    break
        self.starttime = time.monotonic()

    def run(self):
        hour = -1
        while not self.getout:
            # Create new file for each hour
            # First entry into loop is considered new hour
            if datetime.datetime.now().hour != hour:
                d = datetime.datetime.now()
                hour = d.hour
                path = os.path.join( self.config['filepath'].format(CONFIG=self.config['CONFIGPATH']), d.strftime("%Y"), d.strftime("%m"), d.strftime("%d") )
                os.makedirs( path, exist_ok = True )
                filepath = os.path.join( path, d.strftime("%Y-%m-%d.%H.json") )
                # On first loop or at hour change, write the frequency and current time
                with open(filepath, 'a') as f:
                    f.write(json.dumps({"frequency": f"{self.config['frequency']}", "starttime": f"{datetime.datetime.now().isoformat()}" }) + "\n")
            # Lock collection
            self.collect = False    
            with open(filepath, 'a') as f:
                f.write( f"{json.dumps(self.data)}\n")
            # Clear data
            self.data = dict()
            # Unlock collection
            self.collect = True
            # Wait for remainder of frequency interval
            time.sleep((self.config['frequency']/1000) - ((time.monotonic() - self.starttime) % (self.config['frequency']/1000)))

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

