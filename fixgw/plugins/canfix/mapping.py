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

meta_replacements_in = {}
meta_replacements_out = {}

# This is a list of function closures
input_mapping = [None] * 1280
output_mapping = {}


# The idea here is that we create arrays and dictionaries for each type of
# mapping.  These contain closure functions that know how to put the data in
# the right place.  The functions are determined ahead of time for
# performance reasons which is why we are using closures.

# This is a closure that holds the information we need to transfer data
# from the CAN-FIX port to the FIXGW Database
def getInputFunction(dbKey):
    dbItem = database.get_raw_item(dbKey)
    if dbItem == None: return None

    def InputFunc(cfpar):
        if cfpar.meta:
            try:
                # Check to see if we have a replacemtn string in the dictionary
                if cfpar.meta in meta_replacements_in:
                    m = meta_replacements_in[cfpar.meta]
                else: # Just use the one we were sent
                    m = cfpar.meta
                dbItem.set_aux_value(m, cfpar.value)
            except:
                self.log.warning("Problem setting Aux Value for {0}".format(dbItem.key))
        else:
            dbItem.value = (cfpar.value, cfpar.annunciate, cfpar.quality, cfpar.failure)

    return InputFunc


# This opens the map file and buids the input mapping lists.
def initialize(mapfile):
    global meta_replacements_in
    try:
        f = open(mapfile)
    except:
        log.error("Unable to Open Mapfile - {}".format(mapfile))
        raise
    maps = yaml.load(f)


    # each input mapping item := [CANID, Index, FIX DB ID, Priority]
    for each in maps['inputs']:
        p = canfix.parameters[each["canid"]]
        # Parameters start at 0x100 so we subtract that offset to index the array
        ix = each["canid"] - 0x100
        if input_mapping[ix] is None:
            input_mapping[ix] = [None] * 256
        input_mapping[ix][each["index"]] = getInputFunction(each["fixid"])

    # dictionaries used for converting meta data strings from db to canfix and back
    meta_replacements_in = maps['meta replacements']
    meta_replacements_out = {v:k for k,v in meta_replacements_in.items()}


def inputMap(par):
    ix = par.identifier - 0x100
    im = input_mapping[ix] # This should always exist
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
