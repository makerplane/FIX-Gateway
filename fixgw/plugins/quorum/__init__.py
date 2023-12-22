import threading
import time
import logging
from collections import OrderedDict
import fixgw.plugin as plugin
class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        #print("running mavlink plugin")
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self.config = parent.config
        self.vote_key = f"QVOTE{self.config['nodeid']}"
        self.vote_value = (self.config['nodeid'] ** self.config['total_nodes']) + self.config['nodeid']
        

    def run(self):
        while not self.getout:
            time.sleep(0.001)
            self.parent.db_write(self.vote_key,self.vote_value)
            largest_vote = 0
            for nodeid in range(1, self.config['total_nodes'] + 1):
                data = self.parent.db_read(f"QVOTE{nodeid}")
                if True not in data[1:] and data[0] > largest_vote:
                    largest_vote = data[0]
            self.parent.db_write("LEADER", largest_vote >= self.vote_value)


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

