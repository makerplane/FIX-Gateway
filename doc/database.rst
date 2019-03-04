=============================
The Main Database
=============================

The central feature of FIX-Gateway is the **database**.  The database is essentially just
a table of information stored in memory.  All the data from all the plug-ins must pass through
the database for the system to become functional.  One plugin may be reading the Airspeed from
a sensor and would write this data to the database.  Another plugin may be communicating the
airspeed to an EFIS or other type of indicator.

Each item in the database is identified by a key.  The key is a short string that is unique for
each entry in the database.  An example would be ``IAS`` which is for indicated airspeed.

The value of the entry is not the only piece of information stored in the database.  There are also
descriptions of the entry, the range of the value, etc.

* Value - This is the actual value that the entry represents.  An airspeed might be 123.4.

* Units - This would be the engineering units of the give database entry.  For airspeed it is ``knots``.

* Description - A detailed description of what the point represents.  i.e. "Altimeter Setting" or
  "Exhuast Gas Temp Engine 1 Cylinder 3"

* Min / Max - The maximum range the of the value

* Bad - A flag indicating that the data might be in doubt.  Some indication should be made that
  this data may be untrustworthy.  ``True`` if data is bad and ``False`` otherwise.

* Fail - A flag indicating that the data is known to be bad.  This flag is set when the plugin
  that is writing the data knows that the data is bad.  Typically a zero value will be sent as well.
  This data should not be displayed at all and should not be used in any calculations.

* Old - A flag indicating that the database entry has not been updated within the specified period of
  time.  Each database entry has a *time to live* and if this time is exceeded before another update to
  the database is made the *Old* flag will be set to ``True``.  For some data this is not relevant so
  the *time to live* is set to zero and the entry will never be marked as old.

* Annunciate - This is a flag that would tell indicating equipment that this point needs to be
  annunciated.  This might mean that an oil pressure limit has been exceeded.  It's more appropriate
  for the sending devices to decide when to annunciate information than the display equipment.  There
  are a couple of reasons for this.  The first is that the equipment that generates the data is
  better equiped to know when that data has exceeded limits.  An example is oil temperature.  There
  are typically low oil temperature limits, but they are useless right after engine startup when the
  oil temperature will be low anyway.  No need to alarm on that.  The other reason is, there may
  be more than one piece of display equipment and configuring each one with alarm limits is redundant.

* Auxillary Data - The Auxiliary Data (or Aux Data) is additional data that is associated with the
  point.  It is mostly used for ranging instruments and indicating alarm and
  warning set points.  It could be used for other things like 'V' speeds for
  Indicated airspeed as well.  These aux data values are assumed to be of the same
  data type and should be within the same range as the item itself.  They are
  simply stored in the database and delivered to the plugins that need them.
