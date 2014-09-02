================================
 FIX Gateway Plugin Development
================================

The FIX Gateway architecture involves multiple plugins reading and/or writing to a central
database of flight information.  Each plugin is a Python class that inherits from a base
class that is supplied with the FIX Gateway program.  The plugin files need only be in the
Python search path and their associated information given in the main configuration file.

FIX Gateway will read the configuration file, determine which plugins to load, load them,
start them and stop them when the time comes.
