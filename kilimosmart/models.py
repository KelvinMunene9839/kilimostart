"""Domain models for KilimoSmart."""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class SoilProfile:
    region: str
    ph: float
    nitrogen: str      # low / medium / high
    phosphorus: str
    potassium: str
    texture: str        # e.g. loam, clay, sandy


@dataclass
class WeatherForecast:
    region: str
    rainfall_mm: float
    avg_temp_c: float
    outlook: str         # favorable / moderate / poor
    season: str          # e.g. "long rains", "dry season"


@dataclass
class Crop:
    name: str
    category: str
    ph_min: float
    ph_max: float
    water_need_mm: float
    maturity_days: int
    base_yield_kg_per_acre: float
    production_cost_per_acre: float

    def ph_fit(self, ph: float) -> float:
        """1.0 if ph is inside the crop's ideal range, decaying to 0 outside it."""
        if self.ph_min <= ph <= self.ph_max:
            return 1.0
        span = self.ph_max - self.ph_min
        distance = self.ph_min - ph if ph < self.ph_min else ph - self.ph_max
        return max(0.0, 1.0 - distance / span)

    def water_fit(self, rainfall_mm: float) -> float:
        """1.0 when rainfall matches the crop's water need, decaying as it diverges."""
        if self.water_need_mm == 0:
            return 1.0
        diff_ratio = abs(rainfall_mm - self.water_need_mm) / self.water_need_mm
        return max(0.0, 1.0 - diff_ratio)


@dataclass
class MarketPrice:
    crop_name: str
    price_per_kg: float
    trend: str  # rising / stable / falling


@dataclass
class Recommendation:
    crop: Crop
    score: float
    estimated_profit: float
    reasoning: str


@dataclass
class RecommendationLog:
    """A record of a recommendation session, kept so a farmer can look back
    at what was suggested and when.
    """
    timestamp: str
    region: str
    farm_size_acres: float
    top_crop: str
    score: float
    estimated_profit: float

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "region": self.region,
            "farm_size_acres": self.farm_size_acres,
            "top_crop": self.top_crop,
            "score": self.score,
            "estimated_profit": self.estimated_profit,
        }

    @staticmethod
    def from_dict(data: dict) -> "RecommendationLog":
        return RecommendationLog(**data)


@dataclass
class Farmer:
    """One registered farm. A phone number may own several of these — each
    is its own row, identified by `id` once persisted (`id` is None for a
    farm that hasn't been saved yet).
    """
    phone: str
    name: str
    region: str
    farm_size_acres: float
    sms_opt_in: bool = False
    registered_on: str = field(default_factory=lambda: date.today().isoformat())
    id: int | None = None
