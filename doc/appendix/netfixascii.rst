=======================================
Net-FIX ASCII Protocol Description
=======================================

.. Need to clean up this file and make it look like an intelligent
   person wrote it.  ]]]

The Net-FIX ASCII Protocol is a TCP/IP based FIX protocol that uses simple ASCII
sentences.

Net-FIX ASCII is a sentence based ASCII protocol.  There are two types of
sentences.  The first type is a simple data update.  This is how the server
would communicate the actual values of each data point.  The second type of
sentence is a command/response type of sentence.

Data Sentence Descripition
--------------------------

Data points are transmitted in colon ';' delimited strings that begin
with the FIX identifier and are followed by the data.

The data sentence from the server to the client is formed like this...

::

  ID;xxxx.x;aobfs\n

Where the ID is the Net-FIX ASCII identifier for the data point.  For example TAS =
True Airspeed.  The Net-FIX ASCII identifier is the same identifier that is setup
in the FIX-Gateway database.  At some point these ID's may be formailzed separately
but since we are still in development of this system at this stage we are using
the FIX-Gateway :doc:`database` as a common place to configure this information.

The ``xxxx.x`` represents the value. The value can be a float, int,
bool or string (The string cannot contain a ;).  Floats will contain the decimal
point, integers will not. Booleans will be 'T' or 'F' and strings will begin
with an '&'.  the 'aobfs' represent the quality flags.  They will be either 1 or
0. a=annunciate, o=Old, b=bad, f=failed, s=secondary fail.  The old flag is set
if the data has not been written within the configured time to live for that
point.  The bad is set if there is reason to doubt the data but it hasn't
actually failed. If the failed flag is set then the data cannot be trusted and
should not be displayed or used in a calculation.  The secondary failed flag may
not always exist and if it is there it means that the secondary source of the
data (for redundant systems) is failed and is not available.  The sentence is
terminated with a newline ('\n' or 0x0A) character.

The sentence from the client to the server is similar...

::

  ID;xxxx.x;abfs\n

The difference is that the old flag is removed.  If the client
determines that the data is old it should simply set the bad flag.
The secondary failed flag is optional.  If flags are not sent they are
assumed to be false '0';

Command Sentence Description
----------------------------

Commands from the client to the server should begin with an '@'.  What
follows the '@' depend on the individual command.

Commands are single letter commands that are followed by any
parameters that are needed.  Responses to the command from the server
will begin with the '@' and the command letter.

``@cxxxxx...\n``

c = the command letter
xxxx... represents the data required by the individual command

Typically arguments to command are separated by semicolons ';'

``@cxxxxx;arg1;arg2;arg3...\n``

If the command expects a response then the response will follow with a message
that starts with the @ symbol followed by the command letter then followed by
the response. The individual command messages will document the actual syntax of
a response.

If the command only expects an acknowledgement of success the server will simply
respond with the message that was sent.


If there is a problem with the command the server
would respond with the error symbol '!' followed by the error code.
The following is an exmple of an error returned by the read command.

``@rIAS!001`` where 001 is the error code.

Some common error codes are given below...

* 001 - ID Not Found
* 002 - Bad Argument
* 003 - Bad Value
* 004 - Unknown Command

Read Command
~~~~~~~~~~~~

``r`` = Read Data - pass the ID or the ID + aux value that you
want to read.

The response from the read command is the ID, folowed by the value, followed
by the quality flags.  The flags are exactly like the quality flags sent in
a data update sentence

``@rIAS;105.2;00000``

``@rIAS.Vs`` would cause the server to report the Vs auxilliary data
if it exists.

Error Codes:

* 001 - ID Not Found


Write Command
~~~~~~~~~~~~~

``w`` = Write the value.  This command is similar to sending a normal
data sentence except that it does not affect the quality flags and it gives
the client a return value with errors if something fails.

``@wIAS;105.2``

Error Codes:

* 001 - ID Not Found
* 003- Bad Argument


Subscribe Command
~~~~~~~~~~~~~~~~~

``s`` = subscribe - subscribe to an ID to have the server send this data
each time it's written.

``@sTAS`` would cause the server to send the True Airspeed each time it's
written to the database.  The server would respond with the identical
message, or the ! followed by an error code.

Error Codes:

* 001 - ID Not Found

Unsubscribe Command
~~~~~~~~~~~~~~~~~~~

``u`` = unsubscribe - unsubscribe from the data point.

``@uTAS`` would undo the above subscription.  The server would respond
with the identical message, or the ! followed by an error code.

Error Codes:

* 001 - ID Not Found
* 002 - Duplicate Subscription

List Command
~~~~~~~~~~~~

``l`` = List - used to list the Identifiers that the server is handling.

``@l`` would cause the server to send the entire list of IDs that are
configured.  The list may be huge and as such may be returned in
more than one response.  The client should be prepared for
multiple responses.  The response will include the total number of
Identifiers to expect as well as the current index.  The Identifiers will
not be in any kind of order.  Identifiers would be separated with commas ','

The response might look like this...

::

  @l234;12;ID1,ID2,ID3,ID4...

Where 234 is the total and 12 is the starting index.

Query Command
~~~~~~~~~~~~~

``q`` = Item Report - Used to cause the server to report all the
data associated with a given database key.  Data such as the min and max
values the units the time to live etc.

``@qAOA`` would cause the server to respond with all the parameters
associated with this data point.

Server response.

::

  @qAOA;desc;type;min;max;units;tol;aux

*desc* = the description of the data ("Indicated Airspeed")
*type* = data type and will be one of [float, int, bool, str]
*min* = the minimum value the point will ever be
*max* = the maximum value the point will ever be
*units* = string denoting the units ("knots")
*tol* = an integer indicating the time to live of the point in milliseconds.
*aux* = a comma separated list of the auxillary data points.  ("min,max,lowWarn,lowAlarm")

Error Codes:

* 001 - ID Not Found

Flags Command
~~~~~~~~~~~~~

``f`` = Set or Clear quality flags on a database item atomically

``@fID;flag;setting`` where ID is the ID of the data point to modify.  Flag is a
single letter that represents the quality flag.  It can be one of the following
[aobfs].  Setting is either a '1' or a '0'.

On success the server will respond with the same command that it received.

::

  ``@fID;flag;bit``


Error Codes:

* 001 - ID Not Found
* 002 - Invalid Flag
* 003 - Invalid setting

Server Specific Command
~~~~~~~~~~~~~~~~~~~~~~~

``x`` = Server Specific Command - This is used to send specific commands to a
particular server.

``@x<cmd>`` sends the <cmd> command to a server.

``@x<cmd>;<arguments>;...`` sends the <cmd> command to a server with some number
of arguments separated by ';'.

Server response.

::

  @x<cmd>;<response>

Currently FIX-Gateway uses this command for retreiving the status.  The command
is...

``@xstatus`` and the server will respond with a JSON string representing
the status of the server.

The client/server is asynchronous so the client does not have to wait
for a response from the server before sending another command.  Data
updates from subscriptions may also come in between the client command
and the response.  The client should pay attention to the structure of
the message to make sure that it is a response to the command.  This
is why the arguments to the command are returned with the response.
So the client can differentiate.

Min and Max that might show up in auxillary data is different than the
min and max that show up as items in the report.  The report items are
the protocols limit on the data.  If they show up in the aux data they
are to be used for setting the range of indicators for display units.
The datapoint will never exceed the min/max that are set in the
database definition but the min and max that may be in the aux data
are arbitrary and the server does nothing except type check that
information.
