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

#  This is the gui plugin.  It gives us a graphical interface into the
#  inner workings of the gateway.

import fixgw.plugin as plugin
import threading
import sys

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

#from collections import OrderedDict

from . import table
from . import statusview
from . import simulate

class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging

    def run(self):
        app = QApplication(sys.argv)
        window = QTabWidget()
        pushButton1 = QPushButton("BTN 1")
        pushButton2 = QPushButton("BTN 2")
        pushButton3 = QPushButton("BTN 3")
        pushButton4 = QPushButton("BTN 4")
        pushButton5 = QPushButton("BTN 5")
        pushButton6 = QPushButton("BTN 6")
        self.dial        = QDial()
        self.dial.setMinimum(0)
        self.dial.setMaximum(9)
        self.dial.setWrapping(True)
        self.dial.setFixedSize (30,30)

        tab1 = statusview.StatusView()
        tab1.update()
        tab2 = table.DataTable(window)
        tab3 = QWidget()

        hBoxlayout	= QHBoxLayout()
        hBoxlayout.addWidget(pushButton1)
        hBoxlayout.addWidget(pushButton2)
        hBoxlayout.addWidget(pushButton3)
        hBoxlayout.addWidget(pushButton4)
        hBoxlayout.addWidget(pushButton5)
        hBoxlayout.addWidget(pushButton6)
        hBoxlayout.addWidget(self.dial)
        pushButton1.pressed.connect (self.btn1_pressed)
        pushButton2.pressed.connect (self.btn2_pressed)
        pushButton3.pressed.connect (self.btn3_pressed)
        pushButton4.pressed.connect (self.btn4_pressed)
        pushButton5.pressed.connect (self.btn5_pressed)
        pushButton6.pressed.connect (self.btn6_pressed)
        pushButton1.released.connect (self.btn1_released)
        pushButton2.released.connect (self.btn2_released)
        pushButton3.released.connect (self.btn3_released)
        pushButton4.released.connect (self.btn4_released)
        pushButton5.released.connect (self.btn5_released)
        pushButton6.released.connect (self.btn6_released)
        self.dial.valueChanged.connect(self.dialChanged)
        self._last_dial = self.dial.value()

        #Resize width and height
        window.resize(600, 400)

        #Set Layout for Third Tab Page
        tab3.setLayout(hBoxlayout)

        window.addTab(tab1,"Status")
        window.addTab(tab2,"Data")
        window.addTab(tab3,"Sim")

        window.setWindowTitle('FIX Gateway')
        window.show()

        #sys.exit(app.exec_())
        app.exec_()
        self.parent.running = False

    def btn1_pressed(self):
        self.parent.db_write("BTN1", True)
    def btn2_pressed(self):
        self.parent.db_write("BTN2", True)
    def btn3_pressed(self):
        self.parent.db_write("BTN3", True)
    def btn4_pressed(self):
        self.parent.db_write("BTN4", True)
    def btn5_pressed(self):
        self.parent.db_write("BTN5", True)
    def btn6_pressed(self):
        self.parent.db_write("BTN6", True)

    def btn1_released(self):
        self.parent.db_write("BTN1", False)
    def btn2_released(self):
        self.parent.db_write("BTN2", False)
    def btn3_released(self):
        self.parent.db_write("BTN3", False)
    def btn4_released(self):
        self.parent.db_write("BTN4", False)
    def btn5_released(self):
        self.parent.db_write("BTN5", False)
    def btn6_released(self):
        self.parent.db_write("BTN6", False)

    def dialChanged(self, event):
        val = self.dial.value()
        diff = val - self._last_dial
        if diff > 5:
            diff -= 10
        elif diff < -5:
            diff += 10
        key = "ENC1"
        self._last_dial = val
        self.parent.db_write(key, self.parent.db_read(key)[0] + diff)

    def stop(self):
        QApplication.quit()

class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self)

    def run(self):
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(1.0)
        if self.thread.is_alive():
            raise plugin.PluginFail

    # Probably don't need status for the GUI
    #def get_status(self):
    #    return OrderedDict({"Count":self.thread.count})
