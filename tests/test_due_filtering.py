from datetime import date
import unittest

from ticktick_cli.commands.tasks import _filter_due_tasks


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


if __name__ == "__main__":
    unittest.main()
