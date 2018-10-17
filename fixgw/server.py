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

import yaml
try:
    import queue
except:
    import Queue as queue
import importlib
import logging
import logging.config
import argparse
import fixgw.database as database
import fixgw.status as status
import fixgw.plugin as plugin

import signal
import os
import sys

config_filename = "default.yaml"
path_options = ['.', 'config', '/usr/local/etc/fixgw', '/etc/fixgw']


# This dictionary holds the modules for each plugin that we load
plugin_mods = {}
# This holds the instantiated object of each plugin that we load
plugins = {}


def load_plugin(name, module, config):
    plugin_mods[name] = importlib.import_module(module)
    # strings here remove the options from the config before it is
    # sent to the plugin.
    for each in ["load", "module"]:
        del config[each]
    plugins[name] = plugin_mods[name].Plugin(name, config)


def main():
    # Look for our configuration file in the list of directories
    for directory in path_options:
        # store the first match that we find
        if os.path.isfile("{}/{}".format(directory, config_filename)):
            config_path = directory
            break

    config_file = "{}/{}".format(config_path, config_filename)
    parser = argparse.ArgumentParser(description='FIX Gateway')
    parser.add_argument('--debug', action='store_true',
                        help='Run in debug mode')
    parser.add_argument('--config-file', type=argparse.FileType('r'),
                        help='Alternate configuration file')
    parser.add_argument('--log-config', type=argparse.FileType('r'),
                        help='Alternate logger configuration file')

    args, unknown_args = parser.parse_known_args()

    # if we passed in a configuration file on the command line...
    if args.config_file:
        cf = open(args.config_file)
    else: # otherwise use the default
        cf = open(config_file)
    config = yaml.load(cf)

    if args.log_config:
        logging.config.fileConfig(args.log_config)
    else:
        logging.config.dictConfig(config['logging'])

    log = logging.getLogger()
    if args.debug:
        log.setLevel(logging.DEBUG)
    log.info("Starting FIX Gateway")


    try:
        database.init(config["database file"].format(CONFIG=config_path))
    except Exception as e:
        log.error("Database failure, Exiting")
        print(e)
        raise
        return # we don't want to run with a screwed up database

    log.info("Setting Initial Values")
    ifiles = config["initialization files"]
    for fn in ifiles:
        try:
            f = open(fn.format(CONFIG=config_path), 'r')
            for line in f.readlines():
                l = line.strip()
                if l and l[0] != '#':
                    x = l.split("=")
                    if len(x) >= 2:
                        database.write(x[0].strip(), x[1].strip())
        except Exception as e:
            log.error("Problem setting initial values from configuration - {0}".format(e))
            raise

    # TODO: Add a hook here for post database creation code

    # TODO: Need to do some more thorough error checking here

    # run through the plugin_list dict and find all the plugins that are
    # configured to be loaded and load them.

    for each in config['connections']:
        if config['connections'][each]['load']:
            module = config['connections'][each]["module"]
            try:
                load_plugin(each, module, config['connections'][each])
            except Exception as e:
                logging.critical("Unable to load module - " + module + ": " + str(e))
                if args.debug:
                    raise


    status.initialize(plugins)

    def sig_int_handler(signum, frame):
        plugin.jobQueue.put("QUIT")

    signal.signal(signal.SIGINT, sig_int_handler)


    # TODO add a hook here for pre module run code

    for each in plugins:
        log.debug("Attempting to start plugin {0}".format(each))
        try:
            plugins[each].start()
        except Exception as e:
            if args.debug:
                raise e  # If we have debuggin set we'll raise this exception

    iteration = 0
    while True:
        try:
            job = plugin.jobQueue.get(timeout=1.0)
            if job == "QUIT":
                break
        except KeyboardInterrupt:  # This should be broken by the signal handler
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

    cleanstop = True
    for each in plugins:
        log.debug("Attempting to stop plugin {0}".format(each))
        try:
            plugins[each].shutdown()
        except plugin.PluginFail:
            log.warning("Plugin {0} did not shutdown properly".format(each))
            cleanstop = False

    if cleanstop == True:
        log.info("FIX Gateway Exiting Normally")
    else:
        log.info("FIX Gateway Exiting Forcefully")
        os._exit(-1)

if __name__ == "__main__":
    # TODO: Add daemonization
    main()
