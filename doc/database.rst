====================
Database Definition
====================

The database for FIX Gateway is configured using a colon ':' delimited text
file.  The database is initialized based on the contents of this file before any
of the plugins are loaded.  The database is immutable.  It cannot be changed by
plugins once the program is loaded.  Users can modify the database definition
for their own use.

File Format
----------------

The following is an excerpt from the default database definition file.

::

    e=2:Engines
    c=4:Cylinders per engine
    t=2:Fuel Tanks
    b=16:Generic Buttons
    r=4:Generic Encoders
    a=16:Generic Analog
    ---
    #Key:Description:Type:Min:Max:Units:Initial:TOL:Auxiliary Data
    ANLGa:Generic Analog %a:float:0:1:%/100:0.0:2000:
    BTNb:Generic Button %b:bool:0:1::False:0:
    ENCr:Generic Encoder %r:int:-32768:32767:Pulses:0:0:
    IAS:Indicated Airspeed:float:0:1000:knots:0.0:2000:Min,Max,V1,V2,Vne,Vfe,Vmc,Va,Vno,Vs,Vs0,Vx,Vy
    ALT:Indicated Altitude:float:-1000:60000:ft:0.0:2000:
    BARO:Altimeter Setting:float:0:35:inHg:29.92:2000:
    VS:Vertical Speed:float:-10000:10000:ft/min:0.0:2000:Min,Max,lowWarn,highWarn,lowAlarm,highAlarm
    HEAD:Current Aircraft Magnetic Heading:float:0:360:deg:0.0:2000:
    AOA:Angle of attack:float:-180:180:deg:0.0:200:Min,Max,0g,Warn,Stall
    CTLPTCH:Pitch Control:float:-1:1:%/100:0.0:200:
    CTLROLL:Roll Control:float:-1:1:%/100:0.0:200:
    THRe:Throttle Control Engine %e:float:0:1:%/100:0.0:1000:
    OILPe:Oil Pressure Engine %e:float:0:200:psi:0.0:2000:Min,Max,lowWarn,highWarn,lowAlarm,highAlarm
    MAPe:Manifold Pressure Engine %e:float:0:60:inHg:0.0:2000:
    EGTec:Exhaust Gas Temp Engine %e, Cylinder %c:float:0:1000:degC:0.0:2000:
    CHTec:Cylinder Head Temp Engine %e, Cylinder %c:float:0:1000:degC:0.0:2000:
    FUELQt:Fuel Quantity Tank %t:float:0:200:gal:0.0:2000:Min,Max,lowWarn,lowAlarm
    TACHe:Engine RPM:int:0:10000:RPM:0:2000:Min,Max,lowWarn,highWarn,lowAlarm,highAlarm
    LAT:Latitude:float:-90:90:deg:0.0:2000:
    LONG:Longitude:float:-180:180:deg:0:2000:

The first few lines describe variables.  Variables are a way to eliminate
duplication in the database definition file.  The line that begins with '---'
tells FIXGateway that the variable definitions are finished and to treat the
rest of the file as item definitions.  Any line that begins with a # is treated
as a comment.

Variables
`````````

Each variable when found in the definition will cause the initialization routine
to duplicate and index that particular datapoint based on the number given.  For
example the variable e=2 represents the number of engines that our aircraft will
have.  Instead of having to write each of the following three points twice (once
for each engine) we just use the lower case letter 'e' in the Key definition and
%e in the description.

::

    THRe:Throttle Control Engine %e:float:0:1:%/100:0.0:1000:
    OILPe:Oil Pressure Engine %e:float:0:200:psi:0.0:2000:Min,Max,lowWarn,highWarn,lowAlarm,highAlarm
    MAPe:Manifold Pressure Engine %e:float:0:60:inHg:0.0:2000:

This would cause THR1 and THR2 to be created in the database.  This doesn't seem
like much with just this example but consider the following...

::

    EGTec:Exhaust Gas Temp Engine %e, Cylinder %c:float:0:1000:degC:0.0:2000:

...if e=2 and c=6 that's a single line that would produce 12 items in the
database.  It also makes it quite easy for a user to change the counts of these
things without having to search the entire database file to manage the data
points.  There are a number of items that use the 'e' for number of engine.
Each of these would have to be managed individually if we had a line for each
point.  As it is the user simply changes the line `e=1` to `e=2` if the aircraft
only has two engines, and he'll get two Oil Pressures, Two Manifold Pressures,
two Fuel Flows etc.

Database Item Definitions
-------------------------

The lines that follow the '---' are definitions of the individual database
items.  The format is...

::

    Key:Description:Type:Min:Max:Units:Initial:TOL:Auxiliary Data

Key
```

The Key is the unique identifier of the data point.  The key should be
in all capitol letters as any lower case letter will be considered to be a
variable.

Description
```````````

The description is obvious.  It is the human readable
name of the item.  '%x' can be used in the description to cause variable
duplication and indexing.  The text "Oil Pressure Engine #%e" would become "Oil
Pressure Engine #1" during the fist item's creation and "Oil Pressure Engine #2"
during the second.

Type
````

There are four datatypes recognized by FIX Gateway, `float`, `int`, `bool` and
`str`.  `float` is the most common and simply represents a real number.  `int`
represents a whole number, or a number that has no decimal point.  These are
good for counters or numbers that would never contain a fractional part.  `bool`
is boolean value or a True/False value.  Buttons and switches would be the most
common booleans.  `str` is a text string.  This might be the aircrafts
registration number or the time in string format.

Min and Max
```````````

These are the absolute limits by which the item's value will be constrained.
Regardless of what value is written to the database the database item will never
exceed these values.  For example the magnetic heading (HEAD) has a Min of 0 and
a Max of 360.  If 370 is written to the point the actual value stored in the
database would be 360.

Units
`````

These are the engineering units applied to the item.  "psi", "inHg", "feet", or
"knots" are examples of units.

Initial
```````

This is the initial value that the item will contain on start up.  Most would be
zero but occasionally it makes sense to initialize a datapoint to something
else.  For example the altimeter setting (BARO) is initialized to 29.92.

TOL
```

TOL stands for Time Out Lifetime in milliseconds.  It's the amount of time that
is given for each point to be written to the database.  If a value is not
written to the database in this amount of time the item is considered to be
'old' and the point will have the 'old' flag set to True when the value is read
from the database.  It is assumed that for the most part, the TOL is set to
double the update rate.  For some points a timeout does not make sense.  If the
TOL is set to zero the item will never be considered to be old.

Auxiliary Data
``````````````

The Auxiliary Data (or Aux Data) is additional data that is associated with the
point.  It is mostly used for ranging instruments and indicating alarm and
warning set points.  It could be used for other things like 'V' speeds for
Indicated airspeed as well.  These aux data values are assumed to be of the same
data type and should be within the same range as the item itself.  They are
simply stored in the database and delivered to the plugins that need them.

There are six fairly common aux data points, `Min`, `Max`, `lowWarn`,
`lowAlarm`, `highWarn` and `highAlarm.`  Min and Max here don't override the Min
and Max above (probably should change the names to avoid confusion.) they would
not affect the value that the database would store but are most often used to
change the indicating range of the item.  The other four might be used to
indicate yellow arcs and/or red lines on gauges.  In fact all of the gauges in
pyEfis use these six values to determine the range of the gauge and the yellow
and red arcs that are on the gauge.  All a pyEfis gauge widget needs to know to
do it's job is the key of the point you want to display.  The aux data tells it
everything else that it needs to know to do it's job.

The reason that the Auxiliary Data is stored in the FIX Gateway database instead
of being handed off to the displaying device, is to make integration simpler.
There may be several EFIS screens in the aircraft and each one would have to be
configured with all of the low / warning setpoints for each point.  Centralizing
this information in the gateway makes it easier.  It could also mean that a flap
controller could have access to the Vfe data from the IAS point and then could
protest in some way or indicate an alarm if the pilot tried to lower the flaps
above this threshold.  The flap controller would not have to be configured with
this information it would simply be available and it would always match what is
indicated on the Airspeed Indicator(s).
