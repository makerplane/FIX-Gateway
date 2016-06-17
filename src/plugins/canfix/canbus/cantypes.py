#  Copyright (c) 2012 Phil Birkelbach
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


class Frame(object):
    """Class represents a CANBus frame"""
    def __init__(self, id=0, data=[]):
        self.id = id
        self.data = data
    def __str__(self):
        s = hex(self.id)[2:] + ':'
        for each in self.data:
            if each < 16: s = s + '0'
            s = s + hex(each)[2:]  + ' '
        return s.upper()
