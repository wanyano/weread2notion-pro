"""Credential-free tests for safe historical reading-time imports."""
import unittest
from datetime import datetime, timezone
from weread2notionpro.read_time_planning import (
    daily_reconciliation,
    local_midnight_timestamp,
    monthly_daily_seconds,
)


class ReadingTimePlanningTests(unittest.TestCase):
    def test_unix_seconds_and_monthly_daily_buckets(self):
        one = local_midnight_timestamp("2026-11-01")
        two = local_midnight_timestamp("2026-11-02")
        self.assertEqual(monthly_daily_seconds({
            "totalReadTime": 420,
            "readTimes": {str(one): 120, str(two): 300},
        }, 2026, 11), {"2026-11-01": 120, "2026-11-02": 300})
        self.assertEqual(datetime.fromtimestamp(one, timezone.utc).hour, 16)

    def test_fails_closed_without_daily_data(self):
        with self.assertRaisesRegex(ValueError, "no usable daily"):
            monthly_daily_seconds({"totalReadTime": 900}, 2026, 11)

    def test_rejects_daily_bucket_outside_month(self):
        stamp = local_midnight_timestamp("2026-10-31")
        with self.assertRaisesRegex(ValueError, "out-of-period"):
            monthly_daily_seconds({"readTimes": {str(stamp): 60}}, 2026, 11)

    def test_rejects_negative_time(self):
        stamp = local_midnight_timestamp("2026-11-03")
        with self.assertRaises(ValueError):
            monthly_daily_seconds({"readTimes": {str(stamp): -1}}, 2026, 11)

    def test_skip_zero_durations_and_preserve_existing_days(self):
        one = local_midnight_timestamp("2026-11-01")
        two = local_midnight_timestamp("2026-11-02")
        plan = daily_reconciliation(
            {"2026-11-01": 120, "2026-11-02": 0,
             "2026-11-03": 500, "2026-11-04": 200},
            [{"id": "a", "timestamp": one, "duration": 120},
             {"id": "b", "timestamp": two, "duration": 300},
             {"id": "c", "timestamp": local_midnight_timestamp("2026-11-04"),
              "duration": 100}],
            2026
        )
        self.assertEqual(plan["unchanged"], 1)
        self.assertEqual(len(plan["create"]), 1)
        self.assertEqual(len(plan["update"]), 1)
        self.assertEqual(plan["update"][0]["page_id"], "c")

    def test_duplicates_stop_import(self):
        one = local_midnight_timestamp("2026-11-01")
        with self.assertRaisesRegex(ValueError, "Duplicate Notion"):
            daily_reconciliation(
                {"2026-11-01": 300},
                [{"id": "a", "timestamp": one, "duration": 200},
                 {"id": "b", "timestamp": one, "duration": 200}], 2026
            )


if __name__ == "__main__":
    unittest.main()
