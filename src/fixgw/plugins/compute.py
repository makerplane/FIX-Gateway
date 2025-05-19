#!/usr/bin/env python3

#  Copyright (c) 2018 Phil Birkelbach
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307,
#  USA.import plugin

#  This is a compute plugin.  It calculates derivative points like averages,
#  minimums or maximums and the like.  Specific calculations for things like
#  True Airspeed could be done also.

import fixgw.plugin as plugin
from fixgw.database import read
import fixgw.quorum as quorum

# Determine pressure altitude
# inputs: BARO, ALTMSL
# Pressure Altitude = Elevation  in FT + (145442.2 * ( 1 - ( altimeter setting in inhg/29.92126)^.190261))


def altPressure(inputs, output, require_leader):
    vals = {}
    for each in inputs:
        vals[each] = None

    def func(key, value, parent):
        if not quorum.leader and require_leader:
            return  # Only the leader can do calculations
        # This is to set the aux data in the output to one of the inputs
        o = parent.db_get_item(output)
        if type(value) != tuple:
            x = key.split(".")
            # we use the first input in the list to set the aux values
            if x[0] == inputs[0]:
                if o.get_aux_value(x[1]) != value:
                    o.set_aux_value(x[1], value)
            return
        vals[key] = value
        flag_old = False
        flag_bad = False
        flag_fail = False
        flag_secfail = False
        pa = None
        for each in vals:
            if vals[each] is None:
                return  # We don't have one of each yet
            if vals[each][2]:
                flag_old = True
            if vals[each][3]:
                flag_bad = True
            if vals[each][4]:
                flag_fail = True
            if vals[each][5]:
                flag_secfail = True

        baro = list(vals)[0]
        msl = list(vals)[1]
        pa = vals[msl][0] + (145442.2 * (1 - (vals[baro][0] / 29.92126) ** 0.190261))
        o.value = pa
        o.fail = flag_fail
        if o.fail:
            o.value = 0.0
        o.bad = flag_bad
        o.old = flag_old
        o.secfail = flag_secfail

    return func


# Density altitude
# Standard Temperature = 15 – 1.98 * (A in ft) /1000
# Density Altitude = Pressure Altitude + (120 * (OAT deg C - Standard Temperature))
# inputs PALT ALTMSL OAT
def altDensity(inputs, output, require_leader):
    vals = {}
    for each in inputs:
        vals[each] = None

    def func(key, value, parent):
        if not quorum.leader and require_leader:
            return  # Only the leader can do calculations
        # This is to set the aux data in the output to one of the inputs
        o = parent.db_get_item(output)
        if type(value) != tuple:
            x = key.split(".")
            # we use the first input in the list to set the aux values
            if x[0] == inputs[0]:
                if o.get_aux_value(x[1]) != value:
                    o.set_aux_value(x[1], value)
            return
        vals[key] = value
        flag_old = False
        flag_bad = False
        flag_fail = False
        flag_secfail = False
        da = None
        for each in vals:
            if vals[each] is None:
                return  # We don't have one of each yet
            if vals[each][2]:
                flag_old = True
            if vals[each][3]:
                flag_bad = True
            if vals[each][4]:
                flag_fail = True
            if vals[each][5]:
                flag_secfail = True
        palt = list(vals)[0]
        talt = list(vals)[1]
        oat = list(vals)[2]
        st = 15 - (1.98 * (vals[talt][0]) / 1000)
        da = vals[palt][0] + (120 * (vals[oat][0] - st))
        o.value = da
        o.fail = flag_fail
        if o.fail:
            o.value = 0.0
        o.bad = flag_bad
        o.old = flag_old
        o.secfail = flag_secfail

    return func


# Determines the average of the inputs and writes that to output
def averageFunction(inputs, output, require_leader):
    vals = {}
    for each in inputs:
        vals[each] = None

    def func(key, value, parent):
        if not quorum.leader and require_leader:
            return  # Only the leader can do calculations
        o = parent.db_get_item(output)
        # This is to set the aux data in the output to one of the inputs
        if type(value) != tuple:
            x = key.split(".")
            # we use the first input in the list to set the aux values
            if x[0] == inputs[0]:
                if o.get_aux_value(x[1]) != value:
                    o.set_aux_value(x[1], value)
            return

        vals[key] = value
        arrsum = 0
        flag_old = False
        flag_bad = False
        flag_fail = False
        flag_secfail = False
        for each in vals:
            if vals[each] is None:
                return  # We don't have one of each yet
            arrsum += vals[each][0]
            if vals[each][2]:
                flag_old = True
            if vals[each][3]:
                flag_bad = True
            if vals[each][4]:
                flag_fail = True
            if vals[each][5]:
                flag_secfail = True
        o.value = arrsum / len(vals)
        o.fail = flag_fail
        if o.fail:
            o.value = 0.0
        o.bad = flag_bad
        o.old = flag_old
        o.secfail = flag_secfail

    return func


def encoderFunction(inputs, output, multiplier, require_leader):
    """Multiplies the input by the multiplier and adds the result to the output"""

    def func(key, value, parent):
        if type(value) != tuple:
            return  # This might be a meta data update
        if not quorum.leader and require_leader:
            return  # Only the leader can do calculations

        o = parent.db_get_item(output)
        try:
            total = (value[0] * multiplier) + o.value[0]
        except TypeError:
            print(f"WTF Encoder output {output}")
            raise
        o.value = total

    return func


def setFunction(inputs, output, val, require_leader):
    """When fixids in inputs are True, set to output to val"""

    def func(key, value, parent):
        if type(value) != tuple:
            return  # This might be a meta data update
        if not quorum.leader and require_leader:
            return  # Only the leader can do calculations
        if value[0]:
            o = parent.db_get_item(output)
            o.value = val

    return func


def sumFunction(inputs, output, require_leader):
    """Determines the sum of the inputs and writes that to output"""
    vals = {}
    for each in inputs:
        vals[each] = None

    def func(key, value, parent):
        if type(value) != tuple:
            return  # This might be a meta data update
        if not quorum.leader and require_leader:
            return  # Only the leader can do calculations

        vals[key] = value
        arrsum = 0
        flag_old = False
        flag_bad = False
        flag_fail = False
        flag_secfail = False
        for each in vals:
            if vals[each] is None:
                return  # We don't have one of each yet
            try:
                arrsum += vals[each][0]
                if vals[each][2]:
                    flag_old = True
                if vals[each][3]:
                    flag_bad = True
                if vals[each][4]:
                    flag_fail = True
                if vals[each][5]:
                    flag_secfail = True
            except TypeError:
                print("WTF {} {}".format(key, value))
                raise
        o = parent.db_get_item(output)
        o.value = arrsum
        o.fail = flag_fail
        if o.fail:
            o.value = 0.0
        o.bad = flag_bad
        o.old = flag_old
        o.secfail = flag_secfail

    return func


# Determines the max of the inputs and writes that to output
def maxFunction(inputs, output, require_leader):
    vals = {}
    for each in inputs:
        vals[each] = None

    def func(key, value, parent):
        if not quorum.leader and require_leader:
            return  # Only the leader can do calculations
        # This is to set the aux data in the output to one of the inputs
        o = parent.db_get_item(output)
        if type(value) != tuple:
            x = key.split(".")
            # we use the first input in the list to set the aux values
            if x[0] == inputs[0]:
                if o.get_aux_value(x[1]) != value:
                    o.set_aux_value(x[1], value)
            return
        vals[key] = value
        flag_old = False
        flag_bad = False
        flag_fail = False
        flag_secfail = False
        vmax = None
        for each in vals:
            if vals[each] is None:
                return  # We don't have one of each yet
            if vmax:
                if vals[each][0] > vmax:
                    vmax = vals[each][0]
            else:  # The first time through we just set vmax to the value
                vmax = vals[each][0]
            if vals[each][2]:
                flag_old = True
            if vals[each][3]:
                flag_bad = True
            if vals[each][4]:
                flag_fail = True
            if vals[each][5]:
                flag_secfail = True
        o.value = vmax
        o.fail = flag_fail
        if o.fail:
            o.value = 0.0
        o.bad = flag_bad
        o.old = flag_old
        o.secfail = flag_secfail

    return func


# Determines the min of the inputs and writes that to output
def minFunction(inputs, output, require_leader):
    vals = {}
    for each in inputs:
        vals[each] = None

    def func(key, value, parent):
        if not quorum.leader and require_leader:
            return  # Only the leader can do calculations
        # This is to set the aux data in the output to one of the inputs
        o = parent.db_get_item(output)
        if type(value) != tuple:
            x = key.split(".")
            # we use the first input in the list to set the aux values
            if x[0] == inputs[0]:
                if o.get_aux_value(x[1]) != value:
                    o.set_aux_value(x[1], value)
            return
        vals[key] = value
        flag_old = False
        flag_bad = False
        flag_fail = False
        flag_secfail = False
        vmin = None
        for each in vals:
            if vals[each] is None:
                return  # We don't have one of each yet
            if vmin:
                if vals[each][0] < vmin:
                    vmin = vals[each][0]
            else:  # The first time through we just set vmax to the value
                vmin = vals[each][0]
            if vals[each][2]:
                flag_old = True
            if vals[each][3]:
                flag_bad = True
            if vals[each][4]:
                flag_fail = True
            if vals[each][5]:
                flag_secfail = True
        o.value = vmin
        o.fail = flag_fail
        if o.fail:
            o.value = 0.0
        o.bad = flag_bad
        o.old = flag_old
        o.secfail = flag_secfail

    return func


# Determines the span between the highest and lowest of the inputs
# and writes that to output
def spanFunction(inputs, output, require_leader):
    vals = {}
    for each in inputs:
        vals[each] = None

    def func(key, value, parent):
        if not quorum.leader and require_leader:
            return  # Only the leader can do calculations
        if type(value) != tuple:
            return  # This might be a meta data update
        vals[key] = value
        flag_old = False
        flag_bad = False
        flag_fail = False
        flag_secfail = False
        vmin = None
        vmax = None
        for each in vals:
            if vals[each] is None:
                return  # We don't have one of each yet
            if vmin is not None:
                if vals[each][0] < vmin:
                    vmin = vals[each][0]
                if vals[each][0] > vmax:
                    vmax = vals[each][0]
            else:  # The first time through we just set vmax to the value
                vmin = vals[each][0]
                vmax = vals[each][0]

            if vals[each][2]:
                flag_old = True
            if vals[each][3]:
                flag_bad = True
            if vals[each][4]:
                flag_fail = True
            if vals[each][5]:
                flag_secfail = True
        o = parent.db_get_item(output)
        o.value = vmax - vmin
        o.fail = flag_fail
        if o.fail:
            o.value = 0.0
        o.bad = flag_bad
        o.old = flag_old
        o.secfail = flag_secfail

    return func


AOA_pitch_history = list()
AOA_ias_history = list()
AOA_acc_history = list()
AOA_vs_history = list()
AOA_heading_history = list()
AOA_lift_constant = None


def AOAFunction(inputs, output, require_leader):
    vals = {}
    # pitch_root: the pitch of the wing relative to the aircraft at the root
    (
        AOA_pitch_root,
        AOA_smooth_min_len,
        AOA_max_mean_vs,
        AOA_max_vs_dev,
        AOA_max_vs_trend,
        AOA_max_heading_dev,
        AOA_max_heading_trend,
        AOA_max_pitch_dev,
        AOA_max_pitch_trend,
    ) = inputs[5:]
    AOA_hist_count = 0
    for each in inputs[:5]:
        vals[each] = None

    def func(key, value, parent):
        if not quorum.leader and require_leader:
            return  # Only the leader can do calculations
        global AOA_lift_constant
        nonlocal AOA_hist_count
        if not isinstance(key, str):
            return
        # This is to set the aux data in the output to one of the inputs
        o = parent.db_get_item(output)
        vals[key] = value
        Vs = read("IAS.Vs")
        if Vs is None:
            Vs = 9999
        #
        # Accumulate history values for estimating a lift constant
        #
        if key == "PITCH":
            AOA_pitch_history.append(value[0])
            if len(AOA_pitch_history) > AOA_smooth_min_len:
                del AOA_pitch_history[0]
        if key == "IAS":
            AOA_ias_history.append(value[0])
            if len(AOA_ias_history) > AOA_smooth_min_len:
                del AOA_ias_history[0]
        if key == "ANORM":
            AOA_acc_history.append(value[0])
            if len(AOA_acc_history) > AOA_smooth_min_len:
                del AOA_acc_history[0]
        if key == "VS":
            AOA_vs_history.append(value[0])
            if len(AOA_vs_history) > AOA_smooth_min_len:
                del AOA_vs_history[0]
            AOA_hist_count += 1
        if key == "HEAD":
            AOA_heading_history.append(value[0])
            if len(AOA_heading_history) > AOA_smooth_min_len:
                del AOA_heading_history[0]
        #
        # Restart value history accumulation if any input is
        # not perfect quality
        #
        for each in vals:
            ve = vals[each]
            if not isinstance(ve, tuple):
                continue
            if ve is None:
                AOA_hist_count = 0
                break
            if ve[2]:
                AOA_hist_count = 0
                break
            if ve[3]:
                AOA_hist_count = 0
                break
            if ve[4]:
                AOA_hist_count = 0
                break
            if ve[5]:
                AOA_hist_count = 0
                break
        #
        # Compute AOA, one way or another
        #
        if len(AOA_ias_history):
            ias = AOA_ias_history[-1]
        else:
            ias = 0
        if AOA_lift_constant is not None and ias > Vs:
            # We're flying with a known lift constant, so compute alpha directly
            AOA_pitch_0 = read("AOA.0g")
            # Alpha (AOA) = lift_constant * acc[NORMAL/Z axis] / ias^2 -
            #               AOA_pitch_0
            o.value = (
                AOA_lift_constant * AOA_acc_history[-1] / (ias * ias) - AOA_pitch_0
            )
            flag_old = False
            flag_bad = False
            flag_fail = False
            flag_secfail = False
            for each in ["IAS", "ANORM"]:
                if vals[each] is None:
                    flag_fail = True
                if vals[each][2]:
                    flag_old = True
                if vals[each][3]:
                    flag_bad = True
                if vals[each][4]:
                    flag_fail = True
                if vals[each][5]:
                    flag_secfail = True
            o.old = flag_old
            o.bad = flag_bad
            o.fail = flag_fail
            o.secfail = flag_secfail
            if flag_old or flag_bad or flag_fail or flag_secfail:
                AOA_hist_count = 0
        elif ias < Vs and vals["PITCH"] is not None:
            # Give an answer for taxi'ing and/or takeoff roll
            pitch = vals["PITCH"]
            o.value = AOA_pitch_root + pitch[0]
            o.old, o.bad, o.fail, o.secfail = pitch[2:]
            # Since we're taxi'ing, we might have just refueled,
            # or changed the weight and balance, which drastically changes
            # the lift constant. Mark it as unknown to re-estimate
            # when possible.
            AOA_lift_constant = None
        elif vals["PITCH"] is not None:
            # Flying, but the lift constant is not yet established.
            # Give a guesstimate
            pitch = vals["PITCH"]
            o.value = AOA_pitch_root + pitch[0]
            o.old = pitch[2]
            o.bad = True
            o.fail = pitch[4]
        else:
            # We're not getting any basic data. Fail out.
            o.fail = True
        #
        # Update lift constant, if possible
        #
        if (
            AOA_hist_count > AOA_smooth_min_len
            and len(AOA_vs_history)
            and len(AOA_ias_history)
        ):
            # Check if we've been straight and level for a sufficient time
            AOA_hist_count = 0
            mean_vs = sum(AOA_vs_history) / len(AOA_vs_history)
            if (
                mean_vs < AOA_max_mean_vs
                and is_calm(AOA_vs_history, AOA_max_vs_dev, AOA_max_vs_trend)
                and is_calm(AOA_pitch_history, AOA_max_pitch_dev, AOA_max_pitch_trend)
                and is_calm(
                    AOA_heading_history,
                    AOA_max_heading_dev,
                    AOA_max_heading_trend,
                    wrap=360,
                )
            ):
                # Flying straight and level! We can estimate a lift constant
                acc_mean = sum(AOA_acc_history) / len(AOA_acc_history)
                ias_mean = sum(AOA_ias_history) / len(AOA_ias_history)
                pitch_mean = sum(AOA_pitch_history) / len(AOA_pitch_history)
                AOA_pitch_0 = read("AOA.0g")
                # The steady state angle of attack at wing root
                # Alpha [steady state] + AOA_pitch_0 = lift_constant * acc[NORMAL/Z axis] / ias^2
                alpha_ss = pitch_mean + AOA_pitch_root
                # (Alpha [steady state] + AOA_pitch_0) * ias^2 = lift_constant * acc
                # lift_constant = (Alpha [steady state] + AOA_pitch_0) * ias^2 / acc
                new_lift_constant = (
                    (alpha_ss + AOA_pitch_0) * ias_mean * ias_mean / acc_mean
                )
                if AOA_lift_constant is None:
                    AOA_lift_constant = new_lift_constant
                else:
                    filter_coefficient = 0.9
                    anti_filter_coefficient = 1 - filter_coefficient
                    AOA_lift_constant = (
                        new_lift_constant * anti_filter_coefficient
                        + AOA_lift_constant * filter_coefficient
                    )
                print("AOA estimation lift constant %g" % AOA_lift_constant)

    return func


def is_calm(samples, max_sample_dev, max_trend_dev, end_size=10, wrap=None):
    if wrap is None:
        mean = sum(samples) / len(samples)
        deviation = [abs(x - mean) for x in samples]
    else:
        mean = mean_wrap(samples, wrap)
        deviation = [abs_wrap(x, mean, wrap) for x in samples]
    deviation = max(deviation)
    end_count = int(round(float(len(samples)) * float(end_size) / 100.0))
    if end_count > 0:
        end_mean = sum(samples[-end_count:]) / end_count
        beg_mean = sum(samples[:end_count]) / end_count
        trend = abs(end_mean - beg_mean)
    else:
        trend = 0
    return deviation < max_sample_dev and trend < max_trend_dev


def mean_wrap(samples, wrap):
    standard = samples[0]
    sm = 0
    for s in samples:
        diff = s - standard
        if diff > wrap / 2:
            sm += s - wrap
        elif diff < -wrap / 2:
            sm += s + wrap
        else:
            sm += s
    ret = sm / len(samples)
    if ret < 0:
        ret += wrap
    elif ret >= wrap:
        ret -= wrap
    return ret


def abs_wrap(x, mean, wrap):
    diff = x - mean
    if diff > wrap / 2:
        diff -= wrap
    elif diff < -wrap / 2:
        diff += wrap
    return abs(diff)


class Plugin(plugin.PluginBase):
    # def __init__(self, name, config):
    #     super(Plugin, self).__init__(name, config)

    def run(self):
        # This directory of functions are functions that aggregate a list
        # of inputs and produce a single output.
        aggregate_functions = {
            "average": averageFunction,
            "sum": sumFunction,
            "max": maxFunction,
            "min": minFunction,
            "span": spanFunction,
            "aoa": AOAFunction,
            "altp": altPressure,
            "altd": altDensity,
            "encoder": encoderFunction,
            "set": setFunction,
        }

        for function in self.config["functions"]:
            req_lead = True
            if "require_leader" in function:
                if not function["require_leader"]:
                    req_lead = False

            fname = function["function"].lower()
            if fname in aggregate_functions:
                if fname == "encoder":
                    f = aggregate_functions[fname](
                        function["inputs"],
                        function["output"],
                        function["multiplier"],
                        req_lead,
                    )
                elif fname == "set":
                    f = aggregate_functions[fname](
                        function["inputs"],
                        function["output"],
                        function["value"],
                        req_lead,
                    )
                else:
                    f = aggregate_functions[fname](
                        function["inputs"], function["output"], req_lead
                    )
                for each in function["inputs"]:
                    if isinstance(each, str):
                        self.db_callback_add(each, f, self)

            else:
                self.log.warning("Unknown function - {}".format(function["function"]))

    def stop(self):
        pass

    # def get_status(self):
    #     """ The get_status method should return a dict or OrderedDict that
    #     is basically a key/value pair of statistics"""
    #     return OrderedDict({"Count":self.thread.count})


# TODO: Add a check for Warns and alarms and annunciate appropriatly
# TODO: Add tests for this plugin
# TODO: write stop function to remove all the callbacks
