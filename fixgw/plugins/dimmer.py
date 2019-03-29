#  Copyright (c) 2019 Garrett Herschleb
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

#  This is a compute plugin.  It calculates derivative points like averages,
#  minimums or maximums and the like.  Specific calculations for things like
#  True Airspeed could be done also.

import fixgw.plugin as plugin

def dimFunction(key, value, parent):
    #print ("Dim to", str(int(round(value[0]*parent.config['Multiplier']))))
    with open(parent.config["DimmerDevice"], 'w') as dim:
        dim.write (str(int(round(value[0]*parent.config['Multiplier']))) + '\n')
        dim.close()

class Plugin(plugin.PluginBase):
    def run(self):
        self.db_callback_add("DIM", dimFunction, self)

    def stop(self):
        pass
