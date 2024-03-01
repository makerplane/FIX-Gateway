============
FIX Gateway
============

Copyright (c) 2014 Phil Birkelbach

FIX stands for Flight Information eXchange.  It is a set of specifications,
protocols and documentation for use in exchanging flight related
information easily and reliably.

Fix Gateway is a program that abstracts this flight information and allows
communication between different technologies.

The primary use is as the interface to the pyEfis electronic flight information
project. It can also be used to interface flight simulator software to 'real'
hardware such as instrumentation or custom flight controls.

Installation
------------

Begin by cloning the Git repository

::

    git clone git@github.com:makerplane/FIX-Gateway.git fixgw

or

::

    git clone https://github.com/makerplane/FIX-Gateway.git fixgw

Install requirements

::

    sudo python3 -m pip install -r requirements.txt

Then run one of the two helper scripts.

::

    ./fixgw.py
    ./fixgwc.py

These will run the client and the server respectively.

The configuration files are in the ``fixgw/config`` directory.

If you'd like to install the program permanently to your system or into a virtualenv you
can issue the command...

::

  sudo pip3 install .

from the root directory of the source repository.  **Caution** This feature is still
in development and may not work consistently.

Requirements
------------

The only dependencies for FIX Gateway are Python itself and ``pyyaml``.  If you used
pip3 to install FIX Gateway the dependencies should have been installed
automatically. FIX Gateway requires Python 3.6 and should run on versions of
Python higher than 3.6.  It may run on versionso of Python 2.x but Python 2.x
support is deprecated and it's expected that FIX Gateway will eventually stop
working with these older versions of Python.

Many of the plugins will require other dependencies.  See the individual plugin
documentation for information about those.  We'll discuss some of the more common
ones.

Under Ubuntu distibutions socketcan can be installed with: `apt install can-utils`
Some background on linux can can be found here: https://elinux.org/Bringing_CAN_interface_up
To bring up the vcan0 interface:

::

    $ modprobe vcan
    $ sudo ip link add dev vcan0 type vcan
    $ sudo ip link set up vcan0


If you intend to use the gui plugin you will also need PyQt installed.  Note that if you use pyEfis
then PyQt is required. FixGW should work with either PyQt4 or PyQt5, however support for PyQT4 is 
likely to be dropped. Consult the PyQt documentation on how to install PyQt on your system.  
Typically it is

::

    sudo apt-get install python3-pyqt5

The canfix plugin will require both the python-can package as well as the
python-canfix package.  Installing the python-canfix package with pip3 should
install both.

sudo pip3 install python-canfix

