"""Simulates a USSD session (Africa's Talking style CON/END screens) over
the terminal, so the CLI behaves like what a feature-phone user would see
dialing a short code such as *384*7#.
"""

from kilimosmart.data_store import MockDataProvider
from kilimosmart.models import Farmer
from kilimosmart.recommendation import RecommendationEngine
from kilimosmart.repository import FarmerRepository

MAIN_MENU = "menu"
REGISTER_NAME = "register_name"
REGISTER_REGION = "register_region"
REGISTER_SIZE = "register_size"
RECOMMEND_REGION = "recommend_region"
RECOMMEND_SIZE = "recommend_size"
WEATHER_REGION = "weather_region"
MARKET_PRICES = "market_prices"
PROFILE = "profile"
DONE = "done"


class USSDSession:
    """One simulated *384# dialog. Call `handle(input)` per screen and print
    the returned text, exactly like a real USSD gateway request/response.
    """

    def __init__(self, phone: str, repo: FarmerRepository, data: MockDataProvider, engine: RecommendationEngine):
        self._phone = phone
        self._repo = repo
        self._data = data
        self._engine = engine
        self._state = MAIN_MENU
        self._pending: dict = {}

    def start(self) -> str:
        return self._main_menu_screen()

    def handle(self, text: str) -> str:
        text = text.strip()
        handler = getattr(self, f"_handle_{self._state}")
        return handler(text)

    def is_done(self) -> bool:
        return self._state == DONE

    # -- Screens -----------------------------------------------------

    def _main_menu_screen(self) -> str:
        return (
            "CON Welcome to KilimoSmart\n"
            "1. Register / update my farm\n"
            "2. Get crop recommendation\n"
            "3. View weather forecast\n"
            "4. View market prices\n"
            "5. My farm profile\n"
            "0. Exit"
        )

    def _handle_menu(self, choice: str) -> str:
        if choice == "1":
            self._state = REGISTER_NAME
            return "CON Enter your full name:"
        if choice == "2":
            if not self._repo.exists(self._phone):
                self._state = DONE
                return "END You must register first (option 1)."
            self._state = RECOMMEND_REGION
            return self._region_prompt()
        if choice == "3":
            self._state = WEATHER_REGION
            return self._region_prompt()
        if choice == "4":
            self._state = DONE
            return self._market_prices_screen()
        if choice == "5":
            self._state = DONE
            return self._profile_screen()
        if choice == "0":
            self._state = DONE
            return "END Asante for using KilimoSmart. Kwaheri!"
        return "CON Invalid choice.\n" + self._main_menu_screen().replace("CON ", "")

    def _region_prompt(self) -> str:
        options = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(self._data.regions()))
        return f"CON Choose your region:\n{options}"

    def _region_from_choice(self, choice: str) -> str | None:
        regions = self._data.regions()
        if choice.isdigit() and 1 <= int(choice) <= len(regions):
            return regions[int(choice) - 1]
        return None

    # -- Registration --

    def _handle_register_name(self, name: str) -> str:
        if not name:
            return "CON Name cannot be empty. Enter your full name:"
        self._pending["name"] = name
        self._state = REGISTER_REGION
        return self._region_prompt()

    def _handle_register_region(self, choice: str) -> str:
        region = self._region_from_choice(choice)
        if not region:
            return "CON Invalid region.\n" + self._region_prompt().replace("CON ", "")
        self._pending["region"] = region
        self._state = REGISTER_SIZE
        return "CON Enter your farm size in acres (e.g. 2.5):"

    def _handle_register_size(self, size_text: str) -> str:
        try:
            size = float(size_text)
            if size <= 0:
                raise ValueError
        except ValueError:
            return "CON Invalid size. Enter your farm size in acres (e.g. 2.5):"
        farmer = Farmer(phone=self._phone, name=self._pending["name"], region=self._pending["region"], farm_size_acres=size)
        self._repo.save(farmer)
        self._state = DONE
        return f"END Registered {farmer.name} in {farmer.region} ({farmer.farm_size_acres} acres). Dial in again for recommendations."

    # -- Recommendation --

    def _handle_recommend_region(self, choice: str) -> str:
        region = self._region_from_choice(choice)
        if not region:
            return "CON Invalid region.\n" + self._region_prompt().replace("CON ", "")
        self._pending["region"] = region
        farmer = self._repo.get(self._phone)
        self._pending["size"] = farmer.farm_size_acres
        return self._recommendation_screen()

    def _recommendation_screen(self) -> str:
        region = self._pending["region"]
        size = self._pending["size"]
        results = self._engine.recommend(region, size, top_n=3)
        lines = [f"END Top crops for {region} ({size} acres):"]
        for i, rec in enumerate(results, start=1):
            lines.append(f"{i}. {rec.crop.name} - score {rec.score:.0%} - {rec.reasoning}")
        self._state = DONE
        return "\n".join(lines)

    # -- Weather --

    def _handle_weather_region(self, choice: str) -> str:
        region = self._region_from_choice(choice)
        if not region:
            return "CON Invalid region.\n" + self._region_prompt().replace("CON ", "")
        forecast = self._data.weather_forecast(region)
        self._state = DONE
        return (
            f"END Weather for {region}:\n"
            f"Rainfall: {forecast.rainfall_mm}mm | Avg temp: {forecast.avg_temp_c}C\n"
            f"Outlook: {forecast.outlook} ({forecast.season})"
        )

    # -- Market prices / profile (single-screen, no further input) --

    def _market_prices_screen(self) -> str:
        lines = ["END Today's market prices (KES/kg):"]
        for price in self._data.market_prices():
            lines.append(f"{price.crop_name}: {price.price_per_kg} ({price.trend})")
        return "\n".join(lines)

    def _profile_screen(self) -> str:
        farmer = self._repo.get(self._phone)
        if not farmer:
            return "END No profile found. Register first (option 1)."
        return (
            f"END Farm profile:\n"
            f"Name: {farmer.name}\n"
            f"Region: {farmer.region}\n"
            f"Size: {farmer.farm_size_acres} acres\n"
            f"Registered: {farmer.registered_on}"
        )
