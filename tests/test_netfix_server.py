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

- key: ALT
  description: Indicated Altitude
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

- key: OILPe
  description: Oil Pressure Engine %e
  type: float
  min: 0.0
  max: 200.0
  units: psi
  initial: 0.0
  tol: 2000
  aux: [Min,Max,lowWarn,highWarn,lowAlarm,highAlarm]

- key: TIMEZ
  description: Zulu Time String
  type: str
  tol: 2000

- key: ACID
  description: Aircraft ID
  type: str
"""

netfix_config = """
type: server
host: 0.0.0.0
port: 3490
buffer_size: 1024
timeout: 1.0
"""

class TestNetfixServer(unittest.TestCase):
    def setUp(self):
        sf = io.StringIO(db_config)
        database.init(sf)

        nc = yaml.load(netfix_config)
        import fixgw.plugins.netfix

        self.pl =  fixgw.plugins.netfix.Plugin("netfix", nc)
        self.pl.start()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(1.0)
        self.sock.connect(("127.0.0.1", 3490))

    def tearDown(self):
        self.sock.close()
        self.pl.shutdown()


    def test_does_this_work_at_all(self):
        self.assertEqual(True, True)



if __name__ == '__main__':
    unittest.main()


#
