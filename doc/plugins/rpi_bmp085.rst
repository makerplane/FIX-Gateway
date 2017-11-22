=========================
rpi_bmp085 Plugin
=========================

This precision sensor from Bosch is the best low-cost sensing solution for measuring barometric pressure and temperature. Because pressure changes with altitude you can also use it as an altimeter! The sensor is soldered onto a PCB with a 3.3V regulator, I2C level shifter and pull-up resistors on the I2C pins.

* Pressure sensing range: 300-1100 hPa (9000m to -500m above sea level)
* Up to 0.03hPa / 0.25m resolution
* -40 to +85°C operational range, +-2°C temperature accuracy



Installation 
--------------------

The Adafruit_BMP library is required to use this plugin

https://learn.adafruit.com/using-the-bmp085-with-raspberry-pi/using-the-adafruit-bmp085-python-library?view=all

::

  sudo apt-get update
  sudo apt-get install git build-essential python-dev python-smbus
  git clone https://github.com/adafruit/Adafruit_Python_BMP.git
  cd Adafruit_Python_BMP
  sudo python setup.py install


Configuration
-------------------

::

  [conn_bmp085]
  load = yes # yes or no
  module = plugins.rpi_bmp085 
  tkey = CAT # temperature KEY
  pkey = AIRPRESS # Air pressure KEY

  # Altitude result send directly to ALT KEY in feet


