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
        l1 = QLabel(self.scrollAreaWidgetContents)
        l1.setText("Type:")
        r1 = QLabel(self.scrollAreaWidgetContents)
        r1.setText(types[self.item.dtype])
        self.formLayout.addRow(l1, r1)

        if self.item.dtype in [int, float]:
            l2 = QLabel(self.scrollAreaWidgetContents)
            l2.setText("Units:")
            r2 = QLabel(self.scrollAreaWidgetContents)
            r2.setText(self.item.units)
            self.formLayout.addRow(l2, r2)

            l3 = QLabel(self.scrollAreaWidgetContents)
            l3.setText("Min:")
            r3 = QLabel(self.scrollAreaWidgetContents)
            r3.setText(str(self.item.min))
            self.formLayout.addRow(l3, r3)

            l4 = QLabel(self.scrollAreaWidgetContents)
            l4.setText("Max:")
            r4 = QLabel(self.scrollAreaWidgetContents)
            r4.setText(str(self.item.max))
            self.formLayout.addRow(l4, r4)

        l5 = QLabel(self.scrollAreaWidgetContents)
        l5.setText("Value:")
        if self.item.dtype is float:
            r5 = QDoubleSpinBox(self.scrollAreaWidgetContents)
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
            r5.setSingleStep(ss)
            r5.setDecimals(dp)
            r5.setMinimum(self.item.min)
            r5.setMaximum(self.item.max)
            r5.valueChanged.connect(self.item.setValue)
            self.item.valueChanged.connect(r5.setValue)
        elif self.item.dtype is int:
            r5 = QSpinBox(self.scrollAreaWidgetContents)
            r5.setMinimum(self.item.min)
            r5.setMaximum(self.item.max)
            r5.valueChanged.connect(self.item.setValue)
            self.item.valueChanged.connect(r5.setValue)
        elif self.item.dtype is bool:
            r5 = QCheckBox(self.scrollAreaWidgetContents)
            r5.setChecked(self.item.value)
            r5.stateChanged.connect(self.item.setValue)
            self.item.valueChanged.connect(r5.setChecked)
        elif self.item.dtype is str:
            r5 = QLineEdit(self.scrollAreaWidgetContents)
            r5.setText(self.item.value)
            r5.textChanged.connect(self.item.setValue)
            self.item.valueChanged.connect(r5.setText)
        self.formLayout.addRow(l5, r5)

        l6 = QLabel(self.scrollAreaWidgetContents)
        l6.setText("Annunciate")
        r6 = QCheckBox(self.scrollAreaWidgetContents)
        r6.setChecked(self.item.annunciate)
        r6.stateChanged.connect(self.item.setAnnunciate)
        self.item.annunciateChanged.connect(r6.setChecked)
        self.formLayout.addRow(l6, r6)

        l7 = QLabel(self.scrollAreaWidgetContents)
        l7.setText("Old")
        r7 = QCheckBox(self.scrollAreaWidgetContents)
        r7.setChecked(self.item.old)
        r7.stateChanged.connect(self.item.setOld)
        self.item.oldChanged.connect(r7.setChecked)
        self.formLayout.addRow(l7, r7)

        l8 = QLabel(self.scrollAreaWidgetContents)
        l8.setText("Bad")
        r8 = QCheckBox(self.scrollAreaWidgetContents)
        r8.setChecked(self.item.bad)
        r8.stateChanged.connect(self.item.setBad)
        self.item.badChanged.connect(r8.setChecked)
        self.formLayout.addRow(l8, r8)

        l9 = QLabel(self.scrollAreaWidgetContents)
        l9.setText("Failed")
        r9 = QCheckBox(self.scrollAreaWidgetContents)
        r9.stateChanged.connect(self.item.setFail)
        r9.setChecked(self.item.fail)
        self.item.failChanged.connect(r9.setChecked)
        self.formLayout.addRow(l9, r9)

        l10 = QLabel(self.scrollAreaWidgetContents)
        l10.setText("Sec Failed")
        r10 = QCheckBox(self.scrollAreaWidgetContents)
        r10.setChecked(self.item.secFail)
        r10.stateChanged.connect(self.item.setSecFail)
        self.item.secFailChanged.connect(r10.setChecked)
        self.formLayout.addRow(l10, r10)

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
