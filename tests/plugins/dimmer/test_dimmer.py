import fixgw.plugins.dimmer as dimmer


class FakePlugin:
    def __init__(self, path):
        self.config = {"DimmerDevice": str(path), "Multiplier": 2.5}
        self.callbacks = []

    def db_callback_add(self, key, function, udata=None):
        self.callbacks.append((key, function, udata))


def test_dim_function_writes_scaled_integer_value(tmp_path):
    device = tmp_path / "brightness"
    parent = FakePlugin(device)

    dimmer.dimFunction("DIM", (4.4, False, False, False, False, False), parent)

    assert device.read_text(encoding="utf-8") == "11\n"


def test_plugin_registers_dimmer_callback(tmp_path):
    plugin = dimmer.Plugin("dimmer", {"DimmerDevice": str(tmp_path / "d"), "Multiplier": 1}, {})
    callbacks = []
    plugin.db_callback_add = lambda key, function, udata=None: callbacks.append(
        (key, function, udata)
    )

    plugin.run()
    plugin.stop()

    assert callbacks == [("DIM", dimmer.dimFunction, plugin)]
