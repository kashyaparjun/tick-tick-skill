from datetime import date
import unittest
from unittest.mock import patch

from ticktick_cli.commands.tasks import _collect_due_tasks_for_status, _due_query_window, _filter_due_tasks, _merge_by_id


TASKS = [
    {"id": "a", "title": "A", "status": 0, "dueDate": "2026-03-14T23:00:00.000+0000"},
    {"id": "b", "title": "B", "status": 0, "dueDate": "2026-03-15T23:00:00.000+0000"},
    {"id": "c", "title": "C", "status": 2, "dueDate": "2026-03-14T23:00:00.000+0000"},
    {"id": "d", "title": "No due", "status": 0},
]


class TestDueFiltering(unittest.TestCase):
    def test_strict_target_day(self):
        out = _filter_due_tasks(TASKS, mode="strict", status_filter="all", target_date=date(2026, 3, 15))
        self.assertEqual([t["id"] for t in out], ["a", "c"])

    def test_web_today_target_day_includes_overdue(self):
        out = _filter_due_tasks(TASKS, mode="web-today", status_filter="all", target_date=date(2026, 3, 16))
        self.assertEqual([t["id"] for t in out], ["a", "c", "b"])

    def test_status_filter_open_only(self):
        out = _filter_due_tasks(TASKS, mode="strict", status_filter="open", target_date=date(2026, 3, 15))
        self.assertEqual([t["id"] for t in out], ["a"])

    def test_status_filter_completed_only(self):
        out = _filter_due_tasks(TASKS, mode="strict", status_filter="completed", target_date=date(2026, 3, 15))
        self.assertEqual([t["id"] for t in out], ["c"])

    def test_range_strict(self):
        out = _filter_due_tasks(
            TASKS,
            mode="strict",
            status_filter="all",
            start_date=date(2026, 3, 15),
            end_date=date(2026, 3, 16),
        )
        self.assertEqual([t["id"] for t in out], ["a", "c", "b"])

    def test_range_web_today_uses_upper_bound(self):
        out = _filter_due_tasks(
            TASKS,
            mode="web-today",
            status_filter="all",
            start_date=date(2026, 3, 16),
            end_date=date(2026, 3, 16),
        )
        self.assertEqual([t["id"] for t in out], ["a", "c", "b"])

    def test_due_query_window_target(self):
        start, end = _due_query_window(target_date=date(2026, 3, 15))
        self.assertEqual(start.isoformat(), "2026-03-15")
        self.assertEqual(end.isoformat(), "2026-03-15")

    def test_merge_by_id_prefers_second(self):
        merged = _merge_by_id(
            [{"id": "x", "title": "open", "status": 0}],
            [{"id": "x", "title": "completed", "status": 2}],
        )
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["title"], "completed")

    @patch("ticktick_cli.commands.tasks._get_completed_tasks_from_private_api", return_value=None)
    @patch("ticktick_cli.commands.tasks._get_all_tasks", return_value=TASKS)
    @patch("ticktick_cli.commands.tasks._get_projects", return_value=[{"id": "p"}])
    @patch("ticktick_cli.commands.tasks.get_open_api", return_value=object())
    def test_collect_due_tasks_all_falls_back_to_open_when_private_unavailable(
        self,
        _mock_open_api,
        _mock_projects,
        _mock_all_tasks,
        _mock_completed,
    ):
        out = _collect_due_tasks_for_status(
            mode="strict",
            status_filter="all",
            target_date=date(2026, 3, 15),
        )
        self.assertEqual([t["id"] for t in out], ["a"])

    @patch("ticktick_cli.commands.tasks._get_completed_tasks_from_private_api", return_value=None)
    def test_collect_due_tasks_completed_returns_none_when_private_unavailable(self, _mock_completed):
        out = _collect_due_tasks_for_status(
            mode="strict",
            status_filter="completed",
            target_date=date(2026, 3, 15),
        )
        self.assertIsNone(out)


if __name__ == "__main__":
    unittest.main()
