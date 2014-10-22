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

import ConfigParser
import importlib
import logging
import logging.config
import argparse
import plugin
import Queue

config_file = "main.cfg"
logconfig_file = config_file

# This dictionary holds the modules for each plugin that we load
plugin_mods = {}
# This holds the instantiated object of each plugin that we load
plugins = {}


def load_plugin(name, module, config):
    # strings here remove the options from the list before it is
    # sent to the plugin.
    exclude_options = ["load", "module"]
    try:
        plugin_mods[name] = importlib.import_module(module)
    except Exception as e:
        logging.critical("Unable to load module - " + module + ": " + str(e))
        return
    items = [item for item in config.items(name)
             if item[0] not in exclude_options]
    plugins[name] = plugin_mods[name].Plugin(name, items)


def main():
    parser = argparse.ArgumentParser(description='FIX Gateway')
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode')
    parser.add_argument('--config-file', type=file,
                        help='Alternate configuration file')
    parser.add_argument('--log-config', type=file,
                        help='Alternate logger configuration file')

    args = parser.parse_args()

    logging.config.fileConfig(logconfig_file)
    log = logging.getLogger()
    if args.debug:
        log.setLevel(logging.DEBUG)
    log.info("Starting FIX Gateway")

    config = ConfigParser.ConfigParser()
    config.read(config_file)

    #TODO: Need to do some more thorough error checking here

    # run through the plugin_list dict and find all the plugins that are
    # configured to be loaded and load them.

    try:
        for each in config.get("config", "plugins").split(","):
            if config.getboolean(each, "load"):
                module = config.get(each, "module")
                load_plugin(each, module, config)
    except ConfigParser.NoOptionError:
        log.warning("Unable to find option for " + each)
    except ConfigParser.NoSectionError:
        log.warning("No plugin found in configuration file with name " + each)

    for each in plugins:
        plugins[each].run()

    iteration = 0
    while True:
        try:
            job = plugin.jobQueue.get(timeout=1.0)
            if job == "QUIT":
                break
        except KeyboardInterrupt:
            log.info("Termination from keybaord received")
            break
        except Queue.Empty:
            pass
        iteration += 1
        # Every four times through the loop we do some stuff
        if iteration % 4 == 0:
            # check how many plugins are running and exit if zero
            running_count = 0
            for each in plugins:
                if plugins[each].is_running():
                    running_count += 1
            if running_count == 0:
                log.info("No plugins running, quitting")
                break

    for each in plugins:
        plugins[each].stop()

    log.info("FIX Gateway Exiting Normally")

if __name__ == "__main__":
    main()

