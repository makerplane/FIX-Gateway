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
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
#  USA.import plugin

#  This is the gui client.  It gives us a graphical interface into the
#  inner workings of the gateway.

from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *


# This function creates and returns a proper control to use to adjust
# the value..
def getValueControl(item, parent, signals = True):
    if item.dtype is float:
        control = QDoubleSpinBox(parent)
        span = item.max - item.min
        if span < 2.1:
            ss = 0.001
            dp = 3
        elif span < 201:
            ss = 0.01
            dp = 2
        elif span < 2001:
            ss = 0.1
            dp = 1
        elif span < 20001:
            ss = 1
            dp = 0
        else:
            ss = 10
            dp = 0
        control.setSingleStep(ss)
        control.setDecimals(dp)
        control.setMinimum(item.min)
        control.setMaximum(item.max)
        if signals:
            control.setValue(item.value)
            control.valueChanged.connect(item.setValue)
            item.valueChanged.connect(control.setValue)
    elif item.dtype is int:
        control = QSpinBox(parent)
        control.setMinimum(item.min)
        control.setMaximum(item.max)
        if signals:
            control.setValue(item.value)
            control.valueChanged.connect(item.setValue)
            item.valueChanged.connect(control.setValue)
    elif item.dtype is bool:
        control = QCheckBox(parent)
        if signals:
            control.setChecked(item.value)
            control.stateChanged.connect(item.setValue)
            item.valueChanged.connect(control.setChecked)
    elif item.dtype is str:
        control = QLineEdit(parent)
        if signals:
            control.setText(item.value)
            control.textChanged.connect(item.setValue)
            item.valueChanged.connect(control.setText)
    return control
