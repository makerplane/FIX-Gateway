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

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import status

# TODO get the dictionary and convert to a tree view instead of just text

class StatusView(QScrollArea):
    def __init__(self, parent=None):
        super(StatusView, self).__init__(parent)
        self.setWidgetResizable(True)
        self.textBox = QLabel(self)
        self.setWidget(self.textBox)

        self.timer = QTimer()
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.update)
        #self.timer.start()

    def update(self):
        self.textBox.clear()
        s = status.get_string()
        self.textBox.setText(s)

    def showEvent(self, QShowEvent):
        self.timer.start()

    def hideEvent(self, QHideEvent):
        self.timer.stop()
