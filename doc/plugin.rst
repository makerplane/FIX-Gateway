================================
 FIX Gateway Plugin Development
================================

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

::

    import plugin
    import threading
    import time
    from collections import OrderedDict

    class MainThread(threading.Thread):
        def __init__(self, parent):
            """The calling object should pass itself as the parent.
               This gives the thread all the plugin goodies that the
               parent has."""
            super(MainThread, self).__init__()
            self.getout = False   # indicator for when to stop
            self.parent = parent  # parent plugin object
            self.log = parent.log  # simplifies logging
            self.count = 0

        def run(self):
            while True:
                if self.getout:
                    break
                time.sleep(1)
                self.count += 1
                self.log.debug("Yep")  # Do something more useful here
            self.running = False

        def stop(self):
            self.getout = True


    class Plugin(plugin.PluginBase):
        """ All plugins for FIX Gateway should implement at least the class
        named 'Plugin.'  They should be derived from the base class in
        the plugin module.

        The run and stop methods of the plugin should be overridden but the
        base module functions should be called first."""
        def __init__(self, name, config):
            super(Plugin, self).__init__(name, config)
            self.thread = MainThread(self)

        def run(self):
            """ The run method should return immediately.  The main routine will
            block when calling this function.  If the plugin is simply a collection
            of callback functions, those can be setup here and no thread will be
            necessary"""
            super(Plugin, self).run()
            self.thread.start()

        def stop(self):
            """ The stop method should not return until the plugin has completely
            stopped.  This generally means a .join() on a thread.  It should
            also undo any callbacks that were set up in the run() method"""
            self.thread.stop()
            if self.thread.is_alive():
                self.thread.join(1.0)
            if self.thread.is_alive():
                raise plugin.PluginFail
            super(Plugin, self).stop()

        def get_status(self):
            """ The get_status method should return a dict or OrderedDict that
            is basically a key/value pair of statistics"""
            return OrderedDict({"Count":self.thread.count})


The basic idea is that you need to create a module that contains a class named
``Plugin``.  That class should extend the ``plugin.PluginBase`` class.  If you
override the ``__init__`` method, your plugin should call the ``__init__``
method of the parent class. At a minimum override the ``run`` method of the
parent class and call the parent classes ``run`` method.  If your plugin runs
another thread that may need to be stopped cleanly you should also reimplement
the ``stop`` method.

The ``run`` method that you implement should return quickly.  All the parts of
your plugin that need to run continuously should be done in another thread and
that thread started  from ``run``.  The rest of the system will wait for your
``run`` method to exit.
