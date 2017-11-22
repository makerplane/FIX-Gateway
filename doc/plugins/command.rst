==========================
Command Line Plugin
==========================

The command line plugin is useful for debugging and testing.  It gives us the ability
to view and manipulate the database from an interactive interface.

Configuration
-------------------

::

  [conn_command]
  load = yes
  module = plugins.command
  prompt = FIX:
  
  # If set quiting the command interpreter plugin
  # will end execution of the program
  quit = yes


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

``sub <KEY>``

Subscribes to the given key.  Once this command is run the value for the database item given by
the key will be returned each time the database entry is changed.

``unsub <KEY>``

Unsubscribes from the given key.  Stops the update of the given key.

``status``

Prints the plugin's status to the screen

``quit``
``exit``

Exits the Command Line Plugin.  If ``quit = yes`` is set in the configuration file this will also
cause the entire FIX-Gateway process to exit.  Otherwise the command line plugin will stop and 
the rest of the system will function as it was.

