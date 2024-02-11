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
import traceback
import datetime

import fixgw.database as database
import fixgw.status as status
import fixgw.plugin as plugin
import fixgw.quorum as quorum

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
log = None

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

def sig_int_handler(signum, frame):
    plugin.jobQueue.put("QUIT")

def main_setup():
    global config_path
    global log
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
    parser.add_argument('--daemonize', '-D', action='store_true',
                        help='Run program in the background')
    parser.add_argument('--config-file', type=argparse.FileType('r'),
                        help='Alternate configuration file')
    parser.add_argument('--log-config', type=argparse.FileType('r'),
                        help='Alternate logger configuration file')
    parser.add_argument('--playback-start-time', type=datetime.datetime.fromisoformat, 
                        help='ISOformat - YYYY-MM-DD:HH:mm:ss') 
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
    config = yaml.safe_load(cf)

    # Either load the config file given as a command line argument or
    # look in the configuration for the logging object
    if args.log_config:
        logging.config.fileConfig(args.log_config)
    elif 'logging' in config:
        logging.config.dictConfig(config['logging'])
    else:
        logging.basicConfig()

    log = logging.getLogger("fixgw")
    if args.verbose:
        log.setLevel(logging.INFO)
    if args.debug:
        log.setLevel(logging.DEBUG)
    log.info("Starting FIX Gateway")
    log.info("Configuration Found at {}".format(config_file))

    # If quorum is enabled, set leader to false
    # When the database is started default values are set
    # We do not want to send those values out unless we are indeed the leader
    # and we do not know who the leader is when we are first starting
    if 'connections' in config:
        for con in config["connections"]:
            if 'module' in config["connections"][con]:
                if config["connections"][con]['module'].lower() == 'fixgw.plugins.quorum':
                    if config["connections"][con]['load']:
                        quorum.leader = False
                        break

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
        ifiles = config["initialization files"]
        for fn in ifiles:
            filename = fn.format(CONFIG=config_path)
            log.info("Setting Initial Values - {}".format(filename))
            try:
                f = open(filename, 'r')
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
    print(args.playback_start_time)
    if args.playback_start_time:
        # We are in playback mode, if logs for the time provided exist we will play them back
        for each in config['connections']:
            if config['connections'][each]["module"] == 'fixgw.plugins.data_recorder':
                # Find the data recorder config
                path = os.path.join( config['connections'][each]['filepath'].format(CONFIG=config_path), args.playback_start_time.strftime("%Y"), args.playback_start_time.strftime("%m"), args.playback_start_time.strftime("%d") )
                filepath = os.path.join( path, args.playback_start_time.strftime("%Y-%m-%d.%H.json") )
                print(filepath)
                file_list = [filepath] 
                if not os.path.isfile(filepath): raise Exception("No logs found for the date and time provided")
                # TODO Check the next hour, if file exists add it to the array.
                # Build the array until you have found 24 hours OR a hour file is missing
                more_files = True
                next_hour = args.playback_start_time + datetime.timedelta(hours=1)
                while more_files:
                    more_path = os.path.join( config['connections'][each]['filepath'].format(CONFIG=config_path), next_hour.strftime("%Y"), next_hour.strftime("%m"), next_hour.strftime("%d") )
                    more_file = os.path.join( more_path, next_hour.strftime("%Y-%m-%d.%H.json") )
                    if os.path.isfile(more_file):
                        file_list.append(more_file)
                        next_hour += datetime.timedelta(hours=1)
                    else:
                        more_files = False
                module = 'fixgw.plugins.data_playback'
                try:
                    load_plugin('netfix', 'fixgw.plugins.netfix', {'module': 'fixgw.plugins.netfix', 'load': True, 'type': 'server', 'host': '0.0.0.0', 'port': '3490', 'buffer_size': 1024})
                    load_plugin('data_playback', module,{'module': module, 'load': True, 'files': file_list, 'start_time': args.playback_start_time})

                except Exception as e:
                    logging.critical("Unable to load module - " + module + ": " + str(e))
                    if args.debug:
                        raise

    else:
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

    if not args.daemonize:
        signal.signal(signal.SIGINT, sig_int_handler)
        signal.signal(signal.SIGTERM, sig_int_handler)
    return args

def main():
    args = main_setup()
    log = logging.getLogger("fixgw")
    if args.daemonize:
        try:
            import daemon
            import lockfile
        except ModuleNotFoundError:
            log.error("Unable to load daemon module.")
            raise
        log.debug("Sending to Background")
        context = daemon.DaemonContext(
            #working_directory = '/',
            umask=0o002,
            #pidfile=lockfile.FileLock('/var/run/fixgw.pid'),
        )
        context.signal_map = {
            signal.SIGTERM: server.sig_int_handler,
            signal.SIGINT: server.sig_int_handler,
            signal.SIGHUP: 'terminate',
        }
        with context:
            try:
                run(args)
            except Exception as e:
                log.error(str(e))
    else:
        run(args)


def run(args):
    for each in plugins:
        log.debug("Attempting to start plugin {0}".format(each))
        try:
            plugins[each].start()
        except Exception as e:
            log.error("Problem Starting Plugin: {} - {}".format(each,e))
            if args.debug:
                log.debug(traceback.format_exc())
                plugin.jobQueue.put("QUIT")
                break
                # We cannot raise exception here, it will lock up
                # instead we exit

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
    main_setup()
    main()
