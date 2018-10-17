===============
Getting Started
===============

Welcome to FIX Gateway (FGW).

Installation
------------

Begin by cloning the Git repository

::

    git clone git@github.com:makerplane/FIX-Gateway.git fixgw

or

::

    git clone https://github.com/makerplane/FIX-Gateway.git fixgw

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
Python higher than 3.6.  It may run on versions of Python 2.x but Python 2.x
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


Basic Configuration
-------------------

FIX Gateway is configured through a configuration file named ``default.yaml``
that is located in the config/ subdirectory of distribution, or installed into
the proper place on the filesystem (eg. ``/usr/local/etc/fixgw``).  The
configuration uses `YAML` as it's  configuration language.

The **database file** option tells FGW where to find the database definition file. This
file tells FGW how to build the internal database that is how all the
connections communicate with one another.  For details on the format of the
database definition file see the :doc:`database` section.

::

    database file: "{CONFIG}/default.db"

The **initialization files** is a way to initialize the data in the database
before the plugins are loaded. This will override the initial value defined in
the database definition file but it's mostly used to set up things like the V
speeds (Vfe, Vs, Vx, Vy, etc) or high and low alarm setpoints. It's preferable
that the end devices send this data as part of their communication but not all
end devices are designed to do this.  The initialization file is a way to
customize this data easily.  Any plugin that writes to the datbase can override
this data.  Information in files listed later in the list will override earlier
initialilzations.  The database is initialized once on startup with this
information.  Any connections will be able to overwrite this data at runtime.

::

  initialization files:
    - "{CONFIG}/c170b.ini"
    - "{CONFIG}/fg_172.ini"

In both of the above declarations the string `{CONFIG}` is used.  This will
be replaced with the location where pip3 installed the configuration files.
Relative paths can be used here as well and they will be relative to the
current directory from where the server was run.  Absolute paths to these
files can also be given.

There is a list of connections in the configuration file that determine which
connection plugins will be loaded.  Each item in this connection list represents
a specific connection plugin.  Here is a short snippet of the connections list...

::

  connections:
    # Network FIX Protocol Interface
    netfix:
      load: yes
      module: fixgw.plugins.netfix
      type: server
      host: 0.0.0.0
      port: 3490
      buffer_size: 1024
      timeout: 1.0


The above configuration tells FGW to load a connection plugin named *netfix* and
use the python module found at ``fixgw.plugins.netfix``. The `load` and `module`
configuration options are the only two mandatory items.  Any other options
inside a connection object would be passed as to the plugin.  The included
configuration file contains examples of all the plugins that ship with the FIX
Gateway distribution. Configuration of the individual plugins are documented
elsewhere.

The rest of the configuration file contains directives for message logging.  FGW
uses the built in Python logging module. This is for message logging of the
program itself.  Not to be confused with logging flight data which is handled in
a connection plugin.  Python's logging system is very sophisticated and can log
information in many different ways.  It can log to the terminal, a file, the
system logger, network sockets even email.  A description of all that this
system is capable of is beyond the scope of this documentation.  See Python's
logging module documentation for more details.  So far we don't add any logging
levels beyond what is included in the logger by default.

Running the server
-------------------

To run the program simply type the following at the command line.

::

    fixgw

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

    fixgw --debug --config-file="test.yaml"

FGW will load the ``test.yaml`` file instead of the ``default.yaml``
configuration file that ships with the program.

Running the client
-------------------

FIX Gateway ships with a small client program that allows the user to interact
with the server through the netfix protocol.  The netfix plugin must be loaded
for this to work.

To run the client simply type the following at the command line.

::

    fixgwc
