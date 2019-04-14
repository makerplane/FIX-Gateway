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

# Basically what we do with this test is set up a skeleton of the application
# by loading and initializing the database module and loading the netfix
# plugin.  Then we just create out own local sockets and test.
class TestNetfixServerSimple(unittest.TestCase):
    def setUp(self):
        sf = io.StringIO(db_config)
        database.init(sf)

        nc = yaml.load(netfix_config)
        import fixgw.plugins.netfix

        self.pl =  fixgw.plugins.netfix.Plugin("netfix", nc)
        self.pl.start()
        time.sleep(0.1) # Give plugin a chance to get started
        # Grab a client socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.settimeout(0.5)
        self.sock.connect(("127.0.0.1", 3490))

    def tearDown(self):
        self.sock.shutdown(socket.SHUT_RDWR)
        self.sock.close()
        self.pl.shutdown()


    def test_value_write(self):
        self.sock.sendall("@wALT;2500\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@wALT;2500.0;00000\n")
        x = database.read("ALT")
        self.assertEqual(x, (2500.0, False, False, False, False, False))


    def test_subscription(self):
        self.sock.sendall("@sALT\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@sALT\n")
        database.write("ALT", 3000)
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "ALT;3000.0;00000\n")


    def test_multiple_subscription_fail(self):
        """Test that we receive an error if we try to subscribe to the same
           point again"""
        self.sock.sendall("@sALT\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@sALT\n")

        database.write("ALT", 3100)
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "ALT;3100.0;00000\n")

        self.sock.sendall("@sALT\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@sALT!002\n")


    def test_unsubscribe(self):
        self.sock.sendall("@sIAS\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@sIAS\n")
        self.sock.sendall("@sALT\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@sALT\n")

        database.write("IAS", 120.0)
        database.write("ALT", 3100)
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "IAS;120.0;00000\nALT;3100.0;00000\n")

        self.sock.sendall("@uIAS\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@uIAS\n")

        database.write("IAS", 125.0)
        database.write("ALT", 3200)
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "ALT;3200.0;00000\n")


    def test_normal_write(self):
        self.sock.sendall("IAS;121.2;0000\n".encode())
        time.sleep(0.1)
        x = database.read("IAS")
        self.assertEqual(x, (121.2, False, False, False, False, False))

        self.sock.sendall("IAS;121.3;1000\n".encode())
        time.sleep(0.1)
        x = database.read("IAS")
        self.assertEqual(x, (121.3, True, False, False, False, False))

        self.sock.sendall("IAS;121.4;0100\n".encode())
        time.sleep(0.1)
        x = database.read("IAS")
        self.assertEqual(x, (121.4, False, False, True, False, False))

        self.sock.sendall("IAS;121.5;0010\n".encode())
        time.sleep(0.1)
        x = database.read("IAS")
        self.assertEqual(x, (121.5, False, False, False, True, False))

        self.sock.sendall("IAS;121.6;0001\n".encode())
        time.sleep(0.1)
        x = database.read("IAS")
        self.assertEqual(x, (121.6, False, False, False, False, True))


    def test_read(self):
        database.write("IAS", 105.4)
        self.sock.sendall("@rIAS\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@rIAS;105.4;00000\n")

        i = database.get_raw_item("IAS")
        i.annunciate = True
        self.sock.sendall("@rIAS\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@rIAS;105.4;10000\n")
        i.bad = True
        self.sock.sendall("@rIAS\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@rIAS;105.4;10100\n")
        i.fail = True
        self.sock.sendall("@rIAS\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@rIAS;105.4;10110\n")
        i.secfail = True
        self.sock.sendall("@rIAS\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@rIAS;105.4;10111\n")

        i.annunciate = False
        self.sock.sendall("@rIAS\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@rIAS;105.4;00111\n")
        i.bad = False
        self.sock.sendall("@rIAS\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@rIAS;105.4;00011\n")
        i.fail = False
        self.sock.sendall("@rIAS\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@rIAS;105.4;00001\n")
        i.secfail = False
        self.sock.sendall("@rIAS\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@rIAS;105.4;00000\n")


    def test_read_errors(self):
        self.sock.sendall("@rJUNKID\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@rJUNKID!001\n")
        # Try it with a good key but bad aux
        self.sock.sendall("@rOILP1.lowWarned\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@rOILP1.lowWarned!001\n")


    def test_write_errors(self):
        self.sock.sendall("@wJUNKID;12.8\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@wJUNKID!001\n")
        # Try it with a good key but bad aux
        self.sock.sendall("@wOILP1.lowWarned;12.0\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@wOILP1.lowWarned!001\n")


    def test_value_write_with_subscription(self):
        """Make sure we don't get a response to a value write on our subscriptions"""
        self.sock.sendall("@sALT\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@sALT\n")
        self.sock.sendall("@sIAS\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@sIAS\n")
        # writing both from database should give subscription returns
        database.write("IAS", 135.4)
        database.write("ALT", 4300)
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "IAS;135.4;00000\nALT;4300.0;00000\n")
        # writing over the socket should not create a callback
        self.sock.sendall("@wALT;3200\n".encode())
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "@wALT;3200.0;00000\n")
        database.write("IAS", 132.4)
        res = self.sock.recv(1024).decode()
        # we should only get the IAS one
        self.assertEqual(res, "IAS;132.4;00000\n")
        # using a normal write should do the same
        self.sock.sendall("ALT;3400;000\n".encode())
        database.write("IAS", 136.4)
        res = self.sock.recv(1024).decode()
        self.assertEqual(res, "IAS;136.4;00000\n")


    def test_aux_write(self):
        self.sock.sendall("@wOILP1.lowWarn;12.5\n".encode())
        res = self.sock.recv(1024).decode()
        x = database.read("OILP1.lowWarn")
        self.assertEqual(x, 12.5)


    # def test_aux_subscription(self):
    #     self.sock.sendall("@wOILP1\n".encode())
    #     res = self.sock.recv(1024).decode()
    #     self.assertEqual(res, "@OILP1\n")


    # def test_list(self):
    #     pass
    #
    #
    # def test_get_report(self):
    #     pass
    #
    #
    # def test_min_max(self):
    #     pass
    #
    #
    # def test_tol(self):
    #     pass
    #
    #
    # def test_flags(self):
    #     pass
    #
    #
    # def test_string_type(self):
    #     pass
    #
    #
    # def test_none_string(self):
    #     pass
    #
    # def test_subscribe_flags(self):
    #     pass
    #
    # def test_unknown_command(self):
    #     pass
    #
    # def test_status_command(self):
    #     pass



if __name__ == '__main__':
    unittest.main()


#
