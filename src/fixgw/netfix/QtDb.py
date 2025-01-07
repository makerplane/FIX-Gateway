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

import logging

from PyQt6.QtCore import QObject, pyqtSignal

import fixgw.netfix
import fixgw.netfix.db


# This class represents a single data point in the database.
class QtDB_Item(QObject):
    valueChanged = pyqtSignal(object)
    valueWrite = pyqtSignal(object)
    annunciateChanged = pyqtSignal(bool)
    oldChanged = pyqtSignal(bool)
    badChanged = pyqtSignal(bool)
    failChanged = pyqtSignal(bool)
    secFailChanged = pyqtSignal(bool)
    auxChanged = pyqtSignal(str, object)
    reportReceived = pyqtSignal(bool)
    destroyed = pyqtSignal()

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
        item.secFailChanged = self.secFailChangedFunc
        item.auxChanged = self.auxChangedFunc
        item.reportReceived = self.reportReceivedFunc
        item.destroyed = self.destroyedFunc

    def valueChangedFunc(self, value):
        self.valueChanged.emit(value)

    def valueWriteFunc(self, value):
        self.valueWrite.emit(value)

    def annunciateChangedFunc(self, value):
        self.annunciateChanged.emit(value)

    def oldChangedFunc(self, value):
        self.oldChanged.emit(value)

    def badChangedFunc(self, value):
        self.badChanged.emit(value)

    def failChangedFunc(self, value):
        self.failChanged.emit(value)

    def secFailChangedFunc(self, value):
        self.secFailChanged.emit(value)

    def auxChangedFunc(self, name, value):
        self.auxChanged.emit(name, value)

    def reportReceivedFunc(self, value):
        self.reportReceived.emit(value)

    def destroyedFunc(self):
        self.destroyed.emit()

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
    def getAge(self):
        return self._item.age

    age = property(getAge)

    def getDescription(self):
        return self._item.description

    description = property(getDescription)

    def getValue(self):
        return self._item.value

    def setValue(self, x):
        self._item.value = x

    value = property(getValue, setValue)

    def getDtype(self):
        return self._item.dtype

    dtype = property(getDtype)

    def getTypestring(self):
        return self._item.typestring

    typestring = property(getTypestring)

    def getUnits(self):
        return self._item.units

    units = property(getUnits)

    def getMin(self):
        return self._item.min

    min = property(getMin)

    def getMax(self):
        return self._item.max

    max = property(getMax)

    def getTol(self):
        return self._item.tol

    tol = property(getTol)

    def getAnnunciate(self):
        return self._item.annunciate

    def setAnnunciate(self, x):
        self._item.annunciate = x

    annunciate = property(getAnnunciate, setAnnunciate)

    def getOld(self):
        return self._item.old

    def setOld(self, x):
        self._item.old = x

    old = property(getOld, setOld)

    def getBad(self):
        return self._item.bad

    def setBad(self, x):
        self._item.bad = x

    bad = property(getBad, setBad)

    def getFail(self):
        return self._item.fail

    def setFail(self, x):
        self._item.fail = x

    fail = property(getFail, setFail)

    def getSecFail(self):
        return self._item.secFail

    def setSecFail(self, x):
        self._item.secFail = x

    secFail = property(getSecFail, setSecFail)

    def get_aux_list(self):
        return self._item.get_aux_list()

    def set_aux_value(self, name, value):
        return self._item.set_aux_value(name, value)

    def get_aux_value(self, name):
        return self._item.get_aux_value(name)


class Database(object):
    def __init__(self, client):
        self.__db = fixgw.netfix.db.Database(client)  # main netfix client database
        self.__items = {}
        self.client = client
        global log
        log = logging.getLogger(__name__)
        if self.__db.connected:
            self.initialize()

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

    def get_item(self, key):
        return self.__items[key]

    def get_item_list(self):
        return list(self.__items.keys())

    def set_value(self, key, value):
        self.__items[key].value = value

    def get_value(self, key):
        return self.__items[key].value
