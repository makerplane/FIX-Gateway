#!/usr/bin/env python3

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
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


import http.server
import socketserver

PORT = 80

roll = 0
droll = 0.15
pitch = 0
dpitch = 0.1
lat = 29.7
long = -95.4

getSituation = """{{
  "GPSLastFixSinceMidnightUTC": 67337.6,
  "GPSLatitude": {LAT},
  "GPSLongitude": {LONG},
  "GPSFixQuality": 4,
  "GPSHeightAboveEllipsoid": 115.51,
  "GPSGeoidSep": -17.523,
  "GPSSatellites": 5,
  "GPSSatellitesTracked": 11,
  "GPSSatellitesSeen": 8,
  "GPSHorizontalAccuracy": 10.2,
  "GPSNACp": 9,
  "GPSAltitudeMSL": 170.10767,
  "GPSVerticalAccuracy": 8,
  "GPSVerticalSpeed": -0.6135171,
  "GPSLastFixLocalTime": "0001-01-01T00:06:44.24Z",
  "GPSTrueCourse": 0,
  "GPSTurnRate": 0,
  "GPSGroundSpeed": 0.77598433056951,
  "GPSLastGroundTrackTime": "0001-01-01T00:06:44.24Z",
  "GPSTime": "2017-09-26T18:42:17Z",
  "GPSLastGPSTimeStratuxTime": "0001-01-01T00:06:43.65Z",
  "GPSLastValidNMEAMessageTime": "0001-01-01T00:06:44.24Z",
  "GPSLastValidNMEAMessage": "$PUBX,04,184426.00,260917,240266.00,1968,18,-177618,-952.368,21*1A",
  "GPSPositionSampleRate": 0,
  "BaroTemperature": 37.02,
  "BaroPressureAltitude": 153.32,
  "BaroVerticalSpeed": 1.3123479,
  "BaroLastMeasurementTime": "0001-01-01T00:06:44.23Z",
  "AHRSPitch": {PITCH},
  "AHRSRoll": {ROLL},
  "AHRSGyroHeading": 187741.08073052,
  "AHRSMagHeading": 3276.7,
  "AHRSSlipSkid": 0.52267604604907,
  "AHRSTurnRate": 3276.7,
  "AHRSGLoad": 0.99847599584255,
  "AHRSGLoadMin": 0.99815989027411,
  "AHRSGLoadMax": 1.0043409597397,
  "AHRSLastAttitudeTime": "0001-01-01T00:06:44.28Z",
  "AHRSStatus": 7
}}"""

class TestHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        global pitch, roll, dpitch, droll, lat, long
        self.close_connection = True
        if(self.path == "/getSituation"):
            self.send_response(200)
            self.send_header('Content-type','application/json')
            self.end_headers()
            pitch += dpitch
            roll += droll
            if(pitch > 10): dpitch = -0.1
            if(pitch < -10): dpitch = 0.1
            if(roll > 10): droll = -0.15
            if(roll < -10): droll = 0.15
            lat += 0.01
            long += 0.015
            s = getSituation.format(PITCH=pitch, ROLL=roll, LAT=lat, LONG=long)
            self.wfile.write(s.encode())
        else:
            self.send_error(404)

#sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

with socketserver.TCPServer(("", PORT), TestHandler) as httpd:
    print("serving at port", PORT)
    httpd.serve_forever()
