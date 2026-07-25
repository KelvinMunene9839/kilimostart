"""Mock data provider standing in for KilimoSmart's soil, weather, and market
data feeds. A real deployment would replace this with soil-lab APIs, a
weather service, and live market-price feeds; the rest of the app only
depends on the methods below, so swapping the backend later needs no
changes elsewhere.
"""

import random
from datetime import date

from kilimosmart.models import Crop, MarketPrice, SoilProfile, WeatherForecast

REGIONS = ["Kericho", "Nakuru", "Machakos", "Kitale", "Kisumu"]

_SOIL_PROFILES = {
    "Kericho": SoilProfile("Kericho", ph=5.6, nitrogen="high", phosphorus="medium", potassium="high", texture="clay loam"),
    "Nakuru": SoilProfile("Nakuru", ph=6.4, nitrogen="medium", phosphorus="medium", potassium="medium", texture="volcanic loam"),
    "Machakos": SoilProfile("Machakos", ph=6.8, nitrogen="low", phosphorus="low", potassium="medium", texture="sandy loam"),
    "Kitale": SoilProfile("Kitale", ph=6.0, nitrogen="high", phosphorus="high", potassium="medium", texture="loam"),
    "Kisumu": SoilProfile("Kisumu", ph=5.9, nitrogen="medium", phosphorus="medium", potassium="low", texture="clay"),
}

_WEATHER = {
    "Kericho": WeatherForecast("Kericho", rainfall_mm=180, avg_temp_c=18, outlook="favorable", season="long rains"),
    "Nakuru": WeatherForecast("Nakuru", rainfall_mm=90, avg_temp_c=20, outlook="moderate", season="short rains"),
    "Machakos": WeatherForecast("Machakos", rainfall_mm=45, avg_temp_c=24, outlook="poor", season="dry spell"),
    "Kitale": WeatherForecast("Kitale", rainfall_mm=160, avg_temp_c=19, outlook="favorable", season="long rains"),
    "Kisumu": WeatherForecast("Kisumu", rainfall_mm=110, avg_temp_c=26, outlook="moderate", season="short rains"),
}

_CROP_CATALOG = [
    Crop("Maize", "cereal", ph_min=5.5, ph_max=7.0, water_need_mm=120, maturity_days=120, base_yield_kg_per_acre=900, production_cost_per_acre=9000),
    Crop("Beans", "legume", ph_min=6.0, ph_max=7.5, water_need_mm=90, maturity_days=90, base_yield_kg_per_acre=500, production_cost_per_acre=6000),
    Crop("Sorghum", "cereal", ph_min=5.5, ph_max=7.5, water_need_mm=60, maturity_days=110, base_yield_kg_per_acre=700, production_cost_per_acre=5000),
    Crop("Cassava", "tuber", ph_min=5.0, ph_max=6.5, water_need_mm=50, maturity_days=270, base_yield_kg_per_acre=4000, production_cost_per_acre=7000),
    Crop("Sweet Potato", "tuber", ph_min=5.5, ph_max=6.8, water_need_mm=70, maturity_days=120, base_yield_kg_per_acre=3500, production_cost_per_acre=6500),
    Crop("Tea", "cash crop", ph_min=4.5, ph_max=6.0, water_need_mm=170, maturity_days=730, base_yield_kg_per_acre=1200, production_cost_per_acre=15000),
    Crop("Avocado", "cash crop", ph_min=6.0, ph_max=7.0, water_need_mm=140, maturity_days=1095, base_yield_kg_per_acre=2000, production_cost_per_acre=12000),
    Crop("Tomatoes", "vegetable", ph_min=6.0, ph_max=6.8, water_need_mm=100, maturity_days=80, base_yield_kg_per_acre=8000, production_cost_per_acre=20000),
    Crop("Kale (Sukuma Wiki)", "vegetable", ph_min=6.0, ph_max=7.5, water_need_mm=90, maturity_days=60, base_yield_kg_per_acre=6000, production_cost_per_acre=8000),
    Crop("Green Grams", "legume", ph_min=6.2, ph_max=7.2, water_need_mm=40, maturity_days=75, base_yield_kg_per_acre=450, production_cost_per_acre=4500),
    Crop("Sunflower", "oilseed", ph_min=6.0, ph_max=7.5, water_need_mm=55, maturity_days=100, base_yield_kg_per_acre=650, production_cost_per_acre=5500),
    Crop("Groundnuts", "legume", ph_min=5.5, ph_max=6.5, water_need_mm=65, maturity_days=100, base_yield_kg_per_acre=800, production_cost_per_acre=6000),
]

_BASE_PRICES = {
    "Maize": 45, "Beans": 110, "Sorghum": 55, "Cassava": 30, "Sweet Potato": 35,
    "Tea": 60, "Avocado": 80, "Tomatoes": 40, "Kale (Sukuma Wiki)": 25,
    "Green Grams": 130, "Sunflower": 70, "Groundnuts": 140,
}


class MockDataProvider:
    """Serves soil, weather, crop, and market data.

    Market prices are perturbed with a day-seeded random walk so figures
    feel 'live' while staying identical for every user checking on the
    same day (and reproducible for grading/demo purposes).
    """

    def __init__(self, seed_date: date | None = None):
        self._seed_date = seed_date or date.today()

    def regions(self) -> list[str]:
        return list(REGIONS)

    def soil_profile(self, region: str) -> SoilProfile:
        return _SOIL_PROFILES[region]

    def weather_forecast(self, region: str) -> WeatherForecast:
        return _WEATHER[region]

    def crop_catalog(self) -> list[Crop]:
        return list(_CROP_CATALOG)

    def market_prices(self) -> list[MarketPrice]:
        prices = []
        for crop_name, base_price in _BASE_PRICES.items():
            rng = random.Random(f"{self._seed_date.isoformat()}-{crop_name}")
            fluctuation = rng.uniform(-0.08, 0.08)
            price = round(base_price * (1 + fluctuation), 2)
            trend = "rising" if fluctuation > 0.02 else "falling" if fluctuation < -0.02 else "stable"
            prices.append(MarketPrice(crop_name, price, trend))
        return prices

    def market_price_for(self, crop_name: str) -> MarketPrice:
        for price in self.market_prices():
            if price.crop_name == crop_name:
                return price
        raise KeyError(f"No market price found for {crop_name}")
