import fixgw.plugin as plugin


def test_plugin_base_running_state_and_default_status():
    base = plugin.PluginBase("base", {}, {})

    assert base.is_running() is False
    assert base.get_status() is None
