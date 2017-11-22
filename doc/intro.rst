============
Introduction
============

FIX is an acronym for Flight Information eXchange.  It is a set of protocol
specifications for exchanging information between aircraft avionics and flight
systems.  This specification and the protocols themselves are licensed under a
Creative Commons license that allows anyone to modify and redistribute these
documents without charge.

This is a community supported endeavor, with the primary goal of providing a
standard method for avionics and flight control systems to communicate with one
other in a vendor neutral way.

These specifications and protocols are primarily geared toward the Experimental
Amateur Built (E-AB) aircraft community.  Keeping the specification open and
free allows airplane builders to create their own devices and write their own
software that will be able to communicate with other devices without need to pay
for specifications or licenses.  It also encourages collaboration in the
development and improvement of the protocols themselves.

FIX is a protocol family.  This manual describes the operation of FIX Gateway.
A program designed to pass data between disparate technologies that may or may
not communicate with any of the FIX protocols.  Examples of use are...

* Allow an Electronic Flight Information System (EFIS) communicate with a flight
  simulator.

* EFIS communication to CAN-FIX or other FIX devices within the airplane

* Conversion of data from one format to a standard FIX type.

* Hardware interface to flight simulators.

* Testing


General Description
-------------------

FIX Gateway is a plug-in based program written in Python.  Which plug-ins are
loaded is determined by the configuration file during the program start.  Each
of the plug-ins communicates with a central database of data items.  Each data
item represents a distinct aircraft data point.  Airspeed, altitude or oil
pressure are simple examples but control positions and radio frequencies are
also examples.

The database is determined by a database configuration file that is read during
start up.  The user can modify this file if need be to customize the database
for specific needs.

Possible Applications
---------------------
The primary use case for FIX Gateway is to integrate all the disparate flight
information in the aircraft for display on an Electronic Flight Information
System (EFIS).  PyEFIS is a Python based EFIS that is being developed in concert
with FGW.  This allows the EFIS designers to not have to worry about all the
data interfaces that may be necessary and concentrate on development of the
EFIS.  FGW supplies a common interface through a network connection that
abstracts the data so the EFIS does not care whether the data comes from a
flight simulator, a real airplane or is just being managed manually by the
programmer.

Once the EFIS program is finished and installed in the airplane it needn't be
modified to get actual aircraft data.  Only FGW configuration needs to be
changed.

Another use for FGW is to make it easy to integrate flight simulator data into
other system.  The EFIS could be used as an instrument for the flight simulator.
The entire aircraft panel could be duplicated in the EFIS/FGW and removed from
the flight simulator itself.  Interface to real equipment is simplified.  Since
FGW is written in Python it's quite easy to write a custom plug-in to read data
from any source and get it into the database.  Once in the database it's a
simple matter of configuring other plug-ins to move that data to/from other
sources.

For example, one plug-in could be written to read analog values from an Arduino
and then that information could be used as pilot inputs to FlightGear, X-Plane
or any other flight simulator that has an interface built for FGW.  It could
also be used as a real hardware interface for an actual aircraft as well but
good engineering practices should be used here for obvious reason.  Flight
controls should probably be done by other means in an actual aircraft.

It's conceivable that different flight simulators could be tied together using
this technology as well.  You could be flying a 172 in FlightGear and your
neighbor could fly with you in his RV using X-Plane.  The plug-ins for the
different flight simulators are not quite this sophisticated yet but it's
possible.
