import unittest

from weread2notionpro.book_progress_planning import (
    cumulative_update,
    select_book_batch,
)
from weread2notionpro.read_time_planning import (
    daily_reconciliation,
    local_midnight_timestamp,
    monthly_daily_seconds,
)


class SafePlanningTests(unittest.TestCase):
    def test_monthly_data_and_zero_source_are_safe(self):
        stamp = local_midnight_timestamp("2026-11-01")
        self.assertEqual(
            monthly_daily_seconds(
                {"totalReadTime": 120, "readTimes": {str(stamp): 120}},
                2026,
                11,
            ),
            {"2026-11-01": 120},
        )
        plan = daily_reconciliation(
            {"2026-11-01": 0},
            [{"id": "a", "timestamp": stamp, "duration": 300}],
            2026,
        )
        self.assertEqual(plan["create"], [])
        self.assertEqual(plan["update"], [])

    def test_daily_value_never_moves_backwards(self):
        stamp = local_midnight_timestamp("2026-11-01")
        plan = daily_reconciliation(
            {"2026-11-01": 120},
            [{"id": "a", "timestamp": stamp, "duration": 300}],
            2026,
        )
        self.assertEqual(plan["update"], [])
        self.assertEqual(plan["preserved"], 1)

    def test_daily_value_can_increase(self):
        stamp = local_midnight_timestamp("2026-11-01")
        plan = daily_reconciliation(
            {"2026-11-01": 300},
            [{"id": "a", "timestamp": stamp, "duration": 120}],
            2026,
        )
        self.assertEqual(plan["update"][0]["seconds"], 300)

    def test_book_history_is_monotonic(self):
        self.assertIsNone(cumulative_update(100, 200))
        self.assertIsNone(cumulative_update(200, 200))
        self.assertEqual(cumulative_update(300, 200), 300)

    def test_zero_limit_selects_every_remaining_book(self):
        books = [str(index) for index in range(233)]
        self.assertEqual(len(select_book_batch(books, 0, 0)), 233)
        self.assertEqual(select_book_batch(books, 230, 0), ["230", "231", "232"])


if __name__ == "__main__":
    unittest.main()

