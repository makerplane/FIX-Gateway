#  Copyright (c) 2013 Phil Birkelbach
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

# This is the CAN-FIX plugin. CAN-FIX is a CANBus based protocol for
# aircraft data.

import threading
import fixgw.plugin as plugin
from collections import OrderedDict

import can
import canfix

from . import mapping
import fixgw.quorum as quorum


class MainThread(threading.Thread):
    def __init__(self, parent, config):
        super(MainThread, self).__init__()
        # self.interface = config['interface']
        # self.channel = config['channel']
        # self.device = int(config['device'])

        self.getout = False
        self.parent = parent
        self.log = parent.log
        self.mapping = parent.mapping
        # We use this to check to see if we are even interested in this frame
        self.interesting = [False] * 2048
        for x in range(1280):
            if self.mapping.input_mapping[x] is not None:
                self.interesting[x + 0x100] = True

    def run(self):
        self.bus = self.parent.bus

        while True:
            try:
                msg = self.bus.recv(1.0)
                if msg is not None:
                    self.parent.recvcount += 1
                    # Node Specific
                    # ncanid = msg.arbitration_id - canfix.NODE_SPECIFIC_MSGS
                    # Is this a node specific message?
                    # id between 1760 and 2015
                    # control code, first data byte is between 12 and 19
                    if (msg.arbitration_id > 1759 and msg.arbitration_id < 2016) and (
                        msg.data[0] > 11 and msg.data[0] < 20
                    ):
                        try:
                            ns = canfix.NodeSpecific(msg)
                            nsid = int.from_bytes(
                                bytearray(ns.data[0:2]), byteorder="little"
                            )  # - 0x100
                            # Is this a node specific we are interested in?
                            if self.mapping.input_nodespecific[nsid]:
                                # If we want to allow node specific messages
                                # modify the message so it looks like a
                                # normal parameter update
                                # We clear out the function code bits
                                nid = msg.arbitration_id - canfix.NODE_SPECIFIC_MSGS
                                t = msg.data[0]  # - 0x0C
                                msg.arbitration_id = nsid
                                data = bytearray([])
                                data.append(nid)  # Node ID
                                data.append(t - 0x0C)  # Index
                                data.append(0x00)  # Function codes
                                data.extend(msg.data[3:])
                                msg.data = data
                            else:
                                self.parent.recvignorecount += 1
                                continue
                        except:
                            self.parent.recvinvalidcount += 1
                            continue
                    if (quorum.enabled and msg.data[0] == 6 and msg.data[1] == 9) and (
                        msg.arbitration_id > 1759 and msg.arbitration_id < 2016
                    ):
                        # This is a quorum node status message
                        # We only want ones that are not our own
                        cfobj = canfix.parseMessage(msg)
                        if cfobj.value != quorum.nodeid:
                            # This is not ourself
                            if cfobj.value > 0 and cfobj.value < 100:
                                try:
                                    self.parent.db_write(
                                        f"QVOTE{cfobj.value}", cfobj.value
                                    )
                                except:
                                    self.parent.recvinvalidcount += 1
                                    self.log.warning(
                                        f"Received a vote for QVOTE{cfobj.value} but this fixid does not exist"
                                    )
                            else:
                                self.parent.recvinvalidcount += 1
                        else:
                            # We ignore our own messages
                            self.parent.recvignorecount += 1
                        continue
                    if self.interesting[msg.arbitration_id]:
                        try:
                            cfobj = canfix.parseMessage(msg)
                        except ValueError as e:
                            # Can we ever get here?
                            self.parent.recvinvalidcount += 1
                            self.log.warning(e)
                        else:
                            self.log.debug(
                                # A bug in canfix lib __str__ causes exception if indexName is not defined
                                # So changed this to output cfobj.getName instead of cfobj
                                # when canfix bug is resolved should change this back
                                "Fix Thread parseFrame() returned, {0}".format(
                                    cfobj.getName
                                )
                            )
                            if isinstance(cfobj, canfix.Parameter):
                                self.mapping.inputMap(cfobj)
                            else:
                                # TODO What to do with the other types
                                # Can we ever get here?
                                self.parent.recvignorecount += 1
                    else:
                        self.parent.recvignorecount += 1
            finally:
                if self.getout:
                    break

    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.interface = config["interface"]
        self.channel = config["channel"]
        self.device = int(config["device"])
        self.node = int(config["node"])
        mapfilename = config["mapfile"].format(CONFIG=config["CONFIGPATH"])
        self.mapping = mapping.Mapping(mapfilename, self.log)
        self.thread = MainThread(self, config)
        self.recvcount = 0
        self.recvignorecount = 0
        self.recvinvalidcount = 0
        self.mapping.sendcount = 0
        self.mapping.senderrorcount = 0
        self.mapping.recvignorecount = 0
        self.mapping.recvinvalidcount = 0

    def run(self):
        self.bus = can.ThreadSafeBus(self.channel, interface=self.interface)
        for each in self.mapping.output_mapping:
            self.db_callback_add(
                each, self.mapping.getOutputFunction(self.bus, each, self.node)
            )
        if quorum.enabled:
            # canfix needs updated to support quorum so we will monkey patch it for now
            # Pull to fix canfix: https://github.com/birkelbach/python-canfix/pull/13
            # Request to add this to the canfix specification: https://github.com/makerplane/canfix-spec/issues/4
            canfix.NodeStatus.knownTypes = (
                ("Status", "WORD", 1),
                ("Unit Temperature", "INT", 0.1),
                ("Supply Voltage", "INT", 0.1),
                ("CAN Transmit Frame Count", "UDINT", 1),
                ("CAN Receive Frame Count", "UDINT", 1),
                ("CAN Transmit Error Count", "UDINT", 1),
                ("CAN Transmit Error Count", "UDINT", 1),
                ("CAN Receive Overrun Count", "UDINT", 1),
                ("Serial Number", "UDINT", 1),
                ("Quorum", "UINT", 1),
            )
            # Added callback to transmit our quorum vote on the bus
            self.db_callback_add(
                quorum.vote_key,
                self.mapping.getQuorumOutputFunction(
                    self.bus, quorum.vote_key, self.node
                ),
            )
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            try:
                self.thread.join(1.0)
            except:
                pass
        if self.thread.is_alive():
            raise plugin.PluginFail

    def get_status(self):
        x = OrderedDict()
        x["CAN Interface"] = self.interface
        x["CAN Channel"] = self.channel
        x["Received Frames"] = self.recvcount
        x["Ignored Frames"] = self.recvignorecount + self.mapping.recvignorecount
        x["Invalid Frames"] = self.recvinvalidcount + self.mapping.recvinvalidcount
        x["Sent Frames"] = self.mapping.sendcount
        x["Send Error Count"] = self.mapping.senderrorcount
        return x


# TODO: Add error reporting in debug mode
# TODO: Add output parameter mapping
# TODO: Add parameter setting node specific mapping
# TODO: Finish adding the mappings to the YAML file
# TODO: Add the rest of the CAN-FIX protocol mandatory stuff
# TODO: Add tests, tests, tests
