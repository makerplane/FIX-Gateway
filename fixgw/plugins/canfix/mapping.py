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
        self.input_nodespecific = [None] * 1280
        self.output_mapping = {}
        self.log = log
        self.sendcount = 0


        # Open and parse the YAML mapping file passed to us
        try:
            f = open(mapfile)
        except:
            self.log.error("Unable to Open Mapfile - {}".format(mapfile))
            raise
        maps = yaml.safe_load(f)
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
            #p = canfix.protocol.parameters[each["canid"]]
            # Parameters start at 0x100 so we subtract that offset to index the array
            ix = each["canid"] - 0x100
            if self.input_mapping[ix] is None:
                self.input_mapping[ix] = [None] * 256
            self.input_mapping[ix][each["index"]] = self.getInputFunction(each["fixid"])
            self.input_nodespecific[ix] = each.get('nodespecific',False)
        # each input mapping item := [CANID, Index, FIX DB ID, Priority]
        for each in maps['encoders']:
            #p = canfix.protocol.parameters[each["canid"]]
            # Parameters start at 0x100 so we subtract that offset to index the array
            ix = each["canid"] - 0x100
            if self.input_mapping[ix] is None:
                self.input_mapping[ix] = [None] * 256
            self.input_mapping[ix][each["index"]] = self.getEncoderFunction(each["fixid"], each.get('sum', False))
            self.input_nodespecific[each["canid"]] = each.get('nodespecific',False)
        for each in maps['switches']:
            ix = each["canid"] - 0x100
            if self.input_mapping[ix] is None:
                self.input_mapping[ix] = [None] * 256
            self.input_mapping[ix][each["index"]] = self.getSwitchFunction(each["fixid"])

    # The idea here is that we create arrays and dictionaries for each type of
    # mapping.  These contain closure functions that know how to put the data in
    # the right place.  The functions are determined ahead of time for
    # performance reasons which is why we are using closures.

    # This is a closure that holds the information we need to transfer data
    # from the CAN-FIX port to the FIXGW Database
    def getInputFunction(self, dbKey):
        try:
            dbItem = database.get_raw_item(dbKey)
        except KeyError:
            return None

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
                    # Check to see if we have a replacement string in the dictionary
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
                bus.send(p.msg)
                self.sendcount += 1

        return outputCallback

    # This is a closure that holds the information we need to transfer data
    # from the CAN-FIX port to the FIXGW Database
    def getEncoderFunction(self, dbKeys, add):
        # the dbKeys parameter should be three fix ids separated by commas
        # the first two are the encoder ids for each of the encoders that
        # are contained in the fix message and the third is the button.
        buttons = list()
        encoders = list()
        try:
            ids = dbKeys.split(",")
            skip = 1
            # allow 1 or more encoders
            encoders.append( database.get_raw_item(ids[0].strip()) )
            if len(ids) > 1:
                encoders.append( database.get_raw_item(ids[1].strip()) )
                skip += 1
            # Allow 0 to 8 buttons too
            if len(ids) > 2 and len(ids) < 11:
                for bc, btn in enumerate(ids[2:]):
                    buttons.append( database.get_raw_item(ids[bc + skip].strip()) )

        except KeyError:
            return None

        def InputFunc(cfpar):
            for ec, e in enumerate(encoders):
                if add:
                    encoders[ec].value =  encoders[ec].value[0] + cfpar.value[ec]
                else:
                    encoders[ec].value = cfpar.value[ec]
            for bc, b in enumerate(buttons):
                b.value = cfpar.value[2][bc]

        return InputFunc


    def getSwitchFunction(self, dbKeys):
        try:
            switches = []
            ids = dbKeys.split(",")
            for each in ids:
                switches.append(database.get_raw_item(each.strip()))
        except KeyError:
            return None

        def InputFunc(cfpar):
            x = cfpar.value
            bit = 0
            byte = 0
            for each in switches:
                each.value = x[byte][bit]
                bit += 1
                if bit >=8:
                    bit = 0
                    byte += 1

        return InputFunc

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
