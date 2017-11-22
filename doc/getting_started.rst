=====================
Getting Started Guide
=====================

Welcome to FIX Gateway (FGW).  This Getting Started Guide is meant as a way to help
you get FIX Gateway up and running quickly.  It is not meant to be the full
documentation of the project.

Installation
------------

Currently the only way to install FIX Gateway is to clone the GitHub repository.
Typically this is done with one of these commands...

::

    git clone git@github.com:makerplane/FIX-Gateway.git fixgw

or

::

    git clone https://github.com/makerplane/FIX-Gateway.git fixgw


Requirements
------------

The only dependencies for FIX Gateway to function is Python itself.  FGW works
with Python 2.7 and the latest version of Python 3.

Many of the plugins will require other dependencies.  See the individual plugin
documentation for information about that.  We'll discuss some of the more common
ones.

If you intend to use the gui
plugin you will also need PyQt installed.  It should work with either PyQt4 or
PyQt5.  You'll have to consult the PyQt documentation on how to install PyQt on
your system.

The canfix plugin will require both the python-can package as well as the
python-canfix package.  Installing the python-canfix package with pip should
install both.

There are several plugins that are specific to use on the Raspberry Pi SBC.
These plugins require some python modules that are specific to the Raspberry Pi.

The flight simulator plugins will obviously require that you have the flight
simulators installed and configured properly as well.


Basic Configuration
-------------------

FIX Gateway is configured through a configuration file named main.cfg that is
located in the config/ subdirectory of distribution.  This is an `INI` style
file that contains sections with key=value pairs in each section.  The first
section is called [config].

The **db_file** option tells FGW where to find the database definition file. This
file tells FGW how to build the internal database that is how all the
connections communicate with one another.  For details on the format of the
database definition file see the :doc:`database` section.

::

    db_file = config/database.csv

The **ini_file** is a way to initialize the data in the database before the
plugins are loaded. This will override the initial value defined in the database
definition file but it's mostly used to set up things like the V speeds (Vfe,
Vs, Vx, Vy, etc) or high and low alarm setpoints. It's preferable that the end
devices send this data as part of their communication but not all end devices
are designed to do this.  The initialization file is a way to customize this
data easily.  Any plugin that writes to the datbase can override this data.

::

    ini_file = config/fg_172.ini

Each connection has it's own section in the configuration file.  These sections
all begin with **conn_**.  The text folowing the "_" will be the name of the
connection within FGW.  There are only two required options to load and run a
connection.

::

    [conn_test]
    load = yes
    module = plugin.test

The above configuration tells FGW to load a connection plugin named *test* and
use the python module found at plugin.test. Any other options under a connection
section would be passed as to the plugin itself.  The included configuration
file contains examples of all the plugins that ship with the FGW distribution.
Configuration of the individual plugins are documented elsewhere.

The rest of the configuration file contains directives for message logging.  FGW
uses the built in Python logging module. This is for message logging of the
program itself.  Not to be confused with logging flight data which is handled in
a connection plugin.  Python's logging system is very sophisticated and can log
information in many different ways.  It log to the terminal, a file, the system
logger, network sockets even email.  A description of all that this system is
capable of is beyond the scope of this documentation.  See Python's logging
module documentation for more details.  So far we don't add any logging levels
beyond what is included in the logger by default.

Running the program
-------------------

To run the program simply type the following at the command line.

::

    python fixgw.py

There are a few command line arguments that can be used to adjust how the
program runs.  ``--debug`` is probably the most useful.  This forces the logging
module to set the loglevel to **debug**.  If you are having trouble getting things
to work the way you think they should using this argument can give you a lot of
information to discover where the problem is.  This option will produce a lot of
data and probably shouldn't be used in the actual airplane.

Also if ``--debug`` is set there are some exceptions that will be raised in
certain  parts of the program that will stop the whole program.  Without this
flag they may  simply cause a particular part of the program to stop
functioning.  With this flag it will raise the exception all the way to the top
so that we can get the traceback information for troubleshooting.  Again don't
set this flag unless you are troubleshooting.

Other command line options are ``--config-file`` and ``--log-config``.  These
set  alternate files for the main configuration and logging configuration
respectively. If the ``--log-config`` option is not set whatever file is used
for the main configuration will be used for logging.  The following command will
load an alternate configuration file and turn debugging on...

::

    python fixgw --debug --config-file="test.cfg"

FGW will load the ``test.cfg`` file instead of the ``main.cfg`` file that ships with
the program.
