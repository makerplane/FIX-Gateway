#  Copyright (c) 2018 Phil Birkelbach
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

import unittest
#import string
import io
import fixgw.database as database


# This is a poorly formatted example of a database configuration file.
# it should test leading/trailing spaces blank lines etc.
minimal_config = """
  # indented comment ^extra space last line too
a = 8:Generic Analog

   ---

#Key:Description:Type:Min:Max:Units:Initial:TOL:Auxiliary Data
ANLGa:Generic Analog %a:float:0:1:%/100:0.0:2000:
"""
minimal_list = []
for x in range(8):
    minimal_list.append("ANLG{}".format(x+1))

variable_config = """
  # indented comment ^extra space last line too
e=4:Engines
c=6:Cylinders per engine
t=20:Fuel Tanks
 ---
#Key:Description:Type:Min:Max:Units:Initial:TOL:Auxiliary Data
EGTec:Exhaust Gas Temp Engine %e, Cylinder %c:float:0:1000:degC:0.0:2000:
FUELQt:Fuel Quantity Tank %t:float:0:200:gal:0.0:2000:Min,Max,lowWarn,lowAlarm
"""
variable_list = []
for e in range(4):
    for c in range(6):
        variable_list.append("EGT{}{}".format(e+1,c+1))
for t in range(20):
    variable_list.append("FUELQ{}".format(t+1))
variable_list.sort()


class TestDatabase(unittest.TestCase):
    def setUp(self):
        pass

    def test_Minimal_Database_Build(self):
        sf = io.StringIO(minimal_config)
        database.init(sf)
        l = database.listkeys()
        l.sort()
        self.assertEqual(l, minimal_list)

    def test_Variable_Expansion(self):
        sf = io.StringIO(variable_config)
        database.init(sf)
        l = database.listkeys()
        l.sort()
        self.assertEqual(l, variable_list)
        for e in range(4):
            for c in range(6):
                key = "EGT{}{}".format(e+1,c+1)
                item = database.get_raw_item(key)
                s = "Exhaust Gas Temp Engine {}, Cylinder {}".format(e+1,c+1)
                self.assertEqual(item.description, s)


if __name__ == '__main__':
    unittest.main()
