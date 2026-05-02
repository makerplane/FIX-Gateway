"""
Unit tests for the annunciate plugin.

Tests AnnunciateItem callback logic by writing directly to the database and
observing the item's annunciate flag — no serial ports or network sockets
are involved.

Coverage:
  - High and low threshold detection
  - Deadband hysteresis (prevents flag oscillation at the setpoint boundary)
  - Conditional bypass: flag clears when a bypass condition is met
    (also verifies the annunicate→annunciate typo fix on the bypass path)
  - Start bypass: no annunciation until value first rises above low setpoint
  - stop(): callbacks removed, flag no longer updated after shutdown
  - get_status(): item count reported correctly
"""
import io
import unittest
from types import SimpleNamespace

import fixgw.database as database
from fixgw.plugins import annunciate

DB_CONFIG = """
variables:
  e: 1

entries:
- key: OILP1
  description: Oil Pressure Engine 1
  type: float
  min: 0.0
  max: 120.0
  units: psi
  initial: 60.0
  tol: 2000
  aux: [lowAlarm, highAlarm]

- key: TACH1
  description: Tachometer Engine 1
  type: float
  min: 0.0
  max: 3600.0
  units: rpm
  initial: 0.0
  tol: 2000
"""

_DEFAULTS = {
    "low_aux_point": "lowAlarm",
    "high_aux_point": "highAlarm",
    "deadband": 1.0,
    "start_bypass": None,
    "cond_bypass": "None",
}


def _make_plugin(items, defaults=None):
    config = {"defaults": defaults or _DEFAULTS, "items": items}
    p = annunciate.Plugin("test_annunciate", config, None)
    p.run()
    return p


class TestAnnunciatePlugin(unittest.TestCase):

    def setUp(self):
        database.init(io.StringIO(DB_CONFIG))
        database.write("OILP1.lowAlarm", 10.0)
        database.write("OILP1.highAlarm", 100.0)

    # ------------------------------------------------------------------
    # Basic threshold detection
    # ------------------------------------------------------------------

    def test_no_annunciation_when_in_range(self):
        p = _make_plugin([{"key": "OILP1"}])
        database.write("OILP1", 60.0)
        self.assertFalse(p.items[0].item.annunciate)

    def test_high_annunciation_above_threshold(self):
        p = _make_plugin([{"key": "OILP1"}])
        database.write("OILP1", 105.0)
        self.assertTrue(p.items[0].item.annunciate)

    def test_low_annunciation_below_threshold(self):
        p = _make_plugin([{"key": "OILP1"}])
        database.write("OILP1", 5.0)
        self.assertTrue(p.items[0].item.annunciate)

    def test_high_flag_clears_when_back_in_range(self):
        p = _make_plugin([{"key": "OILP1"}])
        database.write("OILP1", 105.0)
        self.assertTrue(p.items[0].item.annunciate)
        database.write("OILP1", 60.0)
        self.assertFalse(p.items[0].item.annunciate)

    def test_missing_aux_points_disable_that_side(self):
        p = _make_plugin(
            [
                {
                    "key": "OILP1",
                    "low_aux_point": "missingLow",
                    "high_aux_point": "missingHigh",
                }
            ]
        )

        self.assertIsNone(p.items[0].low_set_point)
        self.assertIsNone(p.items[0].high_set_point)
        database.write("OILP1", 105.0)
        self.assertFalse(p.items[0].item.annunciate)

    # ------------------------------------------------------------------
    # Deadband hysteresis
    # ------------------------------------------------------------------

    def test_percent_deadband_uses_item_range(self):
        p = _make_plugin([{"key": "OILP1", "deadband": "10%"}])

        self.assertEqual(p.items[0].deadband, 12.0)

    def test_deadband_prevents_rapid_clear_on_high(self):
        # highAlarm=100.0, deadband=1.0 → clears only when value <= 99.0
        p = _make_plugin([{"key": "OILP1"}])
        database.write("OILP1", 105.0)               # trigger
        self.assertTrue(p.items[0].item.annunciate)
        database.write("OILP1", 99.5)                # below threshold but within deadband
        self.assertTrue(p.items[0].item.annunciate)  # still latched
        database.write("OILP1", 98.9)                # past deadband → clear
        self.assertFalse(p.items[0].item.annunciate)

    def test_deadband_prevents_rapid_clear_on_low(self):
        # lowAlarm=10.0, deadband=1.0 → clears only when value >= 11.0
        p = _make_plugin([{"key": "OILP1"}])
        database.write("OILP1", 5.0)                 # trigger
        self.assertTrue(p.items[0].item.annunciate)
        database.write("OILP1", 10.5)                # above threshold but within deadband
        self.assertTrue(p.items[0].item.annunciate)  # still latched
        database.write("OILP1", 11.1)                # past deadband → clear
        self.assertFalse(p.items[0].item.annunciate)

    # ------------------------------------------------------------------
    # Conditional bypass
    # ------------------------------------------------------------------

    def test_conditional_bypass_suppresses_annunciation(self):
        """Bypass condition clears the annunciate flag.

        Also directly validates the annunicate→annunciate typo fix: before
        the fix the bypass path set self.item.annunicate (wrong attribute)
        instead of self.item.annunciate, so the flag was never cleared.
        """
        defaults = dict(_DEFAULTS, cond_bypass="TACH1 < 500")
        p = _make_plugin([{"key": "OILP1"}], defaults=defaults)

        # Bypass inactive: TACH1 >= 500 → annunciation fires normally
        database.write("TACH1", 1000.0)
        database.write("OILP1", 105.0)
        self.assertTrue(p.items[0].item.annunciate)

        # Activate bypass: TACH1 < 500 → flag must clear
        database.write("TACH1", 0.0)
        database.write("OILP1", 105.0)  # re-trigger evaluate
        self.assertFalse(p.items[0].item.annunciate)

    def test_annunciation_resumes_when_bypass_deactivates(self):
        defaults = dict(_DEFAULTS, cond_bypass="TACH1 < 500")
        p = _make_plugin([{"key": "OILP1"}], defaults=defaults)

        database.write("TACH1", 0.0)    # bypass active
        database.write("OILP1", 105.0)
        self.assertFalse(p.items[0].item.annunciate)

        database.write("TACH1", 1000.0)  # bypass inactive
        database.write("OILP1", 105.0)
        self.assertTrue(p.items[0].item.annunciate)

    def test_conditional_bypass_validation_errors(self):
        with self.assertRaisesRegex(ValueError, "Wrong number of tokens"):
            _make_plugin([{"key": "OILP1", "cond_bypass": "TACH1 <"}])

        with self.assertRaisesRegex(ValueError, "Unknown operator"):
            _make_plugin([{"key": "OILP1", "cond_bypass": "TACH1 <> 500"}])

    def test_conditional_bypass_unknown_key_when_lookup_returns_none(self):
        item = SimpleNamespace(
            aux=[],
            min=0.0,
            max=100.0,
            dtype=float,
            value=(0.0, False, False, False, False, False),
        )
        fake_plugin = SimpleNamespace(
            db_get_item=lambda key: item if key == "OILP1" else None,
            db_callback_add=lambda *_args: None,
        )

        with self.assertRaisesRegex(ValueError, "Unknown Key MISSING"):
            annunciate.AnnunciateItem(
                fake_plugin,
                dict(_DEFAULTS, cond_bypass="MISSING < 1"),
                {"key": "OILP1"},
            )

    # ------------------------------------------------------------------
    # Start bypass
    # ------------------------------------------------------------------

    def test_start_bypass_suppresses_until_value_rises(self):
        # start_bypass=True: no annunciation until value first climbs above
        # the low setpoint; after that, normal low-limit behavior applies.
        p = _make_plugin([{"key": "OILP1", "start_bypass": True}])

        database.write("OILP1", 5.0)           # below low (10.0), latch active
        self.assertFalse(p.items[0].item.annunciate)

        database.write("OILP1", 60.0)          # above low → latch released
        database.write("OILP1", 5.0)           # now below low again
        self.assertTrue(p.items[0].item.annunciate)

    def test_none_low_alarm_falls_back_to_minimum_for_start_bypass_and_low_latch(self):
        database.get_raw_item("OILP1").aux["lowAlarm"] = None
        p = _make_plugin([{"key": "OILP1", "start_bypass": True}])
        p.stop()

        p.items[0].evaluate("OILP1", (5.0, False, False, False, False, False), None)
        self.assertFalse(p.items[0].start_bypass_latch)
        self.assertFalse(p.items[0].item.annunciate)

        p.items[0].evaluate("OILP1", (-1.0, False, False, False, False, False), None)
        self.assertTrue(p.items[0].item.annunciate)

    def test_none_high_alarm_falls_back_to_maximum(self):
        database.get_raw_item("OILP1").aux["highAlarm"] = None
        p = _make_plugin([{"key": "OILP1"}])
        p.stop()

        p.items[0].evaluate("OILP1", (121.0, False, False, False, False, False), None)

        self.assertTrue(p.items[0].item.annunciate)

    def test_aux_update_evaluates_current_base_value(self):
        p = _make_plugin([{"key": "OILP1"}])
        database.write("OILP1", 105.0)
        p.items[0].item.annunciate = False

        p.items[0].evaluate("OILP1.highAlarm", None, None)

        self.assertTrue(p.items[0].item.annunciate)

    def test_str_reports_configuration(self):
        p = _make_plugin([{"key": "OILP1", "start_bypass": True}])

        self.assertEqual(
            str(p.items[0]),
            "\n".join(
                [
                    "OILP1",
                    "  Low Set Point: OILP1.lowAlarm",
                    "  High Set Point: OILP1.highAlarm",
                    "  Deadband: 1.0",
                    "  Start Bypass Enabled: Yes",
                    "  Conditional Bypass: None",
                ]
            ),
        )

    def test_null_item_lookup_raises_value_error(self):
        fake_plugin = SimpleNamespace(
            db_get_item=lambda _key: None,
            db_callback_add=lambda *_args: None,
        )

        with self.assertRaisesRegex(ValueError, "Key MISSING not found"):
            annunciate.AnnunciateItem(fake_plugin, _DEFAULTS, {"key": "MISSING"})

    # ------------------------------------------------------------------
    # stop() — callback removal
    # ------------------------------------------------------------------

    def test_stop_removes_callbacks(self):
        p = _make_plugin([{"key": "OILP1"}])
        database.write("OILP1", 60.0)
        self.assertFalse(p.items[0].item.annunciate)

        p.stop()

        # After stop, writing above threshold must NOT update the flag
        database.write("OILP1", 105.0)
        self.assertFalse(p.items[0].item.annunciate)

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def test_get_status_reports_item_count(self):
        p = _make_plugin([{"key": "OILP1"}])
        self.assertEqual(p.get_status()["Item Count"], 1)

    def test_get_status_multiple_items(self):
        p = _make_plugin([{"key": "OILP1"}, {"key": "OILP1"}])
        self.assertEqual(p.get_status()["Item Count"], 2)


if __name__ == "__main__":
    unittest.main()
