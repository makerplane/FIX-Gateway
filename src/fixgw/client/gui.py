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

import sys

from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *

from . import connection
from .ui.main_ui import Ui_MainWindow

from . import table
from . import statusModel

# from . import simulate


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, *args, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        # self.client = client
        self.statusview = statusModel.StatusView()
        self.layoutStatus.addWidget(self.statusview)
        self.dataview = table.DataTable()
        self.layoutData.addWidget(self.dataview)

        self.show()


def main(client):
    connection.initialize(client)
    app = QApplication(sys.argv)
    app.setApplicationName("FIX Gateway Client")

    window = MainWindow()
    x = app.exec()
    return x
