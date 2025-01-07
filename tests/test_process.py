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

# import string
# import io
import subprocess

# import fixgw
# import fixgw.server
import time


class TestProcess(unittest.TestCase):

    def setUp(self):
        pass

    def test_MinimalSuccess(self):
        """Minimal Process start/stop test"""
        p = subprocess.Popen(
            [
                "python3",
                "fixGw.py",
                "--debug",
                "--config-file",
                "tests/config/minimal.yaml",
            ]
        )
        time.sleep(0.3)
        p.terminate()
        x = p.wait()
        self.assertEqual(x, 0)

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
