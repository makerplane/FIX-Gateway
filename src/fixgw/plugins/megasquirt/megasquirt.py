#Get data from RDAC
import threading
import struct
import ctypes
from . import tables
import time
from collections import defaultdict
import numpy as np
import can

class Get(threading.Thread):
    def __init__(self, parent, config):
        super(Get,self).__init__()
        self.parent = parent
        self.config = config
        self.getout = False
        self.log = parent.log

        # Buid the dict needed to handle messages
        self.mega_get_items = dict()
        for key,db in self.config.items():
            mega_id = tables.advanced[key]['canid']
            if not mega_id in self.mega_get_items:
                self.mega_get_items[mega_id] = dict()
            self.mega_get_items[mega_id][key] = db


    def run(self):
        self.bus = self.parent.bus
        while(True):
            try:
                msg = self.bus.recv(1.0)
                if msg is not None:
                    self.parent.recvcount += 1
                    if msg.arbitration_id in self.mega_get_items:
                        #This message has some data we want
                        for mkey,fixkey in self.mega_get_items[msg.arbitration_id].items():
                            # Extract each value we want from this message
                            add = tables.advanced[mkey]['add']
                            factor = tables.advanced[mkey]['factor']
                            size = tables.advanced[mkey]['size']
                            offset = tables.advanced[mkey]['offset']
                            #I think all are ints
                            #type = tables.advanced[mkey]['type']
                            units = tables.advanced[mkey]['units']
                            signed = tables.advanced[mkey]['signed']
                            self.log.debug(f"{msg.data[offset:offset+size]}")
                            value = int.from_bytes(msg.data[offset:offset+size],byteorder='big', signed=signed)
                            value = value * factor + add
                            # TODO deal with unit conversions 
                            # Of the units I've looked at I am not seeing any others that need conversion at the moment.
                            if units == "cc/min":
                                #Convert cc/min to GHP, this unit only exists for 'fuelflow'
                                value = round(value * 0.01585,2)
                            elif units == "kPa":
                                value = round(value * 0.296133971 ,2)
                            elif units == "%":
                                # I am not sure this is correct since I do not have a real megasquirt to test with yet
                                value = round(value * 0.01 ,4)

                            self.log.debug(f"{fixkey}:{value}") 
                            self.parent.db_write(fixkey,value)
 
            finally:
                if(self.getout):
                    break

    def stop(self):
        self.getout = True
        try:
            self.join()
        except:
            pass

