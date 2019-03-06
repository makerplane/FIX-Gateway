===================================
FlightGear Flight Simulator Plugin
===================================

FlightGear is the name of a very popular open source flight simulator.
This plugin is used to allow FIX-Gateway to communicate with this simulator.

http://www.flightgear.org/

The plugin uses FlightGear's *Generic* protocol.  This protocol is customizable
by the user by way of an XML file.  We've included an XML file for this purpose.
The file included is called ``fix_fgfs.xml``  The fix_fgfs.xml file should be
linked or copied to the FG_ROOT/Protocols directory which should be in one of
the following locations...

- LINUX: ``/usr/share/games/flightgear/Protocol/``
- OSX: ``/Applications/FlightGear.app/Contents/Resources/data/``
- WINDOWS: ``c:\Program Files\FlightGear\data\``

This is the location where FlightGear will search for the XML file.

To launch FlightGear using this protocol file use the following command

::

  >fgfs --generic=socket,out,10,localhost,5500,udp,fix_fgfs --generic=socket,in,1,,5501,udp,fix_fgfs

The first `--generic` argument defines the output connection from FlightGear to
FIX-Gateway.  This corresponds to the <output> group in the XML file.  The `10`
is the update rate in updates / second, `localhost` and `5500` are the ip address and port that
FlightGear will send to and FIX-Gateway will listen on.  `udp` is the protocol
to be used and this should not be changed.  FIX-Gateway only usese udp at
this point.  The last argument in the list is the name of the XML file that
would have the <output> group to tell both programs how the output sentence will
be formed.  This can change but it must match for both programs.

The second `--generic` argument contains similar data.  The update rate has no
meaning and if the host address is left off FlightGear will listen on all
available interfaces.

This plugin also needs to know the location of this file so there is a directive in the
configuration file for setting this location.  It is very important that both FlightGear
and this plugin are looking to the exact same file otherwise FIX-Gateway is going to be
very confused.

It is also very important that the host and port information given in the above
command line match what is in the main configuration file.

For more information on FlightGear's Generic Protocol see
http://wiki.flightgear.org/Generic_protocol

Configuration
--------------

::

  fgfs:
    load: yes
    module: fixgw.plugins.fgfs
    # This should be the same as $FG_ROOT on your system.  It is used to help
    # fixgw find the xml configuration files
    fg_root: /usr/share/games/flightgear/
    # fg_root: /Applications/FlightGear.app/Contents/Resources/data/
    # fg_root: c:\Program Files\FlightGear\data\

    # This is the name of the protocol config file that fixgw and fgfs will use to
    # define the protocol. It is very important that both programs are looking at
    # the same file.
    xml_file: fix_fgfs.xml
    # UDP Address and Ports used for communication to FlightGear.
    # Host address to listen on
    recv_host: localhost
    # port used for the -out argument to FlightGear
    recv_port: 5500
    # host address where FlightGear is running
    send_host: localhost
    # port used for the -in argument to FlightGear
    send_port: 5501
    # Update rate for sending data to FlightGear
    rate: 10  # updates / second

Both FIX-Gateway and FlightGear should be looking at the same XML file to
determine how the data will be formatted and sent.  There are two main sections
in the FlightGear XML file.  One is <output> and the other <input>.  The <output>
section defines the data that is output from FlightGear and sent to FIX-Gateway.
The <input> section is what FIX-Gateway sends to FlightGear.  This seems
backwards in FIX-Gateway but the XML file design is driven by FlightGear.

Within each <output> or <input> group each piece of data that we want to
send or receive is contained in a <chunk>.  Within each chunk are elements that
define the protocol.  The following is an example chunk.

::

  <chunk>
       <name>OAT: Outside Air Temperature</name>
       <type>double</type>
       <format>%.1f</format>
       <node>/environment/temperature-degf</node>
       <offset>-32</offset>
       <factor>0.55555555555555555</factor>
  </chunk>


FlightGear ignores the <name> element so we use it to define the database key
within the FIX-Gateway database that we are wanting to read or write. The first
characters up to the `:` are the key.  Everything after the `:` is ignored and
is there for clarity. The <format> element defines how the data will be
represented in the sentence. These are C language style formatting directives.
Both FIX-Gateway and FlightGear use these to encode and decode the data.
FIX-Gateway expects a format that can be directly converted into the data type
of the individual parameter.

The <node> element defines the property within FlightGear that we are going
to read or write.  You can see all the properties that are available with the
Property Browser of FlightGear. (See the Browse Internal Properties menu item
within the Debug menu)

The <offset> and <factor> elements define a way to do unit conversions in
FlightGear.  The <factor> element is a number that FlightGear will multiply
the value by before sending it and <offset> is a number that will be added to
the value.  This example is because FlightGear sends this property in degrees
Farenheit and FIX-Gateway expects the value in Degrees Centigrade.  This is
a bit of a contrived example because there is also a property that's in
degrees C but we wanted something to show how this works.
