=========================
rpi_button plugins
=========================

This plugins is a small python script to handle a momentary button. You can adjust the repeat delay or simply use the debouncing feature


Requirements
---------------

RPi.GPIO python package


Configuration
-------------------

::

  button1:
    load: yes
    module: plugins.rpi_button
    btnkey: BTN1
    btnpin: 4
    rdelay: 0 # 0 for debouncing or time in seconde to determine the repeat delay
