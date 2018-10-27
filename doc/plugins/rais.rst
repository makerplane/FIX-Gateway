====================================================
RAIS (Redundant Array of Inexpensive Sensors) plugin
====================================================

This FIX gateway plugin takes the output of a RAIS flight sensor pipeline
and updates the database with the following keys:

- ROLL
- PITCH
- ALT
- IAS
- VS
- HEAD
- GS
- TRACK
- TRACKM
- YAW
- LAT
- LONG
- TIMEZ


The project with RAIS functionality is found at:

https://github.com/Maker42/openEFIS

Configuration
=========================

There are 3 configuration keys needed by the RAIS plugin:

1. rais_directory -- The directory where the openEFIS code is installed
2. rais_server_module = RAIS    Don't change this unless you're sure you know what you're doing
3. rais_config_path (Optional) The path to the .yml file representing the pubsub configuration for RAIS.
