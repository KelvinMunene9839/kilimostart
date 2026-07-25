import unittest
from datetime import date

from kilimosmart.data_store import MockDataProvider
from kilimosmart.recommendation import RecommendationEngine


class RecommendationEngineTests(unittest.TestCase):
    def setUp(self):
        self.data = MockDataProvider(seed_date=date(2026, 1, 1))
        self.engine = RecommendationEngine(self.data)

    def test_recommend_returns_requested_count_sorted_by_score(self):
        results = self.engine.recommend("Kericho", farm_size_acres=2, top_n=3)
        self.assertEqual(len(results), 3)
        scores = [r.score for r in results]
        self.assertEqual(scores, sorted(scores, reverse=True))

    def test_recommend_favors_drought_tolerant_crop_in_dry_region(self):
        results = self.engine.recommend("Machakos", farm_size_acres=1, top_n=1)
        top_crop = results[0].crop
        forecast = self.data.weather_forecast("Machakos")
        self.assertLessEqual(abs(top_crop.water_need_mm - forecast.rainfall_mm), 80)

    def test_all_catalog_crops_are_scoreable(self):
        results = self.engine.recommend("Nakuru", farm_size_acres=1, top_n=len(self.data.crop_catalog()))
        self.assertEqual(len(results), len(self.data.crop_catalog()))
        for rec in results:
            self.assertGreaterEqual(rec.score, 0.0)
            self.assertLessEqual(rec.score, 1.0)


if __name__ == "__main__":
    unittest.main()
