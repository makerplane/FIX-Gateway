# Common fixtures used by other test files in this directory.


import pytest
import canfix
from collections import namedtuple
import time
import yaml
import fixgw.plugins.canfix
import can
from fixgw import cfg

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


@pytest.fixture
def config_data():
    return """
    load: yes
    module: fixgw.plugins.canfix
    # See the python-can documentation for the meaning of these options
    interface: virtual
    channel: tcan0

    # Use the actual current mapfile
    mapfile: 'tests/config/canfix/map.yaml'
    # The following is our Node Identification Information
    # See the CAN-FIX Protocol Specification for more information
    node: 145     # CAN-FIX Node ID
    device: 145   # CAN-FIX Device Type
    revision: 0   # Software Revision Number
    model: 0      # Model Number
    CONFIGPATH: ''
"""

@pytest.fixture
def bad_mapfile_config_data():
    return """
    load: yes
    module: fixgw.plugins.canfix
    # See the python-can documentation for the meaning of these options
    interface: virtual
    channel: tcan0

    # Use the actual current mapfile
    mapfile: 'missing_map_file.yaml'
    # The following is our Node Identification Information
    # See the CAN-FIX Protocol Specification for more information
    node: 145     # CAN-FIX Node ID
    device: 145   # CAN-FIX Device Type
    revision: 0   # Software Revision Number
    model: 0      # Model Number
    CONFIGPATH: ''
"""

@pytest.fixture
def ptests_data():
    # This is a list of the parameters that we are testing.  It is a list of tuples
    # that contain (FIXID, CANID, DataString, Value, Test tolerance)
    return [
    ("PITCH", 0x180, "FF0000D8DC", -90.0, 0.0),
    ("PITCH", 0x180, "FF00002823", 90.0, 0.0),
    ("PITCH", 0x180, "FF00000000", 0.0, 0.0),
    ("ROLL", 0x181, "FF0000B0B9", -180.0, 0.0),
    ("ROLL", 0x181, "FF00005046", 180.0, 0.0),
    ("ROLL", 0x181, "FF00000000", 0.0, 0.0),
    ("IAS", 0x183, "FF00000000", 0.0, 0.0),
    ("IAS", 0x183, "FF0000E803", 100.0, 0.0),
    ("IAS", 0x183, "FF0000E803", 100.0, 0.0),
    ("IAS", 0x183, "FF00000F27", 999.9, 0.01),
    ("IAS.Min", 0x183, "FF00100000", 0.0, 0.01),
    ("IAS.Max", 0x183, "FF0020D007", 200.0, 0.01),
    ("IAS.V1", 0x183, "FF00309001", 40.0, 0.01),
    ("IAS.V2", 0x183, "FF00406202", 61.0, 0.01),
    ("IAS.Vne", 0x183, "FF0050DC02", 73.2, 0.01),
    ("IAS.Vfe", 0x183, "FF0060EE02", 75.0, 0.01),
    ("IAS.Vmc", 0x183, "FF00702003", 80.0, 0.01),
    ("IAS.Va", 0x183, "FF00802B03", 81.1, 0.01),
    ("IAS.Vno", 0x183, "FF00908603", 90.2, 0.01),
    ("IAS.Vs", 0x183, "FF00A0A501", 42.1, 0.01),
    ("IAS.Vs0", 0x183, "FF00B0C401", 45.2, 0.01),
    ("IAS.Vx", 0x183, "FF00E06203", 86.6, 0.01),
    ("IAS.Vy", 0x183, "FF00F06D03", 87.7, 0.01),
    ("ALT", 0x184, "FF000018FCFFFF", -1000.0, 0.01),
    ("ALT", 0x184, "FF000000000000", 0.0, 0.01),
    ("ALT", 0x184, "FF0000E8030000", 1000.0, 0.01),
    ("ALT", 0x184, "FF0000D0070000", 2000.0, 0.01),
    ("ALT", 0x184, "FF000010270000", 10000.0, 0.01),
    ("ALT", 0x184, "FF000060EA0000", 60000.0, 0.01),
    ("HEAD", 0x185, "FF00000000", 0.0, 0.01),
    ("HEAD", 0x185, "FF00000807", 180.0, 0.01),
    ("HEAD", 0x185, "FF00000F0E", 359.9, 0.01),
    ("HEAD", 0x185, "FF0000100E", 359.9, 0.01),  # Write 360.0 get back 359.9
    ("VS", 0x186, "FF0000D08A", -30000, 0.01),
    ("VS", 0x186, "FF00000000", 0, 0.01),
    ("VS", 0x186, "FF00003075", 30000, 0.01),
    ("VS.Min", 0x186, "FF0010F0D8", -10000, 0.01),
    ("VS.Max", 0x186, "FF00201027", 10000, 0.01),
    ("TACH1", 0x200, "FF00000000", 0, 0.01),
    ("TACH1", 0x200, "FF0000E803", 1000, 0.01),
    ("TACH1", 0x200, "FF00005A0A", 2650, 0.01),
    ("PROP1", 0x202, "FF00000000", 0, 0.01),
    ("PROP1", 0x202, "FF0000E803", 1000, 0.01),
    ("PROP1", 0x202, "FF00005A0A", 2650, 0.01),
    ("MAP1", 0x21E, "FF00000000", 0.0, 0.001),
    ("MAP1", 0x21E, "FF0000C409", 25.0, 0.001),
    ("MAP1.Min", 0x21E, "FF00100000", 0.0, 0.001),
    ("MAP1.Max", 0x21E, "FF0020B80B", 30.0, 0.001),
    ("OILP1", 0x220, "FF00000000", 0.0, 0.001),
    ("OILP1", 0x220, "FF0000A911", 45.21, 0.001),
    ("OILP1", 0x220, "FF00005125", 95.53, 0.001),
    ("OILP1.Min", 0x220, "FF00100000", 0.0, 0.001),
    ("OILP1.Max", 0x220, "FF00201027", 100.0, 0.001),
    ("OILP1.lowWarn", 0x220, "FF0040A00F", 40.0, 0.001),
    ("OILP1.lowAlarm", 0x220, "FF0050AC0D", 35.0, 0.001),
    ("OILP1.highWarn", 0x220, "FF0060401F", 80.0, 0.001),
    ("OILP1.highAlarm", 0x220, "FF00701C25", 95.0, 0.001),
    #          ("OILT1", 0x220, "FF0000", 0.0, 0.001),
]


@pytest.fixture
def qtests_data():
    return [
    ("QVOTE1", 1, 1),
    ("QVOTE2", 2, 2),
    ("QVOTE3", 3, 3),
]



Objects = namedtuple(
    "Objects",
    ["bus", "pl", "interface", "channel", "node", "device", "revision", "model"],
)

@pytest.fixture
def plugin(config_data,database):
    # Use the default database
    #database.init("src/fixgw/config/database.yaml")
    cc,cc_meta = cfg.from_yaml(config_data, metadata=True)
    pl = fixgw.plugins.canfix.Plugin("canfix", cc, cc_meta)
    pl.start()
    can_bus = can.Bus(cc["channel"], interface=cc["interface"])
    time.sleep(0.1)  # Give plugin a chance to get started

    yield Objects(
        bus=can_bus,
        interface=cc["interface"],
        channel=cc["channel"],
        node=cc["node"],
        device=cc["device"],
        revision=cc["revision"],
        model=cc["model"],
        pl=pl,
    )
    pl.stop()
    can_bus.shutdown()

