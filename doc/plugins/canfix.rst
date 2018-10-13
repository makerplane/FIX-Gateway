====================
CAN-FIX Plugin
====================

CAN-FIX is the Fix protocol implementation for CAN Bus.

Requirements
------------

The ``python-canfix`` package is required and can be installed from PyPi with...

::

  pip install python-canfix


This will also install the ``python-can`` package onto your system.  ``python-can`` is used as
the interface to the CAN Bus.  There may be other requirements that need to be installed depending
on which CAN Interface you want to use.  See https://github.com/hardbyte/python-can for more
details.


Configuration
-------------

::

  # CAN-FIX
  canfix:
    load: yes
    module: plugins.canfix
    # See the python-can documentation for the meaning of these options
    interface: socketcan
    channel: vcan0
    #interface: serial
    #channel: /dev/ttyUSB0

    # This file controls the
    mapfile: config/canfix/default.map
    # The following is our Node Identification Information
    # See the CAN-FIX Protocol Specification for more information
    node: 145     # CAN-FIX Node ID
    device: 145   # CAN-FIX Device Type
    revision: 0   # Software Revision Number
    model: 0      # Model Number
