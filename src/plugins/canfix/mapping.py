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


import database
from canfix import parameters
from canfix import Parameter

# This is a list of function closures
input_mapping = [None] * 1280
output_mapping = {}

# This is a closure that holds the information we need to transfer data
# from the CAN-FIX port to the FIXGW Database
def getInputFunction(dbKey, canfixID):
    parDef = parameters[canfixID]
    if parDef.index:  # If there is an index then there are more than one
        dbItem = []
        for n in range(255):
            item = database.get_raw_item(dbKey + str(n+1))
            if item == None: break # we've found them all
            dbItem.append(item)
        if dbItem == []: return None
    else:  # Just one item
        dbItem = database.get_raw_item(dbKey)
        if dbItem == None: return None

    def InputFunc(cfpar):
        if cfpar.meta:
            try:
                dbItem.set_aux_value(cfpar.meta, cfpar.value)
            except:
                self.log.warning("Problem setting Aux Value for {0}".format(dbItem.key))
        else:
            dbItem.value = (cfpar.value, cfpar.annunciate, cfpar.quality, cfpar.failure)

    def InputIndexFunc(cfpar):
        if cfpar.meta:
            try:
                # We set all the items that we have for these.  Nodes won't send
                # aux/meta values for every index.
                for item in dbItem:
                    item.set_aux_value(cfpar.meta, cfpar.value)
            except:
                self.log.warning("Problem setting Aux Value for {0}".format(dbItem.key))
        else:
            dbItem[cfpar.index].value = (cfpar.value, cfpar.annunciate, cfpar.quality, cfpar.failure)

    if parDef.index:
        return InputIndexFunc
    else:
        return InputFunc

# These are the standard numerical mappings
maps = [(0x180, "PITCH"), (0x181, "ROLL"),
        (0x183, "IAS"), (0x184, "ALT"),
        (0x185, "HEAD"), (0x186, "VS"),
        (0x200, "TACH1"), (0x201, "TACH2"),
        (0x202, "PROP1"), (0x203, "PROP2"),
        (0x21E, "MAP1"), (0x21F, "MAP2"),
        (0x220, "OILP1"), (0x221, "OILP2"),
        (0x500, "CHT1")]

for each in maps:
    input_mapping[each[0] - 0x100] = getInputFunction(each[1], each[0])


def inputMap(par):
    try:
        func = input_mapping[par.identifier - 0x100]
    except KeyError:
        func = None
    if func:
        func(par)
