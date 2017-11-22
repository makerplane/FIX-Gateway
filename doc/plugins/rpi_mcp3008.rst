=========================
rpi_mcp3008 plugins
=========================

The MCP3008 is a low cost 8-channel 10-bit analog to digital converter.  The precision of this ADC is similar to that of an Arduino Uno, and with 8 channels you can read quite a few analog signals from the Pi.  This chip is a great option if you just need to read simple analog signals, like from a temperature or light sensor.


Configuration
-------------------

* [conn_mcp3008]
* load = yes
* module = plugins.rpi_mcp3008
* vkey1 = ANLG1 # mcp3008 pin 1 to KEY in database
* vkey2 = ANLG2
* vkey3 = ANLG3
* vkey4 = ANLG4
* vkey5 = ANLG5
* vkey6 = ANLG6
* vkey7 = ANLG7
* vkey8 = ANLG8
* hardw = True # if you want to use hardware SPI or False for software SPI

Software SPI pin Not need if you use hardware SPI
--------------------
* clk = 18 # Software SPI clk pin 
* miso = 23 # Software SPI miso pin
* mosi = 24 # Software SPI mosi pin
* cs = 25 # Software SPI cs pin

Installation 
--------------------

* https://learn.adafruit.com/raspberry-pi-analog-to-digital-converters/mcp3008

* sudo apt-get update
* sudo apt-get install build-essential python-dev python-smbus git
* cd ~
* git clone https://github.com/adafruit/Adafruit_Python_MCP3008.git
* cd Adafruit_Python_MCP3008
* sudo python setup.py install
