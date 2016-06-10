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

import plugin
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
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging

    def run(self):
        app = QApplication(sys.argv)
        window = QTabWidget()
        pushButton1 = QPushButton("QPushButton 1")
        pushButton2 = QPushButton("QPushButton 2")

        tab1 = statusview.StatusView()
        tab1.update()
        tab2 = table.DataTable(window)
        tab3 = QWidget()

        vBoxlayout	= QVBoxLayout()
        vBoxlayout.addWidget(pushButton1)
        vBoxlayout.addWidget(pushButton2)

        #Resize width and height
        window.resize(600, 400)

        #Set Layout for Third Tab Page
        tab3.setLayout(vBoxlayout)

        window.addTab(tab1,"Status")
        window.addTab(tab2,"Data")
        window.addTab(tab3,"Sim")

        window.setWindowTitle('FIX Gateway')
        window.show()

        #sys.exit(app.exec_())
        app.exec_()
        self.parent.running = False

    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self)

    def run(self):
        super(Plugin, self).run()
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join()
        super(Plugin, self).stop()

    # Probably don't need status for the GUI
    #def get_status(self):
    #    return OrderedDict({"Count":self.thread.count})
