"""Profit-optimized crop recommendation logic."""

from kilimosmart.data_store import MockDataProvider
from kilimosmart.models import Recommendation

SOIL_WEIGHT = 0.3
WATER_WEIGHT = 0.3
PROFIT_WEIGHT = 0.4


class RecommendationEngine:
    def __init__(self, data_provider: MockDataProvider):
        self._data = data_provider

    def recommend(self, region: str, farm_size_acres: float, top_n: int = 3) -> list[Recommendation]:
        soil = self._data.soil_profile(region)
        weather = self._data.weather_forecast(region)
        crops = self._data.crop_catalog()
        prices = {p.crop_name: p for p in self._data.market_prices()}

        profits = {}
        for crop in crops:
            price = prices[crop.name].price_per_kg
            revenue = crop.base_yield_kg_per_acre * price * farm_size_acres
            cost = crop.production_cost_per_acre * farm_size_acres
            profits[crop.name] = revenue - cost

        max_profit = max(profits.values()) or 1
        min_profit = min(profits.values())
        profit_range = (max_profit - min_profit) or 1

        scored = []
        for crop in crops:
            soil_score = crop.ph_fit(soil.ph)
            water_score = crop.water_fit(weather.rainfall_mm)
            profit_score = (profits[crop.name] - min_profit) / profit_range

            total_score = (
                soil_score * SOIL_WEIGHT
                + water_score * WATER_WEIGHT
                + profit_score * PROFIT_WEIGHT
            )

            reasoning = (
                f"soil pH fit {soil_score:.0%}, rainfall fit {water_score:.0%}, "
                f"est. profit KES {profits[crop.name]:,.0f} over {crop.maturity_days} days"
            )
            scored.append(Recommendation(crop, total_score, profits[crop.name], reasoning))

        scored.sort(key=lambda r: r.score, reverse=True)
        return scored[:top_n]
