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

    # ------------------------------------------------------------------
    # Deadband hysteresis
    # ------------------------------------------------------------------

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
