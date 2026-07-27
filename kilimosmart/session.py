"""Simulates a USSD session (Africa's Talking style CON/END screens) over
the terminal, so the CLI behaves like what a feature-phone user would see
dialing a short code such as *384*7#.
"""

from datetime import datetime

from kilimosmart.data_store import MockDataProvider
from kilimosmart.models import Farmer, RecommendationLog
from kilimosmart.recommendation import RecommendationEngine
from kilimosmart.repository import FarmerRepository
from kilimosmart.sms import SMSSimulator

DROUGHT_TOLERANT_THRESHOLD_MM = 60

MAIN_MENU = "menu"
REGISTER_CHOICE = "register_choice"
REGISTER_SELECT_FARM = "register_select_farm"
DELETE_SELECT_FARM = "delete_select_farm"
DELETE_CONFIRM = "delete_confirm"
PROFILE_SELECT_FARM = "profile_select_farm"
REGISTER_NAME = "register_name"
REGISTER_REGION = "register_region"
REGISTER_SIZE = "register_size"
REGISTER_SMS = "register_sms"
RECOMMEND_SELECT_FARM = "recommend_select_farm"
WEATHER_REGION = "weather_region"
TOGGLE_SELECT_FARM = "toggle_select_farm"
TOGGLE_SMS = "toggle_sms"
DONE = "done"


class USSDSession:
    """One simulated *384# dialog. Call `handle(input)` per screen and print
    the returned text, exactly like a real USSD gateway request/response.

    A phone number can own several farms, so any action that targets one
    farm (register-update, recommend, toggle SMS) asks the caller to pick
    which farm when more than one is registered.
    """

    def __init__(
        self,
        phone: str,
        repo: FarmerRepository,
        data: MockDataProvider,
        engine: RecommendationEngine,
        sms: SMSSimulator | None = None,
    ):
        self._phone = phone
        self._repo = repo
        self._data = data
        self._engine = engine
        self._sms = sms or SMSSimulator()
        self._state = MAIN_MENU
        self._pending: dict = {}
        # Each entry is (state, pending snapshot, zero-arg re-render callable)
        # for the screen being left, pushed just before moving forward so
        # "0. Back" can restore that exact screen and its in-progress data.
        self._history: list[tuple[str, dict, callable]] = []

    def start(self) -> str:
        return self._main_menu_screen()

    def handle(self, text: str) -> str:
        text = text.strip()
        if text == "0" and self._state != MAIN_MENU and self._history:
            return self._go_back()
        handler = getattr(self, f"_handle_{self._state}")
        return handler(text)

    def is_done(self) -> bool:
        return self._state == DONE

    # -- Navigation history -------------------------------------------

    def _push(self, render) -> None:
        self._history.append((self._state, dict(self._pending), render))

    def _go_back(self) -> str:
        state, pending, render = self._history.pop()
        self._state = state
        self._pending = pending
        return render()

    # -- Screens -----------------------------------------------------

    def _main_menu_screen(self) -> str:
        farms = self._repo.get_by_phone(self._phone)
        sms_line = ""
        if len(farms) == 1:
            sms_line = f"6. SMS alerts: turn {'off' if farms[0].sms_opt_in else 'on'}\n"
        elif len(farms) > 1:
            sms_line = "6. Toggle SMS alerts for a farm\n"
        return (
            "CON Welcome to KilimoSmart\n"
            "1. Register / update my farm\n"
            "2. Get crop recommendation\n"
            "3. View weather forecast\n"
            "4. View market prices\n"
            "5. My farm profile\n"
            f"{sms_line}"
            "0. Exit"
        )

    def _handle_menu(self, choice: str) -> str:
        if choice == "1":
            self._push(self._main_menu_screen)
            return self._start_registration()
        if choice == "2":
            self._push(self._main_menu_screen)
            return self._start_recommendation()
        if choice == "3":
            self._push(self._main_menu_screen)
            self._state = WEATHER_REGION
            return self._region_prompt()
        if choice == "4":
            self._state = DONE
            return self._market_prices_screen()
        if choice == "5":
            self._push(self._main_menu_screen)
            return self._start_profile()
        if choice == "6" and self._repo.exists_for_phone(self._phone):
            self._push(self._main_menu_screen)
            return self._start_toggle()
        if choice == "0":
            self._state = DONE
            return "END Asante for using KilimoSmart. Kwaheri!"
        return "CON Invalid choice.\n" + self._main_menu_screen().replace("CON ", "")

    def _region_prompt(self) -> str:
        options = "\n".join(f"{i + 1}. {r}" for i, r in enumerate(self._data.regions()))
        return f"CON Choose your region:\n{options}\n0. Back"

    def _region_from_choice(self, choice: str) -> str | None:
        regions = self._data.regions()
        if choice.isdigit() and 1 <= int(choice) <= len(regions):
            return regions[int(choice) - 1]
        return None

    def _farm_list_prompt(self, farms: list[Farmer], title: str) -> str:
        options = "\n".join(
            f"{i + 1}. {f.name} - {f.region} ({f.farm_size_acres} acres)" for i, f in enumerate(farms)
        )
        return f"CON {title}\n{options}\n0. Back"

    def _farm_from_choice(self, choice: str, farms: list[Farmer]) -> Farmer | None:
        if choice.isdigit() and 1 <= int(choice) <= len(farms):
            return farms[int(choice) - 1]
        return None

    # -- Registration --

    def _register_choice_screen(self) -> str:
        farms = self._repo.get_by_phone(self._phone)
        return (
            f"CON You have {len(farms)} farm(s) registered.\n"
            "1. Register a new farm\n"
            "2. Update an existing farm\n"
            "3. Delete a farm\n"
            "0. Back"
        )

    def _register_name_prompt(self) -> str:
        return "CON Enter your full name:\n0. Back"

    def _register_size_prompt(self) -> str:
        return "CON Enter your farm size in acres (e.g. 2.5):\n0. Back"

    def _register_sms_prompt(self) -> str:
        return "CON Opt in to free SMS alerts (weather + price warnings)?\n1. Yes\n2. No\n0. Back"

    def _start_registration(self) -> str:
        farms = self._repo.get_by_phone(self._phone)
        if not farms:
            self._pending = {}
            self._state = REGISTER_NAME
            return self._register_name_prompt()
        self._state = REGISTER_CHOICE
        return self._register_choice_screen()

    def _handle_register_choice(self, choice: str) -> str:
        if choice not in ("1", "2", "3"):
            return "CON Invalid choice.\n" + self._register_choice_screen().replace("CON ", "")
        self._push(self._register_choice_screen)
        if choice == "1":
            farms = self._repo.get_by_phone(self._phone)
            self._pending = {"name": farms[0].name}
            self._state = REGISTER_REGION
            return self._region_prompt()
        if choice == "2":
            farms = self._repo.get_by_phone(self._phone)
            if len(farms) == 1:
                return self._begin_farm_update(farms[0])
            self._state = REGISTER_SELECT_FARM
            return self._farm_list_prompt(farms, "Choose a farm to update:")
        farms = self._repo.get_by_phone(self._phone)
        if len(farms) == 1:
            return self._begin_farm_delete(farms[0])
        self._state = DELETE_SELECT_FARM
        return self._farm_list_prompt(farms, "Choose a farm to delete:")

    def _handle_register_select_farm(self, choice: str) -> str:
        farms = self._repo.get_by_phone(self._phone)
        farm = self._farm_from_choice(choice, farms)
        if not farm:
            return "CON Invalid choice.\n" + self._farm_list_prompt(farms, "Choose a farm to update:").replace("CON ", "")
        self._push(lambda: self._farm_list_prompt(self._repo.get_by_phone(self._phone), "Choose a farm to update:"))
        return self._begin_farm_update(farm)

    def _begin_farm_update(self, farm: Farmer) -> str:
        self._pending = {"farm_id": farm.id, "registered_on": farm.registered_on}
        self._state = REGISTER_NAME
        return self._register_name_prompt()

    def _handle_delete_select_farm(self, choice: str) -> str:
        farms = self._repo.get_by_phone(self._phone)
        farm = self._farm_from_choice(choice, farms)
        if not farm:
            return "CON Invalid choice.\n" + self._farm_list_prompt(farms, "Choose a farm to delete:").replace("CON ", "")
        self._push(lambda: self._farm_list_prompt(self._repo.get_by_phone(self._phone), "Choose a farm to delete:"))
        return self._begin_farm_delete(farm)

    def _delete_confirm_prompt(self, farm: Farmer) -> str:
        return (
            f"CON Delete {farm.name}'s farm in {farm.region} ({farm.farm_size_acres} acres)?\n"
            "This cannot be undone.\n"
            "1. Yes, delete\n"
            "2. No, cancel\n"
            "0. Back"
        )

    def _begin_farm_delete(self, farm: Farmer) -> str:
        self._pending = {"farm_id": farm.id}
        self._state = DELETE_CONFIRM
        return self._delete_confirm_prompt(farm)

    def _handle_delete_confirm(self, choice: str) -> str:
        farmer = self._repo.get(self._pending["farm_id"])
        if choice == "1":
            self._repo.delete(farmer.id)
            self._state = DONE
            return f"END Deleted {farmer.name}'s farm in {farmer.region}."
        if choice == "2":
            self._state = DONE
            return "END Deletion cancelled."
        return "CON Invalid choice.\n" + self._delete_confirm_prompt(farmer).replace("CON ", "")

    def _handle_register_name(self, name: str) -> str:
        if not name:
            return "CON Name cannot be empty.\n" + self._register_name_prompt().replace("CON ", "")
        self._push(self._register_name_prompt)
        self._pending["name"] = name
        self._state = REGISTER_REGION
        return self._region_prompt()

    def _handle_register_region(self, choice: str) -> str:
        region = self._region_from_choice(choice)
        if not region:
            return "CON Invalid region.\n" + self._region_prompt().replace("CON ", "")
        self._push(self._region_prompt)
        self._pending["region"] = region
        self._state = REGISTER_SIZE
        return self._register_size_prompt()

    def _handle_register_size(self, size_text: str) -> str:
        try:
            size = float(size_text)
            if size <= 0:
                raise ValueError
        except ValueError:
            return "CON Invalid size.\n" + self._register_size_prompt().replace("CON ", "")
        self._push(self._register_size_prompt)
        self._pending["size"] = size
        self._state = REGISTER_SMS
        return self._register_sms_prompt()

    def _handle_register_sms(self, choice: str) -> str:
        if choice not in ("1", "2"):
            return "CON Invalid choice.\n" + self._register_sms_prompt().replace("CON ", "")
        is_update = "farm_id" in self._pending
        farmer = Farmer(
            phone=self._phone,
            name=self._pending["name"],
            region=self._pending["region"],
            farm_size_acres=self._pending["size"],
            sms_opt_in=(choice == "1"),
            id=self._pending.get("farm_id"),
        )
        if "registered_on" in self._pending:
            farmer.registered_on = self._pending["registered_on"]
        self._repo.save(farmer)
        self._state = DONE
        action = "Updated" if is_update else "Registered"
        return (
            f"END {action} {farmer.name}'s farm in {farmer.region} "
            f"({farmer.farm_size_acres} acres). Dial in again for recommendations."
        )

    # -- Recommendation --

    def _start_recommendation(self) -> str:
        farms = self._repo.get_by_phone(self._phone)
        if not farms:
            self._state = DONE
            return "END You must register first (option 1)."
        if len(farms) == 1:
            return self._recommendation_screen(farms[0])
        self._state = RECOMMEND_SELECT_FARM
        return self._farm_list_prompt(farms, "Choose a farm for this recommendation:")

    def _handle_recommend_select_farm(self, choice: str) -> str:
        farms = self._repo.get_by_phone(self._phone)
        farm = self._farm_from_choice(choice, farms)
        if not farm:
            return "CON Invalid choice.\n" + self._farm_list_prompt(
                farms, "Choose a farm for this recommendation:"
            ).replace("CON ", "")
        return self._recommendation_screen(farm)

    def _recommendation_screen(self, farmer: Farmer) -> str:
        region = farmer.region
        size = farmer.farm_size_acres
        results = self._engine.recommend(region, size, top_n=3)
        lines = [f"END Top crops for {region} ({size} acres):"]
        for i, rec in enumerate(results, start=1):
            lines.append(f"{i}. {rec.crop.name} - score {rec.score:.0%} - {rec.reasoning}")

        top = results[0]
        self._repo.add_history(farmer.id, RecommendationLog(
            timestamp=datetime.now().isoformat(timespec="seconds"),
            region=region,
            farm_size_acres=size,
            top_crop=top.crop.name,
            score=top.score,
            estimated_profit=top.estimated_profit,
        ))

        if farmer.sms_opt_in:
            self._sms.send(
                self._phone,
                f"KilimoSmart: best crop for {region} is {top.crop.name} "
                f"(est. profit KES {top.estimated_profit:,.0f}). Reply on *384*7# for full list.",
            )

        self._state = DONE
        return "\n".join(lines)

    # -- Weather --

    def _handle_weather_region(self, choice: str) -> str:
        region = self._region_from_choice(choice)
        if not region:
            return "CON Invalid region.\n" + self._region_prompt().replace("CON ", "")
        forecast = self._data.weather_forecast(region)
        lines = [
            f"END Weather for {region}:",
            f"Rainfall: {forecast.rainfall_mm}mm | Avg temp: {forecast.avg_temp_c}C",
            f"Outlook: {forecast.outlook} ({forecast.season})",
        ]
        if forecast.outlook == "poor":
            tolerant = [c.name for c in self._data.crop_catalog() if c.water_need_mm <= DROUGHT_TOLERANT_THRESHOLD_MM]
            lines.append(f"Climate tip: drought risk - consider drought-tolerant crops like {', '.join(tolerant)}.")
            farms = self._repo.get_by_phone(self._phone)
            if any(f.sms_opt_in for f in farms):
                self._sms.send(self._phone, f"KilimoSmart alert: drought risk in {region}. Consider {', '.join(tolerant)}.")
        self._state = DONE
        return "\n".join(lines)

    # -- SMS toggle --

    def _start_toggle(self) -> str:
        farms = self._repo.get_by_phone(self._phone)
        if len(farms) == 1:
            self._pending = {"farm_id": farms[0].id}
            self._state = TOGGLE_SMS
            return self._handle_toggle_sms("")
        self._state = TOGGLE_SELECT_FARM
        return self._farm_list_prompt(farms, "Choose a farm to toggle SMS alerts for:")

    def _handle_toggle_select_farm(self, choice: str) -> str:
        farms = self._repo.get_by_phone(self._phone)
        farm = self._farm_from_choice(choice, farms)
        if not farm:
            return "CON Invalid choice.\n" + self._farm_list_prompt(
                farms, "Choose a farm to toggle SMS alerts for:"
            ).replace("CON ", "")
        self._pending = {"farm_id": farm.id}
        self._state = TOGGLE_SMS
        return self._handle_toggle_sms("")

    def _handle_toggle_sms(self, _choice: str) -> str:
        farmer = self._repo.get(self._pending["farm_id"])
        farmer.sms_opt_in = not farmer.sms_opt_in
        self._repo.save(farmer)
        self._state = DONE
        status = "on" if farmer.sms_opt_in else "off"
        return f"END SMS alerts for {farmer.name}'s farm in {farmer.region} turned {status}."

    # -- Market prices / profile (single-screen, no further input) --

    def _market_prices_screen(self) -> str:
        lines = ["END Today's market prices (KES/kg):"]
        for price in self._data.market_prices():
            lines.append(f"{price.crop_name}: {price.price_per_kg} ({price.trend})")
        return "\n".join(lines)

    def _start_profile(self) -> str:
        farms = self._repo.get_by_phone(self._phone)
        if not farms:
            self._state = DONE
            return "END No profile found. Register first (option 1)."
        if len(farms) == 1:
            self._state = DONE
            return self._profile_screen(farms[0])
        self._state = PROFILE_SELECT_FARM
        return self._farm_list_prompt(farms, "Choose a farm to view:")

    def _handle_profile_select_farm(self, choice: str) -> str:
        farms = self._repo.get_by_phone(self._phone)
        farm = self._farm_from_choice(choice, farms)
        if not farm:
            return "CON Invalid choice.\n" + self._farm_list_prompt(farms, "Choose a farm to view:").replace("CON ", "")
        self._state = DONE
        return self._profile_screen(farm)

    def _profile_screen(self, farmer: Farmer) -> str:
        lines = [
            "END Farm profile:",
            f"Name: {farmer.name}",
            f"Region: {farmer.region}",
            f"Size: {farmer.farm_size_acres} acres",
            f"SMS alerts: {'on' if farmer.sms_opt_in else 'off'}",
            f"Registered: {farmer.registered_on}",
        ]
        history = self._repo.get_history(farmer.id)
        if history:
            lines.append("Recent recommendations:")
            for entry in reversed(history[-3:]):
                lines.append(f"- {entry.timestamp}: {entry.top_crop} in {entry.region} (score {entry.score:.0%})")
        return "\n".join(lines)
