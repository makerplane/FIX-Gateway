#  Copyright (c) 2016 Phil Birkelbach
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

# This file controls mapping CAN-FIX parameter ids to FIX database keys


import fixgw.database as database
import yaml
import canfix

class Mapping(object):
    def __init__(self, mapfile, log=None):
        self.meta_replacements_in = {}
        self.meta_replacements_out = {}

        # This is a list of function closures
        self.input_mapping = [None] * 1280
        self.output_mapping = {}
        self.log = log
        self.sendcount = 0


        # Open and parse the YAML mapping file passed to us
        try:
            f = open(mapfile)
        except:
            self.log.error("Unable to Open Mapfile - {}".format(mapfile))
            raise
        maps = yaml.load(f)
        f.close()
        
        # dictionaries used for converting meta data strings from db to canfix and back
        self.meta_replacements_in = maps['meta replacements']
        self.meta_replacements_out = {v:k for k,v in self.meta_replacements_in.items()}

        # We really just assign all the outputs to a dictionary for the main
        # plugin code to use to assign callbacks.
        for each in maps['outputs']:
            output = {'canid':each['canid'],
                      'index':each['index'],
                      'owner':each['owner'],
                      'exclude':False,
                      'lastValue':None}
            self.output_mapping[each['fixid']] = output

        # each input mapping item := [CANID, Index, FIX DB ID, Priority]
        for each in maps['inputs']:
            p = canfix.protocol.parameters[each["canid"]]
            # Parameters start at 0x100 so we subtract that offset to index the array
            ix = each["canid"] - 0x100
            if self.input_mapping[ix] is None:
                self.input_mapping[ix] = [None] * 256
            self.input_mapping[ix][each["index"]] = self.getInputFunction(each["fixid"])


    # The idea here is that we create arrays and dictionaries for each type of
    # mapping.  These contain closure functions that know how to put the data in
    # the right place.  The functions are determined ahead of time for
    # performance reasons which is why we are using closures.

    # This is a closure that holds the information we need to transfer data
    # from the CAN-FIX port to the FIXGW Database
    def getInputFunction(self, dbKey):
        dbItem = database.get_raw_item(dbKey)
        if dbItem == None: return None

        # The output exclusion keeps us from constantly sending updates on the
        # CAN Bus when the change that we recieved was from the CAN Bus.
        # Basically when the input function is called we'll first exclude
        # the output then make the change.  The output callback will be
        # called but will do nothing but reset the exclusion flag.
        if dbKey in self.output_mapping:
            output_exclude = True
        else:
            output_exclude = False

        def InputFunc(cfpar):
            if output_exclude:
                self.output_mapping[dbItem.key]['exclude'] = True
                self.output_mapping[dbItem.key]["lastValue"] = cfpar.value
            if cfpar.meta:
                try:
                    # Check to see if we have a replacemtn string in the dictionary
                    if cfpar.meta in self.meta_replacements_in:
                        m = self.meta_replacements_in[cfpar.meta]
                    else: # Just use the one we were sent
                        m = cfpar.meta
                    dbItem.set_aux_value(m, cfpar.value)
                except:
                    self.log.warning("Problem setting Aux Value for {0}".format(dbItem.key))
            else:
                dbItem.value = (cfpar.value, cfpar.annunciate, cfpar.quality, cfpar.failure)

        return InputFunc

    # Returns a closure that should be used as the callback for database item
    # changes that should be written to the CAN Bus
    def getOutputFunction(self, bus, dbKey, node):

        def outputCallback(key, value, udata):
            m = self.output_mapping[dbKey]
            # If the exclude flag is set we just recieved the value
            # from the bus so we don't turn around and write it back out
            if m['exclude']:
                m['exclude'] = False
                return
            if m["owner"]:
                # If we are the owner we send a regular parameter update
                pass
            else:
                # If we are not the owner we don't worry about the flags or
                # sending values that have not changed.
                if value[0] == m["lastValue"]:
                    return
                m["lastValue"] = value[0]
                p = canfix.ParameterSet(parameter=m["canid"], value=value[0])
                p.sendNode = node
                # print(p.msg)
                # print("Output Callback {} = {}".format(key, value))
                bus.send(p.msg)
                self.sendcount += 1
                # print(bus)
                # print(self.output_mapping[dbKey])

        return outputCallback

    # This opens the map file and buids the input mapping lists.
    # def initialize(self, mapfile):


    def inputMap(self, par):
        """Retrieve the function that should be called for a given parameter"""
        ix = par.identifier - 0x100
        im = self.input_mapping[ix] # This should always exist
        if im is None:
            return None
        if par.meta:
            for func in im:
                if func is not None:
                    func(par)
                #else:
                    #log.error("Yo you gotta be kidding")
        else:
            func = im[par.index]
            if func is not None:
                func(par)
