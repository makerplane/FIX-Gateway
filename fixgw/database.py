#  Copyright (c) 2014 Phil Birkelbach
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

import logging
from datetime import datetime
import threading
import time

__database = {}

class UpdateThread(threading.Thread):
    def __init__(self, func, delay):
        super(UpdateThread, self).__init__()
        self.delay = delay
        self.func = func

    def run(self):
        while True:
            time.sleep(self.delay)
            self.func()


class db_item(object):
    def __init__(self, key, dtype='float'):
        types = {'float':float, 'int':int, 'bool':bool, 'str':str}
        try:
            self.dtype = types[dtype]
            self.typestring = dtype
        except:
            log.error("Unknown datatype - " + str(dtype))
            raise
        self.key = key
        self._value = 0.0
        self.description = ""
        self.units = ""
        self._annunciate = False
        self._old = False
        self._bad = False
        self._fail = False
        self._max = None
        self._min = None
        self._tol = 100     # Time to live in milliseconds.  Any older and quality is bad
        self.timestamp = datetime.utcnow()
        self.aux = {}
        self.callbacks = []
        self.lock = threading.Lock()

    # initialize the auxiliary data dictionary.  aux should be a comma delimited
    # string of the items to include.
    def init_aux(self, aux):
        l = aux.split(',')
        for each in l:
            self.aux[each.strip()] = None

    def get_aux_list(self):
        return list(self.aux.keys())

    def set_aux_value(self, name, value):
        try:
            self.aux[name] = self.dtype(value)
            if self.aux[name] < self._min: self.aux[name] = self._min
            if self.aux[name] > self._max: self.aux[name] = self._max
        except ValueError:
            log.error("Bad Value for aux {0} {1}".format(name, value))
            raise
        except KeyError:
            log.error("No aux {0} for {1}".format(name, self.description))
            raise
        for func in self.callbacks:
            func[1]("{0}.{1}".format(self.key, name), self.aux[name], func[2])

    def get_aux_value(self, name):
        try:
            return self.aux[name]
        except KeyError:
            log.error("No aux {0} for {1}".format(name, self.description))
            raise

    def send_callbacks(self):
        for func in self.callbacks:
            log.debug("Calling Callback for {0}".format(self.key))
            func[1](self.key, self.value, func[2])

    # return the age of the item in milliseconds
    @property
    def age(self):
        d = datetime.utcnow() - self.timestamp
        return d.total_seconds() * 1000 + d.microseconds / 1000

    @property
    def value(self):
        with self.lock:
            if self.tol != 0:
                if self.age > self.tol:
                    self._old = True
                else:
                    self._old = False
            return (self._value, self._annunciate, self._old, self._bad, self._fail)

    # We can set the value in the item with either a value of a tuple that
    # contains the property flags as well.  (value, annunc, bad, fail)
    @value.setter
    def value(self, x):
        with self.lock:
            if type(x) == tuple:
                if len(x) < 4:
                    raise ValueError("Tuple too small for {}".format(self.key))
                self._annunciate = x[1]
                self._bad = x[2]
                self._fail = x[3]
                x = x[0]
            if self.dtype == bool:
                self._value = (x == True or (isinstance(x,str) and x.lower() in ["yes", "true", "1"])
                                    or (isinstance(x,int) and x != 0))
            else:
                try:
                    self._value = self.dtype(x)
                except ValueError:
                    log.error("Bad value '" + str(x) + "' given for " + self.description)
                if self.dtype != str:
                    # bounds check and cap
                    try:
                        if self._value < self._min: self._value = self._min
                    except:  # Probably only fails if min has not been set
                        pass  # ignore at this point
                    try:
                        if self._value > self._max: self._value = self._max
                    except:  # Probably only fails if max has not been set
                        pass  # ignore at this point
                    # set the timestamp to right now
            self.timestamp = datetime.utcnow()
        self.send_callbacks()


    @property
    def min(self):
        return self._min

    @min.setter
    def min(self, x):
        try:
            self._min = self.dtype(x)
        except ValueError:
            log.error("Bad minimum value '" + str(x) + "' given for " + self.description)

    @property
    def max(self):
        return self._max

    @max.setter
    def max(self, x):
        try:
            self._max = self.dtype(x)
        except ValueError:
            log.error("Bad maximum value '" + str(x) + "' given for " + self.description)

    @property
    def tol(self):
        return self._tol

    @tol.setter
    def tol(self, x):
        if x == '': x = 0
        try:
            self._tol = int(x)
        except ValueError:
            log.error("Time to live should be an integer for " + self.description)

    @property
    def annunciate(self):
        with self.lock:
            return self._annunciate

    @annunciate.setter
    def annunciate(self, x):
        with self.lock:
            last = self._annunciate
            self._annunciate = bool(x)
        if self._annunciate != last:
            self.send_callbacks()

    @property
    def old(self):
        with self.lock:
            return self._old

    @old.setter
    def old(self, x):
        with self.lock:
            last = self._old
            self._old = bool(x)
        if self._old != last:
            self.send_callbacks()

    @property
    def bad(self):
        with self.lock:
            return self._bad

    @bad.setter
    def bad(self, x):
        with self.lock:
            last = self._bad
            self._bad = bool(x)
        if self._bad != last:
            self.send_callbacks()

    @property
    def fail(self):
        with self.lock:
            return self._fail

    @fail.setter
    def fail(self, x):
        with self.lock:
            last = self._fail
            self._fail = bool(x)
        if self._fail != last:
            self.send_callbacks()


# These are support functions for loading the initial database
def check_for_variables(entry):
    for ch in entry[0]:
        if ch.islower(): return ch
    return None


# expand the line into a list of lines based on the variables.
def expand_entry(entry, var, count):
    l = []
    for i in range(count):
        newentry = list(entry) #.copy()
        newentry[0] = newentry[0].replace(var, str(i+1))
        newentry[1] = newentry[1].replace('%' + var, str(i+1))
        ch = check_for_variables(newentry)
        if ch:
            l.extend(expand_entry(newentry,ch,variables[ch]))
        else:
            l.append(newentry)
    return l


def add_item(entry):
    log.debug("Adding - " + entry[1])
    try:
        newitem = db_item(entry[0], entry[2])
    except:
        log.error("Failure to add entry - " + entry[0])
        return None

    newitem.description = entry[1]
    newitem.min = entry[3]
    newitem.max = entry[4]
    newitem.units = entry[5]
    newitem.tol = entry[7]
    newitem.value = entry[6]
    newitem.init_aux(entry[8])
    __database[entry[0]] = newitem
    return newitem


# Main database initialization function
def init(f):
    global log
    global __database
    global variables
    __database = {}
    variables = {}
    log = logging.getLogger('database')
    log.info("Initializing Database")

    state = "var"

    for line in f:
        sline = line.strip()
        if sline and sline[0] != '#':  # Skip blank lines and comments
            entry = sline.split(":")
            if entry[0][:3] == "---":
                state = "db"
                log.debug("Database Variables: " + str(variables))
                continue
            if state == "var":
                v = entry[0].split('=')
                variables[v[0].strip().lower()] = int(v[1].strip())
            if state == "db":
                ch = check_for_variables(entry)
                if ch:
                    try:
                        entries = expand_entry(entry, ch, variables[ch])
                        for each in entries:
                            add_item(each)
                    except KeyError:
                        log.error("Variable {0} not set for {1}".format(ch, entry[1]))
                else:
                    add_item(entry)
    f.close()
    t = UpdateThread(update, 1.0)
    t.daemon = True
    t.start()


# These are the public functions for interacting with the database
def write(key, value):
    if '.' in key:
        x = key.split('.')
        entry = __database[x[0]]
        entry.set_aux_value(x[1], value)
    else:
        entry = __database[key]
        entry.value = value


def read(key):
    if '.' in key:
        x = key.split('.')
        entry = __database[x[0]]
        return entry.get_aux_value(x[1])
    else:
        return __database[key].value


def get_raw_item(key):
    try:
        return __database[key]
    except KeyError:
        return None


def listkeys():
    return list(__database.keys())


# Adds or redefines the callback function that will be called when
# the items value is set.
def callback_add(name, key, function, udata):
    item = __database[key]
    item.callbacks.append( (name, function, udata) )
    log.debug("Adding callback function for %s on key %s" % (name, key))


def callback_del(name, key, function, udata):
    if key == "*":
        for each in __database:
            try:
                __database[each].callbacks.remove( (name, function, udata) )
                log.debug("Deleting callback function for %s on key %s" % (name, each))
            except ValueError:
                pass
    else:
        log.debug("Deleting callback function for %s on key %s" % (name, key))
        try:
            __database[key].callbacks.remove( (name, function, udata) )
        except ValueError:
            log.debug("Callback not deleted because it was not found in the list")

# Maintenance Functions
def update():
    for key in __database:
        item = __database[key]
        if item.age > item.tol and item.tol != 0:
            item.old = True
