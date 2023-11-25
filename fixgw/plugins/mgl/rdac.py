#Get data from RDAC
import threading
import struct
import ctypes
from . import tables
import time
from collections import defaultdict
import numpy as np
import can

class MGLStruct(ctypes.BigEndianStructure):
    _fields_ = [
        ("junk",ctypes.c_uint,21),
        ("host", ctypes.c_uint, 7),
        ("msg_id", ctypes.c_uint, 4)
    ]

class Get(threading.Thread):
    def __init__(self, parent, config):
        super(Get,self).__init__()
        self.parent = parent
        self.config = config
        self.getout = False
        self.log = parent.log
        #self.rdac_id = self.config['id']
        self.rdac_get_items = dict()#defaultdict(lambda: defaultdict(dict)) #Holds Each get object
        self.rdac_id = self.config.get('default_id',1)
        #print(self.config)
        for key,conf in self.config['get'].items():
            #self.rdac_get[msg.get('id']
            #print(f"key:{key} conf:{conf}")
            mgl_host_id = conf.get('id',self.rdac_id) + 31
            if not mgl_host_id in self.rdac_get_items:
                self.rdac_get_items[mgl_host_id] = dict()
            mgl_id = tables.rdac[conf['key']]['msg_id']
            if not mgl_id in self.rdac_get_items[mgl_host_id]:
                self.rdac_get_items[mgl_host_id][mgl_id] = dict()
            #print(conf['key'])
            #print(key)
            self.rdac_get_items[mgl_host_id][mgl_id][conf['key']] = { 
                'key':key,
                'calibration':conf.get('calibration', False)
                # We will likely need more things like calibration data 
            }
        #print(self.rdac_get_items[1]['TC2'])
        #print(self.rdac_get_items[2]['TC1'])  
        #print(self.rdac_get_items)
        #time.sleep(5)
#    rdac:             
#      default_id: 1   
#      get:            
#        EGT11:        
#          id: 1       
#          value: TC1  

        # I'm not sure if borrowing the callback method from canfix is useful or not
        # In the main loop we wait for can messages.
        # Each message is parsed.
        # In the parsing method if it has data we want, we can just write it to the fix db at that time.
        # So what we need to do is:
        # In the init, build a lookup table of all the times we want.
        # The table should be indexed to be easy to use for parsing.
        # parsing will extract the RDAC ID, the RDAC messageID and then then individual values in each message.
        #
        # wanted_messages[rdac_id][rdac_msg_id][{fixkey,bytes,type}]
        #

        # Connect or throw error
        # A thread should process incomming messages 
        # And update an array of key/values
        # data stored in dict
        # data['rdac_id']['rdac_msg_id'] = [bytes,type,key]
        #for each in maps['inputs']:
        #    self.input_mapping[ix][each["index"]] = self.getInputFunction(each["fixid"])

    def run(self):
        self.bus = self.parent.bus
        while(True):
            try:
                msg = self.bus.recv(1.0)
                if msg is not None:
                    self.parent.recvcount += 1
                    #self.log.debug(f"{dir(msg)}")
                    #self.log.debug(f"{msg.dlc}")
                    #self.log.debug(f"{msg.data}")
                    mgl = MGLStruct()
                    struct.pack_into('!I', mgl,
                        0, # offset
                        msg.arbitration_id)
                    self.log.debug(f"id:{bin(int(msg.arbitration_id))} host:{int(mgl.host)} msg_id:{mgl.msg_id}")
                    #self.log.debug(f"host:{hex(mgl.host)} msg_id:{hex(mgl.msg_id)}")
                    #self.log.debug(f"{tables.rdac}")
                    if mgl.host in self.rdac_get_items:
                        # We want stuff from this host
                        #print(self.rdac_get_items[mgl.host])
                        if mgl.msg_id in self.rdac_get_items[mgl.host]:
                            # We want stuff from this messageid
                            #print(self.rdac_get_items[mgl.host][mgl.msg_id])
                            for k,d in self.rdac_get_items[mgl.host][mgl.msg_id].items():
                                self.parent.wantcount += 1
                                data_bytes = tables.rdac[k]['bytes']
                                data_type = tables.rdac[k]['type']
                                #data_min = tables.rdac.get('min',False)
                                #data_max = tables.rdac.get('max',False)
                                data_error = tables.rdac.get('error',False)
                                #print(data_bytes)
                                #print((msg.data))
                                #print((msg.data[data_bytes[0]:data_bytes[1] + 1]))
                                data_value = 0
                                if data_type == 'word':
                                    data_value = int.from_bytes(msg.data[data_bytes[0]:data_bytes[1] + 1], byteorder='little', signed=False)
                                elif data_type == 'sint':
                                    data_value = int.from_bytes(msg.data[data_bytes[0]:data_bytes[1] + 1], byteorder='little', signed=True)

                                    #print(data_value)

                                if data_error and data_value == data_error:
                                    # This value indicates an error
                                    pass
                                    # TODO Implement this
                                if 'RPM' in k:
                                    # RPM has some calculations
                                    # From the MGL documentation:
                                    # if number is >=50000, value is scaled to RPM*10. Example: 51000 = 60000 RPM
                                    if data_value >= 50000:
                                        # Not sure if this is right but it matches the example provided
                                        data_value = (data_value - 50000) * 10 + 50000

                                if 'RDACVOLT' == k:
                                    # voltage is scaled, we limit to 2 deciam digits
                                    data_value = round(data_value * 0.017428951,2)

                                if d['calibration']:
                                    x,y = list(zip(*d['calibration']))
                                    data_value = np.interp(data_value, y, x)
                                self.log.debug(f"host:{mgl.host} msig_id:{mgl.msg_id} mgl_key:{k} fix_key:{d['key']} value:{data_value}")
                                self.parent.db_write(d['key'],data_value)
 
            finally:
                if(self.getout):
                    break

    def stop(self):
        self.getout = True
        self.join()


class Send(threading.Thread):
    def __init__(self, parent, config):
        super(Send,self).__init__()
        self.parent = parent
        self.config = config
        self.getout = False
        self.log = parent.log
        self.rdac_send_items = dict()
        self.rdac_ids = []
        self.rdac_frequencies = dict()
        self.rdac_id = self.config.get('default_id',1)

        # MGL Requires sending all RDAC data and at specific intervals.
        # Some of their other equipment collects messages and re-sends on another
        # network in one burst. if messages are missing then data is not passed along.
        # So we build a list of default values, update any we want to send using a callback.
        # Then in the main loop we send all the messages for each interval when interval 
        # amount of time has passed.
        for key,data in tables.rdac.items():
            # Build: self.rdac_send_items[freq][msg_id][key] = value
            if not data['freq'] in self.rdac_send_items:
                self.rdac_send_items[data['freq']] = dict()
            if not data['msg_id'] in self.rdac_send_items[data['freq']]:
                self.rdac_send_items[data['freq']][data['msg_id']] = dict()
            if not key in self.rdac_send_items[data['freq']][data['msg_id']]:
                self.rdac_send_items[data['freq']][data['msg_id']][key] = data.get('error', 0)
            # TODO If any send items are for this key, connect them
            #if self.rdac_ids
            if not data['freq'] in self.rdac_frequencies:
                self.rdac_frequencies[data['freq']] = time.time_ns() // 1000000
            for k,conf in self.config['send'].items():
                self.log.debug(f"key:{key}")
                #time.sleep(0.1)
                if key == conf['key']:
                    self.parent.db_callback_add(k,self.getOutputFunction(data['freq'],data['msg_id'],key))
                if not conf.get('id',self.rdac_id) in self.rdac_ids:
                    self.rdac_ids.append(conf.get('id',self.rdac_id))


    def getOutputFunction(self, freq, msg_id, key):
        def outputCallback(fixkey, value, udata):
            # TODO Manipulate the data to fit rdac
            # set error code if needed
            self.log.debug(f"output: freq:{freq} msg_id:{msg_id} key:{key}")
            self.rdac_send_items[freq][msg_id][key] = value[0]

        return outputCallback 

    def run(self):
        self.bus = self.parent.bus
        while(True):
            time.sleep(0.01)
            try:
                for t,s in self.rdac_frequencies.items():
                    self.log.debug(f"{t}:{s}:{((time.time_ns() // 1000000) - t)}####################################")
                    if ((time.time_ns() // 1000000) - t) >= s:
                        # Time to send the values for frequency t
                        for mid,keys in self.rdac_send_items[t].items():
                            # Each message id
                            msg = bytearray(b'\x00\x00\x00\x00\x00\x00\x00\x00')
                            for key,val in self.rdac_send_items[t][mid].items():#keys.items(): #self.rdac_send_items[t][mid].items():
                                # each item in message id, populate msg
                                self.log.debug(f"key:{key} value:{val}")
                                b = tables.rdac[key]['bytes']
                                # TODO Need to deal with data conversion, decimal points etc
                                # Some data is signed, some is not
                                signed = tables.rdac[key]['type'] == 'sint'
                                # TODO Deal with min/max/calibration

                                v = int(val).to_bytes(2,'little',signed=signed)
                                self.log.debug(v)
                                msg[b[0]] = v[0]
                                msg[b[1]] = v[1]
                            #msg = ''.join(msg)
                            for i in self.rdac_ids:
                                # for each rdac we are sending as
                                # send msg_id:msg
                                rdac_id = 20 - 1 + i
                                #print(f"0x{rdac_id}{mid:x}")
                                msg_id = int(f"0x{rdac_id}{mid:x}",16)
                                self.log.debug(f"msg_id:{msg_id}: msg:{msg}")
                                message = can.Message(is_extended_id=False,arbitration_id=msg_id,data=msg)
                                self.bus.send(message, timeout=0.2)
            finally:
                if(self.getout):
                    break

    def stop(self):
        self.getout = True
        self.join()

