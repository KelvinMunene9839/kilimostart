import tempfile
import unittest
from datetime import date
from pathlib import Path

from kilimosmart.models import Farmer, RecommendationLog
from kilimosmart.repository import FarmerRepository


class FarmerRepositoryTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.repo = FarmerRepository(Path(self._tmpdir.name) / "farmers.json")

    def tearDown(self):
        self._tmpdir.cleanup()

    def test_save_and_get_round_trip(self):
        farmer = Farmer(phone="0700111222", name="Amina", region="Kisumu", farm_size_acres=3.0, sms_opt_in=True)
        self.repo.save(farmer)

        fetched = self.repo.get("0700111222")

        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Amina")
        self.assertTrue(fetched.sms_opt_in)

    def test_exists_false_for_unknown_phone(self):
        self.assertFalse(self.repo.exists("0700000000"))

    def test_history_is_capped_and_ordered(self):
        phone = "0700111222"
        for i in range(15):
            self.repo.add_history(phone, RecommendationLog(
                timestamp=f"2026-01-{i + 1:02d}T00:00:00",
                region="Kericho",
                farm_size_acres=1.0,
                top_crop="Maize",
                score=0.5,
                estimated_profit=1000.0,
            ))

        history = self.repo.get_history(phone)

        self.assertEqual(len(history), 10)
        self.assertEqual(history[-1].timestamp, "2026-01-15T00:00:00")


if __name__ == "__main__":
    unittest.main()
