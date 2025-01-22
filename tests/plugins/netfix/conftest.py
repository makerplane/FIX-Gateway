import pytest
import fixgw.plugins.netfix
from collections import namedtuple
import yaml
import time
import socket

@pytest.fixture
def db_config():
    return """
variables:
  e: 1  # Engines
  c: 6  # Cylinders
  a: 8  # Generic Analogs
  b: 16 # Generic Buttons
  r: 1  # Encoders
  t: 2  # Fuel Tanks

entries:
- key: ANLGa
  description: Generic Analog %a
  type: float
  min: 0.0
  max: 1.0
  units: '%/100'
  initial: 0.0
  tol: 2000

- key: BTNb
  description: Generic Button %b
  type: bool
  tol: 0

- key: ENCr
  description: Generic Encoder %r
  type: int
  min: -32768
  max: 32767
  units: Pulses
  initial: 0
  tol: 0

- key: IAS
  description: Indicated Airspeed
  type: float
  min: 0.0
  max: 1000.0
  units: knots
  initial: 0.0
  tol: 2000
  aux: [Min,Max,V1,V2,Vne,Vfe,Vmc,Va,Vno,Vs,Vs0,Vx,Vy]

- key: ALT
  description: Indicated Altitude
  type: float
  min: -1000.0
  max: 60000.0
  units: ft
  initial: 0.0
  tol: 2000

- key: BARO
  description: Altimeter Setting
  type: float
  min: 0.0
  max: 35.0
  units: inHg
  initial: 29.92
  tol: 2000

- key: ROLL
  description: Roll Angle
  type: float
  min: -180.0
  max: 180.0
  units: deg
  initial: 0.0
  tol: 200

- key: PITCH
  description: Pitch Angle
  type: float
  min: -90.0
  max: 90.0
  units: deg
  initial: 0.0
  tol: 200

- key: AOA
  description: Angle of attack
  type: float
  min: -180.0
  max: 180.0
  units: deg
  initial: 0.0
  tol: 200
  aux:
  - Min
  - Max
  - 0g
  - Warn
  - Stall

- key: OILPe
  description: Oil Pressure Engine %e
  type: float
  min: 0.0
  max: 200.0
  units: psi
  initial: 0.0
  tol: 2000
  aux: [Min,Max,lowWarn,highWarn,lowAlarm,highAlarm]

- key: TIMEZ
  description: Zulu Time String
  type: str
  tol: 2000

- key: ACID
  description: Aircraft ID
  type: str

- key: ZZLOADER
  description: MUST always be the last key listed here. It is read by client applications to ensure all db items have been init before proceeding to prevent race conditions.
  type: str
  initial: "Loaded"
"""

@pytest.fixture
def netfix_config():
    return """
type: server
host: 0.0.0.0
port: 34901
buffer_size: 1024
timeout: 1.0
"""


Objects = namedtuple(
    "Objects",
    ["pl", "sock"],
)


@pytest.fixture
def plugin(netfix_config,database):

    nc = yaml.safe_load(netfix_config)

    pl = fixgw.plugins.netfix.Plugin("netfix", nc)
    pl.start()
    time.sleep(0.1)  # Give plugin a chance to get started
    # Grab a client socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.settimeout(1.0)
    sock.connect(("127.0.0.1", 34901))

    yield Objects(
        pl=pl,
        sock=sock
    )
    sock.shutdown(socket.SHUT_RDWR)
    sock.close()
    pl.stop()

