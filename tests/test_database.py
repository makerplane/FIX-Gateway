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
from unittest.mock import MagicMock, patch

import pytest


# This is a poorly formatted example of a database configuration file.
# it should test leading/trailing spaces blank lines etc.
minimal_config = """
variables:
  a: 8 #Generic Analogs

entries:
- key: ANLGa
  description: Generic Analog %a
  type: float
  min: 0.0
  max: 1.0
  units: '%/100'
  initial: 0.0
  tol: 2000
- key: ZZLOADER
  description: MUST always be the last key listed here. It is read by client applications to ensure all db items have been init before proceeding to prevent race conditions.
  type: str
  initial: "Loaded"
"""

minimal_list = []
for x in range(8):
    minimal_list.append("ANLG{}".format(x + 1))
minimal_list.append('ZZLOADER')

variable_config = """
variables:
  e: 4  # Engines
  c: 6  # Cylinders
  t: 20 # Fuel Tanks
entries:
- key: EGTec
  description: Exhaust Gas Temp Engine %e, Cylinder %c
  type: float
  min: 0.0
  max: 1000.0
  units: degC
  initial: 0.0
  tol: 2000
  aux: [Min,Max]

- key: FUELQt
  description: Fuel Quantity Tank %t
  type: float
  min: 0.0
  max: 200.0
  units: gal
  initial: 0.0
  tol: 2000
  aux: [Min,Max,lowWarn,lowAlarm]
- key: ZZLOADER
  description: MUST always be the last key listed here. It is read by client applications to ensure all db items have been init before proceeding to prevent race conditions.
  type: str
  initial: "Loaded"
"""

variable_list = []
for e in range(4):
    for c in range(6):
        variable_list.append("EGT{}{}".format(e + 1, c + 1))
for t in range(20):
    variable_list.append("FUELQ{}".format(t + 1))
variable_list.sort()
variable_list.append('ZZLOADER')

general_config = """
variables:
  e: 1  # Engines
  c: 6  # Cylinders
  a: 8  # Generic Analogs
  b: 16 # Generic Buttons
  r: 1  # Encoders
  t: 2  # Fuel Tanks

entries:
- key: ANLGa
  description: Generic Analog %a
  type: float
  min: 0.0
  max: 1.0
  units: '%/100'
  initial: 0.0
  tol: 2000

- key: BTNb
  description: Generic Button %b
  type: bool
  tol: 0

- key: ENCr
  description: Generic Encoder %r
  type: int
  min: -32768
  max: 32767
  units: Pulses
  initial: 0
  tol: 0

- key: IAS
  description: Indicated Airspeed
  type: float
  min: 0.0
  max: 1000.0
  units: knots
  initial: 0.0
  tol: 2000
  aux: [Min,Max,V1,V2,Vne,Vfe,Vmc,Va,Vno,Vs,Vs0,Vx,Vy]

- key: IASW
  description: Indicated Airspeed Warning
  type: int
  min: 0
  max: 5
  units: warninglevel
  initial: 0
  tol: 2000

- key: TAS
  description: True Airspeed
  type: float
  min: 0.0
  max: 2000.0
  units: knots
  initial: 0.0
  tol: 2000

- key: CAS
  description: True Airspeed
  type: float
  min: 0.0
  max: 2000.0
  units: knots
  initial: 0.0
  tol: 2000

- key: GS
  description: Ground Speed
  type: float
  min: 0.0
  max: 2000.0
  units: knots
  initial: 0.0
  tol: 2000

- key: ALT
  description: Indicated Altitude
  type: float
  min: -1000.0
  max: 60000.0
  units: ft
  initial: 0.0
  tol: 2000

- key: TALT
  description: True Altitude
  type: float
  min: -1000.0
  max: 60000.0
  units: ft
  initial: 0.0
  tol: 2000

- key: DALT
  description: Density Altitude
  type: float
  min: -1000.0
  max: 60000.0
  units: ft
  initial: 0.0
  tol: 2000

- key: BARO
  description: Altimeter Setting
  type: float
  min: 0.0
  max: 35.0
  units: inHg
  initial: 29.92
  tol: 2000

- key: AIRPRESS
  description: Air Pressure
  type: float
  min: 0.0
  max: 200000.0
  units: Pa
  initial: 101325.0
  tol: 2000

- key: VS
  description: Vertical Speed
  type: float
  min: -30000.0
  max: 30000.0
  units: ft/min
  initial: 0.0
  tol: 2000
  aux: [Min,Max]

- key: HEAD
  description: Current Aircraft Magnetic Heading
  type: float
  min: 0.0
  max: 359.9
  units: deg
  initial: 0.0
  tol: 2000

- key: TRACK
  description: Current Aircraft Bearing
  type: float
  min: 0.0
  max: 359.9
  units: deg
  initial: 0.0
  tol: 2000

- key: TRACKM
  description: Current Aircraft Magnetic Bearing
  type: float
  min: 0.0
  max: 359.9
  units: deg
  initial: 0.0
  tol: 2000

- key: COURSE
  description: Selected Course
  type: float
  min: 0.0
  max: 359.9
  units: deg
  initial: 0.0
  tol: 2000

- key: CDI
  description: Course Deviation Indicator
  type: float
  min: -1.0
  max: 1.0
  initial: 0.0
  tol: 2000

- key: GSI
  description: Glideslope Indicator
  type: float
  min: -1.0
  max: 1.0
  initial: 0.0
  tol: 2000

- key: XTRACK
  description: Cross Track Error
  type: float
  min: 0.0
  max: 100.0
  units: nM
  initial: 0.0
  tol: 2000

- key: OAT
  description: Outside Air Temperature
  type: float
  min: -100.0
  max: 100.0
  units: degC
  initial: 0.0
  tol: 2000
  aux: [Min,Max,lowWarn]

- key: CAT
  description: Cabin Air Temperature
  type: float
  min: -100.0
  max: 100.0
  units: degC
  initial: 0.0
  tol: 2000
  aux: [Min,Max,lowWarn,highWarn,lowAlarm,highAlarm]

- key: OATW
  description: Outside Air Temperature Warning
  type: int
  min: 0
  max: 5
  units: warninglevel
  initial: 0
  tol: 2000

- key: ROLL
  description: Roll Angle
  type: float
  min: -180.0
  max: 180.0
  units: deg
  initial: 0.0
  tol: 200

- key: PITCH
  description: Pitch Angle
  type: float
  min: -90.0
  max: 90.0
  units: deg
  initial: 0.0
  tol: 200

- key: ORISYSW
  description: Orientation System Warning
  type: int
  min: 0
  max: 5
  units: warninglevel
  initial: 0
  tol: 2000

- key: GYROW
  description: Gyroscope sensor Warning
  type: int
  min: 0
  max: 5
  units: warninglevel
  initial: 0
  tol: 2000

- key: ACCELW
  description: Acceleration sensor Warning
  type: int
  min: 0
  max: 5
  units: warninglevel
  initial: 0
  tol: 2000

- key: MAGW
  description: Magnetic sensor Warning
  type: int
  min: 0
  max: 5
  units: warninglevel
  initial: 0
  tol: 2000

- key: PITCHSET
  description: Pitch angle setting
  type: float
  min: -180.0
  max: 180.0
  units: deg
  initial: 0.0
  tol: 200

- key: YAW
  description: Yaw Angle
  type: float
  min: -180.0
  max: 180.0
  units: deg
  initial: 0.0
  tol: 200

- key: AOA
  description: Angle of attack
  type: float
  min: -180.0
  max: 180.0
  units: deg
  initial: 0.0
  tol: 200
  aux:
  - Min
  - Max
  - 0g
  - Warn
  - Stall

- key: CTLPTCH
  description: Pitch Control
  type: float
  min: -1.0
  max: 1.0
  units: '%/100'
  initial: 0.0
  tol: 200

- key: CTLROLL
  description: Roll Control
  type: float
  min: -1.0
  max: 1.0
  units: '%/100'
  initial: 0.0
  tol: 200

- key: CTLYAW
  description: Yaw Control (Rudder)
  type: float
  min: -1.0
  max: 1.0
  units: '%/100'
  initial: 0.0
  tol: 200

- key: CTLCOLL
  description: Collective Control
  type: float
  min: -1.0
  max: 1.0
  units: '%/100'
  initial: 0.0
  tol: 200

- key: CTLATP
  description: AntiTorque Pedal Ctrl
  type: float
  min: -1.0
  max: 1.0
  units: '%/100'
  initial: 0.0
  tol: 200

- key: CTLFLAP
  description: Flap Control
  type: float
  min: -1.0
  max: 1.0
  units: '%/100'
  initial: 0.0
  tol: 200

- key: CTLLBRK
  description: Left Brake Control
  type: float
  min: 0.0
  max: 1.0
  units: '%/100'
  initial: 0.0
  tol: 200

- key: CTLRBRK
  description: Right Brake Control
  type: float
  min: 0.0
  max: 1.0
  units: '%/100'
  initial: 0.0
  tol: 1000

- key: ANORM
  description: Normal Acceleration
  type: float
  min: -30.0
  max: 30.0
  units: g
  initial: 0.0
  tol: 200

- key: ALAT
  description: Lateral Acceleration
  type: float
  min: -30.0
  max: 30.0
  units: g
  initial: 0.0
  tol: 200

- key: ALONG
  description: Longitudinal Acceleration
  type: float
  min: -30.0
  max: 30.0
  units: g
  initial: 0.0
  tol: 200

- key: THRe
  description: Throttle Control Engine %e
  type: float
  min: 0.0
  max: 1.0
  units: '%/100'
  initial: 0.0
  tol: 1000

- key: MIXe
  description: Mixture Control Engine %e
  type: float
  min: 0.0
  max: 1.0
  units: '%/100'
  initial: 0.0
  tol: 1000

- key: OILPe
  description: Oil Pressure Engine %e
  type: float
  min: 0.0
  max: 200.0
  units: psi
  initial: 0.0
  tol: 2000
  aux: [Min,Max,lowWarn,highWarn,lowAlarm,highAlarm]

- key: OILTe
  description: Oil Temperature Engine %e
  type: float
  min: 0.0
  max: 150.0
  units: degC
  initial: 0.0
  tol: 2000
  aux: [Min,Max,lowWarn,highWarn,lowAlarm,highAlarm]

- key: H2OTe
  description: Coolant Temperature Engine %e
  type: float
  min: 0.0
  max: 200.0
  units: degC
  initial: 0.0
  tol: 2000
  aux: [Min,Max,lowWarn,highWarn,lowAlarm,highAlarm]

- key: FUELPe
  description: Fuel Pressure Engine %e
  type: float
  min: 0.0
  max: 200.0
  units: psi
  initial: 0.0
  tol: 2000
  aux: [Min,Max,lowWarn,highWarn,lowAlarm,highAlarm]

- key: FUELFe
  description: Fuel Flow Engine %e
  type: float
  min: 0.0
  max: 100.0
  units: gal/hr
  initial: 0.0
  tol: 2000
  aux: [Min,Max]

- key: MAPe
  description: Manifold Pressure Engine %e
  type: float
  min: 0.0
  max: 60.0
  units: inHg
  initial: 0.0
  tol: 2000
  aux: [Min,Max]

- key: VOLT
  description: System Voltage
  type: float
  min: 0.0
  max: 18.0
  units: volt
  initial: 0.0
  tol: 2000
  aux: [Min,Max,lowWarn,highWarn,lowAlarm,highAlarm]

- key: CURRNT
  description: Bus Current
  type: float
  min: 0.0
  max: 60.0
  units: amps
  initial: 0.0
  tol: 2000
  aux: [Min,Max,lowWarn,highWarn,lowAlarm,highAlarm]

- key: EGTec
  description: Exhaust Gas Temp Engine %e, Cylinder %c
  type: float
  min: 0.0
  max: 1000.0
  units: degC
  initial: 0.0
  tol: 2000
  aux: [Min,Max]

- key: EGTAVGe
  description: Average Exhaust Gas Temp Engine %e
  type: float
  min: 0.0
  max: 1000.0
  units: degC
  initial: 0.0
  tol: 0
  aux: [Min,Max]

- key: EGTSPANe
  description: Exhaust Gas Temp Span Engine %e
  type: float
  min: 0.0
  max: 1000.0
  units: degC
  initial: 0.0
  tol: 0
  aux: [Min,Max]

- key: CHTec
  description: Cylinder Head Temp Engine %e, Cylinder %c
  type: float
  min: 0.0
  max: 1000.0
  units: degC
  initial: 0.0
  tol: 2000
  aux: [Min,Max,lowWarn,highWarn,lowAlarm,highAlarm]

- key: CHTMAXe
  description: Maximum Cylinder Head Temp Engine %e
  type: float
  min: 0.0
  max: 1000.0
  units: degC
  initial: 0.0
  aux: [Min,Max,lowWarn,highWarn,lowAlarm,highAlarm]

- key: FUELQt
  description: Fuel Quantity Tank %t
  type: float
  min: 0.0
  max: 200.0
  units: gal
  initial: 0.0
  tol: 2000
  aux: [Min,Max,lowWarn,lowAlarm]

- key: FUELQT
  description: Total Fuel Quantity
  type: float
  min: 0.0
  max: 200.0
  units: gal
  initial: 0.0
  tol: 2000
  aux: [Min,Max,lowWarn,lowAlarm]

- key: TACHe
  description: Engine RPM Engine %e
  type: int
  min: 0
  max: 10000
  units: RPM
  initial: 0
  tol: 2000
  aux: [Min,Max,lowWarn,highWarn,lowAlarm,highAlarm]

- key: PROPe
  description: Propeller RPM Engine %e
  type: int
  min: 0
  max: 10000
  units: RPM
  initial: 0
  tol: 2000
  aux: [Min,Max,lowWarn,highWarn,lowAlarm,highAlarm]

- key: LAT
  description: Latitude
  type: float
  min: -90.0
  max: 90.0
  units: deg
  initial: 0.0
  tol: 2000

- key: LONG
  description: Longitude
  type: float
  min: -180.0
  max: 180.0
  units: deg
  initial: 0.0
  tol: 2000

- key: TIMEZ
  description: Zulu Time String
  type: str
  tol: 2000

- key: TIMEZH
  description: Zulu Time Hour
  type: int
  min: 0
  max: 23
  initial: 0
  tol: 2000

- key: TIMEZM
  description: Zulu Time Minute
  type: int
  min: 0
  max: 59
  initial: 0
  tol: 2000

- key: TIMEZS
  description: Zulu Time Second
  type: int
  min: 0
  max: 59
  initial: 0
  tol: 2000

- key: TIMEL
  description: Local Time String
  type: str
  tol: 0

- key: TZONE
  description: Time Zone
  type: float
  min: -12.0
  max: 12.0
  initial: 0.0

- key: FTIME
  description: Flight Time
  type: float
  min: 0.0
  max: 1000.0
  initial: 0.0

- key: DIM
  description: Panel Dimmer Level
  type: int
  min: 0
  max: 100
  initial: 100

# Using this to test strings
- key: DUMMY
  description:
  type: str

- key: ZZLOADER
  description: MUST always be the last key listed here. It is read by client applications to ensure all db items have been init before proceeding to prevent race conditions.
  type: str
  initial: "Loaded"

"""


class TestDatabase(unittest.TestCase):
    def setUp(self):
        pass

    def test_Minimal_Database_Build(self):
        """Test minimal database build"""
        sf = io.StringIO(minimal_config)
        database.init(sf)
        keylist = database.listkeys()
        keylist.sort()
        self.assertEqual(keylist, minimal_list)

    def test_Variable_Expansion(self):
        """Test database variable expansion"""
        sf = io.StringIO(variable_config)
        database.init(sf)
        keylist = database.listkeys()
        keylist.sort()
        self.assertEqual(keylist, variable_list)
        for e in range(4):
            for c in range(6):
                key = "EGT{}{}".format(e + 1, c + 1)
                item = database.get_raw_item(key)
                s = "Exhaust Gas Temp Engine {}, Cylinder {}".format(e + 1, c + 1)
                self.assertEqual(item.description, s)

    def test_aux_data_creation(self):
        """Test database auxillary data creation"""
        sf = io.StringIO(general_config)
        database.init(sf)
        tests = ["Min", "Max", "0g", "Warn", "Stall"]
        tests.sort()
        i = database.get_raw_item("AOA")
        keylist = i.get_aux_list()
        keylist.sort()
        self.assertEqual(keylist, tests)

    def test_aux_data_read_write(self):
        """Test database auxillary data reading and writing"""
        sf = io.StringIO(general_config)
        database.init(sf)
        tests = [
            ("Min", -160.0),
            ("Max", -130.0),
            ("0g", 10.0),
            ("Warn", 23.4),
            ("Stall", 45.6),
        ]
        for test in tests:
            x = database.write("AOA." + test[0], test[1])
            x = database.read("AOA." + test[0])
            self.assertEqual(x, test[1])

    def test_database_bounds(self):
        """Test database bounds checking"""
        sf = io.StringIO(general_config)
        database.init(sf)
        tests = [
            (0.0, 0.0),
            (-180.0, -180.0),
            (-180.1, -180.0),
            (0.0, 0, 0),
            (180.0, 180.0),
            (180.1, 180.0),
        ]

        for test in tests:
            database.write("ROLL", test[0])
            x = database.read("ROLL")
            self.assertEqual(x[0], test[1])

    def test_database_aux_data_bounds(self):
        """Test database aux data bounds checking"""
        sf = io.StringIO(general_config)
        database.init(sf)
        tests = [
            (0.0, 0.0),
            (-180.0, -180.0),
            (-180.1, -180.0),
            (0.0, 0, 0),
            (180.0, 180.0),
            (180.1, 180.0),
        ]

        for test in tests:
            database.write("AOA.Warn", test[0])
            x = database.read("AOA.Warn")
            self.assertEqual(x, test[1])

    def test_database_callbacks(self):
        """Test database callback routines"""
        sf = io.StringIO(general_config)
        database.init(sf)
        rval = None

        def test_cb(key, val, udata):  # Use a closure for our callback
            nonlocal rval
            rval = (key, val)

        database.callback_add("test", "PITCH", test_cb, None)
        database.write("PITCH", -11.4)
        self.assertEqual(rval, ("PITCH", (-11.4, False, False, False, False, False)))
        database.write("PITCH", 10.2)
        self.assertEqual(rval, ("PITCH", (10.2, False, False, False, False, False)))
        i = database.get_raw_item("PITCH")
        i.fail = True
        self.assertEqual(rval, ("PITCH", (10.2, False, False, False, True, False)))
        i.annunciate = True
        self.assertEqual(rval, ("PITCH", (10.2, True, False, False, True, False)))
        i.bad = True
        self.assertEqual(rval, ("PITCH", (10.2, True, False, True, True, False)))
        time.sleep(0.250)
        database.update()  # force the update
        self.assertEqual(rval, ("PITCH", (10.2, True, True, True, True, False)))

    def test_timeout_lifetime(self):
        """Test item timeout lifetime"""
        sf = io.StringIO(general_config)
        database.init(sf)
        database.write("PITCH", -11.4)
        x = database.read("PITCH")
        self.assertEqual(x, (-11.4, False, False, False, False, False))
        time.sleep(0.15)
        x = database.read("PITCH")
        self.assertEqual(x, (-11.4, False, False, False, False, False))
        time.sleep(0.05)
        x = database.read("PITCH")
        self.assertEqual(x, (-11.4, False, True, False, False, False))
        database.write("PITCH", -11.4)
        x = database.read("PITCH")
        self.assertEqual(x, (-11.4, False, False, False, False, False))

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
        self.assertEqual(i.description, "")
        self.assertEqual(i.units, "")

    def test_quality_bits(self):
        """Test quality bits"""
        sf = io.StringIO(general_config)
        database.init(sf)
        i = database.get_raw_item("OILP1")
        database.write("OILP1", 15.4)
        x = database.read("OILP1")
        self.assertEqual(x, (15.4, False, False, False, False, False))
        i.annunciate = True
        x = database.read("OILP1")
        self.assertEqual(x, (15.4, True, False, False, False, False))
        i.annunciate = False
        x = database.read("OILP1")
        self.assertEqual(x, (15.4, False, False, False, False, False))
        i.fail = True
        x = database.read("OILP1")
        self.assertEqual(x, (15.4, False, False, False, True, False))
        i.fail = False
        x = database.read("OILP1")
        self.assertEqual(x, (15.4, False, False, False, False, False))
        i.bad = True
        x = database.read("OILP1")
        self.assertEqual(x, (15.4, False, False, True, False, False))
        i.bad = False
        x = database.read("OILP1")
        self.assertEqual(x, (15.4, False, False, False, False, False))

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
        database.write("PITCH", "23.4")
        x = database.read("PITCH")
        self.assertEqual(x[0], 23.4)

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

    def test_similar_aux_items(self):
        """it would be easy for a single aux array to be pointed to
        by different database items."""
        sf = io.StringIO(variable_config)
        database.init(sf)
        database.write("EGT11.Max", 700)
        database.write("EGT12.Max", 800)
        x = database.read("EGT11.Max")
        y = database.read("EGT12.Max")
        self.assertNotEqual(y, x)


if __name__ == "__main__":
    unittest.main()


# TODO: Test that a blank in TOL will result in no timeout.
# TODO: Test that we can set the "OLD" flag if the timeout is zero


def test_db_item_rejects_unknown_datatype():
    database.log = MagicMock()

    with pytest.raises(KeyError):
        database.db_item("BAD", "nonsense")

    database.log.error.assert_called_once_with("Unknown datatype - nonsense")


def test_set_aux_value_handles_none_and_invalid_values():
    item = database.db_item("TEST", "float")
    item.description = "Test Item"
    item.init_aux(["Min"])
    item.min = 0
    item.max = 10
    callback = MagicMock()
    item.callbacks.append(("cb", callback, "udata"))
    database.log = MagicMock()

    item.set_aux_value("Min", "None")
    assert item.get_aux_value("Min") is None
    callback.assert_called_once_with("TEST.Min", None, "udata")

    with pytest.raises(ValueError):
        item.set_aux_value("Min", "bad-value")

    database.log.error.assert_any_call("Bad Value for aux Min bad-value")


def test_send_callbacks_logs_callback_exceptions():
    item = database.db_item("TEST", "float")
    item.description = "Test Item"
    database.log = MagicMock()

    def bad_callback(*_args):
        raise RuntimeError("boom")

    item.callbacks.append(("bad", bad_callback, "udata"))

    item.send_callbacks()

    database.log.error.assert_called_once()
    assert "exception: boom" in database.log.error.call_args[0][0]


def test_value_tuple_requires_quality_flags():
    item = database.db_item("TEST", "float")

    with pytest.raises(ValueError, match="Tuple too small for TEST"):
        item.value = (1.0, True, False)


def test_value_without_bounds_hits_min_max_fallback_paths():
    item = database.db_item("TEST", "float")
    item.value = 12.5
    assert item.value == (12.5, False, False, False, False, False)


def test_min_max_and_tol_invalid_values_are_logged():
    item = database.db_item("TEST", "float")
    item.description = "Test Item"
    database.log = MagicMock()

    item.min = "bad-min"
    item.max = "bad-max"
    item.tol = ""
    assert item.tol == 0
    item.tol = "bad-tol"

    database.log.error.assert_any_call("Bad minimum value 'bad-min' given for Test Item")
    database.log.error.assert_any_call("Bad maximum value 'bad-max' given for Test Item")
    database.log.error.assert_any_call("Time to live should be an integer for Test Item")


def test_old_bad_and_secfail_properties_and_str():
    item = database.db_item("TEST", "float")
    item.value = 1.5

    assert item.old is False
    item.old = True
    assert item.old is True
    assert item.bad is False
    item.bad = True
    assert item.bad is True
    item.secfail = True
    assert item.secfail is False
    assert item.fail is False
    assert item.min is None
    assert item.max is None
    assert str(item) == "TEST = (1.5, False, False, True, False, True)"


def test_add_item_returns_none_for_invalid_entry_type():
    database.log = MagicMock()

    item = database.add_item({"key": "BAD", "type": "not-a-type"})

    assert item is None
    database.log.error.assert_any_call("Failure to add entry - BAD")


def test_init_without_variables_section_and_missing_variable_logs_error():
    cfg_text = """
entries:
- key: EGTx
  description: Exhaust Gas Temp %x
  type: float
  initial: 0
- key: ZZLOADER
  description: Loader
  type: str
  initial: Loaded
"""
    fake_thread = MagicMock()
    fake_thread_instance = MagicMock()
    fake_thread.return_value = fake_thread_instance

    with patch("fixgw.database.cfg.from_yaml", return_value={"entries": [{"key": "EGTx", "description": "Exhaust Gas Temp %x", "type": "float", "initial": 0}, {"key": "ZZLOADER", "description": "Loader", "type": "str", "initial": "Loaded"}]}), patch(
        "fixgw.database.logging.getLogger", return_value=MagicMock()
    ) as get_logger, patch("fixgw.database.UpdateThread", fake_thread):
        database.init(io.StringIO(cfg_text))

    log = get_logger.return_value
    log.error.assert_called_once_with("Variable x not set for EGTx")
    fake_thread.assert_called_once()
    assert fake_thread.call_args[0][0:2] == (database.update, 1.0)
    assert fake_thread_instance.daemon is True
    fake_thread_instance.start.assert_called_once()


def test_callback_del_logs_when_specific_callback_missing(database):
    callback = MagicMock()

    database.callback_del("missing", "PITCH", callback, None)


def test_missing_aux_value_operations_log_and_raise():
    item = database.db_item("TEST", "float")
    item.description = "Test Item"
    item.init_aux(["Min"])
    database.log = MagicMock()

    with pytest.raises(KeyError, match="Aux name Max not found for item TEST"):
        item.set_aux_value("Max", 5)

    with pytest.raises(KeyError):
        item.get_aux_value("Max")

    database.log.error.assert_any_call("No aux Max for Test Item")
    database.log.error.assert_any_call("TEST contains aux keys ['Min']")


def test_value_tuple_with_secfail_and_invalid_value_logging():
    item = database.db_item("TEST", "float")
    item.description = "Test Item"
    item.value = (2.5, True, False, True, True)
    assert item.value == (2.5, True, False, False, True, True)
    item.value = (3.5, False, True, False)
    assert item.value == (3.5, False, False, True, False, True)

    with pytest.raises(ValueError):
        item.value = "bad-value"

    database.log.error.assert_called_with("Bad value 'bad-value' given for Test Item")


def test_flag_setters_only_callback_on_change():
    item = database.db_item("TEST", "float")
    cb = MagicMock()
    item.callbacks.append(("cb", cb, None))
    assert item.annunciate is False
    item.annunciate = False
    item.old = False
    item.bad = False
    item.fail = False
    item.secfail = False
    cb.assert_not_called()

    item.annunciate = True
    item.old = True
    item.bad = True
    item.fail = True
    item.secfail = True
    assert cb.call_count == 5


def test_callback_delete_wildcard_removes_registered_callbacks(database):
    callback = MagicMock()
    database.callback_add("cb", "PITCH", callback, None)
    database.callback_add("cb", "ROLL", callback, None)

    database.callback_del("cb", "*", callback, None)

    assert database.get_raw_item("PITCH").callbacks == []
    assert database.get_raw_item("ROLL").callbacks == []


def test_init_adds_entries_without_variables_section_and_starts_thread():
    cfg_data = {
        "entries": [
            {
                "key": "ITEM",
                "description": "Item",
                "type": "float",
                "min": 0.0,
                "max": 10.0,
                "tol": 1000,
                "initial": 1.0,
            },
            {"key": "ZZLOADER", "description": "Loader", "type": "str", "initial": "Loaded"},
        ]
    }
    fake_thread = MagicMock()
    fake_thread_instance = MagicMock()
    fake_thread.return_value = fake_thread_instance

    with patch("fixgw.database.cfg.from_yaml", return_value=cfg_data), patch(
        "fixgw.database.logging.getLogger", return_value=MagicMock()
    ), patch("fixgw.database.UpdateThread", fake_thread):
        database.init(io.StringIO("entries: []"))

    assert "ITEM" in database.listkeys()
    fake_thread.assert_called_once()
    assert fake_thread.call_args[0][0:2] == (database.update, 1.0)


def test_init_stops_existing_update_thread_before_reinit():
    old_stop = MagicMock()
    old_thread = MagicMock()
    old_thread.is_alive.return_value = True
    old_thread.delay = 1.0
    database._update_thread = old_thread
    database._update_thread_stop = old_stop

    fake_thread = MagicMock()
    fake_thread_instance = MagicMock()
    fake_thread.return_value = fake_thread_instance
    cfg_data = {
        "entries": [
            {
                "key": "ITEM",
                "description": "Item",
                "type": "float",
                "min": 0.0,
                "max": 10.0,
                "tol": 1000,
                "initial": 1.0,
            },
            {"key": "ZZLOADER", "description": "Loader", "type": "str", "initial": "Loaded"},
        ]
    }

    with patch("fixgw.database.cfg.from_yaml", return_value=cfg_data), patch(
        "fixgw.database.logging.getLogger", return_value=MagicMock()
    ), patch("fixgw.database.UpdateThread", fake_thread):
        database.init(io.StringIO("entries: []"))

    old_stop.set.assert_called_once()
    old_thread.join.assert_called_once_with(timeout=2.0)


def test_getters_and_setters_for_quality_flags(database):
    item = database.get_raw_item("PITCH")
    item.fail = True
    assert item.fail is True
    item.fail = False
    assert item.fail is False
    item.bad = True
    assert item.bad is True
    item.old = True
    assert item.old is True
