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
        self._gps = options.get('gps', False)
        self._ahrs = options.get('ahrs', False)
        self._accel = options.get('accel', False)
        self._pressure = options.get('pressure', False)

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

        # Connect
        self.conn = mavutil.mavlink_connection(port, baud=baud)
        ids = []
        if self._airspeed:
            ids.append(mavutil.mavlink.MAVLINK_MSG_ID_VFR_HUD)

        if self._gps or self._ahrs:
            ids.append(mavutil.mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT)
            ids.append(mavutil.mavlink.MAVLINK_MSG_ID_ATTITUDE)
        if self._accel:
            ids.append(mavutil.mavlink.MAVLINK_MSG_ID_SCALED_IMU)
        if self._pressure:
            ids.append(mavutil.mavlink.MAVLINK_MSG_ID_SCALED_PRESSURE)

        for msg_id in ids:
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

        # Init data
        self.init()

    def close(self):
        self.conn.close()

    def wait_heartbeat(self):
        self.conn.wait_heartbeat()

    def process(self):
        # Process recenived messages
        msg = self.conn.recv_match()
        if not msg:
          return
        msg_type = msg.get_type()
        if msg_type == 'VFR_HUD':
            #logger.debug(msg)
            # We can also get other info like GS, VS, MSL, HEAD from this
            # msg.airspeed is CAS or IAS, at the speeds we fly the different is insignificant
            # I do not think TAS can be obtained from the flight controller
            # Maybe we can calculate it
            if self._airspeed:
                self.parent.db_write("IAS", msg.airspeed * 1.9438445) #m/s to knots
            if self._ahrs:
                # The AI in pyefis requires TAS
                # I think we could calculate it but for now we will just use IAS in its place
                self.parent.db_write("TAS", msg.airspeed * 1.9438445) #m/s to knots
        elif msg_type == 'SCALED_IMU':
            #logger.debug(msg.yacc/1000)
            # mavlink is in mG
            # Not exactly sure if G is what pyefis expects for ALAT
            # We can also get other data like xacc and zacc
            if self._accel:
                self.parent.db_write("ALAT", msg.yacc/1000)
                self.parent.db_write("ALONG", msg.xacc/1000)
                self.parent.db_write("ANORM", msg.zacc/1000)
        elif msg_type == "ATTITUDE":
            if self._ahrs:
                self.parent.db_write("ROLL", math.degrees(msg.roll))
                self.parent.db_write("PITCH", math.degrees(msg.pitch))
                self.parent.db_write("YAW", math.degrees(msg.yaw))
            #self.parent.db_write("YAW", math.degrees(msg.yaw))
        elif msg_type == "GLOBAL_POSITION_INT":
            if self._ahrs:
                self.parent.db_write("HEAD", msg.hdg/100)             # uint16_t cdeg 
                self.parent.db_write("VS", msg.vz *  1.96850394)      # int16_t cm/s to ft/min
                self.parent.db_write("AGL", msg.relative_alt / 304.8) # int32_t mm to ft
                self.parent.db_write("ALT", msg.alt / 304.8)          # int32_t mm to ft
            if self._gps:
                self.parent.db_write("LAT",msg.lat/10000000.0)        # int32_t degE7 10**7
                self.parent.db_write("LONG",msg.lon/10000000.0)       # int32_t degE7 10**7
        elif msg_type == "SCALED_PRESSURE":
            if self._pressure:
                self.parent.db_write("AIRPRESS", msg.press_abs * 100)       # float hPa to Pa 
                self.parent.db_write("DIFFAIRPRESS", msg.press_diff * 100)  # float hPa to Pa
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
              # Or having this set could be useful from APMODE old           
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
                  self.parent.db_write("APMODE", "UNKNOWN")
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
            self.parent.db_write("APMODE", mode) 

    def sendMode(self,mode,msg):
        self.parent.db_write("APMODE", mode)
        self.parent.db_write("APMSG", msg)


    def setStat(self,stat,msg=None):
        self.parent.db_write("APSTAT", stat)
        self._apstat = stat
        if msg:
            self.parent.db_write("APMSG", msg)


    def sendTrims(self):
        # TODO I suspect we do not want to send trims sometimes.
        # Also, we need to send only zero when in modes other than TRIM
        # Unless the pilot is wanting to change course/altitude.
        # Seems like some non-latching three position toggle switches
        # might work well
        # Pilot could hold up/down to change altitude or 
        # hold right/left to change heading
        # Once on heading let go of switch and AP will maintain
        self.conn.mav.manual_control_send(
            self.conn.target_system,
            self.parent.db_read("TRIMP")[0], #pitch
            self.parent.db_read("TRIMR")[0], #roll
            0, #Throttle
            self.parent.db_read("TRIMY")[0], #Yaw
            0
        )

    def checkMode(self):
        self.checkWaypoint()
        # Check if a mode change has been requested
        if self._apreq != self.parent.db_read("APREQ")[0]\
           and self.parent.db_read("APREQ")[0] != 'INIT':
            # Set the mode
            self.setMode(self.parent.db_read("APREQ")[0])

    def checkWaypoint(self):
        # We need to take actions when the waypoint changes or is deleted
        # For example, if the pilot deletes the flight plan or communication is lost
        # with whatever is providing the waypoints.
        if self.parent.db_read('WPLAT')[2] or self.parent.db_read('WPLON')[2] or (self.parent.db_read('WPLAT')[0] == 0.0 or self.parent.db_read('WPLON')[0] == 0.0):
            # The WPLAT/LON are old or not set
            # IF we are in GUIDED mode we want to drop to CRUISE mode
            if self._apreq == 'GUIDED':
                # drop to CRUISE mode ( Heading Hold )
                self.setMode('CRUISE')
                self.parent.db_write('APMSG', "Drop to Heading Hold")
                # Invalidate the waypoint
            self._apwpv = False
            return
        else:
            # We do have a valid waypoint
            self._apwpv = True
            # Did the waypoint change?
            if self._waypoint != f"{self.parent.db_read('WPLON')[0]}{self.parent.db_read('WPLAT')[0]}{self.parent.db_read('WPNAME')[0]}" and self._apmode == 'GUIDED':
                self.setMode('GUIDED')
 
    def setMode(self, mode):
        # Can we set that mode?
        if self._apstat in ['TRIM','ARMED'] and mode in self._apmodes:
            if mode not in ['TRIM'] and (( mode == 'GUIDED' and not self._apwpv) or (self._apstat != 'ARMED')):
                # Cruise mode requested but we are not armed
                # or do not have a valid waypoint
                
                self.parent.db_write("APMSG", "Invalid Request")
                # This will disrupt AHRS
                # TODO Maybe we need a better way to inform the pilot to the change?
                time.sleep(3)
                self.parent.db_write("APREQ", self._apmode)
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
            self.parent.db_write("APREQ", mode)
            self.parent.db_write("APMODE", mode)
            self._apmode = mode
        else:
            # TODO Likely need more logic here
            pass 


