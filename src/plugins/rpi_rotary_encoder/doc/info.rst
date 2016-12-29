=========================
rpi_rotary_encoder plugins
=========================

This plugins is a small python script to handle a rotary encoder with or without push button. You can use push button to handle 2 setting. You can adjust start setting point and the increment for bolt KEY

TODO : Create a menu navigator like Garmin GNC or GNS series.

Configuration
-------------------

[conn_rotary_encoder]
load = yes
module = plugins.rpi_rotary_encoder
btn = True # Enable push button
btnkey = BARO # when the push button is pressed this KEY change with the rotary encoder
btnstcounter = 29.92 # start setting point when the push button is pressed
btnincr = 0.01 # Each click increment
btnpin = 4 # GPIO pin
pina = 26 #encoder GPIO pin_a
pinb = 19 #encoder GPIO pin_b
stcount = 0 # Standard start point
rkey = PITCHSET # KEY change with the rotary encoder
incr = 1 # Each click increment
