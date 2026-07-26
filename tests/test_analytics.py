import unittest

from kilimosmart.analytics import PlatformAnalytics
from kilimosmart.models import Farmer, RecommendationLog
from tests.db_helpers import clear_test_db, new_test_repository


class PlatformAnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.repo = new_test_repository()
        self.analytics = PlatformAnalytics(self.repo)

    def tearDown(self):
        clear_test_db()

    def test_summary_with_no_farmers(self):
        self.assertEqual(self.analytics.summary(), "No farmers registered yet.")

    def test_summary_reports_counts_and_top_crop(self):
        farmer1 = Farmer("0700000001", "A", "Kericho", 1.0, sms_opt_in=True)
        farmer2 = Farmer("0700000002", "B", "Kericho", 2.0, sms_opt_in=False)
        self.repo.save(farmer1)
        self.repo.save(farmer2)
        self.repo.add_history(farmer1.id, RecommendationLog("2026-01-01T00:00:00", "Kericho", 1.0, "Maize", 0.8, 1000.0))
        self.repo.add_history(farmer2.id, RecommendationLog("2026-01-02T00:00:00", "Kericho", 2.0, "Maize", 0.7, 2000.0))

        summary = self.analytics.summary()

        self.assertIn("Registered farmers: 2", summary)
        self.assertIn("SMS opt-in rate: 1/2 (50%)", summary)
        self.assertIn("Kericho: 2", summary)
        self.assertIn("Maize: 2 time(s)", summary)


if __name__ == "__main__":
    unittest.main()
