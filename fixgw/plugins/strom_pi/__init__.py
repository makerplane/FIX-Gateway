#!/usr/bin/env python

#  Copyright (c) 2024 Janne Mäntyharju
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

#  Checks current power source and battery state from Strom Pi 3 module

import threading
from collections import OrderedDict

import serial
import time
import os
import fixgw.plugin as plugin


class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False   # indicator for when to stop
        self.parent = parent  # parent plugin object
        self.log = parent.log  # simplifies logging
        self._c = None

    def run(self):
        try:
            self._c = serial.Serial(self.parent.config['port'],
                                    baudrate=38400,
                                    timeout=0.5,)
        except serial.SerialException:
            self.parent.log.error("Serial port error")
            return
        
        power_fail_timer = None
        while not self.getout:
            try:
                self._c.reset_input_buffer()
                self._c.write(str.encode('\rstatus-rpi\r'))
                time.sleep(0.2)
                sp3_time = self._c.readline()
                sp3_date = self._c.readline()
                sp3_weekday = self._c.readline()
                sp3_modus = self._c.readline()
                sp3_alarm_enable = self._c.readline()
                sp3_alarm_mode = self._c.readline()
                sp3_alarm_hour = self._c.readline()
                sp3_alarm_min = self._c.readline()
                sp3_alarm_day = self._c.readline()
                sp3_alarm_month = self._c.readline()
                sp3_alarm_weekday = self._c.readline()
                sp3_alarmPoweroff = self._c.readline()
                sp3_alarm_hour_off = self._c.readline()
                sp3_alarm_min_off = self._c.readline()
                sp3_shutdown_enable = self._c.readline()
                sp3_shutdown_time = self._c.readline()
                sp3_warning_enable = self._c.readline()
                sp3_serialLessMode = self._c.readline()
                sp3_intervalAlarm = self._c.readline()
                sp3_intervalAlarmOnTime = self._c.readline()
                sp3_intervalAlarmOffTime = self._c.readline()
                sp3_batLevel_shutdown = self._c.readline()
                sp3_batLevel = self._c.readline()
                sp3_charging = self._c.readline()
                sp3_powerOnButton_enable = self._c.readline()
                sp3_powerOnButton_time = self._c.readline()
                sp3_powersave_enable = self._c.readline()
                sp3_poweroffMode = self._c.readline()
                sp3_poweroff_time_enable = self._c.readline()
                sp3_poweroff_time = self._c.readline()
                sp3_wakeupweekend_enable = self._c.readline()
                sp3_ADC_Wide = float(self._c.readline())
                sp3_ADC_BAT = float(self._c.readline())
                sp3_ADC_USB = float(self._c.readline())
                sp3_ADC_OUTPUT = float(self._c.readline())
                sp3_output_status = self._c.readline()
                sp3_powerfailure_counter = self._c.readline()
                sp3_firmwareVersion = self._c.readline()
            except serial.SerialException:
                self.parent.log.error("Serial port error")
            except ValueError as e:
                self.parent.log.error("Bad data")
                return

            bat = None
            charging = None
            power_fail = None
            try:
                bat = int(sp3_batLevel)
                charging = int(sp3_charging)
                power_fail = int(sp3_output_status)
            except ValueError:
                self.parent.log.error("Bad data")
                continue

            if power_fail == 3: # We are running on battery
                self.parent.db_write("POWER_FAIL", True)
                if not power_fail_timer:
                    power_fail_timer = time.time()
                    self.parent.log.warning("Power has failed")
                
                if power_fail_timer and "shutdown_after" in self.parent.config:
                    if time.time() > power_fail_timer + (self.parent.config['shutdown_after'] * 60):
                        self._c.write(str.encode("quit\n"))                        
                        self._c.write(str.encode("poweroff\n"))
                        os.system("sudo shutdown -h now")

            else:
                self.parent.db_write("POWER_FAIL", False)
                if power_fail_timer:
                    power_fail_timer = None
                    self.parent.log.warning("Power has been restored")

            self.parent.db_write("BAT_CHARGING", charging)

            switcher = {
                1: 10,
                2: 25,
                3: 50,
                4: 100,
            }
            try:
                self.parent.db_write("BAT_REMAINING", switcher[bat])
            except KeyError:
                self.parent.log.error("Bad data")

    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    def __init__(self, name, config):
        super(Plugin, self).__init__(name, config)
        self.thread = MainThread(self)
        self.status = OrderedDict()

    def run(self):
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(1.0)
        if self.thread.is_alive():
            raise plugin.PluginFail

    def get_status(self):
        return self.status
