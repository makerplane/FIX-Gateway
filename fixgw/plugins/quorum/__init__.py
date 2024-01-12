
# In an effort to have some redundancy I wanted a way to control some things,
# such as the auto pilot, from only one gateway at a time. But should one gateway fail
# the other can takover sending commands to the auto pilot. 
# Some keys were created in the database:
# QVOTEn, n is the node id and each node will set its own value.
# LEADER, leader is true if this gateway has the highest vote.
# 
# The module fixgw.quorum contains the bool variable quorum.leader that can be used
# to determine if you are the leader.
#
# NOTE: LEADER could have just been a global variable, making it a fixid allows us to also check the status from 
# other applications. For example we could display a message in pyEFIS if the local canfix is the LEADER or not.
#
# Each node should be configured to send their QVOTEn key to all other nodes in the cluster
# Using the netfix unless you are using canfix. It is not necessary to send the other QVOTEs just the local one.
#
# canfix will automatically send the local QVOTE, no configuration other than enabeling canfix is needed.
# canfix will also import the QVOTE from the other nodes
#
# LEADER is set to true by default, so if this plugin is not used, LEADER will always be true, unless you change it.
# So LEADER can be used in plugins for making decision on actions to ensure only the leader is performing those actions.
# The mavlink plugin is the first one I updated to support this, it will only send commands to the auto pilot
# from the LEADER node. Sinec the auto pilot has multiple serial ports it can be connected to multiple nodes
# at the same time but only receive commands from one node.


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
        self.vote_value = self.config['nodeid'] #(self.config['nodeid'] ** self.config['total_nodes']) + self.config['nodeid']
        self.parent.quorum.enabled = True
        self.parent.quorum.nodeid = self.config["nodeid"]
        self.parent.quorum.vote_key = self.vote_key
        self.parent.quorum.total_nodes = self.config["total_nodes"]

    def run(self):
        while not self.getout:
            time.sleep(0.3)
            self.parent.db_write(self.vote_key,self.vote_value)
            highest_vote = 0
            for nodeid in range(1, self.config['total_nodes'] + 1):
                data = self.parent.db_read(f"QVOTE{nodeid}")
                # Only accept a vote if no old,bad,etc
                if True not in data[1:] and highest_vote < data[0]:
                    highest_vote = data[0]
            self.parent.quorum.leader = (self.vote_value == highest_vote)
            self.parent.db_write("LEADER", self.vote_value == highest_vote )


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

