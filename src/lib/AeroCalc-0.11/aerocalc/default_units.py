#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) 2008, Kevin Horton
# All rights reserved.
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# *
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * The name of Kevin Horton may not be used to endorse or promote products
#       derived from this software without specific prior written permission.
# *
# THIS SOFTWARE IS PROVIDED BY KEVIN HORTON ``AS IS'' AND ANY EXPRESS OR
# IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
# EVENT SHALL KEVIN HORTON BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS;
# OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR
# OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF
# ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# #############################################################################
#
# version 0.10, 17 Mar 2008
#
# Version History:
# vers     date      Notes
# 0.10   17 Mar 08   Initial version.
# #############################################################################
#
# To Do: 1. Add option to use config file in user's home directory to override
#           default_units.py.
#
# #############################################################################

"""
Defines the default units to be used for various modules.
"""

default_area_units = 'ft**2'
default_avgas_units = 'lb'
default_density_units = 'lb/ft**3'
default_length_units = 'ft'
default_power_units = 'hp'
default_press_units = 'in HG'
default_speed_units = 'kt'
default_temp_units = 'C'
default_weight_units = 'lb'
default_vol_units = 'ft**3'

default_alt_units = default_length_units
