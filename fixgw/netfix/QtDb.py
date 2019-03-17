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
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

# This module is a thin wrapper around the netfix.db module to make it more
# friendly for Qt applications.  Mostly it's to make signals and slots act
# as they would be expected to act.

from datetime import datetime
import logging
import threading
import time

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

import fixgw.netfix
import fixgw.netfix.db


# This class represents a single data point in the database.
class QtDB_Item(QObject):
    valueChanged = pyqtSignal(object)
    valueWrite = pyqtSignal(object)
    annunciateChanged = pyqtSignal(bool)
    oldChanged =  pyqtSignal(bool)
    badChanged =  pyqtSignal(bool)
    failChanged =  pyqtSignal(bool)
    secFailCahnged =  pyqtSignal(bool)
    auxChanged =  pyqtSignal(bool)
    reportReceived =  pyqtSignal(bool)
    destroyed =  pyqtSignal(bool)

    def __init__(self, key, item):
        super(QtDB_Item, self).__init__()
        if key == None:
            raise ValueError("Trying to create a Null Item")
        self.key = key
        self._item = item

        log.debug("Creating Qt Item {0}".format(key))
        item.valueChanged = self.valueChangedFunc
        item.valueWrite = self.valueWriteFunc
        item.annunciateChanged = self.annunciateChangedFunc
        item.oldChanged = self.oldChangedFunc
        item.badChanged = self.badChangedFunc
        item.failChanged = self.failChangedFunc
        item.secFailCahnged = self.secFailChangedFunc
        item.auxChanged = self.auxChangedFunc
        item.reportReceived = self.reportReceivedFunc
        item.destroyed = self.destroyedFunc


    def valueChangedFunc(value):
        self.valueChanged.emit(value)

    def valueWriteFunc(value):
        self.valueWrite.emit(value)

    def annunciateChangedFunc(value):
        self.annunciateChanged.emit(value)

    def oldChangedFunc(value):
        self.oldChanged.emit(value)

    def badChangedFunc(value):
        self.badChanged(value)

    def failChangedFunc(value):
        self.failChanged(value)

    def secFailChangedFunc(value):
        self.secFailChanged.emit(value)

    def auxChangedFunc(value):
        self.auxChanged.emit(value)

    def reportReceivedFunc(value):
        self.reportReceived(value)

    def destroyedFunc(value):
        self.destroyed(value)

    def __str__(self):
        s = "{} = {}".format(self.key, self._value)
        return s

    def get_aux_list(self):
        return list(self.aux.keys())

    def set_aux_value(self, name, value):
        self._item.set_aux_value(name, value)

    def get_aux_value(self, name):
        self._item.get_aux_value(name)

    # return the age of the item in milliseconds
    @property
    def age(self):
        return self._item.age

    @property
    def description(self):
        return self._item.description

    @property
    def value(self):
        return self._item.value

    @value.setter
    def value(self, x):
        self._item.value = x

    @property
    def dtype(self):
        return self._item.dtype

    @property
    def typestring(self):
        return self._item.typestring

    @property
    def units(self):
        return self._item.units

    @units.setter
    def units(self, value):
        self._item.units = value

    @property
    def min(self):
        return self._item.min

    @property
    def max(self):
        return self._item.max

    @property
    def tol(self):
        return self._item.tol

    @property
    def annunciate(self):
        return self._item.annunciate

    @annunciate.setter
    def annunciate(self, x):
        self._item.annunciate = x

    @property
    def old(self):
        return self._item.old

    @old.setter
    def old(self, x):
        self._item.old = x

    @property
    def bad(self):
        return self._item.bad

    @bad.setter
    def bad(self, x):
        self._item.bad = x

    @property
    def fail(self):
        return self._item.fail

    @fail.setter
    def fail(self, x):
        self._item.fail = x

    @property
    def secFail(self):
        return self._item.sec

    @secFail.setter
    def secFail(self, x):
        self._item.sec = x


# This Class represents the database itself.  Once instantiated it
# creates and starts the thread that handles all the communication to
# the server.
class Database(object):
    def __init__(self, client):
        self.__db = fixgw.netfix.db.Database(client)  # main netfix client database
        self.__items = {}
        self.client = client
        global log
        log = logging.getLogger(__name__)
        if self.__db.connected:
            self.initialize()

    # These are the callbacks that we use to get events from teh client
    # This function is called when the connection state of the client
    # changes.  It recievs a True when connected and False when disconnected
    def connectFunction(self, x):
        if x:
            self.__items = {}
        else:
            self.initialize()

    def initialize(self):
        log.debug("Initializing Qt Database")
        if self.__items != {}:
            log.warning("Trying to initialize an already initialized database")
            return
        try:
            keys = self.__db.get_item_list()
            for key in keys:
                self.__items[key] = QtDB_Item(key, self.__db.get_item(key))

        except Exception as e:
            log.error(e)


    # If the create flag is set to True this function will create an
    # item with the given key if it does not exist.  Otherwise just
    # return the item if found.
    def get_item(self, key):
        return self.__items[key]

    def get_item_list(self):
        return list(self.__items.keys())

    def set_value(self, key, value):
        self.__items[key].value = value

    def get_value(self, key):
        return self.__items[key].value
