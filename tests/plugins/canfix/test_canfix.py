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

import time
import yaml
import random
import re
import can
import canfix
from fixgw import cfg

#import fixgw.database as database
import fixgw.quorum as quorum
import pytest
import fixgw.plugins.canfix
from unittest.mock import MagicMock, patch
import logging





def string2data(s):
    b = bytearray()
    for x in range(0, len(s), 2):
        b.append(int(s[x : x + 2], 16))  # noqa: E203
    return b


def test_missing_mapfile(bad_mapfile_config_data):
    with pytest.raises(Exception):
        bad_cc = yaml.safe_load(bad_mapfile_config_data)
        bad_pl = fixgw.plugins.canfix.Plugin("canfix", bad_cc)
        bad_pl.start()


def test_parameter_writes(plugin,ptests_data,database):
    for param in ptests_data:
        msg = can.Message(is_extended_id=False, arbitration_id=param[1])
        msg.data = string2data(param[2])
        plugin.bus.send(msg)
        time.sleep(0.03)
        x = database.read(param[0])
        if "." in param[0]:
            val = x
        else:
            val = x[0]
        assert abs(val - param[3]) <= param[4]

    status = plugin.pl.get_status()
    assert status["Received Frames"] == len(ptests_data)
    assert status["Ignored Frames"] == 0
    assert status["Invalid Frames"] == 0
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0


def test_unowned_outputs(plugin,database):
    database.write("BARO", 30.04)
    msg = plugin.bus.recv(1.0)
    assert msg.arbitration_id == plugin.node + 1760
    assert msg.data == bytearray([12, 0x90, 0x01, 0x58, 0x75])
    status = plugin.pl.get_status()
    assert status["Received Frames"] == 0
    assert status["Ignored Frames"] == 0
    assert status["Invalid Frames"] == 0
    assert status["Sent Frames"] == 1
    assert status["Send Error Count"] == 0

def test_block_sending_on_receive(plugin,database):
    # Dont send on the bus, what we just got from the bus
    index = 0
    canid = 0x190
    nodeid = 0x91
    #code = (index // 32) + 0x0C
    # Setup the can message as node specific
    msg = can.Message(arbitration_id=0x6E0 + nodeid, is_extended_id=False)
    # Set the message data
    msg.data = bytearray([12, 0x90, 0x01, 0x0C, 0x7B])
    plugin.bus.send(msg)
    msg2 = plugin.bus.recv(0.3)
    msg3 = plugin.bus.recv(0.3)
    assert database.read("BARO")[0] == 31.50
    assert msg2 is None
    assert msg3 is None

def test_all_frame_ids(plugin):
    """Loop through every CAN ID and every length of data with random data"""
    random.seed(14)  # We want deterministic input for testing
    # Not all ids are usable this causes a warning.
    # Need to only use known ids accroding to canfix library
    # Check against venv/lib/python3.10/site-packages/canfix/protocol.py parameters[pid]
    import canfix.protocol

    count = 0
    for id in range(2048):
        if id in canfix.protocol.parameters:
            for dsize in range(9):
                msg = can.Message(is_extended_id=False, arbitration_id=id)
                for x in range(dsize):
                    msg.data.append(random.randrange(256))
                msg.dlc = dsize
                plugin.bus.send(msg)
                count += 1
                time.sleep(0.0001)
    time.sleep(0.01)
    # Timeing issues can make this fail
    # The receiving thread might not have processed and count the last frame
    # before getting the status
    # Also, plugin might send data causing sent counts to not match
    # Maybe we could disable outputs during this test?
    # The sleeps seem to make this pass consistent but it is not the best solution 
    status = plugin.pl.get_status()
    assert status["Received Frames"] == count
    assert status["Ignored Frames"] == 3294
    assert status["Invalid Frames"] == 10
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0


# TODO Add asserts above


def test_ignore_quorum_messages_when_diabled(plugin,database,qtests_data):
    for param in qtests_data:
        p = canfix.NodeStatus()
        p.sendNode = param[1]
        p.parameter = 0x09
        p.value = param[2]
        plugin.bus.send(p.msg)
        time.sleep(0.03)
        x = database.read(param[0])
        # Nothing should change since we are not accepting the messages
        assert x[0] == 0
    status = plugin.pl.get_status()
    # All received frames should be ignored
    assert status["Received Frames"] == len(qtests_data)
    assert status["Ignored Frames"] == len(qtests_data)
    assert status["Invalid Frames"] == 0
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0


def test_accept_quorum_mssages_when_enabled(plugin,database,qtests_data):
    quorum.enabled = True
    quorum.nodeid = 1
    p = canfix.NodeStatus()
    # keep track of the frames we should ignore
    ignoreframes = 0
    for param in qtests_data:
        if param[1] == quorum.nodeid:
            ignoreframes += 1
        p.sendNode = param[1]
        p.parameter = 0x09
        p.value = param[2]
        plugin.bus.send(p.msg)
        time.sleep(0.03)
        x = database.read(param[0])
        if param[2] == 1:
            assert x[0] == 0
        else:
            assert x[0] == param[2]
    status = plugin.pl.get_status()
    assert status["Received Frames"] == len(qtests_data)
    assert status["Ignored Frames"] == ignoreframes
    assert status["Invalid Frames"] == 0
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0

def test_send_outputs_that_require_leader(plugin,database,caplog):
    # Test that outputs with leader_required = True
    # only send when lader is True
    quorum.enabled = True
    quorum.nodeid = 1
    quorum.leader = True
    time.sleep(0.5)
    with caplog.at_level(logging.DEBUG):
        database.write("WPNAME", "TEST1")
        msg = plugin.bus.recv(0.3)
        assert "Output WPNAME: sent value: 'TEST1'"  in caplog.text
 
    quorum.leader = False
    with caplog.at_level(logging.DEBUG):
        database.write("WPNAME", "TEST2")
        msg = plugin.bus.recv(0.3)
        assert "blocked Output WPNAME: TEST2" in caplog.text
    status = plugin.pl.get_status()
    assert status["Received Frames"] == 0
    assert status["Ignored Frames"] == 0
    assert status["Invalid Frames"] == 0
    assert status["Sent Frames"] == 1
    assert status["Send Error Count"] == 0
    quorum.leader = True

def test_reject_invalid_quorum_mssages_when_enabled(plugin, database, caplog):
    quorum.enabled = True
    quorum.nodeid = 1
    p = canfix.NodeStatus()
    p.parameter = 0x09
    # keep track of the frames we should ignore
    sentframes = 0
    invalidframes = 0
    # Test invalid value 101
    p.sendNode = 5
    p.value = 101
    plugin.bus.send(p.msg)
    time.sleep(0.03)
    invalidframes += 1
    sentframes += 1
    assert database.read("QVOTE5")[0] == 0
    # Test invalid value 0
    p.value = 0
    plugin.bus.send(p.msg)
    time.sleep(0.03)
    invalidframes += 1
    sentframes += 1
    assert database.read("QVOTE5")[0] == 0

    # Test DB not configured for 6 nodes
    p.sendNode = 6
    p.value = 6
    invalidframes += 1
    sentframes += 1
    with caplog.at_level(logging.WARNING):
        plugin.bus.send(p.msg)
        time.sleep(0.03)
        assert "Received a vote for QVOTE6 but this fixid does not exist" in caplog.text
    status = plugin.pl.get_status()
    assert status["Received Frames"] == sentframes
    assert status["Ignored Frames"] == 0
    assert status["Invalid Frames"] == invalidframes
    assert status["Sent Frames"] == 0
    assert status["Send Error Count"] == 0


def test_get_status(plugin):
    status = plugin.pl.get_status()
    assert status["CAN Interface"] == plugin.interface
    assert status["CAN Channel"] == plugin.channel


# We don't really have any of these yet
# def test_owned_outputs():
#     pass

# These aren't implemented yet
# def test_node_identification():
#     pass
#
# def test_node_report():
#     pass
#
# def test_parameter_disable_enable():
#     pass
#
# def test_node_id_set():
#     pass
