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

__database = {}


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
        self.annunciate = False
        self.old = False
        self.bad = False
        self.fail = False
        self._max = None
        self._min = None
        self._tol = 100     # Time to live in milliseconds.  Any older and quality is bad
        self.timestamp = datetime.utcnow()
        self.aux = {}
        self.callbacks = []

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
        except ValueError:
            log.error("Bad Value for aux {0} {1}".format(name, value))
            raise
        except KeyError:
            log.error("No aux {0} for {1}".format(name, self.description))
            raise
        for func in self.callbacks:
            # We call teh get_aux_value() function again because
            # the value may have been formated or bounds checked
            func[1]("{0}.{1}".format(self.key, name), self.aux[name], func[2])

    def get_aux_value(self, name):
        try:
            return self.aux[name]
        except KeyError:
            log.error("No aux {0} for {1}".format(name, self.description))
            raise


    # return the age of the item in milliseconds
    @property
    def age(self):
        d = datetime.utcnow() - self.timestamp
        return d.total_seconds() * 1000 + d.microseconds / 1000

    @property
    def value(self):
        if self.age > self.tol and self.tol != 0:
            self.old = True
        else:
            self.old = False
        return (self._value, self.annunciate, self.old, self.bad, self.fail)

    @value.setter
    def value(self, x):
        if self.dtype == bool:
            self._value = (x == True or x.lower() in ["yes", "true", "1", 1])
        else:
            try:
                self._value = self.dtype(x)
            except ValueError:
                log.error("Bad value '" + str(x) + "' given for " + self.description)
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
        # call all of the callback functions
        for func in self.callbacks:
            log.debug("Calling Callback for {0}".format(self.key))
            func[1](self.key, self.value, func[2])


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
        try:
            self._tol = int(x)
        except ValueError:
            log.error("Time to live should be an integer for " + self.description)

# cleans up the lines
def clean_line(line):
    while "\t\t" in line: line = line.replace("\t\t", "\t")
    return line

def check_for_variables(entry):
    for ch in entry[0]:
        if ch.islower(): return ch
    return None


# expand the line into a list of lines based on the variables.
def expand_entry(entry, var, count):
    l = []
    for i in range(count):
        newentry = entry.copy()
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


def init(config):
    global log
    global __database
    global variables
    __database = {}
    variables = {}
    log = logging.getLogger('database')
    log.info("Initializing Database")

    ddfile = config.get("config", "db_file")
    try:
        f = open(ddfile,'r')
    except:
        log.critical("Unable to find database definition file - " + ddfile)
        raise

    state = "var"

    for line in f:
        if line[0] != "#":
            line = clean_line(line)
            entry = line.split("\t")
            if entry[0] == "---":
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
    return __database[key]


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
    # for f in __database[key].callbacks:
    #     if f[0] == name and f[1] == function and f[2] == udata:
    #         print("Found it"+str(f))
    #         del f
    #del __database[key].callbacks[name]
