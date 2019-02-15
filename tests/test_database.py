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
import io
import time
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

general_config = """
e=1:Engines
c=6:Cylinders per engine
t=2:Fuel Tanks
b=1:Generic Buttons
r=1:Generic Encoders
a=8:Generic Analog
---
#Key:Description:Type:Min:Max:Units:Initial:TOL:Auxiliary Data
ANLGa:Generic Analog %a:float:0:1:%/100:0.0:2000:
BTNb:Generic Button %b:bool:0:1::False:0:
ENCr:Generic Encoder %r:int:-32768:32767:Pulses:0:0:
IAS:Indicated Airspeed:float:0:1000:knots:0.0:2000:Min,Max,V1,V2,Vne,Vfe,Vmc,Va,Vno,Vs,Vs0,Vx,Vy
TAS:True Airspeed:float:0:2000:knots:0.0:2000:
ALT:Indicated Altitude:float:-1000:60000:ft:0.0:2000:
BARO:Altimeter Setting:float:0:35:inHg:29.92:2000:
HEAD:Current Aircraft Magnetic Heading:float:0:360:deg:0.0:2000:
OAT:Outside Air Temperature:float:-100:100:degC:0.0:2000:Min,Max,lowWarn,highWarn,lowAlarm,highAlarm
ROLL:Roll Angle:float:-180:180:deg:0.0:200:
PITCH:Pitch Angle:float:-180:180:deg:0.0:200:
PITCHSET:Pitch angle setting:float:-180:180:deg:0.0:200:
YAW:Yaw Angle:float:-180:180:deg:0.0:200:
AOA:Angle of attack:float:-180:180:deg:0.0:200:Min,Max,0g,Warn,Stall
CTLPTCH:Pitch Control:float:-1:1:%/100:0.0:200:
CTLFLAP:Flap Control:float:-1:1:%/100:0.0:200:
ANORM:Normal Acceleration:float:-30:30:g:0.0:200:
ALAT:Lateral Acceleration:float:-30:30:g:0.0:200:
OILPe:Oil Pressure Engine %e:float:0:200:psi:0.0:2000:Min,Max,lowWarn,highWarn,lowAlarm,highAlarm
OILTe:Oil Temperature Engine %e:float:0:300:degC:0.0:2000:Min,Max,lowWarn,highWarn,lowAlarm,highAlarm
FUELPe:Fuel Pressure Engine %e:float:0:200:psi:0.0:2000:Min,Max,lowWarn,highWarn,lowAlarm,highAlarm
FUELFe:Fuel Flow Engine %e:float:0:100:gal/hr:0.0:2000:
MAPe:Manifold Pressure Engine %e:float:0:60:inHg:0.0:2000:
EGTec:Exhaust Gas Temp Engine %e, Cylinder %c:float:0:1000:degC:0.0:2000:
CHTec:Cylinder Head Temp Engine %e, Cylinder %c:float:0:1000:degC:0.0:2000:
FUELQt:Fuel Quantity Tank %t:float:0:200:gal:0.0:2000:Min,Max,lowWarn,lowAlarm
TACHe:Engine RPM:int:0:10000:RPM:0:2000:Min,Max,lowWarn,highWarn,lowAlarm,highAlarm
LAT:Latitude:float:-90:90:deg:0.0:2000:
LONG:Longitude:float:-180:180:deg:0:2000:
TIMEZ:Zulu Time String:str:::::2000:
TIMEZH:Zulu Time Hour:int:0:23::0:2000:
TIMEZM:Zulu Time Minute:int:0:59::0:2000:
TIMEZS:Zulu Time Second:int:0:59::0:2000:
TIMEL:Local Time String:str:::::0:
DUMMY::str:::::0:
"""

class TestDatabase(unittest.TestCase):
    def setUp(self):
        pass

    def test_Minimal_Database_Build(self):
        """Test minimal database build"""
        sf = io.StringIO(minimal_config)
        database.init(sf)
        l = database.listkeys()
        l.sort()
        self.assertEqual(l, minimal_list)


    def test_Variable_Expansion(self):
        """Test database variable expansion"""
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


    def test_aux_data_creation(self):
        """Test database auxillary data creation"""
        sf = io.StringIO(general_config)
        database.init(sf)
        tests = ["Min", "Max", "0g", "Warn", "Stall"]
        tests.sort()
        i = database.get_raw_item("AOA")
        l = i.get_aux_list()
        l.sort()
        self.assertEqual(l, tests)


    def test_aux_data_read_write(self):
        """Test database auxillary data reading and writing"""
        sf = io.StringIO(general_config)
        database.init(sf)
        tests = [("Min",  -160.0),
                 ("Max",  -130.0),
                 ("0g",    10.0),
                 ("Warn",  23.4),
                 ("Stall", 45.6)]
        for test in tests:
             x = database.write("AOA." + test[0], test[1])
             x = database.read("AOA." + test[0])
             self.assertEqual(x, test[1])


    def test_database_bounds(self):
        """Test database bounds checking"""
        sf = io.StringIO(general_config)
        database.init(sf)
        tests = [(0.0,     0.0),
                 (-180.0, -180.0),
                 (-180.1, -180.0),
                 (0.0,     0,0),
                 (180.0,   180.0),
                 (180.1,   180.0)]

        for test in tests:
            database.write("ROLL", test[0])
            x = database.read("ROLL")
            self.assertEqual(x[0], test[1])


    def test_database_aux_data_bounds(self):
        """Test database aux data bounds checking"""
        sf = io.StringIO(general_config)
        database.init(sf)
        tests = [(0.0,     0.0),
                 (-180.0, -180.0),
                 (-180.1, -180.0),
                 (0.0,     0,0),
                 (180.0,   180.0),
                 (180.1,   180.0)]

        for test in tests:
            database.write("AOA.Warn", test[0])
            x = database.read("AOA.Warn")
            self.assertEqual(x, test[1])


    def test_database_callbacks(self):
        """Test database callback routines"""
        sf = io.StringIO(general_config)
        database.init(sf)
        rval = None
        def test_cb(key, val, udata): # Use a closure for our callback
            nonlocal rval
            rval = (key, val)

        database.callback_add("test", "PITCH", test_cb, None)
        database.write("PITCH", -11.4)
        self.assertEqual(rval, ("PITCH", (-11.4, False, False, False, False)))
        database.write("PITCH", 10.2)
        self.assertEqual(rval, ("PITCH", (10.2, False, False, False, False)))
        i = database.get_raw_item("PITCH")
        i.fail = True
        self.assertEqual(rval, ("PITCH", (10.2, False, False, False, True)))
        i.annunciate = True
        self.assertEqual(rval, ("PITCH", (10.2, True, False, False, True)))
        i.bad = True
        self.assertEqual(rval, ("PITCH", (10.2, True, False, True, True)))
        time.sleep(0.250)
        database.update() # force the update
        self.assertEqual(rval, ("PITCH", (10.2, True, True, True, True)))


    def test_timeout_lifetime(self):
        """Test item timeout lifetime"""
        sf = io.StringIO(general_config)
        database.init(sf)
        database.write("PITCH", -11.4)
        x = database.read("PITCH")
        self.assertEqual(x, (-11.4, False, False, False, False))
        time.sleep(0.250)
        x = database.read("PITCH")
        self.assertEqual(x, (-11.4, False, True, False, False))
        database.write("PITCH", -11.4)
        x = database.read("PITCH")
        self.assertEqual(x, (-11.4, False, False, False, False))


    def test_description_units(self):
        """Test description and units"""
        sf = io.StringIO(general_config)
        database.init(sf)
        i = database.get_raw_item("ROLL")
        self.assertEqual(i.description, "Roll Angle")
        self.assertEqual(i.units, "deg")


    def test_missing_description_units(self):
        """Test missing description and units"""
        sf = io.StringIO(general_config)
        database.init(sf)
        i = database.get_raw_item("DUMMY")
        self.assertEqual(i.description, '')
        self.assertEqual(i.units, '')


    def test_quality_bits(self):
        """Test quality bits"""
        sf = io.StringIO(general_config)
        database.init(sf)
        i = database.get_raw_item("OILP1")
        database.write("OILP1", 15.4)
        x = database.read("OILP1")
        self.assertEqual(x, (15.4, False, False, False, False))
        i.annunciate = True
        x = database.read("OILP1")
        self.assertEqual(x, (15.4, True, False, False, False))
        i.annunciate = False
        x = database.read("OILP1")
        self.assertEqual(x, (15.4, False, False, False, False))
        i.fail = True
        x = database.read("OILP1")
        self.assertEqual(x, (15.4, False, False, False, True))
        i.fail = False
        x = database.read("OILP1")
        self.assertEqual(x, (15.4, False, False, False, False))
        i.bad = True
        x = database.read("OILP1")
        self.assertEqual(x, (15.4, False, False, True, False))
        i.bad = False
        x = database.read("OILP1")
        self.assertEqual(x, (15.4, False, False, False, False))


    def test_string_datatype(self):
        """test writing a string to an item"""
        sf = io.StringIO(general_config)
        database.init(sf)
        database.write("DUMMY", "test string")
        x = database.read("DUMMY")
        self.assertEqual(x[0], "test string")


    def test_wrong_datatype(self):
        """test using wrong datatype for item"""
        sf = io.StringIO(general_config)
        database.init(sf)
        database.write("DUMMY", 1234)
        x = database.read("DUMMY")
        self.assertEqual(x[0], "1234")
        database.write("PITCH", "123.4")
        x = database.read("PITCH")
        self.assertEqual(x[0], 123.4)


    def test_bool_write(self):
        """test using wrong datatype for item"""
        sf = io.StringIO(general_config)
        database.init(sf)
        # Test actual booleans
        database.write("BTN1", True)
        x = database.read("BTN1")
        self.assertEqual(x[0], True)
        database.write("BTN1", False)
        x = database.read("BTN1")
        self.assertEqual(x[0], False)
        # Test strings
        database.write("BTN1", "True")
        x = database.read("BTN1")
        self.assertEqual(x[0], True)
        database.write("BTN1", "False")
        x = database.read("BTN1")
        self.assertEqual(x[0], False)
        database.write("BTN1", "1")
        x = database.read("BTN1")
        self.assertEqual(x[0], True)
        database.write("BTN1", "0")
        x = database.read("BTN1")
        self.assertEqual(x[0], False)
        database.write("BTN1", "Yes")
        x = database.read("BTN1")
        self.assertEqual(x[0], True)
        database.write("BTN1", "No")
        x = database.read("BTN1")
        self.assertEqual(x[0], False)
        # Test integers
        database.write("BTN1", 1)
        x = database.read("BTN1")
        self.assertEqual(x[0], True)
        database.write("BTN1", 0)
        x = database.read("BTN1")
        self.assertEqual(x[0], False)


if __name__ == '__main__':
    unittest.main()


# TODO: Test that a blank in TOL will result in no timeout.
# TODO: Test that we can set the "OLD" flag if the timeout is zero
