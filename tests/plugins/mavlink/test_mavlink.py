from types import SimpleNamespace
import importlib

import pytest

import fixgw.plugin as plugin_base
import fixgw.plugins.mavlink as mav_plugin

mav_module = importlib.import_module("fixgw.plugins.mavlink.Mav")


class FakeLog:
    def __init__(self):
        self.messages = []

    def debug(self, message):
        self.messages.append(message)


class FakeParent:
    def __init__(self):
        self.log = FakeLog()
        self.quorum = SimpleNamespace(leader=True)
        self.writes = []
        self.values = {
            "MAVREQADJ": (False, False, False, False, False, False),
            "MAVADJ": (False, False, False, False, False, False),
            "TRIMP": (1.0, False, False, False, False, False),
            "TRIMR": (2.0, False, False, False, False, False),
            "TRIMY": (3.0, False, False, False, False, False),
            "MAVREQTRIM": (False, False, False, False, False, False),
            "MAVREQCRUISE": (False, False, False, False, False, False),
            "MAVREQAUTOTUNE": (False, False, False, False, False, False),
            "MAVREQAUTO": (False, False, False, False, False, False),
            "MAVREQGUIDED": (False, False, False, False, False, False),
            "WPLAT": (40.0, False, False, False, False, False),
            "WPLON": (-88.0, False, False, False, False, False),
            "WPNAME": ("HOME", False, False, False, False, False),
            "ALT": (1000.0, False, False, False, False, False),
        }

    def db_write(self, key, value):
        self.writes.append((key, value))
        self.values[key] = (value, False, False, False, False, False)

    def db_read(self, key):
        return self.values.get(key, (0, False, False, False, False, False))


class FakeMavSender:
    def __init__(self):
        self.sent = []
        self.manual_controls = []
        self.long_commands = []
        self.int_commands = []

    def command_long_encode(self, *args):
        self.long_commands.append(args)
        return ("long", args)

    def command_int_encode(self, *args):
        self.int_commands.append(args)
        return ("int", args)

    def send(self, message):
        self.sent.append(message)

    def manual_control_send(self, *args):
        self.manual_controls.append(args)


class FakeConn:
    def __init__(self, messages=None, ack=None):
        self.messages = list(messages or [])
        self.ack = ack
        self.mav = FakeMavSender()
        self.target_system = 1
        self.target_component = 2
        self.closed = False
        self.heartbeat_waited = False

    def recv_match(self, **kwargs):
        if kwargs.get("type") == "COMMAND_ACK":
            return self.ack
        if self.messages:
            value = self.messages.pop(0)
            if isinstance(value, Exception):
                raise value
            return value
        return None

    def wait_heartbeat(self):
        self.heartbeat_waited = True

    def close(self):
        self.closed = True


class Msg(SimpleNamespace):
    def __init__(self, msg_type, **kwargs):
        super().__init__(**kwargs)
        self._msg_type = msg_type

    def get_type(self):
        return self._msg_type


def make_mav(messages=None, parent=None, options=None):
    mav = mav_module.Mav.__new__(mav_module.Mav)
    mav.parent = parent or FakeParent()
    mav._apreq = "INIT"
    mav._apstat = "TRIM"
    mav._apmode = "INIT"
    mav._apwpv = False
    mav._apmodes = {
        "TRIM": 0,
        "CRUISE": 7,
        "AUTOTUNE": 8,
        "AUTO": 10,
        "GUIDED": 15,
    }
    options = options or {
        "airspeed": True,
        "groundspeed": True,
        "gps": True,
        "ahrs": True,
        "accel": True,
        "pressure": True,
    }
    mav._airspeed = options.get("airspeed", False)
    mav._groundspeed = options.get("groundspeed", False)
    mav._gps = options.get("gps", False)
    mav._ahrs = options.get("ahrs", False)
    mav._accel = options.get("accel", False)
    mav._pressure = options.get("pressure", False)
    mav._pascal_offset = options.get("pascal_offset", 0)
    mav._min_airspeed = options.get("min_airspeed", 10)
    mav._outputPitch = 0
    mav._outputRoll = 0
    mav._outputYaw = 0
    mav._apAdjust = False
    mav._trimsSaved = False
    mav._trimsSavedRoll = 0
    mav._trimsSavedPitch = 0
    mav._trimsSavedYaw = 0
    mav._waypoint = str
    mav._interval = mav_module.defaultdict(lambda: 200000)
    mav._data = mav_module.defaultdict(list)
    mav._max_average = 15
    mav.ids = [101, 202]
    mav.conn = FakeConn(messages)
    mav.no_msg_count = 0
    return mav


def assert_write(parent, key, value):
    assert (key, value) in parent.writes


def test_constructor_requests_configured_ids_and_initializes(monkeypatch):
    ack = SimpleNamespace(
        command=mav_module.mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
        result=mav_module.mavutil.mavlink.MAV_RESULT_ACCEPTED,
    )
    conn = FakeConn(ack=ack)
    monkeypatch.setattr(mav_module, "stat", lambda _port: True)
    monkeypatch.setattr(mav_module.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(mav_module.mavutil, "mavlink_connection", lambda *_a, **_k: conn)
    parent = FakeParent()

    mav = mav_module.Mav(
        parent,
        port="/dev/fake",
        baud=115200,
        options={
            "airspeed": True,
            "groundspeed": True,
            "gps": True,
            "ahrs": True,
            "accel": True,
            "pressure": True,
            "pascal_offset": 12,
            "min_airspeed": 20,
        },
    )

    assert mav.conn is conn
    assert conn.mav.sent
    assert_write(parent, "ROLL", 0)
    assert_write(parent, "VS", 0)


def test_constructor_raises_when_port_missing(monkeypatch):
    parent = FakeParent()
    monkeypatch.setattr(mav_module, "stat", lambda _port: False)

    with pytest.raises(Exception, match="serial port /dev/missing is not found"):
        mav_module.Mav(parent, port="/dev/missing")

    assert_write(parent, "MAVSTATE", "ERROR")


def test_constructor_raises_when_second_port_check_fails(monkeypatch):
    parent = FakeParent()
    checks = [True, False]
    monkeypatch.setattr(mav_module, "stat", lambda _port: checks.pop(0))
    monkeypatch.setattr(mav_module.time, "sleep", lambda _seconds: None)

    with pytest.raises(Exception, match="serial port /dev/flaky is not found"):
        mav_module.Mav(parent, port="/dev/flaky")

    assert_write(parent, "MAVSTATE", "ERROR")


def test_request_ids_records_failed_ack_and_helpers_close_heartbeat(caplog):
    mav = make_mav()
    mav.conn.ack = SimpleNamespace(command=999, result=999)

    mav.request_ids()
    mav.wait_heartbeat()
    mav.close()

    assert len(mav.conn.mav.sent) == 2
    assert mav.conn.heartbeat_waited is True
    assert mav.conn.closed is True


def test_process_no_message_re_requests_ids_after_threshold(monkeypatch):
    mav = make_mav(messages=[None])
    calls = []
    mav.no_msg_count = 15
    mav.request_ids = lambda: calls.append("request")

    mav.process()

    assert calls == ["request"]
    assert mav.no_msg_count == 0


def test_process_vfr_hud_writes_speed_and_vertical_speed_paths():
    parent = FakeParent()
    mav = make_mav(
        parent=parent,
        messages=[
            Msg("VFR_HUD", airspeed=20.0, groundspeed=4.0, climb=1.25),
            Msg("VFR_HUD", airspeed=1.0, groundspeed=1.0, climb=0.0),
        ],
    )

    mav.process()
    mav.process()

    assert_write(parent, "IAS", 38.88)
    assert_write(parent, "GS", 7.78)
    assert_write(parent, "TAS", 38.88)
    assert_write(parent, "VS", 246)

    low_parent = FakeParent()
    low_mav = make_mav(
        parent=low_parent,
        messages=[Msg("VFR_HUD", airspeed=1.0, groundspeed=1.0, climb=0.0)],
    )
    low_mav.process()

    assert_write(low_parent, "IAS", 0)
    assert_write(low_parent, "GS", 0)
    assert_write(low_parent, "TAS", 0)


def test_process_sensor_attitude_gps_position_pressure_and_servo_messages(monkeypatch):
    parent = FakeParent()
    monkeypatch.setattr(mav_module, "rot", lambda speed, roll: ("rot", speed, roll))
    mav = make_mav(
        parent=parent,
        messages=[
            Msg("VFR_HUD", airspeed=20.0, groundspeed=5.0, climb=0.0),
            Msg("SCALED_IMU", xacc=1111, yacc=-2222, zacc=3333),
            Msg("ATTITUDE", roll=0.5, pitch=-0.25, yaw=1.0),
            Msg(
                "GPS_RAW_INT",
                cog=12345,
                fix_type=3,
                alt_ellipsoid=304800,
                satellites_visible=8,
                vel_acc=2000,
                h_acc=3048,
                v_acc=6096,
            ),
            Msg("GLOBAL_POSITION_INT", hdg=9876, relative_alt=15240, alt=304800, lat=400000000, lon=-880000000),
            Msg("SCALED_PRESSURE", press_abs=1013.25, press_diff=1.234),
            Msg("SERVO_OUTPUT_RAW", servo1_raw=1600, servo2_raw=1400, servo4_raw=1504),
        ],
    )

    for _ in range(7):
        mav.process()

    assert_write(parent, "ALAT", -2.222)
    assert_write(parent, "ALONG", 1.111)
    assert_write(parent, "ANORM", 3.333)
    assert_write(parent, "ROLL", 28.65)
    assert_write(parent, "ROT", ("rot", 20.0, 0.5))
    assert_write(parent, "PITCH", -14.32)
    assert_write(parent, "YAW", 57.3)
    assert_write(parent, "COURSE", 123.45)
    assert_write(parent, "GPS_FIX_TYPE", 3)
    assert_write(parent, "GPS_ELLIPSOID_ALT", 1000.0)
    assert_write(parent, "GPS_SATS_VISIBLE", 8)
    assert_write(parent, "GPS_ACCURACY_SPEED", 3.89)
    assert_write(parent, "GPS_ACCURACY_HORIZ", 1.0)
    assert_write(parent, "GPS_ACCURACY_VERTICAL", 2.0)
    assert_write(parent, "HEAD", 98.76)
    assert_write(parent, "AGL", 50.0)
    assert_write(parent, "ALT", 1000.0)
    assert_write(parent, "TALT", 1000.0)
    assert_write(parent, "LAT", 40.0)
    assert_write(parent, "LONG", -88.0)
    assert_write(parent, "AIRPRESS", 101325.0)
    assert_write(parent, "DIFFAIRPRESS", 123.4)
    assert mav._outputRoll == 250
    assert mav._outputPitch == -250
    assert mav._outputYaw == 10


def test_process_gps_course_uses_heading_when_stationary():
    parent = FakeParent()
    mav = make_mav(parent=parent, messages=[Msg("GPS_RAW_INT", cog=9000, fix_type=0, alt_ellipsoid=0, satellites_visible=0, vel_acc=0, h_acc=0, v_acc=0)])
    mav._data["HEAD"].append(271.0)

    mav.process()

    assert_write(parent, "COURSE", 271.0)


@pytest.mark.parametrize(
    "mode,name,message",
    [
        (0, "TRIM", "Trim Mode"),
        (7, "CRUISE", "Heading Hold"),
        (8, "AUTOTUNE", "Auto Tune"),
        (15, "GUIDED", "Nav to: HOME"),
    ],
)
def test_process_heartbeat_sets_known_modes(mode, name, message):
    parent = FakeParent()
    flags = (
        mav_module.mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
        | mav_module.mavutil.mavlink.MAV_MODE_FLAG_MANUAL_INPUT_ENABLED
        | mav_module.mavutil.mavlink.MAV_MODE_FLAG_HIL_ENABLED
        | mav_module.mavutil.mavlink.MAV_MODE_FLAG_STABILIZE_ENABLED
        | mav_module.mavutil.mavlink.MAV_MODE_FLAG_GUIDED_ENABLED
        | mav_module.mavutil.mavlink.MAV_MODE_FLAG_AUTO_ENABLED
        | mav_module.mavutil.mavlink.MAV_MODE_FLAG_TEST_ENABLED
        | mav_module.mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
    )
    mav = make_mav(parent=parent, messages=[Msg("HEARTBEAT", type=1, custom_mode=mode, base_mode=flags)])

    mav.process()

    assert_write(parent, "MAVSTATE", "ARMED")
    assert_write(parent, "MAVMODE", name)
    assert_write(parent, "MAVMSG", message)


def test_process_heartbeat_unknown_mode_sets_error_and_ignores_other_vehicle_type():
    parent = FakeParent()
    mav = make_mav(
        parent=parent,
        messages=[
            Msg("HEARTBEAT", type=1, custom_mode=999, base_mode=0),
            Msg("HEARTBEAT", type=27, custom_mode=0, base_mode=0),
        ],
    )

    mav.process()
    mav.process()

    assert_write(parent, "MAVMODE", "UNKNOWN")
    assert_write(parent, "MAVSTATE", "ERROR")


def test_process_sys_status_sends_arm_command_when_prearm_check_passes():
    parent = FakeParent()
    mav = make_mav(
        parent=parent,
        messages=[
            Msg(
                "SYS_STATUS",
                onboard_control_sensors_health=mav_module.mavutil.mavlink.MAV_SYS_STATUS_PREARM_CHECK,
            ),
            Msg("SYS_STATUS", onboard_control_sensors_health=0),
        ],
    )

    mav.process()
    mav.process()

    assert mav.conn.mav.sent[0][0] == "long"


def test_send_trims_adjusts_and_restores_saved_trims():
    parent = FakeParent()
    mav = make_mav(parent=parent)
    parent.values["MAVREQADJ"] = (True, False, False, False, False, False)
    mav._apmode = "CRUISE"

    mav.sendTrims()

    assert_write(parent, "MAVADJ", True)
    assert_write(parent, "TRIMR", 0)
    assert mav.conn.mav.manual_controls

    parent.values["MAVREQADJ"] = (False, False, False, False, False, False)
    mav.sendTrims()
    assert_write(parent, "MAVADJ", False)

    mav._apmode = "CRUISE"
    mav._outputPitch = 120
    mav._outputRoll = -80
    mav._outputYaw = 30
    mav.sendTrims()
    assert mav._trimsSaved is True
    assert_write(parent, "TRIMP", 12.0)
    assert_write(parent, "TRIMR", -8.0)
    assert_write(parent, "TRIMY", 3.0)

    mav._apmode = "TRIM"
    mav.sendTrims()
    assert_write(parent, "TRIMR", 0.0)
    assert_write(parent, "TRIMP", 0.0)
    assert_write(parent, "TRIMY", 0.0)


def test_send_trims_does_not_send_when_not_leader():
    parent = FakeParent()
    parent.quorum.leader = False
    mav = make_mav(parent=parent)
    mav._apmode = "TRIM"

    mav.sendTrims()

    assert mav.conn.mav.manual_controls == []


def test_check_mode_returns_when_not_leader_and_changes_requested_mode(monkeypatch):
    parent = FakeParent()
    parent.quorum.leader = False
    mav = make_mav(parent=parent)
    calls = []
    mav.checkWaypoint = lambda: calls.append("waypoint")

    mav.checkMode()
    assert calls == ["waypoint"]

    parent.quorum.leader = True
    parent.values["MAVREQTRIM"] = (True, False, False, False, False, False)
    parent.values["MAVREQCRUISE"] = (True, False, False, False, False, False)
    mav._apmode = "CRUISE"
    mav.setMode = lambda mode: calls.append(mode)

    mav.checkMode()

    assert calls[-1] == "TRIM"
    assert_write(parent, "MAVREQCRUISE", False)


def test_check_waypoint_invalid_guided_drops_to_cruise_and_valid_updates_mode():
    parent = FakeParent()
    mav = make_mav(parent=parent)
    calls = []
    mav.setMode = lambda mode: calls.append(mode)
    mav._apreq = "GUIDED"
    mav._apmode = "GUIDED"
    parent.values["WPLAT"] = (0.0, False, False, False, False, False)

    mav.checkWaypoint()

    assert calls == ["CRUISE"]
    assert_write(parent, "MAVREQGUIDED", False)
    assert_write(parent, "MAVREQCRUISE", True)
    assert_write(parent, "MAVWPVALID", False)

    parent.values["WPLAT"] = (40.0, False, False, False, False, False)
    parent.values["WPLON"] = (-88.0, False, False, False, False, False)
    parent.values["WPNAME"] = ("NEW", False, False, False, False, False)
    mav._waypoint = "old"
    calls.clear()
    mav.checkWaypoint()

    assert mav._apwpv is True
    assert calls == ["GUIDED"]
    assert_write(parent, "MAVWPVALID", True)


def test_set_mode_valid_invalid_guided_and_non_leader(monkeypatch):
    parent = FakeParent()
    mav = make_mav(parent=parent)
    monkeypatch.setattr(mav_module.time, "sleep", lambda _seconds: None)

    mav._apstat = "TRIM"
    mav._apwpv = False
    mav.setMode("CRUISE")
    assert_write(parent, "MAVMSG", "Invalid Request")

    parent.quorum.leader = False
    mav._apstat = "ARMED"
    mav.setMode("CRUISE")
    assert mav.conn.mav.sent == []

    parent.quorum.leader = True
    mav.setMode("CRUISE")
    assert mav.conn.mav.sent[-1][0] == "long"
    assert mav._apmode == "CRUISE"
    assert_write(parent, "MAVMODE", "CRUISE")

    mav._apwpv = True
    mav.setMode("GUIDED")
    assert mav.conn.mav.sent[-1][0] == "int"
    assert mav._waypoint == "-88.040.0HOME"

    mav._apstat = "ERROR"
    mav.setMode("TRIM")


def test_avg_and_get_avg_limit_samples():
    mav = make_mav()
    mav._max_average = 2

    assert mav.avg("X", 1, 1) == 1
    assert mav.avg("X", 3, 1) == 2
    assert mav.avg("X", 5, 1) == 4
    assert mav._data["X"] == [3, 5]
    assert mav.get_avg("X", 1) == 4
    assert mav.get_avg("EMPTY", 1) == 0


class FakeMainMav:
    instances = []

    def __init__(self, parent, port, baud, options):
        self.parent = parent
        self.port = port
        self.baud = baud
        self.options = options
        self.closed = False
        self.process_calls = 0
        FakeMainMav.instances.append(self)
        if options.get("raise_init"):
            raise RuntimeError("init failed")

    def wait_heartbeat(self):
        if self.options.get("raise_heartbeat"):
            raise RuntimeError("heartbeat failed")

    def process(self):
        self.process_calls += 1
        if self.options.get("raise_process"):
            raise RuntimeError("process failed")
        if self.process_calls > 42:
            self.parent.thread.getout = True

    def sendTrims(self):
        pass

    def checkMode(self):
        self.checked_mode = True

    def close(self):
        self.closed = True


def test_main_thread_run_success_and_error_paths(monkeypatch):
    monkeypatch.setattr(mav_plugin, "Mav", FakeMainMav)
    monkeypatch.setattr(mav_plugin.time, "sleep", lambda _seconds: None)
    parent = FakeParent()
    parent.config = {"type": "serial", "baud": "38400", "port": "/dev/fake", "options": {}}
    thread = mav_plugin.MainThread(parent)
    parent.thread = thread

    thread.run()

    assert FakeMainMav.instances[-1].baud == 38400
    assert getattr(FakeMainMav.instances[-1], "checked_mode", False) is True

    parent.config = {"type": "serial", "options": {"raise_heartbeat": True}}
    thread = mav_plugin.MainThread(parent)
    parent.thread = thread
    sleeps = 0

    def stop_after_retry(_seconds):
        nonlocal sleeps
        sleeps += 1
        if sleeps > 1:
            thread.getout = True

    monkeypatch.setattr(mav_plugin.time, "sleep", stop_after_retry)
    thread.run()
    assert FakeMainMav.instances[-1].closed is True

    parent.config = {"type": "serial", "options": {"raise_process": True}}
    thread = mav_plugin.MainThread(parent)
    parent.thread = thread
    sleeps = 0
    monkeypatch.setattr(mav_plugin.time, "sleep", stop_after_retry)
    thread.run()
    assert FakeMainMav.instances[-1].closed is True


def test_main_thread_run_init_failure_logs_and_retries(monkeypatch):
    monkeypatch.setattr(mav_plugin, "Mav", FakeMainMav)
    parent = FakeParent()
    parent.config = {"type": "serial", "options": {"raise_init": True}}
    thread = mav_plugin.MainThread(parent)
    sleeps = 0

    def stop_after_retry(_seconds):
        nonlocal sleeps
        sleeps += 1
        if sleeps > 1:
            thread.getout = True

    monkeypatch.setattr(mav_plugin.time, "sleep", stop_after_retry)

    thread.run()

    assert any("failed to connect" in str(message) for message in parent.log.messages)


def test_plugin_lifecycle_and_invalid_type(monkeypatch):
    class DummyThread:
        def __init__(self, parent):
            self.parent = parent
            self.started = False
            self.stopped = False
            self.alive = False

        def start(self):
            self.started = True

        def stop(self):
            self.stopped = True

        def is_alive(self):
            return self.alive

        def join(self, timeout):
            self.joined = timeout

    monkeypatch.setattr(mav_plugin, "MainThread", DummyThread)

    plugin = mav_plugin.Plugin("mavlink", {"type": "serial"}, {})
    plugin.run()
    plugin.stop()

    assert plugin.thread.started is True
    assert plugin.thread.stopped is True
    assert plugin.get_status() == mav_plugin.OrderedDict()

    with pytest.raises(ValueError, match="Only serial"):
        mav_plugin.Plugin("mavlink", {"type": "udp"}, {})

    failing = mav_plugin.Plugin("mavlink", {"type": "serial"}, {})
    failing.thread.alive = True
    with pytest.raises(plugin_base.PluginFail):
        failing.stop()


def test_main_thread_stop_sets_getout():
    parent = FakeParent()
    parent.config = {"type": "serial"}
    thread = mav_plugin.MainThread(parent)

    thread.stop()

    assert thread.getout is True


def test_plugin_stop_ignores_join_exception_then_raises(monkeypatch):
    class BadJoinThread:
        def __init__(self, parent):
            self.parent = parent

        def start(self):
            pass

        def stop(self):
            pass

        def is_alive(self):
            return True

        def join(self, timeout):
            raise RuntimeError("join failed")

    monkeypatch.setattr(mav_plugin, "MainThread", BadJoinThread)
    plugin = mav_plugin.Plugin("mavlink", {"type": "serial"}, {})

    with pytest.raises(plugin_base.PluginFail):
        plugin.stop()
