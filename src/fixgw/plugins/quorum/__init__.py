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
from collections import OrderedDict
import fixgw.plugin as plugin


class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        # print("running mavlink plugin")
        self.getout = False  # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self.config = parent.config
        self.vote_key = f"QVOTE{self.config['nodeid']}"
        self.vote_value = self.config[
            "nodeid"
        ]  # (self.config['nodeid'] ** self.config['total_nodes']) + self.config['nodeid']
        self.parent.quorum.enabled = True
        self.parent.quorum.nodeid = self.config["nodeid"]
        self.parent.quorum.vote_key = self.vote_key
        self.parent.quorum.total_nodes = self.config["total_nodes"]

    def run(self):
        # If a client, such as pyEFIS is already running and has the value LEADER set to True and FIX is starting.
        # The LEADER in pyEFIS might not get updated because we start with LEADER false, and if it stays false
        # nothing will trigger the update.
        # If we make LEADER True at startup, so it can be changed to false to trigger an update, it still might not always
        # notify pyEFIS.  pyEFIS tries to reconnect every two seconds, if we change LEADER from false to true before
        # pyEFIS reconnects and subscribes to LEADER then pyEFIS will not get the first change.
        # The only solution I could come up for this is to startup with LEADER set to true
        # Before we set it based on quorum, we pause long enough to allow pyEFIS the time to reconnect and subscribe.
        # I picked 2x time reconnect interval set in pyEFIS

        # This should not cause any issues in the gateway, plugins in here should use quorum.leader, not the fixid LEADER.
        # This workaround is only needed to ensure that clients get the proper fixid value for LEADER.

        time.sleep(4)

        while not self.getout:
            time.sleep(0.3)
            self.parent.db_write(self.vote_key, self.vote_value)
            highest_vote = 0
            nodes_seen = 0
            for nodeid in range(1, self.config["total_nodes"] + 1):
                data = self.parent.db_read(f"QVOTE{nodeid}")
                # Only accept a vote if no old,bad,etc
                if True not in data[1:]:
                    nodes_seen += 1
                    if highest_vote < data[0]:
                        highest_vote = data[0]
            if self.config["total_nodes"] > 2 and (
                (nodes_seen / self.config["total_nodes"]) <= 0.50
            ):
                # When more than two nodes we require real quorum
                # If 50% or less of the total nodes are seen, we do not have quorum and no one is a leader
                self.parent.quorum.leader = False
                self.parent.db_write("LEADER", False)
            else:
                self.parent.quorum.leader = self.vote_value == highest_vote
                self.parent.db_write("LEADER", self.vote_value == highest_vote)

    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    def __init__(self, name, config, config_meta):
        super(Plugin, self).__init__(name, config, config_meta)
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
