====================================
FIX Gateway Database Key Definitions
====================================

Lower case letters indicate where numbers would be.  For example
EGTec  would look like EGT14 for the fourth EGT on engine 1.

======= ======================== ====== ============== =======
Key     Description              Type   Range          Notes
======= ======================== ====== ============== =======
IAS     Indicated Airspeed       float  0-1,000        knots
TAS     True Airspeed            float  0-2,000        knots
CAS     True Airspeed            float  0-2,000        knots
ALT     Indicated Altitude       float  -1,000-60,000  ft
TALT    True Altitude            float  -1,000-60,000  ft
DALT    Density Altitude         float  -1,000-60,000  ft
BARO    Altimeter Setting        float  0-35           inHg
OAT     Outside Air Temperature  float  -300-300       deg C
ROLL    Roll Angle               float  -180-180       deg
PITCH   Pitch Angle              float  -180-180       deg
YAW     Yaw Angle                float  -180-180       deg
AOA     Angle of attack          float  -180-180       deg
CTLPTCH Pitch Control            float  -1-1           %/100
CTLROLL Roll Control             float  -1-1           %/100
CTLYAW  Yaw Control (Rudder)     float  -1-1           %/100
CTLCOLL Collective Control       float  -1-1           %/100
CTLATP  AntiTorque Pedal Ctrl    float  -1-1           %/100
CTLFLAP Flap Control             float  -1-1           %/100
CTLLBRK Left Brake Control       float   0-1           %/100
CTLRBRK Right Brake Control      float   0-1           %/100
THRe    Throttle Control         float   0-1           %/100
PROPe   Prop Control             float   0-1           %/100
MIXe    Mixture Control          float   0-1           %/100
======= ======================== ====== ============== =======
