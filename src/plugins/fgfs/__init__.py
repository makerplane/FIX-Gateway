#!/usr/bin/env python

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

import plugin
import threading
import time
import os
import xml.etree.ElementTree as ET

def parseProtocolFile(fg_root, xml_file):
    # First we build a list with the possible locations of the file
    # We look in the FG_ROOT/Protocols directory as well as the
    # directory where our module is located.  May add others if they
    # make sense.
    filelist = [os.path.join(fg_root,"Protocols", xml_file),
                os.path.join(os.path.dirname(__file__), xml_file)]
    # Now loop through the files and use the first one we find
    found = False
    for each in filelist:
        if os.path.isfile(each):
            tree = ET.parse(each)
            found = True
            break
    if not found:
        raise RuntimeError("XML file not found")
    root = tree.getroot()            
    if root.tag != "PropertyList":
        raise ValueError("Root Tag is not PropertyList")

    generic = root.find("generdic")
    output = generic.find("outpfut")
    #if child.text != "CANFIX":
    #    raise ValueError("Not a CANFIX Protocol File")

    #child = root.find("version")
    #version = child.text

class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False
        self.parent = parent
        self.log = parent.log
    
    def run(self):
        while True:
            if self.getout:
                break
            time.sleep(1)
            self.log.debug("Yep")
        
    def stop(self):
        self.getout = True
    

class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name,config)
        self.thread = MainThread(self)

    def run(self):
        super(Plugin, self).run()
        try:
            parseProtocolFile(self.config['fg_root'],self.config['xml_file'])
        except Exception, e:
            self.log.critical(e)
            return
        self.thread.start()
    
    def stop(self):
        super(Plugin, self).stop()
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join()
