#  Copyright (c) 2023 Eric Blevins
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

from pymavlink import mavutil, mavwp

from os import stat
import math
import time 
from collections import defaultdict
import statistics
import logging
logger = logging.getLogger(__name__)

class Mav:
    def __init__(self, parent, conn_type='serial',port='/dev/ttyACM0',baud=57600, options={'airspeed': True, 'gps': True, 'ahrs': True, 'accel': True, 'pressure': True}):
        # Currently all that is supported is serial so conn_type is not yet used
        self.parent = parent

        self._apreq = 'INIT'           # Requested mode
        self._apstat = 'INIT'          # Current status
        self._apmode = 'INIT'
        self._apwpv = False            # valid waypoint or not

        self._apmodes = dict() # List of customs modes we use with TRIM being default
        self._apmodes['TRIM'] = 0
        self._apmodes['CRUISE'] = 7
        self._apmodes['AUTOTUNE'] = 8
        self._apmodes['AUTO'] = 10
        self._apmodes['GUIDED'] = 15

        self._airspeed = options.get('airspeed', False)
        self._groundspeed = options.get('groundspeed', False)
        self._gps = options.get('gps', False)
        self._ahrs = options.get('ahrs', False)
        self._accel = options.get('accel', False)
        self._pressure = options.get('pressure', False)
        # Pressure sensors are typically quite accurate at detecting pressure change with altitude
        # but they are often quite inaccurate on the exact pressure
        # This option allows adding/subtracting from the reading to make it more accurate
        self._pascal_offset = options.get('pascal_offset', 0)
        self._min_airspeed = options.get('min_airspeed', 10)

        self._outputPitch = 0
        self._outputRoll = 0
        self._outputYaw = 0

        self._apAdjust        = False
        self._trimsSaved      = False 
        self._trimsSavedRoll  = 0
        self._trimsSavedPitch = 0
        self._trimsSavedYaw   = 0

        self._waypoint = str           # The current known waypoint 
        self.setStat('ERROR', 'No Communication')

        if not stat(port):
            self.setStat('ERROR', 'No Communication')
            raise Exception(f"serial port {port} is not found!")
        # When using USB serial when flight computer boots it creates /dev/ttyASM0
        # But then removes it and re-creates it again, we want to ensure we open the correct one so we wait and check again
        time.sleep(5)
        if not stat(port):
            self.setStat('ERROR', 'No Communication')
            raise Exception(f"serial port {port} is not found!")

        self._data = defaultdict(list)
        self._max_average = 15

        # Connect
        self.conn = mavutil.mavlink_connection(port, baud=baud)
        self.ids = []
        self.ids.append(mavutil.mavlink.MAVLINK_MSG_ID_SERVO_OUTPUT_RAW)
        if self._airspeed:
            self.ids.append(mavutil.mavlink.MAVLINK_MSG_ID_VFR_HUD)

        if self._gps or self._ahrs:
            self.ids.append(mavutil.mavlink.MAVLINK_MSG_ID_GPS_RAW_INT)
            self.ids.append(mavutil.mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT)
            self.ids.append(mavutil.mavlink.MAVLINK_MSG_ID_ATTITUDE)
        if self._accel:
            self.ids.append(mavutil.mavlink.MAVLINK_MSG_ID_SCALED_IMU)
        if self._pressure:
            self.ids.append(mavutil.mavlink.MAVLINK_MSG_ID_SCALED_PRESSURE)

        self.request_ids()
        self.no_msg_count = 0
        # Init data
        self.init()

    def request_ids(self):
        for msg_id in self.ids:
            logger.debug(f"Requesting msg_id:{msg_id}")
            # Send message requesting info every 100ms
            message = self.conn.mav.command_long_encode(
                self.conn.target_system,
                self.conn.target_component,
                mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
                0,
                msg_id,  # param1: message ID
                100,     # param2: interval in microseconds
                0,       # param3: not used
                0,       # param4: not used
                0,       # param5: not used
                0,       # param5: not used
                0        # param6: not used
            )
            # Send the command
            self.conn.mav.send(message)

    def close(self):
        self.conn.close()

    def wait_heartbeat(self):
        self.conn.wait_heartbeat()

    def process(self):
        # Process recenived messages
        msg = self.conn.recv_match(timeout=0.1, blocking=True)
        if not msg:
          self.no_msg_count += 1
          if self.no_msg_count > 15:
              self.request_ids()
          return
        msg_type = msg.get_type()
        #logger.debug(repr(msg))
        #logger.debug(msg_type)
        if msg_type == 'VFR_HUD':
            #logger.debug(msg)
            # We can also get other info like GS, VS, MSL, HEAD from this
            # msg.airspeed is CAS or IAS, at the speeds we fly the different is insignificant
            # I do not think TAS can be obtained from the flight controller
            # Maybe we can calculate it
            if self._airspeed:
                spd = self.avg('IAS',msg.airspeed * 1.9438445,2)
                if self._min_airspeed < spd:
                    self.parent.db_write("IAS", spd) #m/s to knots
                else:
                    self.parent.db_write("IAS",0)
            if self._groundspeed:
                self.parent.db_write("GS", round(msg.groundspeed * 1.9438445,2)) #m/s to knots
            if self._ahrs:
                # The AI in pyefis requires TAS
                # I think we could calculate it but for now we will just use IAS in its place
                spd = self.avg('TAS',msg.airspeed * 1.9438445,2)
                if self._min_airspeed < spd:
                    self.parent.db_write("TAS", spd) #m/s to knots
                else:
                    self.parent.db_write("TAS",0)
                self.parent.db_write("VS", round(msg.climb * 196.85039)) #m/s to ft/min
        elif msg_type == 'SCALED_IMU':
            #logger.debug(msg.yacc/1000)
            # mavlink is in mG
            # Not exactly sure if G is what pyefis expects for ALAT
            # We can also get other data like xacc and zacc
            if self._accel:
                self.parent.db_write("ALAT", round(msg.yacc/1000,4))
                self.parent.db_write("ALONG", round(msg.xacc/1000,4))
                self.parent.db_write("ANORM", round(msg.zacc/1000,4))
        elif msg_type == "ATTITUDE":
            if self._ahrs:
                self.parent.db_write("ROLL", round(math.degrees(msg.roll), 2))
                self.parent.db_write("PITCH", round(math.degrees(msg.pitch),2))
                self.parent.db_write("YAW", round(math.degrees(msg.yaw),2))
            #self.parent.db_write("YAW", math.degrees(msg.yaw))
        elif msg_type == "GPS_RAW_INT":
            if self._ahrs:
                self.parent.db_write("COURSE",round(msg.cog/100,2))
        elif msg_type == "GLOBAL_POSITION_INT":
            if self._ahrs:
                self.parent.db_write("HEAD", round(msg.hdg/100,2))             # uint16_t cdeg 
                self.parent.db_write("AGL", round(msg.relative_alt / 304.8,2)) # int32_t mm to ft
                # Seems like MSD is TALT and ALT should be indicated, not sure hoe to get both:
                self.parent.db_write("ALT", round(msg.alt / 304.8, 2))          # int32_t mm to ft
                self.parent.db_write("TALT", round(msg.alt / 304.8, 2))          # int32_t mm to ft
            if self._gps:
                self.parent.db_write("LAT",msg.lat/10000000.0)        # int32_t degE7 10**7
                self.parent.db_write("LONG",msg.lon/10000000.0)       # int32_t degE7 10**7
        elif msg_type == "SCALED_PRESSURE":
            if self._pressure:
                self.parent.db_write("AIRPRESS", round((msg.press_abs * 100) + self._pascal_offset,4))       # float hPa to Pa 
                self.parent.db_write("DIFFAIRPRESS", round(msg.press_diff * 100,4))  # float hPa to Pa
                # We can also get temperature and temperature_press_diff i cDegC
                # HIGHRES_IMU might also be useful

        #if msg_type == "EKF_STATUS_REPORT":
        # This might be useful to get some info about the state of the
        # imus/gyros
        #    print(msg)
        elif msg_type == "HEARTBEAT":
            # Heartbeat type 27 = ADSB Not sure what to do with this yet so not implemented
            # heartbeat type 1 = fixed wing
            if msg.type == 1:
              # custom_mode has current flight mode
              # 0 = manual, 8 = autotune, 10 = auto, 7 = cruise https://ardupilot.org/plane/docs/parameters.html#fltmod
               
              logger.debug(f"custom_mode: {msg.custom_mode}") # What mode we are in
              if msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED !=0:
                  logger.debug("MAV_MODE_FLAG_SAFETY_ARMED")
                  # This status means we are ARMED and can use more than just TRIM mode
                  self.setStat('ARMED')
              if msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_MANUAL_INPUT_ENABLED	 !=0:
                  logger.debug("MAV_MODE_FLAG_MANUAL_INPUT_ENABLED	")
              if msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_HIL_ENABLED !=0:
                  logger.debug("MAV_MODE_FLAG_HIL_ENABLED")
              if msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_STABILIZE_ENABLED !=0:
                  logger.debug("MAV_MODE_FLAG_STABILIZE_ENABLED")
              if msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_GUIDED_ENABLED !=0:
                  logger.debug("MAV_MODE_FLAG_GUIDED_ENABLED")
                  #self.setStat('ARMED', 'Ready')
              if msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_AUTO_ENABLED !=0:
                  logger.debug("MAV_MODE_FLAG_AUTO_ENABLED")
              if msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_TEST_ENABLED !=0:
                  logger.debug("MAV_MODE_FLAG_TEST_ENABLED")
              if msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED !=0:
                  logger.debug("MAV_MODE_FLAG_CUSTOM_MODE_ENABLED")

              # TODO Maybe we only want to do this if the mode in flight controller is different than what we think it is
              # Or having this set could be useful from MAVMODE old           
              if msg.custom_mode == self._apmodes['TRIM']:
                  # TRIM mode allows manual control of servos
                  self.sendMode("TRIM", "Trim Mode")
                  self.checkInit('TRIM')

              elif msg.custom_mode == self._apmodes['CRUISE']:
                  # CRUISE mode is like heading hold
                  # Using the TRIM inputs you could change
                  # course or altitude
                  self.sendMode("CRUISE", "Heading Hold")
                  self.checkInit('CRUISE')

              elif msg.custom_mode == self._apmodes['AUTOTUNE']:
                  # AUTOTUNE helps to train the auto pilot
                  # You have to make full trim deflections on all axis
                  # numerous times for it to learn how best
                  # to control your aircraft
                  self.sendMode("AUTOTUNE", "Auto Tune")
                  self.checkInit('AUTOTUNE')

              elif msg.custom_mode == self._apmodes['GUIDED']:
                  # Will navigate to a pont defined by fix keys:
                  # WPLON, WPLAT
                  # Also uses WPNAME for the name of the waypoint.
                  # Altitude is set to your current altitude MSL
                  # Trims can be used to change altitude
                  # Maybe we can add other methods in the future.
                  self.sendMode("GUIDED", f"Nav to: {self.parent.db_read('WPNAME')[0]}")
                  self.checkInit('GUIDED')

              else:
                  self.parent.db_write("MAVMODE", "UNKNOWN")
                  self.setStat('ERROR', 'Unknown Condition')
                  # TODO Likely need to do more here
                  # But we should never end up here in the first place

        elif msg_type == "SYS_STATUS":
            # Can we arm? 
            if msg.onboard_control_sensors_health & mavutil.mavlink.MAV_SYS_STATUS_PREARM_CHECK !=0:
                # Arming checks pass, we can arm now

                # If not armed, arm
                if not self._apstat == 'ARMED':
                    message = self.conn.mav.command_long_encode(
                        self.conn.target_system,
                        self.conn.target_component,
                        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                        0,       # Confirmation
                        1,       # param1: 1 = arm 0 = disarm
                        100,     # param2: 
                        0,       # param3 not used
                        0,       # param4 not used
                        0,       # param5 not used
                        0,       # param5 not used
                        0        # param6 not used
                    )
                    # Send the command
                    self.conn.mav.send(message)
                    # TODO Can we ack that the cmd was applied?

            else:
                pass 
                # TODO Maybe we can set some status to indicate we cannot arm?
        elif msg_type == "SERVO_OUTPUT_RAW":
            #logger.debug(f"SERVO_OUTPUT_RAW:{dir(msg)}")
            #logger.debug(f"roll:servo1_raw:{msg.servo1_raw}:{(msg.servo1_raw - 1500) * 2.5}")
            #logger.debug(f"pich:servo2_raw:{msg.servo2_raw}:{(msg.servo2_raw - 1500) * 2.5}")
            #logger.debug(f"yaw :servo4_raw:{msg.servo4_raw}:{(msg.servo4_raw - 1500) * 2.5}")
            self._outputRoll = int((msg.servo1_raw - 1500) * 2.5) #1100-1900us 1500 center
            self._outputPitch = int((msg.servo2_raw - 1500) * 2.5)
            self._outputYaw = int((msg.servo4_raw - 1500) * 2.5)

           # TODO We need to drop out of AP mode, alert pilot if system is in a bad state
           # unhealthy GPS signal is one such state
           # Not sure what all we need to check for


    def init(self):
        self.parent.db_write("ROLL", 0)
        self.parent.db_write("PITCH", 0)
        self.parent.db_write("HEAD", 0)
        self.parent.db_write("AGL", 0)
        self.parent.db_write("ALT", 0)
        self.parent.db_write("VS", 0)

    def checkInit(self,mode):
        if self._apmode == 'INIT':
            self._apmode = mode
            self._apreq = mode
            self.parent.db_write("MAVMODE", mode)

    def sendMode(self,mode,msg):
        self.parent.db_write("MAVMODE", mode)
        self.parent.db_write("MAVMSG", msg)


    def setStat(self,stat,msg=None):
        self.parent.db_write("MAVSTATE", stat)
        self._apstat = stat
        if msg:
            self.parent.db_write("MAVMSG", msg)


    def sendTrims(self):
        # TODO I suspect we do not want to send trims sometimes.
        # Also, we need to send only zero when in modes other than TRIM
        # Unless the pilot is wanting to change course/altitude.
        # Seems like some non-latching three position toggle switches
        # might work well
        # Pilot could hold up/down to change altitude or 
        # hold right/left to change heading
        # Once on heading let go of switch and AP will maintain

        # TODO
        # When changing out of trim mode save the trims
        # Then start updating TRIM keys with the data from servo outputs

        # IF yaw or pitch trim change while not in trim mode
        # This should be used as input to change altitude or heading
        # Operator can move trims off center, when at desired alt or heading press center

        # How can we detect that the operator is making changes?
        # Seems like we would need another value to set by operator
        # Maybe a fly by wire button?

        adj_req = self.parent.db_read("MAVREQADJ")[0]

        if not self._apAdjust and adj_req:
            self._apAdjust = True
            if not self.parent.db_read("MAVADJ")[0] and self.parent.quorum.leader:
                self.parent.db_write("MAVADJ", True)
            if self.parent.quorum.leader:
                self.parent.db_write("TRIMR",0)
                self.parent.db_write("TRIMP",0)
                self.parent.db_write("TRIMY",0)


        elif self._apAdjust and not adj_req:
            self._apAdjust = False
            if self.parent.db_read("MAVADJ")[0] and self.parent.quorum.leader:
                self.parent.db_write("MAVADJ", False)

        if self._apmode == 'TRIM' or self._apAdjust:
            if not self._apAdjust and self._trimsSaved:
                self._trimsSaved = False
                if self.parent.quorum.leader:
                    self.parent.db_write("TRIMR", self._trimsSavedRoll / 10)
                    self.parent.db_write("TRIMP", self._trimsSavedPitch / 10)
                    self.parent.db_write("TRIMY", self._trimsSavedYaw / 10)

            if self.parent.quorum.leader:
                self.conn.mav.manual_control_send(
                    self.conn.target_system,
                    int(self.parent.db_read("TRIMP")[0] * 10), #pitch
                    int(self.parent.db_read("TRIMR")[0] * 10), #roll
                    0, #Throttle
                    int(self.parent.db_read("TRIMY")[0] * 10), #Yaw
                    0
                )
        elif self.parent.quorum.leader:
            if not self._trimsSaved:
                self._trimsSaved = True
                self._trimsSavedRoll  = self.parent.db_read("TRIMR")[0] * 10
                self._trimsSavedPitch = self.parent.db_read("TRIMP")[0] * 10
                self._trimsSavedYaw   = self.parent.db_read("TRIMY")[0] * 10
            self.parent.db_write("TRIMP",self._outputPitch / 10) 
            self.parent.db_write("TRIMR",self._outputRoll / 10)
            self.parent.db_write("TRIMY",self._outputYaw / 10) 

    def checkMode(self):
        self.checkWaypoint()
        if not self.parent.quorum.leader: 
            logger.debug(f"Nothing else to check becaure leader = true")
            return

        new_mode = 'INIT'
        logger.debug(f"Current mode is {self._apmode}")
        for f in self._apmodes:
            requested = self.parent.db_read(f"MAVREQ{f}")[0]
            logger.debug(f"Processing {f}: MAVREQ{f}: {requested}")
            if requested and f != self._apmode:
                # Requested and not the current active mode
                # so this is what we want.
                # If it is the current mode, another one might be requested
                logger.debug(f"Mode {f} was requested True")
                new_mode = f
                break

        if new_mode != 'INIT':
            for f in self._apmodes:
                if f != new_mode and self.parent.db_read(f"MAVREQ{f}")[0]:
                    # Set all other modes to False if set to True
                    self.parent.db_write(f"MAVREQ{f}", False)
                    logger.debug(f"MAVREQ{f} set to False")
            # Check if a mode change has been requested
            if self._apmode != new_mode and new_mode != 'INIT':
                # Set the mode
                self.setMode(new_mode)

    def checkWaypoint(self):
        # We need to take actions when the waypoint changes or is deleted
        # For example, if the pilot deletes the flight plan or communication is lost
        # with whatever is providing the waypoints.
        if self.parent.db_read('WPLAT')[2] or self.parent.db_read('WPLON')[2] or (self.parent.db_read('WPLAT')[0] == 0.0 or self.parent.db_read('WPLON')[0] == 0.0):
            # The WPLAT/LON are old or not set
            # IF we are in GUIDED mode we want to drop to CRUISE mode
            if self._apreq == 'GUIDED' and self.parent.quorum.leader:
                # drop to CRUISE mode ( Heading Hold )
                #self.setMode('CRUISE')
                self.parent.db_write('MAVMSG', "Drop to Heading Hold")
                self.parent.db_write('MAVREQCRUISE', True)
            if self.parent.quorum.leader:
                # Invalidate the waypoint
                self.parent.db_write('MAVWPVALID', False)
            self._apwpv = False
            return
        else:
            # We do have a valid waypoint
            self._apwpv = True
            if self.parent.quorum.leader:
                self.parent.db_write('MAVWPVALID', True)
            # Did the waypoint change?
            if self._waypoint != f"{self.parent.db_read('WPLON')[0]}{self.parent.db_read('WPLAT')[0]}{self.parent.db_read('WPNAME')[0]}" and self._apmode == 'GUIDED':
                if self.parent.quorum.leader:
                    self.setMode('GUIDED')
 
    def setMode(self, mode):
        logger.debug(f"Trying to set mode {mode}")
        # Can we set that mode?
        if self._apstat in ['TRIM','ARMED'] and mode in self._apmodes:
            if mode not in ['TRIM'] and (( mode == 'GUIDED' and not self._apwpv) or (self._apstat != 'ARMED')):
                # Cruise mode requested but we are not armed
                # or do not have a valid waypoint
                
                self.parent.db_write("MAVMSG", "Invalid Request")
                # This will disrupt AHRS
                # TODO Maybe we need a better way to inform the pilot to the change?
                time.sleep(3)
                return
            if not self.parent.quorum.leader:
                return
            if mode == 'GUIDED':
                # Request is for guided mode so we need to set the mode differently
                self._waypoint = f"{self.parent.db_read('WPLON')[0]}{self.parent.db_read('WPLAT')[0]}{self.parent.db_read('WPNAME')[0]}"
                message = self.conn.mav.command_int_encode(
                    self.conn.target_system,
                    self.conn.target_component,
                    mavutil.mavlink.MAV_FRAME_GLOBAL,
                    mavutil.mavlink.MAV_CMD_DO_REPOSITION, # Command
                    0, # not used
                    0, # not used
                    0, # default speed
                    1, # goto location now
                    0, # radius
                    0, # loiter direction
                    int(self.parent.db_read('WPLAT')[0] * 10**7), # int32_t degE7
                    int(self.parent.db_read('WPLON')[0] * 10**7),
                    self.parent.db_read('ALT')[0] * .3048 # altitude ALT is in ft, mavlink uses meters
                )
            else:
                message = self.conn.mav.command_long_encode(
                    self.conn.target_system,
                    self.conn.target_component,
                    mavutil.mavlink.MAV_CMD_DO_SET_MODE,  # command to send
                    0,  
                    mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,  # custom mode
                    self._apmodes[mode],     # param2: custom mode to set
                    0,       # param3 not used
                    0,       # param4 not used
                    0,       # param5 not used
                    0,       # param5 not used
                    0        # param6 not used
                )
            # Send the command
            self.conn.mav.send(message)
            self._apreq = mode

            # Set APREQ to in case the mode change was made internally
            self.parent.db_write("MAVMODE", mode)
            self._apmode = mode
        else:
            # TODO Likely need more logic here
            pass 


    def avg(self,item,value,decimals):
        self._data[item].append(value)
        if len(self._data[item]) > self._max_average:
            self._data[item].pop(0)
        return round(statistics.mean(self._data[item]),decimals)

