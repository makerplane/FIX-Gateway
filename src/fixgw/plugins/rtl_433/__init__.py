import subprocess
import json
import sys
import time
import yaml
import threading
import fixgw.plugin as plugin
import random
import select
import os
from collections import OrderedDict
from fixgw.cfg import message


def valid_decoder(id):
    # Needs updated when rtl_433 is updated to newer version
    return id in range(1, 276)


def valid_type(data_type):
    return data_type in ["int", "float", "string", "bool"]


def validate_config(parent):
    for i, sensor in enumerate(parent.config["sensors"]):
        if not valid_decoder(sensor["decoder"]):
            raise ValueError(
                message(
                    f"'{sensor['decoder']}' is not a valid decoder id",
                    parent.config_meta["sensors"][i],
                    "decoder",
                    True,
                )
            )
        for fixid, data in sensor["mappings"].items():
            if fixid not in parent.db_list():
                raise ValueError(
                    message(
                        f"'{fixid}' is not a valid fixid",
                        parent.config_meta["sensors"][i]["mappings"],
                        fixid,
                        True,
                    )
                )
            # TODO Finish validaton and write tests to ensure they work
            if "source" not in data:
                raise ValueError(
                    message(
                        "'source' must be specified in mapping",
                        parent.config_meta["sensors"][i]["mappings"],
                        fixid,
                        True,
                    )
                )
            if "scale" in data:
                if not isinstance(data["scale"], (int, float)):
                    raise ValueError(
                        message(
                            "'scale' must be an integer or float",
                            parent.config_meta["sensors"][i]["mappings"][fixid],
                            "scale",
                            True,
                        )
                    )
            if "round" in data:
                if not isinstance(data["round"], int):
                    raise ValueError(
                        message(
                            "'round' must be an integer",
                            parent.config_meta["sensors"][i]["mappings"][fixid],
                            "round",
                            True,
                        )
                    )
                if not data["round"] in range(0, 5):
                    raise ValueError(
                        message(
                            "'round' must be 0, 1, 2, 3 or 4",
                            parent.config_meta["sensors"][i]["mappings"][fixid],
                            "round",
                            True,
                        )
                    )
            if "type" in data:
                if not valid_type(data["type"]):
                    raise ValueError(
                        message(
                            f"'{data['type']}' is not a valid type",
                            parent.config_meta["sensors"][i]["mappings"][fixid],
                            "type",
                            True,
                        )
                    )

            for key in ["offset", "threshold"]:
                if key in data:
                    if not isinstance(data[key], (int, float)):
                        raise ValueError(
                            message(
                                f"'{data[key]}' must be a float or int",
                                parent.config_meta["sensors"][i]["mappings"][fixid],
                                key,
                                True,
                            )
                        )


def convert_type(value, dtype):
    """Convert value to the specified data type."""
    try:
        if dtype == "int":
            return int(value)
        elif dtype == "float":
            return float(value)
        elif dtype == "bool":
            return bool(value)
        elif dtype == "string":  # pragma: no branch
            return str(value)
    except (ValueError, TypeError):
        pass  # self.parent.log.warning(f"Could not convert {value} to {dtype}")
    return value  # Return unmodified if conversion fails


def apply_transform(value, transform):
    """Apply scale, offset, rounding, and threshold transformations to data."""
    if value is None:
        return None

    # Ensure we only apply mathematical transformations to numbers
    if isinstance(value, (int, float)):
        if "threshold" in transform:
            value = 1 if value > transform["threshold"] else 0
        else:
            value = (value * transform.get("scale", 1)) + transform.get("offset", 0)

            if "round" in transform:
                value = round(value, transform["round"])

    # Apply type conversion if specified
    if "type" in transform:
        value = convert_type(value, transform["type"])

    return value


def map_data(json_data, parent):
    """Map rtl_433 JSON data to application fixids based on YAML config."""
    sensor_id = json_data.get("id")
    protocol = json_data.get("protocol")
    model = json_data.get("model", "unknown")
    sid = f"{protocol}/{model}/{sensor_id}"
    if sid not in parent.status["Devices Seen"]:
        parent.status["Devices Seen"][sid] = 1
    else:
        parent.status["Devices Seen"][sid] += 1
    for sensor in parent.config["sensors"]:  # pragma: no branch
        if sensor["sensor_id"] == sensor_id:
            if sensor["decoder"] != protocol:
                continue
            mappings = sensor["mappings"]
            for fixid, rules in mappings.items():  # pragma: no branch
                source_key = rules["source"]
                if source_key in json_data:
                    value = apply_transform(json_data[source_key], rules)
                    parent.db_write(fixid, value)
            return


def process_json(data, parent):
    """Process each JSON data string received from rtl_433"""
    try:
        parsed_data = json.loads(data)
        map_data(parsed_data, parent)
    except json.JSONDecodeError:
        parent.log.error("Error decoding JSON:", data)


def get_rtl_433_path():
    """Determine the correct path for rtl_433, checking if running inside a Snap."""
    if "SNAP" in os.environ:
        return os.path.join(os.environ["SNAP"], "usr", "bin", "rtl_433")
    return "rtl_433"


def start_rtl_433(parent, simulate=False, device=0, frequency=433920000, decoders=[]):
    """Start rtl_433 process with specific SDR device, frequency, and enabled decoders."""
    if simulate:
        return None  # Indicate simulation mode
    rtl_433_path = get_rtl_433_path()
    command = [
        rtl_433_path,
        "-d",
        str(device),
        "-f",
        str(frequency),
        "-F",
        "json",
        "-M",
        "protocol",
    ]
    for decoder in decoders:
        command.extend(["-R", str(decoder)])
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,  # Line-buffered output
    )
    time.sleep(0.1)
    parent.status["rtl_433 starts"] += 1
    if process.poll() is not None:
        parent.log.warning(
            f"rtl_433 process failed to start with exit code {process.poll()} command:{command}"
        )
        parent.status["rtl_433 pid"] = None
        parent.status["rtl_433 exit code"] = process.poll()
        time.sleep(1)
    else:
        parent.status["rtl_433 pid"] = process.pid
    return process


def generate_mock_data(config):
    """Generate simulated rtl_433 JSON output."""
    while True:  # pragma: no cover
        for sensor in config["sensors"]:
            data = {
                "id": sensor["sensor_id"],
                "pressure_kPa": random.uniform(200, 300),
                "temperature_C": random.uniform(15, 35),
                "battery_V": random.uniform(2.0, 3.5),
            }
            yield json.dumps(data)
            time.sleep(2)  # Simulate sensor transmission interval


class MainThread(threading.Thread):
    def __init__(self, parent):
        super(MainThread, self).__init__()
        self.getout = False  # Indicator for when to stop
        self.parent = parent  # Parent plugin object
        self.simulate = self.parent.config.get("simulate", False)
        self.process = None

    def run(self):

        try:
            config = self.parent.config
            device = config.get("rtl_device", 0)
            frequency = config.get("frequency", 433920000)
            decoders = list(set(sensor["decoder"] for sensor in config["sensors"]))
            self.process = start_rtl_433(
                self.parent,
                simulate=self.simulate,
                device=device,
                frequency=frequency,
                decoders=decoders,
            )
            if self.simulate:  # pragma: no cover
                mock_generator = generate_mock_data(config)
                while not self.getout:
                    process_json(next(mock_generator), self.parent)
            else:
                while not self.getout:
                    ready, _, _ = select.select(
                        [self.process.stdout], [], [], 1
                    )  # 1-second timeout
                    if ready:
                        line = self.process.stdout.readline()
                        if not line and not self.getout:
                            self.parent.log.warning(
                                "rtl_433 exited unexpectedly. Restarting..."
                            )
                            self.process = start_rtl_433(
                                self.parent,
                                device=device,
                                frequency=frequency,
                                decoders=decoders,
                            )
                            continue
                        process_json(line.strip(), self.parent)
                    else:
                        continue
                        # self.parent.log.info("Warning: rtl_433 is not producing output.")
                self.stop_rtl_433()
        finally:
            self.stop_rtl_433()

    def stop_rtl_433(self):
        """Ensure rtl_433 is terminated."""
        if self.process:
            self.parent.log.info("Stopping rtl_433...")
            self.process.terminate()
            self.process.wait()
            self.process = None
            self.parent.status["rtl_433 pid"] = None

    def stop(self):
        self.getout = True


class Plugin(plugin.PluginBase):
    def __init__(self, name, config, config_meta):
        super(Plugin, self).__init__(name, config, config_meta)
        self.thread = MainThread(self)
        self.status = OrderedDict()
        self.status["Devices Seen"] = OrderedDict()
        self.status["rtl_433 pid"] = None
        self.status["rtl_433 starts"] = 0
        validate_config(self)

    def run(self):
        self.thread.start()

    def stop(self):
        self.thread.stop()
        if self.thread.is_alive():
            self.thread.join(2.0)
        if self.thread.is_alive():
            raise plugin.PluginFail

    def get_status(self):
        return self.status
