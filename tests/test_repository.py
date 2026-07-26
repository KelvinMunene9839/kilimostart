import unittest

from kilimosmart.models import Farmer, RecommendationLog
from tests.db_helpers import clear_test_db, new_test_repository


class FarmerRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.repo = new_test_repository()

    def tearDown(self):
        clear_test_db()

    def test_save_and_get_round_trip(self):
        farmer = Farmer(phone="0700111222", name="Amina", region="Kisumu", farm_size_acres=3.0, sms_opt_in=True)
        self.repo.save(farmer)

        fetched = self.repo.get(farmer.id)

        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.name, "Amina")
        self.assertTrue(fetched.sms_opt_in)

    def test_exists_false_for_unknown_phone(self):
        self.assertFalse(self.repo.exists_for_phone("0700000000"))

    def test_get_by_phone_returns_all_farms_for_that_number(self):
        phone = "0700111222"
        self.repo.save(Farmer(phone=phone, name="Amina", region="Kisumu", farm_size_acres=3.0))
        self.repo.save(Farmer(phone=phone, name="Amina", region="Machakos", farm_size_acres=1.5))

        farms = self.repo.get_by_phone(phone)

        self.assertEqual(len(farms), 2)
        self.assertEqual({f.region for f in farms}, {"Kisumu", "Machakos"})

    def test_save_with_id_updates_existing_farm_instead_of_inserting(self):
        farmer = Farmer(phone="0700111222", name="Amina", region="Kisumu", farm_size_acres=3.0)
        self.repo.save(farmer)

        farmer.farm_size_acres = 5.0
        self.repo.save(farmer)

        farms = self.repo.get_by_phone("0700111222")
        self.assertEqual(len(farms), 1)
        self.assertEqual(farms[0].farm_size_acres, 5.0)

    def test_history_is_capped_and_ordered(self):
        farmer = Farmer(phone="0700111222", name="Amina", region="Kericho", farm_size_acres=1.0)
        self.repo.save(farmer)
        for i in range(15):
            self.repo.add_history(farmer.id, RecommendationLog(
                timestamp=f"2026-01-{i + 1:02d}T00:00:00",
                region="Kericho",
                farm_size_acres=1.0,
                top_crop="Maize",
                score=0.5,
                estimated_profit=1000.0,
            ))

        history = self.repo.get_history(farmer.id)

        self.assertEqual(len(history), 10)
        self.assertEqual(history[-1].timestamp, "2026-01-15T00:00:00")


if __name__ == "__main__":
    unittest.main()
