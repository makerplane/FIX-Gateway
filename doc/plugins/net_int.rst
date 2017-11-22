=================================
Network Command Interface
=================================

This is a command interface similar to the command line plugin except
that this one communicates with FIX-Gateway over a network connection.

Configuration
--------------

::

  [conn_net_int]
  load = yes
  module = plugins.net_int
  host = 127.0.0.1   # Network host to listen on
  port = 8888        # TCP port to listen on


Use
---

To use the ``net_int`` plugin as a remote command interface simply use *telnet* to connect to
the host and port that you configured the plugin to listen on.

You could also write another program to communicate to FIX Gateway over this network interface
but that seems a bit counter productive since plugins are so easy to write for FIX-Gateway.
You may have your reasons but a description of what that would take is beyond the scope
of this manual.


Commands
________


``read <KEY>``

This command will return the value in the database associated with the KEY.


``write <KEY> <VALUE>``

This command writes the value into the database entry associated with the key.

``list``

Lists all of the keys that are available in the database.

.. ``report <KEY>``

   Gives a list of all of the information that is associated with the database entry given by
   the key.  This includes the datatype, the value, quality flags etc.

   ``flag <KEY> <FLAG> <ARG>``

   Sets or clears a quality flag associated with the database entry given by key.  The flag argument
   can be any one of ``b,f,a or s``  These are for the *bad*, *fail*, *annunciate* and *secondary failure*
   flags respectively.  ARG can be ``true`` or ``false`` and the flag will be set appropriately.  ``1``
   and ``0`` can also be used for ARG as a shorthand.

``poll <KEY>``

Subscribes to the given key.  Once this command is run the value for the database item given by
the key will be returned each time the database entry is changed.

``stop <KEY>``

Unsubscribes from the given key.  Stops the update of the given key.

.. ``status``

    Prints the plugin's status to the screen

``quit``

Disconnects you from the plugin server.