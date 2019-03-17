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
        #self.verticalHeader().hide()
        for i, key in enumerate(self.dblist):
            item = connection.db.get_item(key)
            #cell = QTableWidgetItem(key)
            #cell.setFlags(Qt.ItemIsEnabled)
            #self.setItem(i, 0, cell)
            cell = QTableWidgetItem(item.description)
            cell.setFlags(Qt.ItemIsEnabled)
            self.setItem(i, 0, cell)
            cell = QTableWidgetItem(str(item.value))
            cell.setFlags(Qt.ItemIsEnabled)
            self.setItem(i, 1, cell)

            cell = QTableWidgetItem()
            cell.setFlags(Qt.ItemIsEnabled)
            self.setItem(i, 2, cell)
            cb = QCheckBox(self)
            self.setCellWidget(i, 2, cb)

        #self.cellClicked.connect(self.clickifcated)
        #self.itemSelectionChanged.connect(self.whatsup)
        self.resizeColumnsToContents()
        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update)
        self.verticalHeader().sectionDoubleClicked.connect(self.keySelected)


    def keySelected(self, x):
        key = self.verticalHeaderItem(x).text()
        d = dbItemDialog.ItemDialog(self)
        d.setKey(key)
        d.show()

    def update(self):
        for i, key in enumerate(self.dblist):
            x = connection.db.get_value(key)
            y = self.item(i,1)
            y.setText(str(x))

    def showEvent(self, QShowEvent):
        self.timer.start()

    def hideEvent(self, QHideEvent):
        self.timer.stop()
