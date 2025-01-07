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
        self.starttime = time.monotonic()
        self.get_all_data(callbacks=True)
 
    # callback
    def persist(self, key, value, udata=None):
        # Pause collection while writing and clearing
        # to ensure data is not lost
        start = time.monotonic()
        while not self.collect:
            time.sleep(0.005)
            # If writing is stalled, continue on
            if ( start - time.monotonic() ) > 0.125:
                break
        self.data[key] = [ value[0], int(value[1]), int(value[2]), int(value[3]), int(value[4]), int(value[5]) ] 

    def get_all_data(self,callbacks=False):
        # Create callbacks for defined keys
        for key in database.listkeys():
            if isinstance(self.config['key_prefixes'], str):
                if callbacks: 
                    self.parent.db_callback_add(key, self.persist)
                else:
                    # Get and save data as of now
                    key_data = self.parent.db_read(key)
                    self.data[key] = [ key_data[0], int(key_data[1]), int(key_data[2]), int(key_data[3]), int(key_data[4]), int(key_data[5]) ]
            else:
                for sw in self.config['key_prefixes']:
                    if key.startswith(sw):
                        if callbacks: 
                            self.parent.db_callback_add(key, self.persist)
                        else:
                            # Get and save data as of now
                            key_data = self.parent.db_read(key)
                            self.data[key] = [ key_data[0], int(key_data[1]), int(key_data[2]), int(key_data[3]), int(key_data[4]), int(key_data[5]) ]
                        break
        if callbacks: self.starttime = time.monotonic()

    def run(self):
        hour = -1
        # Init Error log output by time so first loop will log any errors
        log_time = time.monotonic() - 601
        freq_time = time.monotonic() - 601
        while not self.getout:
            log_loop_time = time.monotonic()
            freq_loop_time = time.monotonic()

            # Create new file for each hour
            # First entry into loop is considered new hour
            if datetime.datetime.now().hour != hour:
                d = datetime.datetime.now()
                hour = d.hour
                path = os.path.join( self.config['filepath'].format(CONFIG=self.config['CONFIGPATH']), d.strftime("%Y"), d.strftime("%m"), d.strftime("%d") )
                os.makedirs( path, exist_ok = True )
                filepath = os.path.join( path, d.strftime("%Y-%m-%d.%H.json") )
                # On first loop or at hour change, write the frequency and current time
                try:
                    with open(filepath, 'a') as f:
                        f.write(json.dumps({"frequency": f"{self.config['frequency']}", "starttime": f"{datetime.datetime.now().isoformat()}" }, separators=(',', ':')) + "\n")
                except:
                    # Only log message every 5 minutes, no sense spamming the logs
                    if ( freq_loop_time - freq_time ) > 300:
                        freq_time = freq_loop_time
                        self.log.warning(f"Unable to write frequency to the file: {filepath}")
                    # Reset and try to write this on the next loop
                    hour = -1
                # Get all data for first log entry
                self.get_all_data(callbacks=False)
            # Lock collection
            self.collect = False
            try:    
                with open(filepath, 'a') as f:
                    f.write( f"{json.dumps(self.data, separators=(',', ':'))}\n")
            except:
                # Only log message every 5 minutes, no sense spamming the logs
                if ( log_loop_time - log_time ) > 300:
                    log_time = log_loop_time
                    self.log.warning(f"Unable to write data to the file: {filepath}")

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

