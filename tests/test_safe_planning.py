import unittest

from weread2notionpro.book_progress_planning import (
    book_state_update,
    cumulative_update,
    select_book_batch,
    title_matches,
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

    def test_finished_book_promotes_status_and_progress(self):
        plan = book_state_update(
            {"progress": 72, "finishTime": 1730000000, "recordReadingTime": 900},
            {"status": "想读", "readingProgress": 0.1, "readingTime": 600},
        )
        self.assertEqual(plan["status"], "已读")
        self.assertEqual(plan["reading_progress"], 1.0)
        self.assertEqual(plan["reading_time"], 900)

    def test_shelf_finished_marker_is_authoritative(self):
        plan = book_state_update(
            {"progress": 72, "finishTime": 0, "finishReading": 1,
             "recordReadingTime": 900},
            {"status": "想读", "readingProgress": 0.72, "readingTime": 900},
        )
        self.assertEqual(plan["status"], "已读")
        self.assertEqual(plan["reading_progress"], 1.0)

    def test_legacy_marked_status_four_is_finished(self):
        plan = book_state_update(
            {"progress": 72, "finishTime": 0, "finishReading": 0,
             "markedStatus": 4, "recordReadingTime": 900},
            {"status": "想读", "readingProgress": 0.72, "readingTime": 900},
        )
        self.assertEqual(plan["status"], "已读")
        self.assertEqual(plan["reading_progress"], 1.0)

    def test_book_state_never_moves_backwards(self):
        plan = book_state_update(
            {"progress": 30, "finishTime": 0, "recordReadingTime": 300},
            {"status": "已读", "readingProgress": 1.0, "readingTime": 1000},
        )
        self.assertIsNone(plan["status"])
        self.assertIsNone(plan["reading_progress"])
        self.assertIsNone(plan["reading_time"])

    def test_progress_without_finish_promotes_to_reading(self):
        plan = book_state_update(
            {"progress": 1, "finishTime": 0, "recordReadingTime": 60},
            {"status": "想读", "readingProgress": 0, "readingTime": 0},
        )
        self.assertEqual(plan["status"], "在读")
        self.assertEqual(plan["reading_progress"], 0.01)

    def test_update_timestamp_alone_does_not_mean_reading(self):
        plan = book_state_update(
            {"progress": 0, "finishTime": 0, "recordReadingTime": 0,
             "updateTime": 1730000000},
            {"status": "想读", "readingProgress": 0, "readingTime": 0},
        )
        self.assertIsNone(plan["status"])
        self.assertIsNone(plan["reading_progress"])

    def test_zero_limit_selects_every_remaining_book(self):
        books = [str(index) for index in range(233)]
        self.assertEqual(len(select_book_batch(books, 0, 0)), 233)
        self.assertEqual(select_book_batch(books, 230, 0), ["230", "231", "232"])

    def test_debug_title_match_is_exact(self):
        self.assertTrue(title_matches("全员嫌疑人", "全员嫌疑人"))
        self.assertFalse(title_matches("嫌疑人", "全员嫌疑人"))


if __name__ == "__main__":
    unittest.main()

