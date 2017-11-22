==================
Plugin Development
==================

The FIX Gateway architecture involves multiple plugins reading and/or writing to
a central database of flight information.  Each plugin is a Python class that
inherits from a base class that is supplied with the FIX Gateway program.  The
plugin files need only be in the Python search path and their associated
information given in the main configuration file.

FIX Gateway will read the configuration file, determine which plugins to load,
load them, start them and stop them when the time comes.

The best place to start with writing a plugin is with the ``skel.py`` file that
is included in the distribution under the ``plugins/`` directory.  This is a
skeleton file that will give you a start on writing your own plugin.

.. literalinclude:: ../src/plugins/skel.py


The basic idea is that you need to create a module that contains a class named
``Plugin``.  That class should extend the ``plugin.PluginBase`` class.

At a minimum implement two methods ``run()`` and ``stop()``.  The ``run()``
method will be called by FGW to start your plugin.  Likewise, ``stop()`` will be
called to tell your plugin to shutdown cleanly.

The ``__init__`` method of the parent class will be passed an argument called
*config*.  This is stored in the created object as *self.config*.  This is simply
a dictionary of the configuration key/value pairs that were in your plugin's ``conn_``
section of the main configuration file, minus the few directives that FIX-Gateway
needs to do it's work.

``run()`` needs to return quickly.  This is not the place for continuously
running code. All the parts of your plugin that need to run continuously should
be done in another thread and that thread started  from ``run()``.  The rest of
the system will wait for your ``run()`` method to exit so if it takes a long
time it will slow the start of the rest of the system.

At anytime during the execution of your plugin it stops running, set the
property ``self.running = False``.  This  is a status point that is
automatically generated for you plugin so the user can see if  you are actually
running or not.  If the ``run()`` method raises an exception the flag will never
be set to ``True`` by FGW.

The ``stop()`` method should also return fairly quickly.  A common way of
getting out of threads that are blocked on I/O is to set a timeout for the I/O
and check a flag and exit if the flag is set.  If the  ``stop()`` method raises
the exception ``plugin.PluginFail`` the FGW system will recognize that some
threads may have not shutdown cleanly and will do a hard exit with an error
code.  This allows the program to go ahead and exit cleanly (without having to
be killed) so that it can be restarted.

If you override the ``__init__`` method, your plugin should call the
``__init__`` method of the parent class.

The ``get_status()`` method can be overriden in your plugin to give information
back to the status subsystem.  The method should simply return a dictionary of
key/value pairs of status information. The ``skel.py`` example simply returns
the number of times we've been through the loop.  Other plugins might send
information about number of connections active, message counters, error counters
etc.  An ``OrderedDict`` is prefered as well since the user will get your
information in the same order that you sent it.  If this is not important then a
normal python dictionary will work fine as well.

The dictionary that you return will be added to an internal dictionary along
with all the ones returned by the other plugins.  User interface plugins can use
this information to display status to the user.
