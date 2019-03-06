==========================
Client Utility
==========================

The client is useful for debugging and testing.  The server should generally
be run in the background as a service.  The client connects to the server
using the `netfix` protocol.  The client allows us to remotely read and
write database items as well as see database details and server status.

Usage
-------------------

The Client can be run by executing the ``fixgwc`` command from the console. Or
by executing the ``fixgwc.py`` python script from the distribution.

If run with no arguments the client will try to connect to a server running
on the same host with the default port number and start up in interactive mode.

The following command line arguments can be passed to the client to change
the behavior.

::

  --help, -h                   Show a help message and exit
  --debug                      Run in debug mode
  --host HOST, -H HOST         IP address or hostname of the FIX-Gateway Server
  --port PORT, -P PORT         Port number to use for FIX-Gateway Server connection
  --prompt PROMPT, -p PROMPT   Command line prompt
  --file FILENAME, -f FILENAME Execute commands within file
  --execute EXECUTE [EXECUTE ...], -x EXECUTE [EXECUTE ...] Execute command
  --interactive, -i            Keep running after commands are executed



Commands
----------

``read <KEY>``

This command will return the value in the database associated with the KEY.


``write <KEY> <VALUE>``

This command writes the value into the database entry associated with the key.

``list``

Lists all of the keys that are available in the database.

``report <KEY>``

Gives a list of all of the information that is associated with the database entry given by
the key.  This includes the datatype, the value, quality flags etc.

``flag <KEY> <FLAG> <ARG>``

Sets or clears a quality flag associated with the database entry given by key.  The flag argument
can be any one of ``b,f,a or s``  These are for the *bad*, *fail*, *annunciate* and *secondary failure*
flags respectively.  ARG can be ``true`` or ``false`` and the flag will be set appropriately.  ``1``
and ``0`` can also be used for ARG as a shorthand.

``poll <KEY>``

Subscribes to the given key and prints the value of the the item in the database
every time that item changes.  Pressing a key stops the polling.


``status``

Prints the  status to the screen

``quit``
``exit``

Exits the Client
