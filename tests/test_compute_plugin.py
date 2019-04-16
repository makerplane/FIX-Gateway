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
import socket
import fixgw.database as database


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
  - function: sum
    inputs: ["FUELQ1", "FUELQ2"]
    output: FUELQT
"""

# Basically what we do with this test is set up a skeleton of the application
# by loading and initializing the database module and loading the compute
# plugin.
class TestComputePlugin(unittest.TestCase):
    def setUp(self):
        sf = io.StringIO(db_config)
        database.init(sf)

        cc = yaml.load(config)
        import fixgw.plugins.compute

        self.pl =  fixgw.plugins.compute.Plugin("compute", cc)
        self.pl.start()
        time.sleep(0.1) # Give plugin a chance to get started


    def tearDown(self):
        self.pl.shutdown()


    def test_average(self):
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
