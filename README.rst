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

FIX Gateway may run okay on Python 2.7 but we have deprecated support for Python
2.x in favor of Python 3.x.  The easiest way to install FIX Gateway is to use
pip3.

::

    sudo pip3 install fixgw

Once installed you should be able to run the server with the command...

::

  fixgw

or the client with this command.

::

  fixgwc

You can also clone the GitHub repository.

::

    git clone git@github.com:makerplane/FIX-Gateway.git fixgw

or

::

    git clone https://github.com/makerplane/FIX-Gateway.git fixgw

There are a couple of helper scripts that will allow you to run FIX Gateway from
within the source tree, if you don't want to install the packages to your system.

::

    ./fixgw.py
    ./fixgwc.py

These will run the client and the server respectively.

The configuration files are installed into '/usr/local/etc/fixgw' by default and
other files such as this documentation and other support files are located in
'/usr/local/share/fixgw'

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

If you intend to use the gui plugin you will also need PyQt installed.  It
should work with either PyQt4 or PyQt5.  You'll have to consult the PyQt
documentation on how to install PyQt on your system.  Support for PyQt4 will
likely be dropped in the future as well.

The canfix plugin will require both the python-can package as well as the
python-canfix package.  Installing the python-canfix package with pip3 should
install both.
