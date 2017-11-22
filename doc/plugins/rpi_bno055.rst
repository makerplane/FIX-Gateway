=========================
rpi_bno055 plugins
=========================

If you've ever ordered and wire up a 9-DOF sensor, chances are you've also realized the challenge of turning the sensor data from an accelerometer, gyroscope and magnetometer into actual "3D space orientation"! Orientation is a hard problem to solve. The sensor fusion algorithms (the secret sauce that blends accelerometer, magnetometer and gyroscope data into stable three-axis orientation output) can be mind-numbingly difficult to get right and implement on low cost real time systems.

Bosch is the first company to get this right by taking a MEMS accelerometer, magnetometer and gyroscope and putting them on a single die with a high speed ARM Cortex-M0 based processor to digest all the sensor data, abstract the sensor fusion and real time requirements away, and spit out data you can use in quaternions, Euler angles or vectors.
  
Rather than spending weeks or months fiddling with algorithms of varying accuracy and complexity, you can have meaningful sensor data in minutes thanks to the BNO055 - a smart 9-DOF sensor that does the sensor fusion all on its own!


The BNO055 can output the following sensor data:


Absolute Orientation (Euler Vector, 100Hz)
*Three axis orientation data based on a 360° sphere

Absolute Orientation (Quaterion, 100Hz)
*Four point quaternion output for more accurate data manipulation

Angular Velocity Vector (100Hz)
*Three axis of 'rotation speed' in rad/s

Acceleration Vector (100Hz)
*Three axis of acceleration (gravity + linear motion) in m/s^2

Magnetic Field Strength Vector (20Hz)
*Three axis of magnetic field sensing in micro Tesla (uT)

Linear Acceleration Vector (100Hz)
*Three axis of linear acceleration data (acceleration minus gravity) in m/s^2

Gravity Vector (100Hz)
*Three axis of gravitational acceleration (minus any movement) in m/s^2

Temperature (1Hz)
*Ambient temperature in degrees celsius

But this plugins automatique put absolute orientation and acceleration data to database at +/-60Hz

Configuration
-------------------

* [conn_bno055] 
* load = yes
* module = plugins.rpi_bno055

Independency installation 
--------------------

https://learn.adafruit.com/bno055-absolute-orientation-sensor-with-raspberry-pi-and-beaglebone-black/hardware?view=all

* Disable the kernel serial port
* sudo apt-get update
* sudo apt-get install -y build-essential python-dev python-smbus python-pip git
* cd ~
* git clone https://github.com/adafruit/Adafruit_Python_BNO055.git
* cd Adafruit_Python_BNO055
* sudo python setup.py install
