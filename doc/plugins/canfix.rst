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
  [conn_canfix]
  load = yes
  module = plugins.canfix
  # See the python-can documentation for the meaning of these options
  interface = socketcan
  channel = vcan0 

