|Website snapcraft.io|

.. |Website snapcraft.io| image:: https://snapcraft.io/fixgateway/badge.svg
   :target: https://snapcraft.io/fixgateway

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


It is recommende that you work in a virtual environment. To use the global interpreter, skip the below step.

::

    $ make venv
    $ source venv/bin/activate

The second command, the activation of the virtual environment, needs to be performed every time you start a new console session.

Next, you install all dependencies.

::

    $ make init

Then run one of the two helper scripts.

server:
::

    $ ./fixGw.py

client:
::

    $ ./fixGwClient.py

client with GUI interface:
::

    $ ./fixGwClient.py --gui



The configuration files are in the ``src/fixgw/config`` directory.

Testing
------------
To run all of the automated tests and code covreage.

::

    $ make test

Please create tests for your changes and ensure all tests pass before submitting a pull request


Cleanup
------------
To remove the virtual environment and test output
::

    $ make clean


Distribution
------------

To create a Python wheel for distribution, there is a make target. The wheel will be created in the ``dist/`` directory.

::

    $ make wheel

After installing the wheel via pip, the user can run Fix-Gateway from the command line.

server:
::

    $ fixgw

client:
::

    $ fixgwc

client with GUI:
::

    $ fixgwc --gui


Snapcraft Development
------------
To install snapd see: `https://snapcraft.io/docs/installing-snapd <https://snapcraft.io/docs/installing-snapd>`_
To install snapcraft see: `https://snapcraft.io/docs/installing-snapcraft <https://snapcraft.io/docs/installing-snapcraft>`_
 
To build the snap locally:
::

    $ snapcraft

To install the snap locally:
::

    $ sudo snap install fixgateway_2.1.1_amd64.snap --dangerous

Dangerous is needed because locally built snaps are not signed


Requirements
------------

The only dependencies for FIX Gateway are Python itself and ``pyyaml``.  If you used
pip3 to install FIX Gateway the dependencies should have been installed
automatically. FIX Gateway requires Python 3.6 and should run on versions of
Python higher than 3.6.  

Many of the plugins will require other dependencies.  See the individual plugin
documentation for information about those.  We'll discuss some of the more common
ones.

Under Ubuntu distibutions socketcan can be installed with: `apt install can-utils`
Some background on linux can can be found here: https://elinux.org/Bringing_CAN_interface_up
To bring up the vcan0 interface:
```
$ modprobe vcan
$ sudo ip link add dev vcan0 type vcan
$ sudo ip link set up vcan0
```

You will also need PyQt6 installed.
Consult the PyQt documentation on how to install PyQt on your system.  
Typically it is

sudo apt-get install python3-pyqt6

The canfix plugin will require both the python-can package as well as the
python-canfix package.  Installing the python-canfix package with pip3 should
install both.

sudo pip3 install python-canfix

