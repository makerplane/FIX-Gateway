=========================
rpi_virtualwire plugins
=========================

Class to send and receive radio messages compatible with the Virtual Wire library for Arduinos. This library is commonly used with 313MHz and 434MHz radio tranceivers.

This plugins is a complex hardware and software configuration. See in Arduino folder to see the code. 

* TODO : Create a <How to> to explain how to reproduce this little device

Configuration
--------------------

* [conn_virtualwire]
* load = yes
* module = plugins.rpi_virtualwire
* rxpin = 23 # GPIO pin
* bps = 2000 # Bits per second (bps).  The bps defaults to 2000.

Independency installation 
--------------------

* http://abyz.co.uk/rpi/pigpio/

* rm pigpio.zip
* sudo rm -rf PIGPIO
* wget abyz.co.uk/rpi/pigpio/pigpio.zip
* unzip pigpio.zip
* cd PIGPIO
* make -j4
* sudo make install