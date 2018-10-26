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
import subprocess
import os
import time


class TestCanfix(unittest.TestCase):

    def setUp(self):
        pass

    def test_canfix_simple(self):
        self.p = subprocess.Popen(["python3", "fixgw.py", "--debug", "--config-file", "tests/config/canfix_simple.yaml"])
        #self.p = subprocess.Popen(["python3", "fixgw.py", "--config-file", "tests/config/canfix_simple.yaml"])
        x = self.p.wait()
        self.assertEqual(x,0)

if __name__ == '__main__':
    unittest.main()
