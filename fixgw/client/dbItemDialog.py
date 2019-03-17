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

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from . import connection
from .ui import itemDialog_ui

types = {int:"Integer", float:"Float", bool:"Bool", str:"String"}

class ItemDialog(QDialog, itemDialog_ui.Ui_Dialog):
    def __init__(self, *args, **kwargs):
        super(ItemDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)

    def setKey(self, key):
        self.key = key
        self.labelKey.setText(key)
        self.setWindowTitle("Database Item - {}".format(key))
        self.item = connection.db.get_item(key)
        self.labelDescription.setText(self.item.description)
        l = QLabel(self.scrollAreaWidgetContents)
        l.setText("Type:")
        r = QLabel(self.scrollAreaWidgetContents)
        r.setText(types[self.item.dtype])
        self.formLayout.addRow(l, r)

        if self.item.dtype in [int, float]:
            l = QLabel(self.scrollAreaWidgetContents)
            l.setText("Units:")
            r = QLabel(self.scrollAreaWidgetContents)
            r.setText(self.item.units)
            self.formLayout.addRow(l, r)

            l = QLabel(self.scrollAreaWidgetContents)
            l.setText("Min:")
            r = QLabel(self.scrollAreaWidgetContents)
            r.setText(str(self.item.min))
            self.formLayout.addRow(l, r)

            l = QLabel(self.scrollAreaWidgetContents)
            l.setText("Max:")
            r = QLabel(self.scrollAreaWidgetContents)
            r.setText(str(self.item.max))
            self.formLayout.addRow(l, r)

        l = QLabel(self.scrollAreaWidgetContents)
        l.setText("Value:")
        if self.item.dtype is float:
            r = QDoubleSpinBox(self.scrollAreaWidgetContents)
            span = self.item.max - self.item.min
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
            r.setSingleStep(ss)
            r.setDecimals(dp)
            r.setMinimum(self.item.min)
            r.setMaximum(self.item.max)
        elif self.item.dtype is int:
            r = QSpinBox(self.scrollAreaWidgetContents)
            r.setMinimum(self.item.min)
            r.setMaximum(self.item.max)
        elif self.item.dtype is bool:
            r = QCheckBox(self.scrollAreaWidgetContents)
            r.setChecked(self.item.value)
        elif self.item.dtype is str:
            r = QLineEdit(self.scrollAreaWidgetContents)
            r.setText(self.item.value)
        self.formLayout.addRow(l, r)

        l = QLabel(self.scrollAreaWidgetContents)
        l.setText("Annunciate")
        r = QCheckBox(self.scrollAreaWidgetContents)
        self.formLayout.addRow(l, r)
        l = QLabel(self.scrollAreaWidgetContents)
        l.setText("Old")
        r = QCheckBox(self.scrollAreaWidgetContents)
        self.formLayout.addRow(l, r)
        l = QLabel(self.scrollAreaWidgetContents)
        l.setText("Bad")
        r = QCheckBox(self.scrollAreaWidgetContents)
        self.formLayout.addRow(l, r)
        l = QLabel(self.scrollAreaWidgetContents)
        l.setText("Failed")
        r = QCheckBox(self.scrollAreaWidgetContents)
        self.formLayout.addRow(l, r)
        l = QLabel(self.scrollAreaWidgetContents)
        l.setText("Sec Failed")
        r = QCheckBox(self.scrollAreaWidgetContents)
        self.formLayout.addRow(l, r)

            # self.labelMin.setText(str(self.item.min))
            # self.doubleSpinValue.setMinimum(self.item.min)
            # self.labelMax.setText(str(self.item.max))
            # self.doubleSpinValue.setMaximum(self.item.max)
            #
            # span = self.item.max - self.item.min
            # if span < 2.1:
            #     self.doubleSpinValue.setSingleStep(0.001)
            #     self.doubleSpinValue.setDecimals(3)
            # elif span < 201:
            #     self.doubleSpinValue.setSingleStep(0.01)
            #     self.doubleSpinValue.setDecimals(2)
            # elif span < 2001:
            #     self.doubleSpinValue.setSingleStep(0.1)
            #     self.doubleSpinValue.setDecimals(1)
            # elif span < 20001:
            #     self.doubleSpinValue.setSingleStep(1)
            #     self.doubleSpinValue.setDecimals(0)
            # else:
            #     self.doubleSpinValue.setSingleStep(10)
            #     self.doubleSpinValue.setDecimals(0)
