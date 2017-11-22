===================================
FlightGear Flight Simulator Plugin
===================================

FlightGear is the name of a very popular open source flight simulator.  
This plugin is used to allow FIX-Gateway to communicate with this simulator.

http://www.flightgear.org/

The plugin uses FlightGear's *Generic* protocol.  This protocol is customizable by the
user by way of an XML file.  We've included an XML file for this purpose.  The file
included is called ``fix_fgfs.xml``  The fix_fgfs.xml file should be moved to the 
FG_ROOT/Protocols directory which should be in one of the following locations...

- LINUX: ``/usr/share/games/flightgear/``
- OSX: ``/Applications/FlightGear.app/Contents/Resources/data/``
- WINDOWS: ``c:\Program Files\FlightGear\data\``

This is the location where FlightGear will search for the XML file.

To launch FlightGear using this protocol file use the following command

::

  >fgfs --generic=socket,bi,10,localhost,5500,udp,fix_fgfs

This plugin also needs to know the location of this file so there is a directive in the
configuration file for setting this location.  It is very important that both FlightGear
and this plugin are looking to the exact same file otherwise FIX-Gateway is going to be
very confused.

For more information on FlightGear's Generic Protocol see http://wiki.flightgear.org/Generic_protocol

Configuration
--------------

::

  [conn_fgfs]
  load = yes
  module = plugins.fgfs
  
  # This should be the same as $FG_ROOT on your system.  It is used to help
  # fixgw find the xml configuration files
  fg_root = /usr/share/games/flightgear/
  # fg_root = /Applications/FlightGear.app/Contents/Resources/data/
  # fg_root = c:\Program Files\FlightGear\data\
  
  # This is the name of the protocol config file that fixgw and fgfs will use to
  # define the protocol. It is very important that both programs are looking at
  # the same file.
  xml_file = fix_fgfs.xml
  
  # UDP Ports used for communication to FlightGear.
  host = localhost
  # port used for the -out argument to FlightGear
  out_port = 5500
  # port used for the -in argument to FlightGear
  in_port = 5501
  
  # Update rate for sending data to FlightGear
  rate = 10  # updates / second