=============================
Net-FIX Protocol Plugin
=============================

Net-FIX is the TCP/IP implementation of the FIX protocol suite.  There will be two versions of
this protocol set ASCII and Binary.  Currently this plugin only deals with the ASCII version of
the protocol.  [1]_

.. [1] The binary version hasn't even been invented yet.

Currently only the server side is implemented.

Net-FIX is the main way in which we connect FIX-Gateway to the pyEFIS program.  Net-FIX/ASCII is
currently the only communication mechanism that pyEFIS understands.  In fact FIX-Gateway was
written specifically to remove the complexities of multiple communications and data gathering
mechanisms from pyEFIS.

Configuration
--------------

::

  # Network FIX Protocol Interface
  [conn_netfix]
  load = yes
  module = plugins.netfix
  type = server  # Only the server is implemented at this time
  host = 0.0.0.0
  port = 3490
  buffer_size = 1024
  timeout = 1.0



