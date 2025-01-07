#  Copyright (c) 2013 Phil Birkelbach
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

# This is the CAN-FIX plugin. CAN-FIX is a CANBus based protocol for
# aircraft data.

import threading
import fixgw.plugin as plugin
from collections import OrderedDict

import can
#import canfix

#from . import mapping
# TODO Add send class that sends the data at the intervals specified in the MGL docs

from . import rdac

class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.interface = config['interface']
        self.channel = config['channel']
        #self.device = int(config['device'])
        #self.node = int(config['node'])
        #mapfilename = config['mapfile'].format(CONFIG=config['CONFIGPATH'])
        #self.mapping = mapping.Mapping(mapfilename, self.log)
        self.threads = []
        if self.config.get('rdac',False):
            # We have rdac configured
            if self.config['rdac'].get('get',False):
                self.threads.append(rdac.Get(self,self.config['rdac']))
        if self.config.get('rdac',False):
            # We have rdac configured
            if self.config['rdac'].get('send',False):
                self.threads.append(rdac.Send(self,self.config['rdac']))

        #self.thread = rdac.Get(self, config)
        self.recvcount = 0
        self.errorcount = 0
        self.wantcount = 0

    def run(self):
        self.bus = can.ThreadSafeBus(self.channel, interface = self.interface)
        #for each in self.mapping.output_mapping:
            # TODO This will work to collect the data that needs sent
            # But we need another thread where we can send on a timer.
            #self.db_callback_add(each, self.mapping.getOutputFunction(self.bus, each, self.node))
        for each in self.threads:
            each.start()

    def stop(self):
        for each in self.threads:
            each.stop()
        for each in self.threads:
            if each.is_alive():
                each.join(1.0)
            if each.is_alive():
                raise plugin.PluginFail

    def get_status(self):
        x = OrderedDict()
        x["CAN Interface"]=self.interface
        x["CAN Channel"]=self.channel
        x["Received Frames"]=self.recvcount
        x["Wanted Frames"]=self.wantcount
        x["Sent Frames"]=self.mapping.sendcount
        x["Error Count"]=self.errorcount
        return x

# TODO: Add error reporting in debug mode
# TODO: Add output parameter mapping
# TODO: Add parameter setting node specific mapping
# TODO: Finish adding the mappings to the YAML file
# TODO: Add the rest of the CAN-FIX protocol mandatory stuff
# TODO: Add tests, tests, tests
