import tempfile
import unittest
from datetime import date
from pathlib import Path

from kilimosmart.data_store import MockDataProvider
from kilimosmart.recommendation import RecommendationEngine
from kilimosmart.repository import FarmerRepository
from kilimosmart.session import USSDSession
from kilimosmart.sms import SMSSimulator

PHONE = "0700111222"


class USSDSessionTests(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.repo = FarmerRepository(Path(self._tmpdir.name) / "farmers.json")
        self.data = MockDataProvider(seed_date=date(2026, 1, 1))
        self.engine = RecommendationEngine(self.data)
        self.sms = SMSSimulator()

    def tearDown(self):
        self._tmpdir.cleanup()

    def _new_session(self) -> USSDSession:
        return USSDSession(PHONE, self.repo, self.data, self.engine, self.sms)

    def _register(self, session: USSDSession, sms_choice="1") -> None:
        session.handle("1")
        session.handle("Amina Hassan")
        session.handle("1")  # Kericho
        session.handle("2.0")
        session.handle(sms_choice)

    def test_registration_flow_saves_farmer(self):
        session = self._new_session()
        session.start()
        self._register(session)

        farmer = self.repo.get(PHONE)
        self.assertIsNotNone(farmer)
        self.assertEqual(farmer.name, "Amina Hassan")
        self.assertEqual(farmer.region, "Kericho")
        self.assertTrue(farmer.sms_opt_in)
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
        session2.handle("2")
        result = session2.handle("1")  # Kericho

        self.assertTrue(result.startswith("END"))
        history = self.repo.get_history(PHONE)
        self.assertEqual(len(history), 1)
        self.assertEqual(len(self.sms.sent), 1)
        self.assertEqual(self.sms.sent[0][0], PHONE)

    def test_toggle_sms_flips_opt_in(self):
        session = self._new_session()
        session.start()
        self._register(session, sms_choice="2")
        self.assertFalse(self.repo.get(PHONE).sms_opt_in)

        session2 = self._new_session()
        session2.start()
        session2.handle("6")

        self.assertTrue(self.repo.get(PHONE).sms_opt_in)


if __name__ == "__main__":
    unittest.main()
