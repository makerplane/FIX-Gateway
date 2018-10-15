=========================
rpi_rotary_encoder Plugin
=========================

This plugins is a small python script to handle a rotary encoder with or without push button. You can use push button to handle 2 setting. You can adjust start setting point and the increment for bolt KEY

* TODO : Create a menu navigator like Garmin GNC or GNS series.

Requirements
--------------

Python's RPi.GPIO Library


Configuration
-------------------

::

  rotary_encoder:
    load: yes
    module: plugins.rpi_rotary_encoder
    btn: True
    btnkey: BARO
    btnstcounter: 29.92
    btnincr: 0.01
    btnpin: 4
    pina: 26
    pinb: 19
    stcount: 0
    rkey: PITCHSET
    incr: 1
