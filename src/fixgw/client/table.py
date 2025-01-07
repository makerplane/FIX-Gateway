#  Copyright (c) 2016 Phil Birkelbach
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

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

from . import connection
from . import dbItemDialog
from . import common

class CheckButton(QPushButton):
    def setChecked(self, value):
        super(CheckButton, self).setChecked(value)
        if value:
            self.setText("I")
        else:
            self.setText("0")


class DataTable(QTableWidget):
    def __init__(self, parent=None):
        super(DataTable, self).__init__(parent)
        cols = ["Description", "Value", "A", "O", "B", "F", "S"]
        self.setColumnCount(len(cols))
        self.setHorizontalHeaderLabels(cols)
        self.dblist = connection.db.get_item_list()
        self.dblist.sort()
        self.setRowCount(len(self.dblist))
        self.setVerticalHeaderLabels(self.dblist)
        for i, key in enumerate(self.dblist):
            item = connection.db.get_item(key)

            cell = QTableWidgetItem(item.description)
            cell.setFlags(Qt.ItemIsEnabled)
            self.setItem(i, 0, cell)

            cell = common.getValueControl(item, self)
            self.setCellWidget(i, 1, cell)

            cb = CheckButton(self)
            cb.setCheckable(True)
            cb.setChecked(item.annunciate)
            cb.clicked.connect(item.setAnnunciate)
            item.annunciateChanged.connect(cb.setChecked)
            self.setCellWidget(i, 2, cb)

            cb = CheckButton(self)
            cb.setCheckable(True)
            cb.setChecked(item.old)
            cb.clicked.connect(item.setOld)
            item.oldChanged.connect(cb.setChecked)
            self.setCellWidget(i, 3, cb)

            cb = CheckButton(self)
            cb.setCheckable(True)
            cb.setChecked(item.bad)
            cb.clicked.connect(item.setBad)
            item.badChanged.connect(cb.setChecked)
            self.setCellWidget(i, 4, cb)

            cb = CheckButton(self)
            cb.setCheckable(True)
            cb.setChecked(item.fail)
            cb.clicked.connect(item.setFail)
            item.failChanged.connect(cb.setChecked)
            self.setCellWidget(i, 5, cb)

            cb = CheckButton(self)
            cb.setCheckable(True)
            cb.setChecked(item.secFail)
            cb.clicked.connect(item.setSecFail)
            item.secFailChanged.connect(cb.setChecked)
            self.setCellWidget(i, 6, cb)

        self.resizeColumnsToContents()
        self.verticalHeader().sectionDoubleClicked.connect(self.keySelected)


    def keySelected(self, x):
        key = self.verticalHeaderItem(x).text()
        d = dbItemDialog.ItemDialog(self)
        d.setKey(key)
        d.show()
