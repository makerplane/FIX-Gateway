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
import signal
import os
import sys
import io

import fixgw.database as database
import fixgw.status as status
import fixgw.plugin as plugin

config_filename = "default.yaml"
user_home = os.path.expanduser("~")
prefix_path = sys.prefix
path_options = ['{USER}/.makerplane/fixgw/config',
                '{PREFIX}/local/etc/fixgw',
                '{PREFIX}/etc/fixgw',
                '/etc/fixgw',
                'fixgw/config',
                '.']
config_path = None

# This dictionary holds the modules for each plugin that we load
plugin_mods = {}
# This holds the instantiated object of each plugin that we load
plugins = {}


def load_plugin(name, module, config):
    plugin_mods[name] = importlib.import_module(module)
    # remove these options from the config before it is
    # sent to the plugin.
    for each in ["load", "module"]:
        del config[each]
    # Add some global information to the config
    config["CONFIGPATH"] = config_path
    plugins[name] = plugin_mods[name].Plugin(name, config)


# This function recursively walks the given directory in the installed
# package and creates a mirror of it in basedir.
def create_config_dir(basedir):
    # Look in the package for the configuration
    import pkg_resources as pr
    package = 'fixgw'
    def copy_dir(d):
        os.makedirs(basedir + "/" + d, exist_ok=True)
        for each in pr.resource_listdir(package, d):
            filename = d + "/" + each
            if pr.resource_isdir(package, filename):
                copy_dir(filename)
            else:
                s = pr.resource_string(package, filename)
                with open(basedir + "/" + filename, "wb") as f:
                    f.write(s)
    copy_dir('config')


def main():
    global config_path
    # Look for our configuration file in the list of directories
    for directory in path_options:
        # store the first match that we find
        d = directory.format(USER=user_home, PREFIX=prefix_path)
        if os.path.isfile("{}/{}".format(d, config_filename)):
            config_path = d
            break

    config_file = "{}/{}".format(config_path, config_filename)
    parser = argparse.ArgumentParser(description='FIX Gateway')
    parser.add_argument('--debug', '-d', action='store_true',
                        help='Run in debug mode')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Run in verbose mode')
    parser.add_argument('--config-file', type=argparse.FileType('r'),
                        help='Alternate configuration file')
    parser.add_argument('--log-config', type=argparse.FileType('r'),
                        help='Alternate logger configuration file')

    args, unknown_args = parser.parse_known_args()

    # if we passed in a configuration file on the command line...
    if args.config_file:
        cf = args.config_file
        config_file = cf.name
    elif config_path is not None: # otherwise use the default
        cf = open(config_file)
    else:
        # If all else fails copy the configuration from the package
        # to ~/.makerplane/fixgw/config
        create_config_dir("{USER}/.makerplane/fixgw".format(USER=user_home))
        # Reset this stuff like we found it
        config_file = "{USER}/.makerplane/fixgw/config/{FILE}".format(USER=user_home, FILE=config_filename)
        cf = open(config_file)

    config_path = os.path.dirname(cf.name)
    config = yaml.load(cf)

    # Either load the config file given as a command line argument or
    # look in the configuration for the logging object
    if args.log_config:
        logging.config.fileConfig(args.log_config)
    elif 'logging' in config:
        logging.config.dictConfig(config['logging'])
    else:
        logging.basicConfig()

    log = logging.getLogger()
    if args.verbose:
        log.setLevel(logging.INFO)
    if args.debug:
        log.setLevel(logging.DEBUG)
    log.info("Starting FIX Gateway")
    log.info("Configuration Found at {}".format(config_file))


    # Open database definition file and send to database initialization
    try:
        ddfile = config["database file"].format(CONFIG=config_path)
        f = open(ddfile,'r')
    except:
        log.critical("Unable to open database definition file - " + ddfile)
        raise
    try:
        database.init(f)
    except Exception as e:
        log.error("Database failure, Exiting:" + str(e))
        raise

    if "initialization files" in config and config["initialization files"]:
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

    ss = {"Configuration File": config_file,
          "Configuration Path": config_path}
    status.initialize(plugins, ss)

    def sig_int_handler(signum, frame):
        plugin.jobQueue.put("QUIT")

    signal.signal(signal.SIGINT, sig_int_handler)
    signal.signal(signal.SIGTERM, sig_int_handler)


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
