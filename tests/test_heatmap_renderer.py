"""Credential-free heatmap rendering and validation tests."""
import unittest
from datetime import date
from weread2notionpro.heatmap_renderer import (
    days_from_notion_rows, render_svg, seconds_color,
)
from weread2notionpro.read_time_planning import local_midnight_timestamp


class HeatmapTests(unittest.TestCase):
    def test_svg_has_365_days(self):
        svg=render_svg(2026,{date(2026,6,20):5999})
        self.assertEqual(svg.count("data-date="),365)
        self.assertIn("2026-06-20",svg)
        self.assertIn("1小时39分59秒",svg)
        self.assertIn("#216e39",svg)

    def test_leap_year(self):
        self.assertEqual(render_svg(2024,{}).count("data-date="),366)

    def test_validate_notions_positive_durations(self):
        day=local_midnight_timestamp("2026-06-20")
        rows=[
            {"properties":{"时间戳":{"number":day},"时长":{"number":5999}}},
            {"properties":{"时间戳":{"number":day},"时长":{"number":0}}}
        ]
        days,existing,dupes=days_from_notion_rows(rows,2026)
        self.assertEqual(days[date(2026,6,20)],5999)
        self.assertEqual((existing,dupes),(2,1))

    def test_conflicts_fail_closed(self):
        day=local_midnight_timestamp("2026-06-20")
        with self.assertRaisesRegex(ValueError,"Conflicting"):
            days_from_notion_rows([
                {"properties":{"时间戳":{"number":day},"时长":{"number":20}}},
                {"properties":{"时间戳":{"number":day},"时长":{"number":40}}},
            ],2026)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            seconds_color(-1)


if __name__=="__main__":
    unittest.main()
