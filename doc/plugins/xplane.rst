===================================
XPlane Flight Simulator Plugin
===================================

This plugin allows FIX-Gateway to be used to communicate to the very popular *X-Plane
Flight Simulator*

**This plugin lacks a lot of work and is not really usable in it's current state**


Configuration
--------------

::

  xplane:
    load: yes
    module: plugins.xplane
    # IP address where the X-Plane simulator is running
    ipaddress: 127.0.0.1
    # UDP Ports to use for sending and receiving data
    # These should match the configuration in the
    # "Net Connections" Menu of X-Plane
    udp_in: 49001   # Port to received data from X-Plane
    udp_out: 49002  # Port to send data to X-Plane

    # These are the X-Plane data indexes that we will write.  These
    # would match the
    #idx8 : CTLPTCH, CTLROLL, CTLYAW, x, x, x, x, x
    idx25: THR1,  THR2,  x, x, x, x, x, x
    #idx28: PROP1, PROP2, x, x, x, x, x, x
    idx29: MIX1,  MIX2,  x, x, x, x, x, x
