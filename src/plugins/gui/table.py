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

import database

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

class DataTable(QTableWidget):
    def __init__(self, parent=None):
        super(DataTable, self).__init__(parent)
        cols = ["Description", "Value", "Set", "A", "O", "B", "F"]
        self.setColumnCount(len(cols))
        self.setHorizontalHeaderLabels(cols)
        l = database.listkeys()
        l.sort()
        self.setRowCount(len(l))
        self.setVerticalHeaderLabels(l)
        for i, key in enumerate(l):
            item = database.get_raw_item(key)
            cell = QTableWidgetItem(item.description)
            cell.setFlags(Qt.ItemIsEnabled)
            self.setItem(i, 0, cell)
            cell = QTableWidgetItem(str(item.value[0]))
            cell.setFlags(Qt.ItemIsEnabled)
            self.setItem(i, 1, cell)


        self.resizeColumnsToContents()
        #self.resizeRowsToContents()
