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

from . import connection
from .ui import itemDialog_ui
from . import common

types = {int: "Integer", float: "Float", bool: "Bool", str: "String"}


# Returns a function that can be used as a slot for aux value changes
def auxValueSlotClosure(item, auxname):
    def func(value):
        item.set_aux_value(auxname, value)

    return func


class ItemDialog(QDialog, itemDialog_ui.Ui_Dialog):
    def __init__(self, *args, **kwargs):
        super(ItemDialog, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.setAttribute(Qt.WindowType.WindowType.WidgetAttribute.WA_DeleteOnClose)

    def auxAddClosure(self, auxname):
        def func():
            none_label = self.aux_controls[auxname]["none"]
            control = self.aux_controls[auxname]["control"]
            del_btn = self.aux_controls[auxname]["del_btn"]
            add_btn = self.aux_controls[auxname]["add_btn"]
            add_btn.hide()
            del_btn.show()
            none_label.hide()
            control.show()
            self.item.set_aux_value(auxname, 0.0)

        return func

    def auxDelClosure(self, auxname):
        def func():
            none_label = self.aux_controls[auxname]["none"]
            control = self.aux_controls[auxname]["control"]
            del_btn = self.aux_controls[auxname]["del_btn"]
            add_btn = self.aux_controls[auxname]["add_btn"]
            add_btn.show()
            del_btn.hide()
            none_label.show()
            control.hide()
            self.item.set_aux_value(auxname, None)

        return func

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
        l1a = QLabel(self.scrollAreaWidgetContents)
        l1a.setText("Lifetime:")
        r1a = QLabel(self.scrollAreaWidgetContents)
        r1a.setText(str(self.item.tol) + " ms")
        self.formLayout.addRow(l1a, r1a)

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
        r5 = common.getValueControl(self.item, self.scrollAreaWidgetContents)
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

        l = QLabel(self.scrollAreaWidgetContents)
        l.setText("Sec Failed")
        r = QCheckBox(self.scrollAreaWidgetContents)
        r.setChecked(self.item.secFail)
        r.stateChanged.connect(self.item.setSecFail)
        self.item.secFailChanged.connect(r.setChecked)
        self.formLayout.addRow(l, r)

        aux_list = self.item.get_aux_list()
        self.aux_controls = {}
        for aux in aux_list:
            d = {}
            l = QLabel(self.scrollAreaWidgetContents)
            l.setText(aux)

            vc = common.getValueControl(self.item, self.scrollAreaWidgetContents, False)
            vc.valueChanged.connect(auxValueSlotClosure(self.item, aux))
            vc.hide()
            d["control"] = vc

            vl = QLabel(self.scrollAreaWidgetContents)
            vl.setText("None")
            d["none"] = vl

            del_icon = QIcon.fromTheme("list-remove")
            del_btn = QPushButton()
            del_btn.setIcon(del_icon)
            del_btn.hide()
            del_btn.clicked.connect(self.auxDelClosure(aux))
            d["del_btn"] = del_btn
            add_icon = QIcon.fromTheme("list-add")
            add_btn = QPushButton()
            add_btn.setIcon(add_icon)
            add_btn.clicked.connect(self.auxAddClosure(aux))
            d["add_btn"] = add_btn
            self.aux_controls[aux] = d

            box = QHBoxLayout()
            box.addWidget(vl)
            box.addWidget(vc)
            box.addWidget(del_btn)
            box.addWidget(add_btn)
            v = self.item.get_aux_value(aux)
            if v is not None:
                vc.setValue(v)
                del_btn.show()
                add_btn.hide()
                vl.hide()
                vc.show()
            self.formLayout.addRow(l, box)


# TODO:
#   When an aux item is None it is displayed as a label that says 'None.'  There
#   should be a click event that will change it to a spinBox so that it can
#   be edited.  None is different that zero.  Once the spinbox comes up we should
#   have a delete 'x' also to set the aux back to None.  This feature probably
#   needs to be added to netfix as well.

#   auxChanged signal from the item needs to be implemented
