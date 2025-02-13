#  Copyright (c) 2019 Phil Birkelbach
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
import yaml
import fixgw.database as database
from fixgw import cfg

db_config = """
variables:
  e: 1  # Engines
  c: 6  # Cylinders
  a: 8  # Generic Analogs
  b: 16 # Generic Buttons
  r: 1  # Encoders
  t: 2  # Fuel Tanks

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

- key: CHTMINe
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

- key: PITCH
  description: Pitch Angle
  type: float
  min: -90.0
  max: 90.0
  units: deg
  initial: 0.0
  tol: 200

- key: AOA
  description: Angle of attack
  type: float
  min: -90.0
  max: 90.0
  units: deg
  initial: 0.0
  tol: 200
  aux: [Min, Max, 0g, Warn, Stall]

- key: IAS
  description: Indicated Airspeed
  type: float
  min: 0.0
  max: 1000.0
  units: knots
  initial: 0.0
  tol: 2000
  aux: [Min,Max,V1,V2,Vne,Vfe,Vmc,Va,Vno,Vs,Vs0,Vx,Vy]

- key: ANORM
  description: Normal Acceleration
  type: float
  min: -30.0
  max: 30.0
  units: g
  initial: 0.0
  tol: 200

"""

config = """
functions:
  - function: average
    inputs: ["EGT11", "EGT12", "EGT13", "EGT14"]
    output: EGTAVG1
  - function: span
    inputs: ["EGT11", "EGT12", "EGT13", "EGT14"]
    output: EGTSPAN1
  - function: max
    inputs: ["CHT11", "CHT12", "CHT13", "CHT14"]
    output: CHTMAX1
  - function: min
    inputs: ["CHT11", "CHT12", "CHT13", "CHT14"]
    output: CHTMIN1
  - function: sum
    inputs: ["FUELQ1", "FUELQ2"]
    output: FUELQT
  - function: AOA
    inputs: ["PITCH", "IAS", "ANORM", "HEAD", "VS",
            2, 100, 100,
            100, 50,
            5, 5,
            3, 3
            ]
    output: AOA
    # AOA input constants:
    #   AOA_pitch_root: The pitch angle of the wing at the root (in degrees)
    #   AOA_smooth_min_len: Minimum number of AHRS samples in which the aircraft must be in straight and level flight in order to estimate the lift constant
    #   AOA_max_mean_vs: The maximum vertical speed (up or down) the aircraft can experience before considered 'not level flight'
    #   AOA_max_vs_dev: The maximum single sample deviation from the average to be considered 'level flight'
    #   AOA_max_vs_trend: The maximum difference between the starting samples and ending samples of vertical speed before it's considered 'not level flight'
    #   AOA_max_heading_dev: The maximum single sample deviation from the average heading to be considered 'straight flight'
    #   AOA_max_heading_trend: The maximum difference between the starting samples and ending samples of heading before it's considered 'not straight flight'
    #   AOA_max_pitch_dev: The maximum single sample deviation from the average to be considered 'level flight'
    #   AOA_max_pitch_trend: The maximum difference between the starting samples and ending samples of pitch before it's considered 'not level flight'
"""


# Basically what we do with this test is set up a skeleton of the application
# by loading and initializing the database module and loading the compute
# plugin.
class TestComputePlugin(unittest.TestCase):
    def setUp(self):
        sf = io.StringIO(db_config)
        database.init(sf)

        cc, cc_meta = cfg.from_yaml(config, metadata=True)
        import fixgw.plugins.compute

        self.pl = fixgw.plugins.compute.Plugin("compute", cc, cc_meta)
        self.pl.start()
        time.sleep(0.1)  # Give plugin a chance to get started

    def tearDown(self):
        self.pl.shutdown()

    def test_compute_average(self):
        database.write("EGT11", 300)
        database.write("EGT12", 320)
        database.write("EGT13", 340)
        database.write("EGT14", 360)
        x = database.read("EGTAVG1")
        self.assertEqual(x, (330, False, False, False, False, False))
        database.write("EGT13", (340, False, True, False, False))
        x = database.read("EGTAVG1")
        self.assertEqual(x, (330, False, False, True, False, False))
        database.write("EGT13", (340, False, False, True, False))
        x = database.read("EGTAVG1")
        self.assertEqual(x, (0, False, False, False, True, False))
        database.write("EGT13", (340, False, False, False, True))
        x = database.read("EGTAVG1")
        self.assertEqual(x, (330, False, False, False, False, True))

    def test_compute_span(self):
        database.write("EGT11", 300)
        database.write("EGT12", 320)
        database.write("EGT13", 340)
        database.write("EGT14", 360)
        x = database.read("EGTSPAN1")
        self.assertEqual(x, (60, False, False, False, False, False))
        database.write("EGT13", (340, False, True, False, False))
        x = database.read("EGTSPAN1")
        self.assertEqual(x, (60, False, False, True, False, False))
        database.write("EGT13", (340, False, False, True, False))
        x = database.read("EGTSPAN1")
        self.assertEqual(x, (0, False, False, False, True, False))
        database.write("EGT13", (340, False, False, False, True))
        x = database.read("EGTSPAN1")
        self.assertEqual(x, (60, False, False, False, False, True))

    def test_compute_max(self):
        database.write("CHT11", 300)
        database.write("CHT12", 320)
        database.write("CHT13", 340)
        database.write("CHT14", 360)
        x = database.read("CHTMAX1")
        self.assertEqual(x, (360, False, False, False, False, False))
        database.write("CHT11", 370)
        x = database.read("CHTMAX1")
        self.assertEqual(x, (370, False, False, False, False, False))
        database.write("CHT12", 380)
        x = database.read("CHTMAX1")
        self.assertEqual(x, (380, False, False, False, False, False))
        database.write("CHT13", 390)
        x = database.read("CHTMAX1")
        self.assertEqual(x, (390, False, False, False, False, False))

        database.write("CHT13", (340, False, True, False, False))
        x = database.read("CHTMAX1")
        self.assertEqual(x, (380, False, False, True, False, False))
        database.write("CHT13", (340, False, False, True, False))
        x = database.read("CHTMAX1")
        self.assertEqual(x, (0, False, False, False, True, False))
        database.write("CHT13", (340, False, False, False, True))
        x = database.read("CHTMAX1")
        self.assertEqual(x, (380, False, False, False, False, True))

    def test_compute_min(self):
        database.write("CHT11", 300)
        database.write("CHT12", 320)
        database.write("CHT13", 340)
        database.write("CHT14", 360)
        x = database.read("CHTMIN1")
        self.assertEqual(x, (300, False, False, False, False, False))
        database.write("CHT11", 295)
        x = database.read("CHTMIN1")
        self.assertEqual(x, (295, False, False, False, False, False))
        database.write("CHT12", 290)
        x = database.read("CHTMIN1")
        self.assertEqual(x, (290, False, False, False, False, False))
        database.write("CHT13", 280)
        x = database.read("CHTMIN1")
        self.assertEqual(x, (280, False, False, False, False, False))

        database.write("CHT13", (280, False, True, False, False))
        x = database.read("CHTMIN1")
        self.assertEqual(x, (280, False, False, True, False, False))
        database.write("CHT13", (280, False, False, True, False))
        x = database.read("CHTMIN1")
        self.assertEqual(x, (0, False, False, False, True, False))
        database.write("CHT13", (280, False, False, False, True))
        x = database.read("CHTMIN1")
        self.assertEqual(x, (280, False, False, False, False, True))

    def test_compute_sum(self):
        database.write("FUELQ1", 10)
        database.write("FUELQ2", 10)
        x = database.read("FUELQT")
        self.assertEqual(x, (20, False, False, False, False, False))

        database.write("FUELQ1", 10)
        database.write("FUELQ2", 0)
        x = database.read("FUELQT")
        self.assertEqual(x, (10, False, False, False, False, False))

        database.write("FUELQ1", 0)
        database.write("FUELQ2", 15)
        x = database.read("FUELQT")
        self.assertEqual(x, (15, False, False, False, False, False))

        database.write("FUELQ1", (10, False, True, False, False))
        x = database.read("FUELQT")
        self.assertEqual(x, (25, False, False, True, False, False))
        database.write("FUELQ1", (10, False, False, True, False))
        x = database.read("FUELQT")
        self.assertEqual(x, (0, False, False, False, True, False))
        database.write("FUELQ1", (10, False, False, False, True))
        x = database.read("FUELQT")
        self.assertEqual(x, (25, False, False, False, False, True))

    def test_compute_aoa(self):
        database.write("IAS.Vs", 72)
        database.write("AOA.0g", -1.0)
        database.write("PITCH", 0)
        database.write("IAS", 10)
        x = database.read("AOA")
        self.assertEqual(x, (2.0, False, False, False, False, False))

        # Takeoff roll
        for i in range(100):
            database.write("PITCH", 0)
            database.write("IAS", 10 + i)
            database.write("VS", 0)
            database.write("ANORM", 9.8)
            database.write("HEAD", 0)
        x = database.read("AOA")
        self.assertEqual(x, (2.0, False, False, True, False, False))

        # Climbout
        for i in range(100):
            database.write("PITCH", 5)
            database.write("IAS", 110)
            database.write("VS", 500)
            database.write("ANORM", 9.8)
            database.write("HEAD", 0)
        x = database.read("AOA")
        self.assertEqual(x, (7.0, False, False, True, False, False))

        # Turn
        for i in range(100):
            database.write("PITCH", 2)
            database.write("IAS", 130)
            database.write("VS", 50)
            database.write("ANORM", 10.8)
            database.write("HEAD", i)
        x = database.read("AOA")
        self.assertEqual(x, (4.0, False, False, True, False, False))

        # Straight and level
        for i in range(110):
            database.write("PITCH", 1)
            database.write("IAS", 130)
            database.write("VS", 0)
            database.write("ANORM", 9.8)
            database.write("HEAD", 100)
        x = database.read("AOA")
        y, a, o, b, f, s = x
        x = (round(y, 2), a, o, b, f, s)
        self.assertEqual(x, (3.0, False, False, False, False, False))

        database.write("IAS", 100)
        database.write("ANORM", 10.8)
        x = database.read("AOA")
        y, a, o, b, f, s = x
        x = (round(y, 2), a, o, b, f, s)
        self.assertEqual(x, (4.72, False, False, False, False, False))

        database.write("IAS", 130)
        database.write("ANORM", 7.8)
        x = database.read("AOA")
        y, a, o, b, f, s = x
        x = (round(y, 2), a, o, b, f, s)
        self.assertEqual(x, (2.59, False, False, False, False, False))


if __name__ == "__main__":
    unittest.main()
