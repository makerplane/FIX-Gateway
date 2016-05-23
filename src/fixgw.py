#!/usr/bin/env python3

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

import configparser
import importlib
import logging
import logging.config
import argparse
import database
import plugin
import queue
import sys

config_file = "config/main.cfg"
logconfig_file = config_file

# This dictionary holds the modules for each plugin that we load
plugin_mods = {}
# This holds the instantiated object of each plugin that we load
plugins = {}


def load_plugin(name, module, config):
    # strings here remove the options from the list before it is
    # sent to the plugin.
    exclude_options = ["load", "module"]
    plugin_mods[name] = importlib.import_module(module)
    # Here items winds up being a list of tuples [('key', 'value'),...]
    items = [item for item in config.items("conn_" + name)
             if item[0] not in exclude_options]
    # Append the command line arguments to the items list as a tuple
    items.append(('argv', sys.argv))
    # Convert this to a dictionary before passing to the plugin
    cfg = {}
    for each in items:
        cfg[each[0]] = each[1]
    plugins[name] = plugin_mods[name].Plugin(name, cfg)


def main():
    parser = argparse.ArgumentParser(description='FIX Gateway')
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode')
    parser.add_argument('--config-file', type=argparse.FileType('r'),
                        help='Alternate configuration file')
    parser.add_argument('--log-config', type=argparse.FileType('w'),
                        help='Alternate logger configuration file')

    args, unknown_args = parser.parse_known_args()

    logging.config.fileConfig(logconfig_file)
    log = logging.getLogger()
    if args.debug:
        log.setLevel(logging.DEBUG)
    log.info("Starting FIX Gateway")

    config = configparser.ConfigParser()
    config.read(config_file)
    try:
        database.init(config)
    except Exception as e:
        log.error("Database failure, Exiting")
        print(e)
        raise
        return # we don't want to run with a screwed up database

    # TODO: Add a hook here for post database creation code

    # TODO: Need to do some more thorough error checking here

    # run through the plugin_list dict and find all the plugins that are
    # configured to be loaded and load them.

    for each in config:
        if each[:5] == "conn_":
            if config.getboolean(each, "load"):
                module = config.get(each, "module")
                try:
                    load_plugin(each[5:], module, config)
                except Exception as e:
                    logging.critical("Unable to load module - " + module + ": " + str(e))


    # TODO add a hook here for pre module run code

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
        except queue.Empty:
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
