from datetime import timedelta, timezone
import unittest

from ticktick_cli.datetime_utils import local_date_yyyy_mm_dd, parse_ticktick_datetime


class TestDateTimeUtils(unittest.TestCase):
    def test_parses_supported_iso_formats(self):
        self.assertIsNotNone(parse_ticktick_datetime("2026-03-15T00:00:00.000Z", target_tz=timezone.utc))
        self.assertIsNotNone(parse_ticktick_datetime("2026-03-15T00:00:00+00:00", target_tz=timezone.utc))
        self.assertIsNotNone(parse_ticktick_datetime("2026-03-15T00:00:00+0000", target_tz=timezone.utc))

    def test_midnight_boundary_in_negative_timezone(self):
        tz_minus_five = timezone(timedelta(hours=-5))
        local_due = local_date_yyyy_mm_dd("2026-03-15T00:30:00+00:00", target_tz=tz_minus_five)
        self.assertEqual(local_due, "2026-03-14")


if __name__ == "__main__":
    unittest.main()
