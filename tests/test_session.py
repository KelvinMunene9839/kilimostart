import unittest
from datetime import date

from kilimosmart.data_store import MockDataProvider
from kilimosmart.recommendation import RecommendationEngine
from kilimosmart.session import USSDSession
from kilimosmart.sms import SMSSimulator
from tests.db_helpers import clear_test_db, new_test_repository

PHONE = "0700111222"


class USSDSessionTests(unittest.TestCase):
    def setUp(self):
        self.repo = new_test_repository()
        self.data = MockDataProvider(seed_date=date(2026, 1, 1))
        self.engine = RecommendationEngine(self.data)
        self.sms = SMSSimulator()

    def tearDown(self):
        clear_test_db()

    def _new_session(self) -> USSDSession:
        return USSDSession(PHONE, self.repo, self.data, self.engine, self.sms)

    def _register(self, session: USSDSession, region_choice="1", size="2.0", sms_choice="1", name="Amina Hassan") -> None:
        session.handle("1")
        session.handle(name)
        session.handle(region_choice)  # 1 = Kericho, 3 = Machakos
        session.handle(size)
        session.handle(sms_choice)

    def _add_second_farm(self, session: USSDSession, region_choice="3", size="1.0", sms_choice="2") -> None:
        """Register another farm for a phone that already has one. The name
        is carried over automatically, so this flow skips straight to region."""
        session.handle("1")  # existing farm(s) -> choice screen
        session.handle("1")  # register a new farm
        session.handle(region_choice)  # 3 = Machakos
        session.handle(size)
        session.handle(sms_choice)

    def test_registration_flow_saves_farmer(self):
        session = self._new_session()
        session.start()
        self._register(session)

        farms = self.repo.get_by_phone(PHONE)
        self.assertEqual(len(farms), 1)
        self.assertEqual(farms[0].name, "Amina Hassan")
        self.assertEqual(farms[0].region, "Kericho")
        self.assertTrue(farms[0].sms_opt_in)
        self.assertTrue(session.is_done())

    def test_recommendation_requires_registration_first(self):
        session = self._new_session()
        session.start()
        result = session.handle("2")

        self.assertTrue(result.startswith("END"))
        self.assertIn("register first", result.lower())

    def test_invalid_menu_choice_stays_on_menu(self):
        session = self._new_session()
        session.start()
        result = session.handle("9")

        self.assertTrue(result.startswith("CON"))
        self.assertFalse(session.is_done())

    def test_recommendation_logs_history_and_sends_sms_when_opted_in(self):
        session = self._new_session()
        session.start()
        self._register(session, sms_choice="1")

        session2 = self._new_session()
        session2.start()
        result = session2.handle("2")

        self.assertTrue(result.startswith("END"))
        farm = self.repo.get_by_phone(PHONE)[0]
        history = self.repo.get_history(farm.id)
        self.assertEqual(len(history), 1)
        self.assertEqual(len(self.sms.sent), 1)
        self.assertEqual(self.sms.sent[0][0], PHONE)

    def test_toggle_sms_flips_opt_in(self):
        session = self._new_session()
        session.start()
        self._register(session, sms_choice="2")
        self.assertFalse(self.repo.get_by_phone(PHONE)[0].sms_opt_in)

        session2 = self._new_session()
        session2.start()
        session2.handle("6")

        self.assertTrue(self.repo.get_by_phone(PHONE)[0].sms_opt_in)

    def test_register_again_offers_new_or_update_choice(self):
        session = self._new_session()
        session.start()
        self._register(session)

        session2 = self._new_session()
        session2.start()
        result = session2.handle("1")

        self.assertTrue(result.startswith("CON"))
        self.assertIn("Register a new farm", result)
        self.assertIn("Update an existing farm", result)

    def test_register_new_farm_adds_second_farm_for_same_phone(self):
        session = self._new_session()
        session.start()
        self._register(session, region_choice="1", name="Amina Hassan")  # Kericho

        session2 = self._new_session()
        session2.start()
        self._add_second_farm(session2)

        farms = self.repo.get_by_phone(PHONE)
        self.assertEqual(len(farms), 2)
        self.assertEqual({f.region for f in farms}, {"Kericho", "Machakos"})
        self.assertTrue(all(f.name == "Amina Hassan" for f in farms))

    def test_update_existing_single_farm_preserves_registered_on(self):
        session = self._new_session()
        session.start()
        self._register(session)
        original_registered_on = self.repo.get_by_phone(PHONE)[0].registered_on

        session2 = self._new_session()
        session2.start()
        session2.handle("1")  # existing farm -> new/update choice
        session2.handle("2")  # update (only one farm, so no selection screen needed)
        session2.handle("Amina Hassan")
        session2.handle("1")  # Kericho
        session2.handle("4.0")  # new size
        session2.handle("1")

        farms = self.repo.get_by_phone(PHONE)
        self.assertEqual(len(farms), 1)
        self.assertEqual(farms[0].farm_size_acres, 4.0)
        self.assertEqual(farms[0].registered_on, original_registered_on)

    def test_profile_shows_all_farms_for_phone(self):
        session = self._new_session()
        session.start()
        self._register(session, region_choice="1", name="Amina Hassan")

        session2 = self._new_session()
        session2.start()
        self._add_second_farm(session2)

        session3 = self._new_session()
        session3.start()
        result = session3.handle("5")

        self.assertIn("Amina Hassan", result)
        self.assertIn("Kericho", result)
        self.assertIn("Machakos", result)

    def test_recommend_prompts_farm_selection_when_multiple_farms(self):
        session = self._new_session()
        session.start()
        self._register(session, region_choice="1", name="Amina Hassan")

        session2 = self._new_session()
        session2.start()
        self._add_second_farm(session2)

        session3 = self._new_session()
        session3.start()
        result = session3.handle("2")

        self.assertTrue(result.startswith("CON"))
        self.assertIn("Kericho", result)
        self.assertIn("Machakos", result)


if __name__ == "__main__":
    unittest.main()
