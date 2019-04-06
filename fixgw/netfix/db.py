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

# This is the FIX-Net client library for FIX-Gateway.  This module represents
# A dynamic database that will replicate the data in the Gateway in real time

from datetime import datetime
import logging
import threading
import time

import fixgw.netfix

log = logging.getLogger(__name__)

# This class represents a single data point in the database.
class DB_Item(object):
    def __init__(self, client, key, dtype='float'):
        super(DB_Item, self).__init__()
        if key == None:
            raise ValueError("Trying to create a Null Item")
        self.lock = threading.RLock()
        self.supressWrite = True # Keeps us from writing to the server
        self.dtype = dtype
        self.key = key
        self._value = 0.0
        self.description = ""
        self._units = ""
        self._annunciate = False
        self._old = False
        self._bad = True
        self._fail = True
        self._secFail = False
        self._max = 100.0
        self._min = 0.0
        self._tol = 100     # Timeout lifetime in milliseconds.  Any older and quality is bad
        self.timestamp = datetime.utcnow()
        self.aux = {}
        self.subscribe = True
        self.is_subscribed = False
        self.client = client
        self.supressWrite = False

        # Callback Functions
        self.valueChanged = None
        self.valueWrite = None
        self.annunciateChanged = None
        self.oldChanged = None
        self.badChanged = None
        self.failChanged = None
        self.secFailChanged = None
        self.auxChanged = None
        self.reportReceived = None
        self.destroyed = None

        log.debug("Creating Item {0}".format(key))

    def __str__(self):
        s = "{} = {}".format(self.key, self._value)
        return s


    # initialize the auxiliary data dictionary.  aux should be a list of
    # aux names
    def init_aux(self, aux):
        with self.lock:
            for each in aux:
                if each != "":
                    self.aux[each] = None

    def get_aux_list(self):
        with self.lock:
            return list(self.aux.keys())

    def set_aux_value(self, name, value):
        with self.lock:
            try:
                last = self.aux[name]
                if value == None or value == "None":
                    self.aux[name] = None
                else:
                    self.aux[name] = self.dtype(value)
                if self.aux[name] != last:
                    if self.auxChanged != None:
                        self.auxChanged(name, value)
            except ValueError:
                log.error("Bad Value for aux {0} {1}".format(name, value))
                raise
            except KeyError:
                log.error("No aux {0} for {1}".format(name, self.description))
                raise

    def get_aux_value(self, name):
        with self.lock:
            try:
                return self.aux[name]
            except KeyError:
                log.error("No aux {0} for {1}".format(name, self.description))
                raise

    # Outputs the value to the send queue and on to the fixgw server
    def output_value(self):
        flags = "1" if self.annunciate else "0"
        flags += "0" # if self.old else "0"
        flags += "1" if self.bad else "0"
        flags += "1" if self.fail else "0"

        # TODO Handle the Aux data.
        db.queue_out("{0};{1};{2}\n".format(self.key, self.value, flags).encode())

    # return the age of the item in milliseconds
    @property
    def age(self):
        with self.lock:
            d = datetime.utcnow() - self.timestamp
            return d.total_seconds() * 1000 + d.microseconds / 1000

    @property
    def value(self):
        with self.lock:
            return self._value #, self.annunciate, self.old, self.bad, self.fail)

    def valueConvert(self, x):
        if self.dtype == bool:
            if type(x) == bool:
                y = x
            elif type(x) == str:
                y = True if x.lower() in ["yes", "true", "1"] else False
            else:
                y = True if x else False
        else:
            try:
                y = self.dtype(x)
            except ValueError:
                log.error("Bad value '" + str(x) + "' given for " + self.description)
            if self.dtype != str:
                # bounds check and cap
                try:
                    if y < self._min: y = self._min
                except:  # Probably only fails if min has not been set
                    #raise
                    pass  # ignore at this point
                try:
                    if y > self._max: y = self._max
                except:  # Probably only fails if max has not been set
                    #raise
                    pass  # ignore at this point
        return y

    @value.setter
    def value(self, x):
        with self.lock:
            last = self._value
            self._value = self.valueConvert(x)
            # set the timestamp to right now
            self.timestamp = datetime.utcnow()

        if last != self._value:
            if self.valueChanged != None:
                # Send the callback if we have a changed value
                self.valueChanged(self._value)
        if self.valueWrite != None:
            # Send Callback everytime we write to it
            self.valueWrite(self._value)
        if not self.supressWrite:
            res = self.client.writeValue(self.key, self._value)
            if '!' in res:
                # TODO: Should probably report the error???
                return
            vals = res.split(';')
            last = self._value
            y = self.valueConvert(vals[1])
            if y != last:
                # Resend the valueChanged callback
                if self.valueChanged != None:
                    self.valueChanged(self._value)
                # Set the actual stored value to the different one returned
                # from the server
                self._value = y
            # Dealwith the returned state of the flags
            self.supressWrite = True
            self.annunciate = vals[2][0]
            self.old = vals[2][1]
            self.bad = vals[2][2]
            self.fail = vals[2][3]
            self.secFail = vals[2][4]
            self.supressWrite = False


    @property
    def dtype(self):
        with self.lock:
            return self._dtype

    @dtype.setter
    def dtype(self, dtype):
        with self.lock:
            types = {'float':float, 'int':int, 'bool':bool, 'str':str}
            try:
                self._dtype = types[dtype]
                self._typestring = dtype
                self._value = self._dtype()
            except:
                log.error("Unknown datatype - " + str(dtype))
                raise

    @property
    def typestring(self):
        with self.lock:
            return self._typestring

    @property
    def units(self):
        with self.lock:
            return self._units

    @units.setter
    def units(self, value):
        with self.lock:
            self._units = value.replace("deg",u'\N{DEGREE SIGN}')

    @property
    def min(self):
        with self.lock:
            return self._min

    @min.setter
    def min(self, x):
        with self.lock:
            try:
                self._min = self.dtype(x)
            except ValueError:
                log.error("Bad minimum value '" + str(x) + "' given for " + self.description)

    @property
    def max(self):
        with self.lock:
            return self._max

    @max.setter
    def max(self, x):
        with self.lock:
            try:
                self._max = self.dtype(x)
            except ValueError:
                log.error("Bad maximum value '" + str(x) + "' given for " + self.description)

    @property
    def tol(self):
        with self.lock:
            return self._tol

    @tol.setter
    def tol(self, x):
        with self.lock:
            try:
                self._tol = int(x)
            except ValueError:
                log.error("Time to live should be an integer for " + self.description)

    def convertBool(self, x):
        if type(x) == str:
            x=x.lower()
            if x in ['0', 'false', 'no', 'f']:
                return False
            else:
                return True
        else:
            return bool(x)

    @property
    def annunciate(self):
        with self.lock:
            return self._annunciate

    @annunciate.setter
    def annunciate(self, x):
        with self.lock:
            last = self._annunciate
            self._annunciate = self.convertBool(x)

        if self._annunciate != last:
            if self.annunciateChanged != None:
                self.annunciateChanged(self._annunciate)
            try:
                if not self.supressWrite:
                    self.client.flag(self.key, 'a', self._annunciate)
            except Exception as e:
                log.error(e)

    @property
    def old(self):
        with self.lock:
            return self._old

    @old.setter
    def old(self, x):
        with self.lock:
            last = self._old
            self._old = self.convertBool(x)

        if self._old != last:
            if self.oldChanged != None:
                self.oldChanged(self._old)
            try:
                if not self.supressWrite:
                    self.client.flag(self.key, 'o', self._old)
            except Exception as e:
                log.error(e)

    @property
    def bad(self):
        with self.lock:
            return self._bad

    @bad.setter
    def bad(self, x):
        with self.lock:
            last = self._bad
            self._bad = self.convertBool(x)

        if self._bad != last:
            if self.badChanged != None:
                self.badChanged(self._bad)
            try:
                if not self.supressWrite:
                    self.client.flag(self.key, 'b', self._bad)
            except Exception as e:
                log.error(e)

    @property
    def fail(self):
        with self.lock:
            return self._fail

    @fail.setter
    def fail(self, x):
        with self.lock:
            last = self._fail
            self._fail = self.convertBool(x)

        if self._fail != last:
            if self.failChanged != None:
                self.failChanged(self._fail)
            try:
                if not self.supressWrite:
                    self.client.flag(self.key, 'f', self._fail)
            except Exception as e:
                log.error(e)

    @property
    def secFail(self):
        with self.lock:
            return self._secFail

    @secFail.setter
    def secFail(self, x):
        with self.lock:
            last = self._secFail
            self._secFail = self.convertBool(x)

        if self._secFail != last:
            if self.secFailChanged != None:
                self.failChanged(self._secFail)
            try:
                if not self.supressWrite:
                    self.client.flag(self.key, 's', self._secFail)
            except Exception as e:
                log.error(e)

    def updateNoWrite(self, report):
        with self.lock:
            try:
                self.supressWrite = True
                self.value = report[1]
                self.annunciate = True if 'a' in report[2] else False
                self.old = True if 'o' in report[2] else False
                self.bad = True if 'b' in report[2] else False
                self.fail = True if 'f' in report[2] else False
                self.secFail = True if 's' in report[2] else False
            except:
                raise
            finally:
                self.supressWrite = False


class UpdateThread(threading.Thread):
    def __init__(self, function, interval = 1.0):
        super(UpdateThread, self).__init__()
        self.daemon = True
        self.interval = interval
        self.getout = False
        self.function = function

    def run(self):
        while not self.getout:
            self.function()
            time.sleep(self.interval)

    def stop(self):
        self.getout = True


# This Class represents the database itself.  Once instantiated it
# creates and starts the thread that handles all the communication to
# the server.
class Database(object):
    def __init__(self, client):
        self.__items = {}
        self.client = client
        self.init_event = threading.Event()
        self.connected = False
        if self.client.isConnected():
            self.initialize()
            self.connected = True
        self.client.setConnectCallback(self.connectFunction)
        self.client.setDataCallback(self.dataFunction)
        self.timer = UpdateThread(self.update)
        self.timer.start()

        # Callback functions
        self.connectCallback = None

    # These are the callbacks that we use to get events from teh client
    # This function is called when the connection state of the client
    # changes.  It recievs a True when connected and False when disconnected
    def connectFunction(self, x):
        self.connected = x
        if self.connectCallback != None:
            self.connectCallback(x)

    def update(self):
        if self.connected and self.__items == {}:
            self.initialize()
        elif not self.connected and self.__items != {}:
            log.debug("Deleting Database")
            for key, item in self.__items.items():
                try:
                    self.client.unsubscribe(key)
                except: # We ignore errors because the server is probably down
                    pass
                if item.destroyed != None:
                    item.destroyed()
            self.__items = {}
        else:
            # Do some maintenance stuff
            pass

    # This callback gets a data update sentence from the server
    def dataFunction(self, x):
        if '.' in x[0]:
            tokens = x[0].split('.')
            i = self.__items[tokens[0]]
            i.supressWrite = True
            i.set_aux_value(tokens[1], x[1])
            i.supressWrite = False
        else:
            i = self.__items[x[0]]
            i.updateNoWrite(x)

    def initialize(self):
        log.debug("Initializing Database")
        if self.__items != {}:
            log.warning("Trying to initialize an already initialized database")
            return
        try:
            keys = self.client.getList()
            for key in keys:
                res = self.client.getReport(key)
                rep = fixgw.netfix.Report(res)
                item = self.define_item(key, rep)
                res = self.client.read(key)
                item.value = res[1]
                item.annunciate = 'a' in res[2]
                item.old = 'o' in res[2]
                item.bad = 'b' in res[2]
                item.fail = 'f' in res[2]
                item.secFail = 's' in res[2]
                auxlist = item.get_aux_list()
                for aux in auxlist:
                    val = self.client.read("{}.{}".format(key, aux))
                    item.set_aux_value(aux, val[1])

            self.init_event.set()
        except Exception as e:
            log.error(e)
            raise

    # Either add an item or redefine the item if it already exists.
    #  This is mostly useful when the FIXGW client reconnects.  The
    #  server may have different information.
    def define_item(self, key, rep):
        if key in self.__items:
            log.debug("Redefining Item {0}".format(key))
            item = self.__items[key]
        else:
            item = DB_Item(self.client, key, rep.dtype)
        item.dtype = rep.dtype
        item.description = rep.desc
        item.min = rep.min
        item.max = rep.max
        item.units = rep.units
        item.tol = rep.tol
        item.init_aux(rep.aux)

        # Send a read command to the server to get initial data
        res = self.client.read(key)
        item.value = res[1]
        for each in item.aux: # Read the Auxiliary data
            self.client.read("{0}.{1}".format(key, each))
        if item.reportReceived != None:
            item.reportReceived()

        # Subscribe to the point
        self.client.subscribe(key)
        self.__items[key] = item
        return item


    # If the create flag is set to True this function will create an
    # item with the given key if it does not exist.  Otherwise just
    # return the item if found.
    def get_item(self, key, create=False, wait=True):
        if wait:
            self.init_event.wait()
        try:
            return self.__items[key]
        except KeyError:
            if create:
                newitem = DB_Item(self.client, key)
                self.__items[key] = newitem
                return newitem
            else:
                raise  # Send the exception up otherwise

    def get_item_list(self):
        return list(self.__items.keys())

    def set_value(self, key, value):
        self.__items[key].value = value

    def get_value(self, key):
        return self.__items[key].value

    def mark_all_fail(self):
        for each in self.__items:
            self.__items[each].fail = True

    def stop(self):
        self.timer.stop()
        self.timer.join()
