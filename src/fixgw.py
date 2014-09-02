#!/usr/bin/env python

#  Copyright (c) 2014 Phil Birkelbach
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

import database
import ConfigParser
import time

config_file = "config"

# This dictionary holds the modules for each plugin that we load
plugin_mods = {}
# This holds the instantiated object of each plugin that we load
plugins = {}

# List of configuration file sections that DO NOT represent plugins
exclude_sections = ["config"]

def log(string):
    print string

def load_plugin(name, module, config):
    # strings here remove the options from the list before it is
    # sent to the plugin.
    exclude_options = ["load", "module"]
    plugin_mods[name] = __import__(module)
    items = [item for item in config.items(name) if item[0] not in exclude_options]
    plugins[name] = plugin_mods[name].Plugin(name,items)

def main():
    log("Starting FIX Gateway")

    config = ConfigParser.ConfigParser()
    config.read(config_file)

    #TODO: Need to do some more thorough error checking here
    
    # run through the plugin_list dict and find all the plugins that are configured
    # to be loaded and load them.
    try:
        for each in config.sections():
            if each not in exclude_sections:
                if config.getboolean(each, "load"):
                    module = config.get(each, "module")
                    load_plugin(each, module, config)
    except ConfigParser.NoOptionError:
        log("Unable to find option for "+each)
    except ConfigParser.NoSectionError:
        log("No plugin found in configuration file with name "+each)

    for each in plugins:
        plugins[each].run()

    # Testing Testing Testing
    for i in range(10):
        print "Do something"
        time.sleep(0.1)
 
    for each in plugins:
        plugins[each].stop()


if __name__ == "__main__":
    main()

